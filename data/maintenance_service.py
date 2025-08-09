#!/usr/bin/env python3
"""
Сервис поддержания актуальности данных
Автоматически проверяет и обновляет рыночные данные
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set
import asyncpg

from core.logger import setup_logger
from core.config.config_manager import ConfigManager
from core.exceptions import DataLoadError
from data.data_loader import DataLoader

logger = setup_logger("data_maintenance")


class DataMaintenanceService:
    """
    Сервис для автоматического поддержания актуальности данных
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.data_loader = DataLoader(config_manager)
        
        # Конфигурация из config/system.yaml
        self.config = config_manager.get_config().get('data_maintenance', {})
        self.enabled = self.config.get('enabled', True)
        self.update_interval = self.config.get('update_interval_minutes', 5) * 60
        self.max_data_age = self.config.get('max_data_age_minutes', 60)
        self.parallel_symbols = self.config.get('parallel_load_symbols', 5)
        self.initial_load_days = self.config.get('initial_load_days', 90)
        
        # Конфигурация качества данных
        self.quality_config = self.config.get('quality_checks', {})
        self.check_gaps = self.quality_config.get('check_gaps', True)
        self.check_anomalies = self.quality_config.get('check_anomalies', True)
        self.min_completeness = self.quality_config.get('min_completeness', 0.95)
        
        # ML конфигурация
        ml_config = config_manager.get_ml_config()
        self.symbols = ml_config.get('symbols', [])
        self.timeframe = '15m'  # Основной таймфрейм для ML
        self.exchange = 'bybit'
        
        # Состояние
        self._running = False
        self._update_task = None
        self._last_check = {}
        self._data_quality_scores = {}
        
        logger.info(f"📊 DataMaintenanceService инициализирован для {len(self.symbols)} символов")
    
    async def initialize(self):
        """Инициализация сервиса"""
        if not self.enabled:
            logger.warning("⚠️ DataMaintenanceService отключен в конфигурации")
            return
        
        await self.data_loader.initialize()
        
        # Проверяем наличие данных при первом запуске
        await self._initial_data_check()
        
        logger.info("✅ DataMaintenanceService инициализирован")
    
    async def start(self):
        """Запуск сервиса обновления данных"""
        if not self.enabled or self._running:
            return
        
        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())
        logger.info("🚀 DataMaintenanceService запущен")
    
    async def stop(self):
        """Остановка сервиса"""
        self._running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 DataMaintenanceService остановлен")
    
    async def _initial_data_check(self):
        """Проверка наличия данных при запуске системы"""
        logger.info("🔍 Проверка данных при запуске...")
        
        missing_symbols = []
        outdated_symbols = []
        
        for symbol in self.symbols:
            try:
                # Проверяем наличие и актуальность данных
                data_info = await self._check_symbol_data(symbol)
                
                if data_info['status'] == 'missing':
                    missing_symbols.append(symbol)
                elif data_info['status'] == 'outdated':
                    outdated_symbols.append(symbol)
                elif data_info['status'] == 'incomplete':
                    logger.warning(
                        f"⚠️ {symbol}: данные неполные "
                        f"(completeness: {data_info['completeness']:.1%})"
                    )
                
            except Exception as e:
                logger.error(f"❌ {symbol}: ошибка проверки данных: {e}")
        
        # Выводим результаты
        if missing_symbols:
            logger.warning(f"🔴 Отсутствуют данные для {len(missing_symbols)} символов: {missing_symbols[:5]}...")
            logger.info("💡 Рекомендуется запустить: python scripts/load_3months_data.py")
        
        if outdated_symbols:
            logger.warning(f"🟡 Устаревшие данные для {len(outdated_symbols)} символов: {outdated_symbols[:5]}...")
            # Автоматически обновляем устаревшие данные
            await self._update_symbols(outdated_symbols)
        
        if not missing_symbols and not outdated_symbols:
            logger.info("✅ Все данные актуальны и готовы к использованию")
    
    async def _update_loop(self):
        """Основной цикл обновления данных"""
        while self._running:
            try:
                # Обновляем данные
                await self._update_all_symbols()
                
                # Ждем следующего цикла
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле обновления: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    async def _update_all_symbols(self):
        """Обновление данных для всех символов"""
        logger.debug("🔄 Начало цикла обновления данных...")
        
        symbols_to_update = []
        
        # Проверяем какие символы нуждаются в обновлении
        for symbol in self.symbols:
            if await self._needs_update(symbol):
                symbols_to_update.append(symbol)
        
        if symbols_to_update:
            logger.info(f"📥 Обновление данных для {len(symbols_to_update)} символов...")
            await self._update_symbols(symbols_to_update)
        else:
            logger.debug("✅ Все данные актуальны")
    
    async def _needs_update(self, symbol: str) -> bool:
        """Проверка необходимости обновления данных для символа"""
        try:
            # Проверяем время последней проверки
            last_check = self._last_check.get(symbol, datetime.min)
            if datetime.now() - last_check < timedelta(minutes=1):
                return False  # Проверяли недавно
            
            self._last_check[symbol] = datetime.now()
            
            # Получаем информацию о данных
            data_info = await self._check_symbol_data(symbol)
            
            # Определяем необходимость обновления
            if data_info['status'] in ['missing', 'outdated']:
                return True
            
            # Проверяем качество данных
            if data_info['completeness'] < self.min_completeness:
                logger.warning(
                    f"⚠️ {symbol}: низкая полнота данных "
                    f"({data_info['completeness']:.1%})"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ {symbol}: ошибка проверки необходимости обновления: {e}")
            return True  # При ошибке лучше попробовать обновить
    
    async def _check_symbol_data(self, symbol: str) -> Dict:
        """Проверка состояния данных для символа"""
        result = {
            'symbol': symbol,
            'status': 'ok',
            'last_timestamp': None,
            'age_minutes': 0,
            'completeness': 1.0,
            'gaps': 0
        }
        
        try:
            # Загружаем последние данные
            df = await self.data_loader.load_ohlcv(
                symbol=symbol,
                exchange=self.exchange,
                interval=self.timeframe,
                limit=100,
                save_to_db=False
            )
            
            if df is None or df.empty:
                result['status'] = 'missing'
                return result
            
            # Проверяем актуальность
            last_timestamp = df.index[-1]
            result['last_timestamp'] = last_timestamp
            
            now = datetime.now(timezone.utc)
            # Проверяем если timestamp уже имеет timezone информацию
            if hasattr(last_timestamp, 'tz') and last_timestamp.tz is not None:
                # Уже timezone-aware, конвертируем в UTC если нужно
                if last_timestamp.tz != timezone.utc:
                    last_timestamp = last_timestamp.tz_convert('UTC')
            else:
                # Timestamp naive, добавляем UTC timezone
                if hasattr(last_timestamp, 'tz_localize'):
                    last_timestamp = last_timestamp.tz_localize('UTC')
            
            age = now - last_timestamp
            result['age_minutes'] = age.total_seconds() / 60
            
            if result['age_minutes'] > self.max_data_age:
                result['status'] = 'outdated'
            
            # Проверяем полноту данных
            if self.check_gaps:
                expected_candles = len(df)
                actual_candles = len(df.dropna())
                result['completeness'] = actual_candles / expected_candles if expected_candles > 0 else 0
                
                if result['completeness'] < self.min_completeness:
                    result['status'] = 'incomplete'
            
            # Сохраняем оценку качества
            self._data_quality_scores[symbol] = result['completeness']
            
        except Exception as e:
            logger.error(f"❌ {symbol}: ошибка проверки данных: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    async def _update_symbols(self, symbols: List[str]):
        """Обновление данных для списка символов"""
        # Разбиваем на батчи для параллельной загрузки
        for i in range(0, len(symbols), self.parallel_symbols):
            batch = symbols[i:i + self.parallel_symbols]
            
            tasks = []
            for symbol in batch:
                task = self._update_single_symbol(symbol)
                tasks.append(task)
            
            # Ждем завершения батча
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Логируем результаты
            successful = sum(1 for r in results if not isinstance(r, Exception))
            if successful < len(batch):
                logger.warning(
                    f"⚠️ Обновлено {successful}/{len(batch)} символов в батче"
                )
    
    async def _update_single_symbol(self, symbol: str):
        """Обновление данных для одного символа"""
        try:
            # Обновляем последние данные
            result = await self.data_loader.update_latest_data(
                symbols=[symbol],
                interval_minutes=15,  # 15m
                exchange=self.exchange
            )
            
            updated_count = result.get(symbol, 0)
            if updated_count > 0:
                logger.info(f"✅ {symbol}: обновлено {updated_count} свечей")
            else:
                logger.debug(f"ℹ️ {symbol}: нет новых данных")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ {symbol}: ошибка обновления: {e}")
            raise
    
    def get_data_quality_score(self, symbol: str) -> float:
        """Получение оценки качества данных для символа"""
        return self._data_quality_scores.get(symbol, 0.0)
    
    async def check_data_continuity(self, symbol: str) -> Dict:
        """Проверка непрерывности данных"""
        try:
            # Загружаем данные за последние сутки
            df = await self.data_loader.load_ohlcv(
                symbol=symbol,
                exchange=self.exchange,
                interval=self.timeframe,
                limit=96  # 24 часа для 15m интервала
            )
            
            if df is None or df.empty:
                return {'continuous': False, 'gaps': [], 'error': 'No data'}
            
            # Проверяем пропуски
            time_diff = df.index.to_series().diff()
            expected_interval = timedelta(minutes=15)
            
            gaps = []
            for i, diff in enumerate(time_diff[1:], 1):
                if diff > expected_interval * 1.5:
                    gaps.append({
                        'start': df.index[i-1],
                        'end': df.index[i],
                        'missing_candles': int(diff.total_seconds() / 900) - 1
                    })
            
            return {
                'continuous': len(gaps) == 0,
                'gaps': gaps,
                'total_missing': sum(g['missing_candles'] for g in gaps)
            }
            
        except Exception as e:
            logger.error(f"❌ {symbol}: ошибка проверки непрерывности: {e}")
            return {'continuous': False, 'gaps': [], 'error': str(e)}
    
    async def force_update(self, symbols: Optional[List[str]] = None):
        """Принудительное обновление данных"""
        symbols = symbols or self.symbols
        logger.info(f"🔄 Принудительное обновление {len(symbols)} символов...")
        
        await self._update_symbols(symbols)
        
        logger.info("✅ Принудительное обновление завершено")