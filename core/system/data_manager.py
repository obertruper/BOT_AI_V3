"""
Менеджер обновления данных для системы
Интегрирует DataUpdateService с основной системой
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, List, Optional

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from exchanges.factory import ExchangeFactory

logger = setup_logger(__name__)


class DataManager:
    """Управляет автоматическим обновлением рыночных данных"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()

        # Конфигурация обновления данных
        self.data_config = self.config.get(
            "data_management",
            {
                "auto_update": True,
                "update_interval": 900,  # 15 минут
                "initial_load_days": 7,
                "min_candles_for_ml": 96,
                "check_on_startup": True,
            },
        )

        self.is_running = False
        self.update_task: Optional[asyncio.Task] = None
        self.exchanges = {}

        # Список торговых пар из конфигурации
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

        logger.info(
            f"DataManager инициализирован: auto_update={self.data_config['auto_update']}, interval={self.data_config['update_interval']}s"
        )

    async def start(self) -> None:
        """Запуск менеджера обновления данных"""
        if self.is_running:
            logger.warning("DataManager уже запущен")
            return

        if not self.data_config.get("auto_update", True):
            logger.info("Автообновление данных отключено в конфигурации")
            return

        logger.info(
            f"🔄 Запуск DataManager (обновление каждые {self.data_config['update_interval'] / 60:.1f} минут)"
        )

        try:
            # Инициализация бирж
            await self._initialize_exchanges()

            # Проверка и загрузка начальных данных
            if self.data_config.get("check_on_startup", True):
                await self._check_and_load_initial_data()

            # Запуск цикла обновления
            self.is_running = True
            self.update_task = asyncio.create_task(self._update_loop())

            logger.info("✅ DataManager успешно запущен")

        except Exception as e:
            logger.error(f"Ошибка запуска DataManager: {e}")
            raise

    async def stop(self) -> None:
        """Остановка менеджера"""
        if not self.is_running:
            return

        logger.info("Остановка DataManager...")
        self.is_running = False

        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

        # Закрытие бирж
        for exchange in self.exchanges.values():
            try:
                await exchange.close()
            except:
                pass

        logger.info("DataManager остановлен")

    async def _initialize_exchanges(self) -> None:
        """Инициализация подключений к биржам"""
        try:
            # Пока только Bybit
            exchange = await ExchangeFactory.create_exchange_client("bybit")
            if exchange:
                self.exchanges["bybit"] = exchange
                logger.info("✅ Биржа Bybit подключена для обновления данных")
            else:
                logger.error("❌ Не удалось подключить Bybit для обновления данных")
        except Exception as e:
            logger.error(f"Ошибка инициализации бирж: {e}")

    async def _check_and_load_initial_data(self) -> None:
        """Проверка и загрузка начальных данных"""
        logger.info("📊 Проверка актуальности данных...")

        try:
            # Проверка свежести данных для каждого символа
            from datetime import timezone

            for symbol in self.trading_pairs:
                latest_data = await self._get_latest_data_time(symbol)

                if latest_data:
                    # Исправляем timezone - если naive, считаем что это UTC
                    if latest_data.tzinfo is None:
                        latest_data = latest_data.replace(tzinfo=timezone.utc)

                    now = datetime.now(timezone.utc)
                    age = now - latest_data

                    if age > timedelta(hours=1):
                        logger.info(
                            f"⚠️ {symbol}: данные устарели на {age.total_seconds() / 3600:.1f} часов"
                        )
                        await self._load_historical_data(symbol)
                    else:
                        logger.debug(
                            f"✅ {symbol}: данные актуальны (возраст: {age.total_seconds() / 60:.1f} минут)"
                        )
                else:
                    logger.info(f"⚠️ {symbol}: нет данных, загружаем историю")
                    await self._load_historical_data(symbol)

        except Exception as e:
            logger.error(f"Ошибка проверки данных: {e}")

    async def _update_loop(self) -> None:
        """Основной цикл обновления"""
        while self.is_running:
            try:
                # Обновление данных для всех символов
                await self._update_all_symbols()

                # Ждем следующего обновления
                await asyncio.sleep(self.data_config["update_interval"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле обновления: {e}")
                await asyncio.sleep(60)  # Пауза перед повтором

    async def _update_all_symbols(self) -> None:
        """Обновление данных для всех символов"""
        logger.debug(f"🔄 Обновление данных для {len(self.trading_pairs)} символов...")

        update_tasks = []
        for symbol in self.trading_pairs:
            task = asyncio.create_task(self._update_symbol_data(symbol))
            update_tasks.append(task)

        if update_tasks:
            results = await asyncio.gather(*update_tasks, return_exceptions=True)

            # Подсчет успешных обновлений
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            if success_count > 0:
                logger.info(
                    f"✅ Обновлено {success_count}/{len(self.trading_pairs)} символов"
                )

            # Логирование ошибок
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Ошибка обновления {self.trading_pairs[i]}: {result}")

    async def _update_symbol_data(self, symbol: str) -> None:
        """Обновление данных для конкретного символа"""
        try:
            exchange = self.exchanges.get("bybit")
            if not exchange:
                return

            # Получение последнего времени данных
            latest_time = await self._get_latest_data_time(symbol)

            if latest_time:
                # Загружаем только новые данные с правильной timezone
                from datetime import timezone

                # Убеждаемся что latest_time в UTC
                if latest_time.tzinfo is None:
                    # Если naive, считаем что это UTC
                    latest_time = latest_time.replace(tzinfo=timezone.utc)

                end_time = datetime.now(timezone.utc)
                start_time = latest_time + timedelta(minutes=15)

                if start_time >= end_time:
                    return  # Нет новых данных

                # Загрузка свечей
                candles = await exchange.get_klines(symbol, "15", limit=200)

                if candles:
                    await self._save_candles(symbol, candles)
                    logger.debug(f"📊 {symbol}: загружено {len(candles)} новых свечей")

            else:
                # Первая загрузка
                await self._load_historical_data(symbol)

        except Exception as e:
            logger.error(f"Ошибка обновления {symbol}: {e}")

    async def _load_historical_data(self, symbol: str) -> None:
        """Загрузка исторических данных"""
        try:
            exchange = self.exchanges.get("bybit")
            if not exchange:
                return

            logger.info(f"📥 Загрузка исторических данных для {symbol}...")

            # Загружаем последние 7 дней 15-минутных свечей
            candles = await exchange.get_klines(symbol, "15", limit=1000)

            if candles:
                await self._save_candles(symbol, candles)
                logger.info(
                    f"✅ {symbol}: загружено {len(candles)} исторических свечей"
                )
            else:
                logger.warning(f"⚠️ {symbol}: не удалось загрузить исторические данные")

        except Exception as e:
            logger.error(f"Ошибка загрузки истории для {symbol}: {e}")

    async def _save_candles(self, symbol: str, candles: List[Any]) -> None:
        """Сохранение свечей в базу данных"""
        if not candles:
            return

        try:
            for candle in candles:
                # Парсинг данных свечи (формат Bybit)
                if isinstance(candle, list) and len(candle) >= 7:
                    timestamp = int(candle[0])
                    open_price = float(candle[1])
                    high_price = float(candle[2])
                    low_price = float(candle[3])
                    close_price = float(candle[4])
                    volume = float(candle[5])
                    turnover = float(candle[6]) if len(candle) > 6 else 0

                    # Сохранение в БД
                    await AsyncPGPool.execute(
                        """
                        INSERT INTO raw_market_data
                        (symbol, timestamp, datetime, open, high, low, close, volume,
                         interval_minutes, exchange, turnover)
                        VALUES ($1, $2, to_timestamp($2/1000), $3, $4, $5, $6, $7, $8, $9, $10)
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
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume,
                        15,
                        "bybit",
                        turnover,
                    )

        except Exception as e:
            logger.error(f"Ошибка сохранения свечей для {symbol}: {e}")

    async def _get_latest_data_time(self, symbol: str) -> Optional[datetime]:
        """Получение времени последних данных"""
        try:
            result = await AsyncPGPool.fetch(
                """
                SELECT MAX(datetime) as latest
                FROM raw_market_data
                WHERE symbol = $1
                  AND exchange = 'bybit'
                  AND interval_minutes = 15
            """,
                symbol,
            )

            if result and result[0]["latest"]:
                return result[0]["latest"]
            return None

        except Exception as e:
            logger.error(f"Ошибка получения последнего времени для {symbol}: {e}")
            return None

    async def force_update(self, symbols: Optional[List[str]] = None) -> None:
        """Принудительное обновление данных"""
        if symbols is None:
            symbols = self.trading_pairs

        logger.info(f"🔄 Принудительное обновление {len(symbols)} символов...")

        update_tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self._update_symbol_data(symbol))
            update_tasks.append(task)

        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)
            logger.info("✅ Принудительное обновление завершено")
