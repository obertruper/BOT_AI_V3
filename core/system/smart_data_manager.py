"""
Умный менеджер данных с минимизацией API запросов
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from core.cache.market_data_cache import MarketDataCache
from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from exchanges.factory import ExchangeFactory

logger = setup_logger(__name__)


class SmartDataManager:
    """
    Оптимизированный менеджер данных:
    - Загружает исторические данные один раз при старте
    - Обновляет только последнюю свечу каждую минуту
    - Сохраняет завершенные свечи в БД
    - Использует кеш для минимизации API запросов
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()

        # Конфигурация
        self.data_config = self.config.get(
            "data_management",
            {
                "auto_update": True,
                "update_interval": 60,  # Обновление каждую минуту
                "initial_load_days": 7,
                "min_candles_for_ml": 96,
                "cache_size": 1000,
                "cache_ttl": 60,
            },
        )

        # Инициализация кеша
        self.cache = MarketDataCache(
            cache_size=self.data_config.get("cache_size", 1000),
            ttl_seconds=self.data_config.get("cache_ttl", 60),
        )

        # Состояние
        self.is_running = False
        self.update_task: Optional[asyncio.Task] = None
        self.exchanges = {}
        self.websocket_connections = {}

        # Торговые пары
        self.trading_pairs = self.config.get(
            "trading_pairs",
            [
                "BTCUSDT",
                "ETHUSDT",
                "BNBUSDT",
                "ADAUSDT",
                "SOLUSDT",
                "XRPUSDT",
                "DOGEUSDT",
                "DOTUSDT",
                "LINKUSDT",
            ],
        )

        # Время последнего сохранения в БД для каждого символа
        self._last_db_save: Dict[str, datetime] = {}

        # Колбэки для обновлений
        self._update_callbacks: List[Callable] = []

        logger.info(
            f"SmartDataManager инициализирован для {len(self.trading_pairs)} пар"
        )

    async def start(self) -> None:
        """Запуск умного менеджера данных"""
        if self.is_running:
            logger.warning("SmartDataManager уже запущен")
            return

        logger.info("🚀 Запуск SmartDataManager...")

        try:
            # 1. Инициализация бирж
            await self._initialize_exchanges()

            # 2. Загрузка исторических данных из БД или API
            await self._load_initial_data()

            # 3. Запуск WebSocket соединений для real-time обновлений
            await self._start_websockets()

            # 4. Запуск цикла минутных обновлений
            self.is_running = True
            self.update_task = asyncio.create_task(self._smart_update_loop())

            logger.info("✅ SmartDataManager успешно запущен")

        except Exception as e:
            logger.error(f"Ошибка запуска SmartDataManager: {e}")
            raise

    async def stop(self) -> None:
        """Остановка менеджера"""
        if not self.is_running:
            return

        logger.info("Остановка SmartDataManager...")
        self.is_running = False

        # Остановка задач
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

        # Закрытие WebSocket соединений
        for ws in self.websocket_connections.values():
            try:
                await ws.close()
            except:
                pass

        # Закрытие бирж
        for exchange in self.exchanges.values():
            try:
                await exchange.close()
            except:
                pass

        logger.info("SmartDataManager остановлен")

    def _ensure_utc_timestamp(self, timestamp) -> pd.Timestamp:
        """
        Ensure timestamp is UTC and timezone-naive for database storage.

        Args:
            timestamp: Input timestamp (can be timezone-aware or naive)

        Returns:
            pd.Timestamp: UTC timestamp without timezone info
        """
        if timestamp is None:
            return None

        # Convert to pandas Timestamp if not already
        if not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)

        # Handle timezone conversion properly
        if timestamp.tzinfo is not None:
            # Already timezone-aware - convert to UTC
            timestamp = timestamp.tz_convert("UTC")
            # Remove timezone info for database storage (PostgreSQL requirement)
            timestamp = timestamp.tz_localize(None)
        else:
            # Naive timestamp - assume it's already UTC
            pass

        return timestamp

    async def _initialize_exchanges(self) -> None:
        """Инициализация подключений к биржам"""
        try:
            exchange = await ExchangeFactory.create_exchange_client("bybit")
            if exchange:
                self.exchanges["bybit"] = exchange
                logger.info("✅ Биржа Bybit подключена")
            else:
                raise Exception("Не удалось подключить Bybit")
        except Exception as e:
            logger.error(f"Ошибка инициализации бирж: {e}")
            raise

    async def _load_initial_data(self) -> None:
        """
        Загрузка начальных данных:
        1. Пытаемся загрузить из БД
        2. Если данных нет или они устарели - загружаем с API
        3. Кешируем все данные
        """
        logger.info("📊 Загрузка исторических данных...")

        tasks = []
        for symbol in self.trading_pairs:
            task = asyncio.create_task(self._load_symbol_data(symbol))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"✅ Загружено {success_count}/{len(self.trading_pairs)} символов")

        # Логирование ошибок
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка загрузки {self.trading_pairs[i]}: {result}")

    async def _load_symbol_data(self, symbol: str) -> None:
        """Загрузка данных для одного символа"""
        try:
            # 1. Пробуем загрузить из БД
            db_data = await self._load_from_database(symbol)

            if (
                db_data is not None
                and len(db_data) >= self.data_config["min_candles_for_ml"]
            ):
                # Проверяем актуальность
                last_time = db_data.index[-1]
                age = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600

                if age < 1:  # Данные свежие (менее часа)
                    await self.cache.update_data(symbol, db_data, is_complete=True)
                    logger.info(f"✅ {symbol}: загружено {len(db_data)} свечей из БД")
                    return
                else:
                    logger.info(f"⚠️ {symbol}: данные в БД устарели ({age:.1f} часов)")

            # 2. Загружаем с API
            await self._load_from_api(symbol)

        except Exception as e:
            logger.error(f"Ошибка загрузки {symbol}: {e}")
            raise

    async def _load_from_database(self, symbol: str) -> Optional[pd.DataFrame]:
        """Загрузка данных из БД"""
        try:
            result = await AsyncPGPool.fetch(
                """
                SELECT timestamp, datetime, open, high, low, close, volume, turnover
                FROM raw_market_data
                WHERE symbol = $1
                  AND exchange = 'bybit'
                  AND interval_minutes = 15
                ORDER BY timestamp DESC
                LIMIT 1000
            """,
                symbol,
            )

            if not result:
                return None

            # Преобразуем в DataFrame
            data = []
            for row in result:
                data.append(
                    {
                        "timestamp": row["timestamp"],
                        "datetime": row["datetime"],
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                        "turnover": float(row["turnover"]) if row["turnover"] else 0,
                    }
                )

            df = pd.DataFrame(data)
            df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
            df.set_index("datetime", inplace=True)
            df.sort_index(inplace=True)

            return df

        except Exception as e:
            logger.error(f"Ошибка загрузки из БД для {symbol}: {e}")
            return None

    async def _load_from_api(self, symbol: str) -> None:
        """Загрузка данных с API"""
        try:
            exchange = self.exchanges.get("bybit")
            if not exchange:
                return

            logger.info(f"📥 Загрузка {symbol} с API...")

            # Загружаем исторические данные
            candles = await exchange.get_klines(symbol, "15", limit=1000)

            if candles:
                # Преобразуем в DataFrame
                df = self._candles_to_dataframe(candles)

                # Сохраняем в кеш
                await self.cache.update_data(symbol, df, is_complete=True)

                # Сохраняем в БД
                await self._save_candles_to_db(symbol, candles)

                logger.info(f"✅ {symbol}: загружено {len(candles)} свечей с API")
            else:
                logger.warning(f"⚠️ {symbol}: не удалось загрузить данные с API")

        except Exception as e:
            logger.error(f"Ошибка загрузки с API для {symbol}: {e}")
            raise

    async def _start_websockets(self) -> None:
        """Запуск WebSocket соединений для real-time обновлений"""
        # TODO: Реализовать WebSocket подключения для каждой биржи
        # Пока используем polling каждую минуту
        logger.info("📡 WebSocket соединения будут реализованы в следующей версии")

    async def _smart_update_loop(self) -> None:
        """
        Умный цикл обновления:
        - Обновляет только последнюю свечу каждую минуту
        - Сохраняет завершенные свечи в БД
        """
        while self.is_running:
            try:
                start_time = asyncio.get_event_loop().time()

                # Обновляем только последние свечи
                await self._update_last_candles()

                # Вызываем колбэки
                for callback in self._update_callbacks:
                    try:
                        await callback()
                    except Exception as e:
                        logger.error(f"Ошибка в callback: {e}")

                # Логируем статистику кеша
                if asyncio.get_event_loop().time() % 300 < 60:  # Каждые 5 минут
                    stats = self.cache.get_stats()
                    logger.info(f"📊 Статистика кеша: {stats}")

                # Ждем до следующей минуты
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, 60 - elapsed)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в smart_update_loop: {e}")
                await asyncio.sleep(10)

    async def _update_last_candles(self) -> None:
        """Обновление только последних свечей для всех символов"""
        tasks = []

        for symbol in self.trading_pairs:
            # Проверяем, нужно ли обновление
            needs_update, update_type = self.cache.needs_update(symbol)

            if needs_update and update_type == "last":
                task = asyncio.create_task(self._update_last_candle(symbol))
                tasks.append(task)
            elif needs_update and update_type == "full":
                # Если нужна полная перезагрузка
                task = asyncio.create_task(self._load_symbol_data(symbol))
                tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Подсчет успешных обновлений
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            if success_count > 0:
                logger.debug(f"🔄 Обновлено {success_count} последних свечей")

    async def _update_last_candle(self, symbol: str) -> None:
        """Обновление последней свечи для символа"""
        try:
            exchange = self.exchanges.get("bybit")
            if not exchange:
                return

            # Запрашиваем только последнюю свечу
            candles = await exchange.get_klines(symbol, "15", limit=2)

            if candles and len(candles) > 0:
                last_candle = candles[-1]

                # Парсим данные свечи из объекта Kline
                candle_data = {
                    "timestamp": self._ensure_utc_timestamp(last_candle.open_time),
                    "open": float(last_candle.open_price),
                    "high": float(last_candle.high_price),
                    "low": float(last_candle.low_price),
                    "close": float(last_candle.close_price),
                    "volume": float(last_candle.volume),
                    "turnover": (
                        float(last_candle.turnover)
                        if hasattr(last_candle, "turnover")
                        else 0
                    ),
                }

                # Обновляем кеш
                await self.cache.update_last_candle(symbol, candle_data)

                # Проверяем, завершена ли свеча
                await self._check_and_save_completed_candle(symbol, candle_data)

        except Exception as e:
            logger.error(f"Ошибка обновления последней свечи {symbol}: {e}")

    async def _check_and_save_completed_candle(
        self, symbol: str, candle_data: Dict[str, Any]
    ) -> None:
        """
        Проверка и сохранение завершенной свечи в БД
        """
        try:
            current_time = datetime.now(timezone.utc)
            candle_time = candle_data["timestamp"].to_pydatetime()

            # Убеждаемся что candle_time также в UTC timezone для сравнения
            if candle_time.tzinfo is None:
                candle_time = candle_time.replace(tzinfo=timezone.utc)

            # Проверяем, прошло ли 15 минут с начала свечи
            if (current_time - candle_time).total_seconds() >= 900:
                # Свеча завершена, проверяем когда последний раз сохраняли
                last_save = self._last_db_save.get(symbol)

                if last_save is None or candle_time > last_save:
                    # Сохраняем в БД
                    await self._save_single_candle(symbol, candle_data)
                    self._last_db_save[symbol] = candle_time
                    logger.debug(f"💾 {symbol}: Завершенная свеча сохранена в БД")

        except Exception as e:
            logger.error(f"Ошибка сохранения завершенной свечи {symbol}: {e}")

    async def _save_single_candle(
        self, symbol: str, candle_data: Dict[str, Any]
    ) -> None:
        """Сохранение одной свечи в БД"""
        try:
            timestamp = int(candle_data["timestamp"].timestamp() * 1000)

            await AsyncPGPool.execute(
                """
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
                symbol,
                timestamp,
                candle_data["timestamp"],
                candle_data["open"],
                candle_data["high"],
                candle_data["low"],
                candle_data["close"],
                candle_data["volume"],
                15,
                "bybit",
                candle_data.get("turnover", 0),
            )

        except Exception as e:
            logger.error(f"Ошибка сохранения свечи {symbol}: {e}")

    async def _save_candles_to_db(self, symbol: str, candles: List[Any]) -> None:
        """Сохранение списка свечей в БД"""
        for candle in candles:
            try:
                candle_data = None
                if isinstance(candle, list) and len(candle) >= 6:
                    # Старый формат - массив
                    candle_data = {
                        "timestamp": self._ensure_utc_timestamp(
                            pd.Timestamp(int(candle[0]), unit="ms")
                        ),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                        "turnover": float(candle[6]) if len(candle) > 6 else 0,
                    }
                elif hasattr(candle, "open_price"):
                    # Новый формат - объект Kline
                    candle_data = {
                        "timestamp": self._ensure_utc_timestamp(candle.open_time),
                        "open": float(candle.open_price),
                        "high": float(candle.high_price),
                        "low": float(candle.low_price),
                        "close": float(candle.close_price),
                        "volume": float(candle.volume),
                        "turnover": float(candle.turnover)
                        if hasattr(candle, "turnover")
                        else 0,
                    }

                if candle_data:
                    await self._save_single_candle(symbol, candle_data)
            except Exception as e:
                logger.error(f"Ошибка сохранения свечи: {e}")

    def _candles_to_dataframe(self, candles: List[Any]) -> pd.DataFrame:
        """Преобразование свечей в DataFrame"""
        data = []
        for candle in candles:
            if isinstance(candle, list) and len(candle) >= 6:
                # Старый формат - массив
                data.append(
                    {
                        "datetime": self._ensure_utc_timestamp(
                            pd.Timestamp(int(candle[0]), unit="ms")
                        ),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                        "turnover": float(candle[6]) if len(candle) > 6 else 0,
                    }
                )
            elif hasattr(candle, "open_price"):
                # Новый формат - объект Kline
                data.append(
                    {
                        "datetime": self._ensure_utc_timestamp(candle.open_time),
                        "open": float(candle.open_price),
                        "high": float(candle.high_price),
                        "low": float(candle.low_price),
                        "close": float(candle.close_price),
                        "volume": float(candle.volume),
                        "turnover": float(candle.turnover)
                        if hasattr(candle, "turnover")
                        else 0,
                    }
                )

        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index("datetime", inplace=True)
            df.sort_index(inplace=True)

        return df

    async def get_data(
        self, symbol: str, required_candles: int = 96
    ) -> Optional[pd.DataFrame]:
        """
        Получить данные для символа (из кеша)

        Args:
            symbol: Торговый символ
            required_candles: Минимальное количество свечей

        Returns:
            DataFrame с OHLCV данными
        """
        return await self.cache.get_data(symbol, required_candles)

    def register_update_callback(self, callback: Callable) -> None:
        """Регистрация callback для уведомления об обновлениях"""
        self._update_callbacks.append(callback)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Получить статистику кеша"""
        return self.cache.get_stats()
