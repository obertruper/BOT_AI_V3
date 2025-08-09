#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загрузчик рыночных данных (OHLCV) для ML стратегий
Поддерживает загрузку данных с бирж и сохранение в БД
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.dialects.postgresql import insert

from core.logger import setup_logger
from database.connections import get_async_db
from database.models.market_data import RawMarketData, MarketDataSnapshot, MarketType
from exchanges.factory import ExchangeFactory
from core.config.config_manager import ConfigManager
from core.exceptions import DataLoadError, ExchangeError


logger = setup_logger(__name__)


class DataLoader:
    """
    Загрузчик рыночных данных с бирж
    Поддерживает инкрементальную загрузку и обновление данных
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Инициализация загрузчика данных"""
        self.config_manager = config_manager or ConfigManager()
        self.exchange_factory = ExchangeFactory()
        self.exchanges = {}
        self._initialized = False
        
        # Параметры из конфигурации
        self.ml_config = self.config_manager.get_config().get('ml', {})
        self.data_config = self.ml_config.get('data', {})
        self.symbols = self.data_config.get('symbols', ['BTCUSDT'])
        self.interval_minutes = self.data_config.get('interval_minutes', 15)
        self.default_exchange = 'bybit'
        
    async def initialize(self):
        """Инициализация подключений к биржам"""
        if self._initialized:
            return
            
        try:
            # Получаем реальные API ключи из конфигурации
            exchange_config = self.config_manager.get_config().get('exchanges', {}).get(self.default_exchange, {})
            
            # Если в конфигурации есть enabled=false, пропускаем
            if not exchange_config.get('enabled', True):
                logger.warning(f"Биржа {self.default_exchange} отключена в конфигурации")
                return
            
            # Получаем API ключи из переменных окружения
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv(f'{self.default_exchange.upper()}_API_KEY')
            api_secret = os.getenv(f'{self.default_exchange.upper()}_API_SECRET')
            
            if not api_key or not api_secret:
                # Используем публичные методы без авторизации
                logger.warning(f"API ключи для {self.default_exchange} не найдены, используем публичный доступ")
                api_key = "public_access"
                api_secret = "public_access"
            
            # Создаем подключение к основной бирже
            self.exchanges[self.default_exchange] = self.exchange_factory.create_client(
                exchange_type=self.default_exchange,
                api_key=api_key,
                api_secret=api_secret,
                sandbox=exchange_config.get('testnet', False)
            )
            
            self._initialized = True
            logger.info(f"DataLoader инициализирован для биржи {self.default_exchange}")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации DataLoader: {e}")
            raise DataLoadError(f"Не удалось инициализировать DataLoader: {e}")

    async def load_ohlcv(
        self,
        symbol: str,
        exchange: str = None,
        interval: str = "15m", 
        limit: int = 1000,
        save_to_db: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Загрузка OHLCV данных - совместимый API для DataMaintenanceService
        
        Args:
            symbol: Торговый символ
            exchange: Биржа
            interval: Интервал (15m, 1h, etc.)
            limit: Количество свечей
            save_to_db: Сохранять ли в БД
            
        Returns:
            DataFrame с OHLCV данными или None
        """
        if not self._initialized:
            await self.initialize()
            
        exchange = exchange or self.default_exchange
        
        try:
            # Преобразуем интервал в минуты
            interval_minutes = self._parse_interval_to_minutes(interval)
            
            # Рассчитываем начальную дату
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(minutes=interval_minutes * limit)
            
            # Загружаем исторические данные
            if save_to_db:
                count = await self.load_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval_minutes=interval_minutes,
                    exchange=exchange
                )
                logger.info(f"Загружено и сохранено {count} записей для {symbol}")
            
            # Загружаем данные из БД
            async with get_async_db() as session:
                stmt = select(RawMarketData).where(
                    and_(
                        RawMarketData.symbol == symbol,
                        RawMarketData.exchange == exchange,
                        RawMarketData.interval_minutes == interval_minutes,
                        RawMarketData.datetime >= start_date
                    )
                ).order_by(RawMarketData.datetime).limit(limit)
                
                result = await session.execute(stmt)
                data = result.scalars().all()
                
                if data:
                    # Конвертируем в DataFrame
                    df = pd.DataFrame([{
                        'timestamp': d.timestamp,
                        'datetime': d.datetime,
                        'open': float(d.open),
                        'high': float(d.high),
                        'low': float(d.low),
                        'close': float(d.close),
                        'volume': float(d.volume),
                        'turnover': float(d.turnover) if d.turnover else 0
                    } for d in data])
                    
                    df.set_index('datetime', inplace=True)
                    df = df.sort_index()
                    
                    return df
                
            return None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки OHLCV для {symbol}: {e}")
            return None
    
    async def load_historical_data(
        self, 
        symbol: str, 
        start_date: datetime,
        end_date: Optional[datetime] = None,
        interval_minutes: Optional[int] = None,
        exchange: Optional[str] = None
    ) -> int:
        """
        Загрузка исторических данных для символа
        
        Args:
            symbol: Торговый символ (например BTCUSDT)
            start_date: Начальная дата
            end_date: Конечная дата (по умолчанию - текущее время)
            interval_minutes: Временной интервал в минутах
            exchange: Название биржи
            
        Returns:
            Количество загруженных записей
        """
        if not self._initialized:
            await self.initialize()
            
        exchange = exchange or self.default_exchange
        interval_minutes = interval_minutes or self.interval_minutes
        end_date = end_date or datetime.now(timezone.utc)
        
        logger.info(
            f"Загрузка исторических данных {symbol} с {start_date} по {end_date}, "
            f"интервал {interval_minutes}м, биржа {exchange}"
        )
        
        try:
            # Получаем экземпляр биржи
            exchange_instance = self.exchanges.get(exchange)
            if not exchange_instance:
                raise DataLoadError(f"Биржа {exchange} не инициализирована")
            
            # Конвертируем интервал в формат биржи
            timeframe = self._convert_interval_to_timeframe(interval_minutes)
            
            # Загружаем данные порциями
            all_candles = []
            current_start = start_date
            batch_size = 1000  # Максимум свечей за запрос
            
            while current_start < end_date:
                # Рассчитываем конец текущей порции
                max_end_time = current_start + timedelta(minutes=interval_minutes * batch_size)
                current_end = min(max_end_time, end_date)
                
                # Загружаем порцию данных
                since = int(current_start.timestamp() * 1000)
                limit = min(batch_size, int((current_end - current_start).total_seconds() / 60 / interval_minutes))
                
                candles = await exchange_instance.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=limit
                )
                
                if not candles:
                    break
                    
                all_candles.extend(candles)
                
                # Обновляем начало для следующей порции
                last_timestamp = candles[-1][0]
                current_start = datetime.fromtimestamp(last_timestamp / 1000, tz=timezone.utc) + timedelta(minutes=interval_minutes)
                
                logger.debug(f"Загружено {len(candles)} свечей, всего: {len(all_candles)}")
                
                # Небольшая задержка между запросами
                await asyncio.sleep(0.1)
            
            # Сохраняем данные в БД
            saved_count = await self._save_candles_to_db(
                symbol=symbol,
                candles=all_candles,
                interval_minutes=interval_minutes,
                exchange=exchange
            )
            
            logger.info(f"Загружено и сохранено {saved_count} записей для {symbol}")
            return saved_count
            
        except Exception as e:
            logger.error(f"Ошибка загрузки исторических данных для {symbol}: {e}")
            raise DataLoadError(f"Не удалось загрузить данные для {symbol}: {e}")
    
    async def update_latest_data(
        self,
        symbols: Optional[List[str]] = None,
        interval_minutes: Optional[int] = None,
        exchange: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Обновление последних данных для списка символов
        
        Args:
            symbols: Список символов (по умолчанию из конфигурации)
            interval_minutes: Временной интервал
            exchange: Биржа
            
        Returns:
            Словарь {symbol: количество_обновленных_записей}
        """
        if not self._initialized:
            await self.initialize()
            
        symbols = symbols or self.symbols
        interval_minutes = interval_minutes or self.interval_minutes
        exchange = exchange or self.default_exchange
        
        results = {}
        
        for symbol in symbols:
            try:
                # Получаем последнюю запись из БД
                last_timestamp = await self._get_last_timestamp(
                    symbol=symbol,
                    interval_minutes=interval_minutes,
                    exchange=exchange
                )
                
                # Определяем начальную дату для загрузки
                if last_timestamp:
                    start_date = datetime.fromtimestamp(last_timestamp / 1000, tz=timezone.utc)
                    start_date += timedelta(minutes=interval_minutes)
                else:
                    # Если данных нет, загружаем за последние 7 дней
                    start_date = datetime.now(timezone.utc) - timedelta(days=7)
                
                # Загружаем новые данные
                count = await self.load_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    interval_minutes=interval_minutes,
                    exchange=exchange
                )
                
                results[symbol] = count
                
                # Обновляем снимок рынка
                await self._update_market_snapshot(symbol)
                
            except Exception as e:
                logger.error(f"Ошибка обновления данных для {symbol}: {e}")
                results[symbol] = 0
        
        return results
    
    async def load_realtime_data(
        self,
        symbols: Optional[List[str]] = None,
        callback=None
    ):
        """
        Подписка на real-time данные через WebSocket
        
        Args:
            symbols: Список символов
            callback: Функция обратного вызова для обработки данных
        """
        if not self._initialized:
            await self.initialize()
            
        symbols = symbols or self.symbols
        
        # TODO: Реализовать WebSocket подписку
        logger.warning("Real-time загрузка данных еще не реализована")
    
    async def _save_candles_to_db(
        self,
        symbol: str,
        candles: List[List],
        interval_minutes: int,
        exchange: str
    ) -> int:
        """
        Сохранение свечей в базу данных
        
        Args:
            symbol: Символ
            candles: Список свечей [[timestamp, open, high, low, close, volume], ...]
            interval_minutes: Интервал
            exchange: Биржа
            
        Returns:
            Количество сохраненных записей
        """
        if not candles:
            return 0
            
        async with get_async_db() as session:
            try:
                # Подготавливаем данные для вставки
                values = []
                for candle in candles:
                    timestamp = candle[0]
                    dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                    
                    values.append({
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'datetime': dt,
                        'open': Decimal(str(candle[1])),
                        'high': Decimal(str(candle[2])),
                        'low': Decimal(str(candle[3])),
                        'close': Decimal(str(candle[4])),
                        'volume': Decimal(str(candle[5])),
                        'turnover': Decimal(str(candle[5] * candle[4])) if len(candle) > 5 else Decimal('0'),
                        'interval_minutes': interval_minutes,
                        'exchange': exchange,
                        'market_type': MarketType.SPOT.value
                    })
                
                # Используем upsert для обновления существующих записей
                stmt = insert(RawMarketData).values(values)
                stmt = stmt.on_conflict_do_update(
                    constraint='_symbol_timestamp_interval_exchange_uc',
                    set_={
                        'open': stmt.excluded.open,
                        'high': stmt.excluded.high,
                        'low': stmt.excluded.low,
                        'close': stmt.excluded.close,
                        'volume': stmt.excluded.volume,
                        'turnover': stmt.excluded.turnover,
                        'updated_at': datetime.now(timezone.utc)
                    }
                )
                
                await session.execute(stmt)
                await session.commit()
                
                return len(values)
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка сохранения данных в БД: {e}")
                raise
    
    async def _get_last_timestamp(
        self,
        symbol: str,
        interval_minutes: int,
        exchange: str
    ) -> Optional[int]:
        """Получение timestamp последней записи для символа"""
        async with get_async_db() as session:
            stmt = select(RawMarketData.timestamp).where(
                and_(
                    RawMarketData.symbol == symbol,
                    RawMarketData.interval_minutes == interval_minutes,
                    RawMarketData.exchange == exchange
                )
            ).order_by(desc(RawMarketData.timestamp)).limit(1)
            
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return row
    
    async def _update_market_snapshot(self, symbol: str):
        """Обновление снимка рынка для символа"""
        async with get_async_db() as session:
            try:
                # Получаем последние данные
                stmt = select(RawMarketData).where(
                    RawMarketData.symbol == symbol
                ).order_by(desc(RawMarketData.timestamp)).limit(1)
                
                result = await session.execute(stmt)
                latest = result.scalar_one_or_none()
                
                if not latest:
                    return
                
                # Получаем данные за 24 часа
                time_24h_ago = latest.timestamp - 24 * 60 * 60 * 1000
                stmt_24h = select(RawMarketData).where(
                    and_(
                        RawMarketData.symbol == symbol,
                        RawMarketData.timestamp >= time_24h_ago
                    )
                ).order_by(RawMarketData.timestamp)
                
                result_24h = await session.execute(stmt_24h)
                data_24h = result_24h.scalars().all()
                
                if data_24h:
                    # Рассчитываем статистику
                    high_24h = max(d.high for d in data_24h)
                    low_24h = min(d.low for d in data_24h)
                    volume_24h = sum(d.volume for d in data_24h)
                    
                    first_price = float(data_24h[0].close)
                    last_price = float(latest.close)
                    price_change = last_price - first_price
                    price_change_pct = (price_change / first_price * 100) if first_price > 0 else 0
                    
                    # Обновляем или создаем снимок
                    snapshot_data = {
                        'symbol': symbol,
                        'last_price': latest.close,
                        'last_volume': latest.volume,
                        'last_update': latest.datetime,
                        'price_24h_change': price_change,
                        'price_24h_change_pct': price_change_pct,
                        'volume_24h': volume_24h,
                        'high_24h': high_24h,
                        'low_24h': low_24h,
                        'is_active': True,
                        'updated_at': datetime.now(timezone.utc)
                    }
                    
                    stmt = insert(MarketDataSnapshot).values(**snapshot_data)
                    stmt = stmt.on_conflict_do_update(
                        constraint='market_data_snapshots_symbol_key',
                        set_=snapshot_data
                    )
                    
                    await session.execute(stmt)
                    await session.commit()
                    
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка обновления снимка рынка для {symbol}: {e}")
    
    def _convert_interval_to_timeframe(self, interval_minutes: int) -> str:
        """Конвертация интервала в минутах в формат timeframe биржи"""
        mapping = {
            1: '1m',
            5: '5m',
            15: '15m',
            30: '30m',
            60: '1h',
            240: '4h',
            1440: '1d'
        }
        return mapping.get(interval_minutes, '15m')

    def _parse_interval_to_minutes(self, interval: str) -> int:
        """Конвертация строкового интервала в минуты"""
        mapping = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        return mapping.get(interval.lower(), 15)
    
    async def get_data_for_ml(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Получение данных для ML в формате DataFrame
        
        Args:
            symbol: Символ
            start_date: Начальная дата
            end_date: Конечная дата
            limit: Максимальное количество записей
            
        Returns:
            DataFrame с OHLCV данными
        """
        async with get_async_db() as session:
            query = select(RawMarketData).where(
                RawMarketData.symbol == symbol
            )
            
            if start_date:
                query = query.where(RawMarketData.datetime >= start_date)
            if end_date:
                query = query.where(RawMarketData.datetime <= end_date)
                
            query = query.order_by(RawMarketData.timestamp)
            
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            data = result.scalars().all()
            
            if not data:
                return pd.DataFrame()
            
            # Конвертируем в DataFrame
            df = pd.DataFrame([{
                'timestamp': d.timestamp,
                'datetime': d.datetime,
                'open': float(d.open),
                'high': float(d.high),
                'low': float(d.low),
                'close': float(d.close),
                'volume': float(d.volume),
                'turnover': float(d.turnover) if d.turnover else 0,
                'symbol': symbol  # ИСПРАВЛЕНО: Добавляем symbol для каждой записи
            } for d in data])
            
            df.set_index('datetime', inplace=True)
            return df
    
    async def cleanup(self):
        """Очистка ресурсов"""
        for exchange in self.exchanges.values():
            if hasattr(exchange, 'close'):
                await exchange.close()
        self.exchanges.clear()
        self._initialized = False


# Пример использования
async def main():
    """Пример использования DataLoader"""
    loader = DataLoader()
    
    try:
        await loader.initialize()
        
        # Загрузка исторических данных
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        count = await loader.load_historical_data(
            symbol='BTCUSDT',
            start_date=start_date
        )
        print(f"Загружено {count} записей")
        
        # Обновление последних данных
        results = await loader.update_latest_data(['BTCUSDT', 'ETHUSDT'])
        print(f"Обновлено: {results}")
        
        # Получение данных для ML
        df = await loader.get_data_for_ml('BTCUSDT', limit=1000)
        print(f"Получено {len(df)} записей для ML")
        print(df.head())
        
    finally:
        await loader.cleanup()


if __name__ == "__main__":
    asyncio.run(main())