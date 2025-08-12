"""
Служба автоматического обновления рыночных данных
"""

from typing import List, Dict, Optional, Set
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from decimal import Decimal

from database.connections.postgres import AsyncPGPool
from core.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class DataGap:
    """Информация о пропуске в данных"""
    symbol: str
    exchange: str
    interval_minutes: int
    start_time: datetime
    end_time: datetime
    expected_candles: int


@dataclass
class DataStatus:
    """Статус данных для символа"""
    symbol: str
    exchange: str
    interval_minutes: int
    latest_timestamp: Optional[datetime]
    candles_count: int
    is_sufficient_for_ml: bool  # Минимум 96 свечей
    gaps: List[DataGap]


class DataUpdateService:
    """Автоматическое обновление рыночных данных"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.exchanges: Dict[str, any] = {}
        
        # Настройки обновления из конфигурации
        data_config = self.config.get('data_management', {})
        self.update_interval = data_config.get('update_interval', 60)  # Секунды между обновлениями
        self.min_candles_for_ml = data_config.get('min_candles_for_ml', 96)  # Минимум для ML
        self.max_gap_hours = data_config.get('max_gap_hours', 2)  # Максимальный пропуск в часах
        self.auto_update = data_config.get('auto_update', True)  # Автообновление включено
        
        # Кэш статусов
        self.data_status_cache: Dict[str, DataStatus] = {}
        self.cache_ttl = 300  # 5 минут
        self.last_cache_update = datetime.min
        
        # Контроль обновлений
        self.is_running = False
        self.update_task: Optional[asyncio.Task] = None
        
        logger.info("DataUpdateService инициализирован")
        
    async def start(self) -> None:
        """Запуск службы обновления данных"""
        if self.is_running:
            logger.warning("DataUpdateService уже запущен")
            return
        
        if not self.auto_update:
            logger.info("DataUpdateService отключен в конфигурации (auto_update=false)")
            return
            
        logger.info("🔄 Запуск DataUpdateService (автообновление каждые %.1f минут)...", self.update_interval / 60)
        
        try:
            # Инициализация подключений к биржам
            await self._initialize_exchanges()
            
            # Первоначальная проверка и заполнение данных
            await self._initial_data_check()
            
            # Запуск фонового обновления
            self.is_running = True
            self.update_task = asyncio.create_task(self._update_loop())
            
            logger.info("DataUpdateService успешно запущен")
            
        except Exception as e:
            logger.error(f"Ошибка запуска DataUpdateService: {e}")
            raise
            
    async def stop(self) -> None:
        """Остановка службы обновления данных"""
        if not self.is_running:
            return
            
        logger.info("Остановка DataUpdateService...")
        
        self.is_running = False
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
                
        # Закрытие подключений к биржам
        for exchange in self.exchanges.values():
            try:
                await exchange.close()
            except:
                pass
                
        logger.info("DataUpdateService остановлен")
        
    async def get_data_status(self, force_refresh: bool = False) -> Dict[str, DataStatus]:
        """Получение статуса данных для всех символов"""
        
        # Проверка кэша
        if (
            not force_refresh and 
            self.data_status_cache and
            (datetime.now() - self.last_cache_update).total_seconds() < self.cache_ttl
        ):
            return self.data_status_cache
            
        logger.debug("Обновление кэша статуса данных...")
        
        # Получение активных символов
        symbols = await self._get_active_symbols()
        
        # Анализ данных для каждого символа
        status_map = {}
        
        for symbol_config in symbols:
            symbol = symbol_config['symbol']
            exchange = symbol_config['exchange']
            interval_minutes = symbol_config['interval_minutes']
            
            status = await self._analyze_symbol_data(
                symbol, 
                exchange, 
                interval_minutes
            )
            
            key = f"{exchange}_{symbol}_{interval_minutes}"
            status_map[key] = status
            
        # Обновление кэша
        self.data_status_cache = status_map
        self.last_cache_update = datetime.now()
        
        return status_map
        
    async def _initialize_exchanges(self) -> None:
        """Инициализация подключений к биржам"""
        
        # Получение списка активных бирж
        active_exchanges = await self._get_active_exchanges()
        
        for exchange_name in active_exchanges:
            try:
                # Используем ExchangeFactory из системы
                from exchanges.factory import ExchangeFactory
                import os
                factory = ExchangeFactory()
                
                # Получаем учетные данные из переменных окружения
                api_key = os.getenv(f"{exchange_name.upper()}_API_KEY")
                api_secret = os.getenv(f"{exchange_name.upper()}_API_SECRET")
                
                if not api_key or not api_secret:
                    logger.warning(f"API ключи для {exchange_name} не найдены")
                    continue
                    
                exchange = factory.create_client(
                    exchange_type=exchange_name,
                    api_key=api_key,
                    api_secret=api_secret,
                    sandbox=False
                )
                
                self.exchanges[exchange_name] = exchange
                logger.info(f"Биржа {exchange_name} инициализирована")
                
            except Exception as e:
                logger.error(f"Ошибка инициализации биржи {exchange_name}: {e}")
                
    async def _initial_data_check(self) -> None:
        """Первоначальная проверка и заполнение критических пропусков"""
        
        logger.info("Первоначальная проверка данных...")
        
        # Получение статуса данных
        data_statuses = await self.get_data_status(force_refresh=True)
        
        # Поиск критических пропусков
        critical_gaps = []
        
        for status in data_statuses.values():
            # Символы без данных для ML
            if not status.is_sufficient_for_ml:
                gap = DataGap(
                    symbol=status.symbol,
                    exchange=status.exchange,
                    interval_minutes=status.interval_minutes,
                    start_time=datetime.now() - timedelta(
                        minutes=self.min_candles_for_ml * status.interval_minutes
                    ),
                    end_time=datetime.now(),
                    expected_candles=self.min_candles_for_ml
                )
                critical_gaps.append(gap)
                
            # Большие пропуски в данных
            for gap in status.gaps:
                if gap.expected_candles > (self.max_gap_hours * 60 // gap.interval_minutes):
                    critical_gaps.append(gap)
                    
        # Заполнение критических пропусков
        if critical_gaps:
            logger.info(f"Найдено {len(critical_gaps)} критических пропусков, заполняем...")
            
            for gap in critical_gaps:
                try:
                    await self._fill_data_gap(gap)
                except Exception as e:
                    logger.error(f"Ошибка заполнения пропуска для {gap.symbol}: {e}")
        else:
            logger.info("Критических пропусков не найдено")
            
    async def _update_loop(self) -> None:
        """Основной цикл обновления данных"""
        
        while self.is_running:
            try:
                await self._update_recent_data()
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле обновления: {e}")
                await asyncio.sleep(30)  # Пауза перед повтором
                
    async def _update_recent_data(self) -> None:
        """Обновление последних данных"""
        
        logger.debug("Обновление последних данных...")
        
        # Получение символов для обновления
        symbols = await self._get_active_symbols()
        
        update_tasks = []
        
        for symbol_config in symbols:
            task = asyncio.create_task(
                self._update_symbol_data(
                    symbol_config['symbol'],
                    symbol_config['exchange'], 
                    symbol_config['interval_minutes']
                )
            )
            update_tasks.append(task)
            
        # Параллельное обновление
        if update_tasks:
            results = await asyncio.gather(*update_tasks, return_exceptions=True)
            
            # Логирование ошибок
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Ошибка обновления {symbols[i]['symbol']}: {result}")
            
    async def _update_symbol_data(
        self,
        symbol: str,
        exchange_name: str,
        interval_minutes: int
    ) -> None:
        """Обновление данных для конкретного символа"""
        
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                logger.warning(f"Биржа {exchange_name} недоступна")
                return
                
            # Определение времени последних данных
            latest_time = await self._get_latest_data_time(
                symbol, 
                exchange_name, 
                interval_minutes
            )
            
            # Загрузка новых данных
            if latest_time:
                start_time = latest_time + timedelta(minutes=interval_minutes)
            else:
                # Нет данных - загружаем последние 96 свечей
                start_time = datetime.now() - timedelta(
                    minutes=self.min_candles_for_ml * interval_minutes
                )
                
            end_time = datetime.now()
            
            if start_time >= end_time:
                return  # Нет новых данных для загрузки
                
            # Загрузка данных через метод биржи
            candles = await exchange.get_candles(
                symbol=symbol,
                interval_minutes=interval_minutes,
                start_time=start_time,
                end_time=end_time,
                limit=1000
            )
            
            if candles:
                # Сохранение в базу данных
                await self._save_candles(candles, exchange_name)
                
                logger.debug(
                    f"Обновлены данные {symbol}: загружено {len(candles)} свечей "
                    f"({start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')})"
                )
                
        except Exception as e:
            logger.error(f"Ошибка обновления данных {symbol} на {exchange_name}: {e}")
            
    async def _analyze_symbol_data(
        self,
        symbol: str,
        exchange: str,
        interval_minutes: int
    ) -> DataStatus:
        """Анализ данных для символа"""
        
        try:
            # Запрос количества и диапазона данных
            query = """
            SELECT 
                COUNT(*) as candles_count,
                MAX(datetime) as latest_timestamp,
                MIN(datetime) as earliest_timestamp
            FROM raw_market_data 
            WHERE symbol = $1 
                AND exchange = $2 
                AND interval_minutes = $3
            """
            
            pool = await AsyncPGPool.get_pool()
            result = await pool.fetchrow(
                query,
                symbol,
                exchange, 
                interval_minutes
            )
            
            if not result or not result['candles_count']:
                # Нет данных для символа
                return DataStatus(
                    symbol=symbol,
                    exchange=exchange,
                    interval_minutes=interval_minutes,
                    latest_timestamp=None,
                    candles_count=0,
                    is_sufficient_for_ml=False,
                    gaps=[]
                )
                
            candles_count = result['candles_count'] or 0
            latest_timestamp = result['latest_timestamp']
            
            # Поиск пропусков (упрощенный вариант)
            gaps = []
            
            # Проверка актуальности данных
            if latest_timestamp:
                time_since_last = (datetime.now(latest_timestamp.tzinfo) - latest_timestamp).total_seconds() / 60
                expected_missing = int(time_since_last // interval_minutes)
                
                if expected_missing > 1:  # Пропущено больше одной свечи
                    gaps.append(DataGap(
                        symbol=symbol,
                        exchange=exchange,
                        interval_minutes=interval_minutes,
                        start_time=latest_timestamp,
                        end_time=datetime.now(),
                        expected_candles=expected_missing
                    ))
            
            return DataStatus(
                symbol=symbol,
                exchange=exchange,
                interval_minutes=interval_minutes,
                latest_timestamp=latest_timestamp,
                candles_count=candles_count,
                is_sufficient_for_ml=candles_count >= self.min_candles_for_ml,
                gaps=gaps
            )
            
        except Exception as e:
            logger.error(f"Ошибка анализа данных для {symbol}: {e}")
            return DataStatus(
                symbol=symbol,
                exchange=exchange,
                interval_minutes=interval_minutes,
                latest_timestamp=None,
                candles_count=0,
                is_sufficient_for_ml=False,
                gaps=[]
            )
        
    async def _fill_data_gap(self, gap: DataGap) -> None:
        """Заполнение пропуска в данных"""
        
        logger.info(
            f"Заполнение пропуска для {gap.symbol}: "
            f"{gap.start_time.strftime('%Y-%m-%d %H:%M')} - {gap.end_time.strftime('%Y-%m-%d %H:%M')} "
            f"(~{gap.expected_candles} свечей)"
        )
        
        exchange = self.exchanges.get(gap.exchange)
        if not exchange:
            logger.error(f"Биржа {gap.exchange} недоступна")
            return
            
        try:
            # Загрузка данных для заполнения пропуска
            candles = await exchange.get_candles(
                symbol=gap.symbol,
                interval_minutes=gap.interval_minutes,
                start_time=gap.start_time,
                end_time=gap.end_time,
                limit=min(gap.expected_candles, 1000)
            )
            
            if candles:
                await self._save_candles(candles, gap.exchange)
                logger.info(f"Пропуск заполнен: загружено {len(candles)} свечей для {gap.symbol}")
            else:
                logger.warning(f"Нет данных для заполнения пропуска {gap.symbol}")
                
        except Exception as e:
            logger.error(f"Ошибка заполнения пропуска для {gap.symbol}: {e}")
            
    async def _save_candles(self, candles: List, exchange_name: str) -> None:
        """Сохранение свечей в базу данных"""
        
        pool = await AsyncPGPool.get_pool()
        for candle in candles:
            try:
                await pool.execute("""
                    INSERT INTO raw_market_data 
                    (symbol, timestamp, datetime, open, high, low, close, volume, 
                     interval_minutes, exchange, turnover)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (symbol, timestamp, interval_minutes, exchange) DO UPDATE
                    SET open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        turnover = EXCLUDED.turnover,
                        updated_at = NOW()
                """, 
                candle.symbol, 
                int(candle.timestamp.timestamp()),
                candle.timestamp,
                Decimal(str(candle.open_price)),
                Decimal(str(candle.high_price)),
                Decimal(str(candle.low_price)),
                Decimal(str(candle.close_price)),
                Decimal(str(candle.volume)),
                candle.interval_minutes,
                exchange_name,
                Decimal(str(getattr(candle, 'turnover', 0)))
                )
            except Exception as e:
                logger.error(f"Ошибка сохранения свечи: {e}")
                
    async def _get_active_symbols(self) -> List[Dict[str, any]]:
        """Получение списка активных торговых символов"""
        
        # Получение из конфигурации
        symbols = []
        
        # Основные криптопары
        trading_pairs = self.config.get('trading_pairs', [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'LINKUSDT'
        ])
        
        # Для ML используем 15-минутные свечи
        for symbol in trading_pairs:
            symbols.append({
                'symbol': symbol,
                'exchange': 'bybit',
                'interval_minutes': 15
            })
                
        return symbols
        
    async def _get_active_exchanges(self) -> Set[str]:
        """Получение списка активных бирж"""
        # Пока только Bybit
        return {'bybit'}
        
    async def _get_latest_data_time(
        self,
        symbol: str,
        exchange: str,
        interval_minutes: int
    ) -> Optional[datetime]:
        """Получение времени последних данных для символа"""
        
        pool = await AsyncPGPool.get_pool()
        result = await pool.fetchval("""
            SELECT MAX(datetime) 
            FROM raw_market_data 
            WHERE symbol = $1 
                AND exchange = $2 
                AND interval_minutes = $3
        """, symbol, exchange, interval_minutes)
        
        return result