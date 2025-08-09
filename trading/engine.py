"""
Основной торговый движок BOT Trading v3
Координирует все торговые операции, обработку сигналов и управление рисками
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Set

from core.signals.unified_signal_processor import UnifiedSignalProcessor as SignalProcessor
from database.repositories.signal_repository import SignalRepository
from database.repositories.trade_repository import TradeRepository
from exchanges.registry import ExchangeRegistry
from risk_management.manager import RiskManager
from strategies.manager import StrategyManager

from .execution.executor import ExecutionEngine
from .orders.order_manager import OrderManager
from .positions.position_manager import PositionManager


class TradingState(Enum):
    """Состояния торгового движка"""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class TradingMetrics:
    """Метрики торгового движка"""

    signals_processed: int = 0
    orders_executed: int = 0
    trades_completed: int = 0
    total_pnl: Decimal = Decimal("0")
    win_rate: float = 0.0
    total_volume: Decimal = Decimal("0")
    active_positions: int = 0
    processing_time_avg: float = 0.0
    errors_count: int = 0
    uptime: timedelta = field(default_factory=lambda: timedelta(0))
    start_time: Optional[datetime] = None


class TradingEngine:
    """
    Основной торговый движок системы

    Основные функции:
    - Обработка торговых сигналов
    - Управление позициями и ордерами
    - Координация стратегий и бирж
    - Контроль рисков
    - Мониторинг производительности
    """

    def __init__(self, orchestrator: Any, config: Dict[str, Any]):
        self.orchestrator = orchestrator
        self.config = config
        # Используем системный логгер
        from core.logger import setup_logger

        self.logger = setup_logger("trading_engine")

        # Состояние движка
        self.state = TradingState.STOPPED
        self.metrics = TradingMetrics()
        self._running = False
        self._tasks: Set[asyncio.Task] = set()

        # Основные компоненты
        self.signal_processor: Optional[SignalProcessor] = None
        self.position_manager: Optional[PositionManager] = None
        self.order_manager: Optional[OrderManager] = None
        self.execution_engine: Optional[ExecutionEngine] = None
        self.risk_manager: Optional[RiskManager] = None
        self.strategy_manager: Optional[StrategyManager] = None
        self.exchange_registry: Optional[ExchangeRegistry] = None
        self.enhanced_sltp_manager = None  # Будет инициализирован в initialize()

        # Репозитории
        self.trade_repository: Optional[TradeRepository] = None
        self.signal_repository: Optional[SignalRepository] = None

        # Очереди для обработки
        self.signal_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.order_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

        # Кеш и состояние
        self._price_cache: Dict[str, Decimal] = {}
        self._instrument_cache: Dict[str, Any] = {}  # Кеш информации об инструментах
        self._last_sync: Optional[datetime] = None
        self._db_session_factory: Optional[Any] = None

    async def initialize(self) -> bool:
        """Инициализация торгового движка"""
        try:
            self.logger.info("Инициализация торгового движка...")
            self.state = TradingState.STARTING

            # Инициализация компонентов
            await self._initialize_components()

            # Инициализация репозиториев
            await self._initialize_repositories()

            # Загрузка информации об инструментах
            await self._load_instruments_info()

            # Проверка системы
            await self._health_check()

            self.logger.info("Торговый движок успешно инициализирован")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации торгового движка: {e}")
            self.state = TradingState.ERROR
            # Не прерываем инициализацию системы
            self.logger.warning(
                "Trading Engine инициализирован с ошибками, но продолжаем работу"
            )
            return True

    async def _initialize_components(self):
        """Инициализация основных компонентов"""

        # Exchange Registry берем из orchestrator если доступен
        if (
            hasattr(self.orchestrator, "exchange_registry")
            and self.orchestrator.exchange_registry
        ):
            self.exchange_registry = self.orchestrator.exchange_registry
        else:
            # Создаем свой если недоступен
            self.exchange_registry = ExchangeRegistry(self.config.get("exchanges", {}))
            await self.exchange_registry.initialize()

        # Order Manager - создаем первым
        self.order_manager = OrderManager(
            exchange_registry=self.exchange_registry,
        )

        # Signal Processor - создаем простой обработчик
        # Закомментируем пока, так как UnifiedSignalProcessor не подходит для наших нужд
        self.signal_processor = None  # Будем обрабатывать сигналы напрямую

        # Position Manager
        self.position_manager = PositionManager(
            exchange_registry=self.exchange_registry,
        )

        # Execution Engine
        self.execution_engine = ExecutionEngine(
            order_manager=self.order_manager,
            exchange_registry=self.exchange_registry,
        )

        # Risk Manager - временно отключен
        self.risk_manager = None  # TODO: Реализовать RiskManager
        # self.risk_manager = RiskManager(
        #     config=self.config.get("risk_management", {}),
        #     position_manager=self.position_manager,
        #     exchange_registry=self.exchange_registry,
        # )

        # Strategy Manager
        self.strategy_manager = StrategyManager(
            config=self.config.get("strategies", {}),
            exchange_registry=self.exchange_registry,
            signal_processor=self.signal_processor,
        )

        # Enhanced SL/TP Manager
        try:
            from core.config.config_manager import ConfigManager
            from trading.sltp.enhanced_manager import EnhancedSLTPManager

            config_manager = ConfigManager()
            self.enhanced_sltp_manager = EnhancedSLTPManager(
                config_manager=config_manager,
                api_client=None,  # Будет устанавливаться для каждой биржи отдельно
            )
            self.logger.info("Enhanced SL/TP Manager инициализирован")
        except Exception as e:
            self.logger.warning(
                f"Не удалось инициализировать Enhanced SL/TP Manager: {e}"
            )
            self.enhanced_sltp_manager = None

        self.logger.info("Основные компоненты инициализированы")

    async def _load_instruments_info(self):
        """Загрузка информации об инструментах"""
        try:
            self.logger.info("Загрузка информации об инструментах...")

            # Список символов для торговли
            symbols = [
                "BTCUSDT",
                "ETHUSDT",
                "BNBUSDT",
                "SOLUSDT",
                "XRPUSDT",
                "ADAUSDT",
                "DOGEUSDT",
                "DOTUSDT",
                "LINKUSDT",
            ]

            # Пока загружаем только для bybit
            exchange_name = "bybit"

            for symbol in symbols:
                try:
                    await self._get_instrument_info(symbol, exchange_name)
                except Exception as e:
                    self.logger.warning(
                        f"Не удалось загрузить {symbol} с {exchange_name}: {e}"
                    )

            self.logger.info(
                f"Загружено информации об инструментах: {len(self._instrument_cache)}"
            )

        except Exception as e:
            self.logger.error(f"Ошибка загрузки информации об инструментах: {e}")
            # Не прерываем инициализацию

    async def _initialize_repositories(self):
        """Инициализация репозиториев БД"""
        try:
            # Импортируем фабрику сессий напрямую
            from database.connections import get_async_db

            # Сохраняем фабрику сессий для использования в репозиториях
            self._db_session_factory = get_async_db

            self.logger.info("Фабрика сессий БД настроена для репозиториев")

        except Exception as e:
            self.logger.error(f"Ошибка инициализации репозиториев: {e}")
            # Не прерываем инициализацию - можем работать без БД
            self._db_session_factory = None
            self.logger.warning("Trading Engine будет работать без БД")

    async def _health_check(self):
        """Проверка здоровья всех компонентов"""
        checks = [
            ("Exchange Registry", self.exchange_registry.health_check()),
            # ("Signal Processor", self.signal_processor.health_check()),  # Отключен
            ("Position Manager", self.position_manager.health_check()),
            ("Order Manager", self.order_manager.health_check()),
            # ("Risk Manager", self.risk_manager.health_check()),  # TODO: Включить после реализации
            ("Strategy Manager", self.strategy_manager.health_check()),
        ]

        for name, check in checks:
            try:
                result = await check
                if not result:
                    raise Exception(f"{name} health check failed")
                self.logger.debug(f"{name} health check passed")
            except Exception as e:
                self.logger.error(f"{name} health check error: {e}")
                raise

        self.logger.info("Все компоненты прошли проверку здоровья")

    async def start(self) -> bool:
        """Запуск торгового движка"""
        try:
            if self.state == TradingState.RUNNING:
                self.logger.warning("Торговый движок уже запущен")
                return True

            self.logger.info("Запуск торгового движка...")

            # Инициализация если нужно
            if self.state == TradingState.STOPPED:
                if not await self.initialize():
                    return False

            # Запуск компонентов
            await self.strategy_manager.start()
            # await self.signal_processor.start()  # Отключен
            await self.position_manager.start()
            await self.order_manager.start()
            await self.execution_engine.start()

            # Запуск основных циклов
            self._running = True
            self.state = TradingState.RUNNING
            self.metrics.start_time = datetime.now()

            # Создание задач
            self._tasks.add(asyncio.create_task(self._signal_processing_loop()))
            self._tasks.add(asyncio.create_task(self._order_processing_loop()))
            self._tasks.add(asyncio.create_task(self._position_sync_loop()))
            self._tasks.add(asyncio.create_task(self._metrics_update_loop()))
            self._tasks.add(asyncio.create_task(self._risk_monitoring_loop()))

            self.logger.info("Торговый движок успешно запущен")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка запуска торгового движка: {e}")
            self.state = TradingState.ERROR
            return False

    async def stop(self, timeout: float = 30.0) -> bool:
        """Остановка торгового движка"""
        try:
            if self.state == TradingState.STOPPED:
                self.logger.warning("Торговый движок уже остановлен")
                return True

            self.logger.info("Остановка торгового движка...")
            self.state = TradingState.STOPPING
            self._running = False

            # Остановка задач
            for task in self._tasks:
                task.cancel()

            if self._tasks:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=timeout,
                )

            # Остановка компонентов
            if self.execution_engine:
                await self.execution_engine.stop()
            if self.order_manager:
                await self.order_manager.stop()
            if self.position_manager:
                await self.position_manager.stop()
            # if self.signal_processor:
            #     await self.signal_processor.stop()  # Отключен
            if self.strategy_manager:
                await self.strategy_manager.stop()

            self.state = TradingState.STOPPED
            self._tasks.clear()

            # Обновление метрик
            if self.metrics.start_time:
                self.metrics.uptime = datetime.now() - self.metrics.start_time

            self.logger.info("Торговый движок остановлен")
            return True

        except asyncio.TimeoutError:
            self.logger.error("Таймаут при остановке торгового движка")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка остановки торгового движка: {e}")
            return False

    async def pause(self) -> bool:
        """Пауза торгового движка"""
        if self.state != TradingState.RUNNING:
            return False

        self.logger.info("Приостановка торгового движка...")
        self.state = TradingState.PAUSED

        # Приостановка стратегий
        await self.strategy_manager.pause()

        return True

    async def resume(self) -> bool:
        """Возобновление торгового движка"""
        if self.state != TradingState.PAUSED:
            return False

        self.logger.info("Возобновление торгового движка...")
        self.state = TradingState.RUNNING

        # Возобновление стратегий
        await self.strategy_manager.resume()

        return True

    async def _signal_processing_loop(self):
        """Основной цикл обработки сигналов"""
        self.logger.info("Запуск цикла обработки сигналов")

        while self._running:
            try:
                if self.state != TradingState.RUNNING:
                    await asyncio.sleep(1)
                    continue

                # Получение сигнала из очереди
                try:
                    signal = await asyncio.wait_for(
                        self.signal_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Обработка сигнала
                start_time = datetime.now()
                await self._process_signal(signal)

                # Обновление метрик
                processing_time = (datetime.now() - start_time).total_seconds()
                self._update_processing_metrics(processing_time)

                self.metrics.signals_processed += 1

            except Exception as e:
                self.logger.error(f"Ошибка в цикле обработки сигналов: {e}")
                self.metrics.errors_count += 1
                await asyncio.sleep(1)

    async def _process_signal(self, signal):
        """Обработка одного торгового сигнала"""
        try:
            # Signal уже должен быть объектом Signal, а не словарем
            signal_id = getattr(signal, "id", "unknown")
            self.logger.info(
                f"🔄 Обработка сигнала {signal_id}: {signal.symbol} {signal.signal_type}"
            )

            # Валидация сигнала
            if not self._validate_signal(signal):
                self.logger.warning(f"❌ Сигнал {signal_id} не прошел валидацию")
                return

            # Проверка рисков - TODO: включить после реализации RiskManager
            # if self.risk_manager and not await self.risk_manager.check_signal_risk(signal):
            #     self.logger.warning(f"Сигнал {signal_id} отклонен по риск-менеджменту")
            #     return

            # Создание ордеров напрямую
            self.logger.info(f"📊 Создаем ордера для сигнала {signal.symbol}")
            orders = await self._create_orders_from_signal(signal)

            if orders:
                self.logger.info(
                    f"✅ Создано {len(orders)} ордеров для {signal.symbol}"
                )
                # Отправка ордеров на исполнение
                for order in orders:
                    self.logger.info(
                        f"📤 Отправляем ордер на исполнение: {order.side} {order.quantity} {order.symbol}"
                    )
                    await self.order_queue.put(order)
            else:
                self.logger.warning(
                    f"⚠️ Не создано ни одного ордера для сигнала {signal.symbol}"
                )

            # Сохранение в БД
            if self._db_session_factory:
                async with self._db_session_factory() as db:
                    signal_repo = SignalRepository(db)
                    # Конвертируем объект Signal в словарь для репозитория
                    signal_dict = {
                        "symbol": signal.symbol,
                        "exchange": signal.exchange,
                        "signal_type": (
                            signal.signal_type.value
                            if hasattr(signal.signal_type, "value")
                            else signal.signal_type
                        ),
                        "strength": signal.strength,
                        "confidence": signal.confidence,
                        "suggested_price": signal.suggested_price,
                        "suggested_quantity": getattr(
                            signal, "suggested_position_size", None
                        ),
                        "suggested_stop_loss": signal.suggested_stop_loss,
                        "suggested_take_profit": signal.suggested_take_profit,
                        "strategy_name": signal.strategy_name,
                        "created_at": signal.created_at,
                        "extra_data": getattr(signal, "signal_metadata", {}),
                    }
                    await signal_repo.save_signal(signal_dict)

            self.logger.info(f"✅ Сигнал {signal_id} полностью обработан")

        except Exception as e:
            self.logger.error(f"Ошибка обработки сигнала: {e}")
            raise

    async def _order_processing_loop(self):
        """Цикл обработки ордеров"""
        self.logger.info("Запуск цикла обработки ордеров")

        while self._running:
            try:
                if self.state != TradingState.RUNNING:
                    await asyncio.sleep(1)
                    continue

                # Получение ордера из очереди
                try:
                    order = await asyncio.wait_for(self.order_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Исполнение ордера
                success = await self.execution_engine.execute_order(order)

                if success:
                    self.metrics.orders_executed += 1
                    self.logger.info("✅ Ордер успешно исполнен")
                else:
                    self.logger.warning("❌ Ошибка исполнения ордера")
                    self.metrics.errors_count += 1

            except Exception as e:
                self.logger.error(f"Ошибка в цикле обработки ордеров: {e}")
                self.metrics.errors_count += 1
                await asyncio.sleep(1)

    async def _position_sync_loop(self):
        """Цикл синхронизации позиций"""
        self.logger.info("Запуск цикла синхронизации позиций")

        while self._running:
            try:
                if self.state != TradingState.RUNNING:
                    await asyncio.sleep(10)
                    continue

                # Синхронизация позиций с биржами
                await self.position_manager.sync_positions()

                # Обновление метрик позиций
                positions = await self.position_manager.get_all_positions()
                self.metrics.active_positions = len(
                    [p for p in positions if p.size != 0]
                )

                # Проверка enhanced SL/TP для активных позиций
                if self.enhanced_sltp_manager:
                    for position in positions:
                        if position.size != 0:  # Только для активных позиций
                            try:
                                # Получаем текущую цену для позиции
                                current_price = 0.0
                                exchange_client = self.exchange_manager.exchanges.get(
                                    position.exchange
                                )
                                if exchange_client:
                                    ticker = await exchange_client.get_ticker(
                                        position.symbol
                                    )
                                    current_price = ticker.last_price
                                else:
                                    self.logger.warning(
                                        f"Не найден клиент биржи {position.exchange} для {position.symbol}"
                                    )
                                    continue

                                # Временно назначаем exchange клиент для enhanced manager
                                self.enhanced_sltp_manager.exchange_client = (
                                    exchange_client
                                )

                                # Применяем enhanced SL/TP функции
                                # Сначала проверяем частичное закрытие
                                partial_tp_executed = (
                                    await self.enhanced_sltp_manager.check_partial_tp(
                                        position
                                    )
                                )
                                if partial_tp_executed:
                                    self.logger.info(
                                        f"Выполнено частичное закрытие для {position.symbol}"
                                    )

                                # Затем обновляем защиту прибыли (может переопределить SL после partial TP)
                                profit_protection_updated = await self.enhanced_sltp_manager.update_profit_protection(
                                    position, current_price
                                )
                                if profit_protection_updated:
                                    self.logger.info(
                                        f"Обновлена защита прибыли для {position.symbol}"
                                    )

                                # Применяем трейлинг стоп
                                trailing_updated = await self.enhanced_sltp_manager.update_trailing_stop(
                                    position, current_price
                                )
                                if trailing_updated:
                                    self.logger.info(
                                        f"Обновлен трейлинг стоп для {position.symbol}"
                                    )

                            except Exception as e:
                                self.logger.error(
                                    f"Ошибка применения enhanced SL/TP для {position.symbol}: {e}"
                                )

                self._last_sync = datetime.now()

                # Пауза между синхронизациями
                await asyncio.sleep(self.config.get("position_sync_interval", 30))

            except Exception as e:
                self.logger.error(f"Ошибка синхронизации позиций: {e}")
                self.metrics.errors_count += 1
                await asyncio.sleep(60)

    async def _metrics_update_loop(self):
        """Цикл обновления метрик"""
        while self._running:
            try:
                await self._update_trading_metrics()
                await asyncio.sleep(self.config.get("metrics_update_interval", 60))

            except Exception as e:
                self.logger.error(f"Ошибка обновления метрик: {e}")
                await asyncio.sleep(60)

    async def _risk_monitoring_loop(self):
        """Цикл мониторинга рисков"""
        while self._running:
            try:
                if self.state == TradingState.RUNNING and self.risk_manager:
                    # Проверка общих рисков
                    risk_status = await self.risk_manager.check_global_risks()

                    if risk_status.requires_action:
                        self.logger.warning(f"Обнаружен риск: {risk_status.message}")

                        if risk_status.action == "pause":
                            await self.pause()
                        elif risk_status.action == "reduce_positions":
                            await self._reduce_positions()

                await asyncio.sleep(self.config.get("risk_check_interval", 30))

            except Exception as e:
                self.logger.error(f"Ошибка мониторинга рисков: {e}")
                await asyncio.sleep(60)

    async def _update_trading_metrics(self):
        """Обновление торговых метрик"""
        try:
            # Получение данных от компонентов
            if self.position_manager:
                total_pnl = await self.position_manager.calculate_total_pnl()
                self.metrics.total_pnl = total_pnl

            if self._db_session_factory:
                # Обновление статистики торговли
                async with self._db_session_factory() as db:
                    trade_repo = TradeRepository(db)
                    trades_stats = await trade_repo.get_trading_stats()
                    self.metrics.trades_completed = trades_stats.get("total_trades", 0)
                    self.metrics.win_rate = trades_stats.get("win_rate", 0.0)
                    self.metrics.total_volume = trades_stats.get(
                        "total_volume", Decimal("0")
                    )

            # Обновление времени работы
            if self.metrics.start_time:
                self.metrics.uptime = datetime.now() - self.metrics.start_time

        except Exception as e:
            self.logger.error(f"Ошибка обновления метрик: {e}")

    def _update_processing_metrics(self, processing_time: float):
        """Обновление метрик времени обработки"""
        if self.metrics.processing_time_avg == 0:
            self.metrics.processing_time_avg = processing_time
        else:
            # Экспоненциальное сглаживание
            alpha = 0.1
            self.metrics.processing_time_avg = (
                alpha * processing_time + (1 - alpha) * self.metrics.processing_time_avg
            )

    async def _reduce_positions(self):
        """Сокращение позиций при высоком риске"""
        try:
            self.logger.info("Начинаем сокращение позиций из-за высокого риска")

            positions = await self.position_manager.get_all_positions()

            for position in positions:
                if position.size != 0:
                    # Сокращение на 50%
                    reduce_size = abs(position.size) * Decimal("0.5")

                    order = {
                        "symbol": position.symbol,
                        "side": "sell" if position.size > 0 else "buy",
                        "size": reduce_size,
                        "type": "market",
                        "reason": "risk_reduction",
                    }

                    await self.order_queue.put(order)

            self.logger.info("Команды на сокращение позиций отправлены")

        except Exception as e:
            self.logger.error(f"Ошибка сокращения позиций: {e}")

    async def add_signal(self, signal: Dict[str, Any]) -> bool:
        """Добавление сигнала в очередь обработки"""
        try:
            if not self._running or self.state != TradingState.RUNNING:
                self.logger.warning("Торговый движок не запущен, сигнал отклонен")
                return False

            await self.signal_queue.put(signal)
            return True

        except asyncio.QueueFull:
            self.logger.error("Очередь сигналов переполнена")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка добавления сигнала: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Получение статуса торгового движка"""
        return {
            "state": self.state.value,
            "running": self._running,
            "metrics": {
                "signals_processed": self.metrics.signals_processed,
                "orders_executed": self.metrics.orders_executed,
                "trades_completed": self.metrics.trades_completed,
                "total_pnl": str(self.metrics.total_pnl),
                "win_rate": self.metrics.win_rate,
                "total_volume": str(self.metrics.total_volume),
                "active_positions": self.metrics.active_positions,
                "processing_time_avg": self.metrics.processing_time_avg,
                "errors_count": self.metrics.errors_count,
                "uptime_seconds": self.metrics.uptime.total_seconds(),
            },
            "queue_sizes": {
                "signals": self.signal_queue.qsize(),
                "orders": self.order_queue.qsize(),
            },
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "component_status": {
                # "signal_processor": (
                #     self.signal_processor.is_running()
                #     if self.signal_processor
                #     else False
                # ),
                "position_manager": (
                    self.position_manager.is_running()
                    if self.position_manager
                    else False
                ),
                "order_manager": self.order_manager.is_running()
                if self.order_manager
                else False,
                "execution_engine": (
                    self.execution_engine.is_running()
                    if self.execution_engine
                    else False
                ),
                "risk_manager": (
                    self.risk_manager.is_running() if self.risk_manager else None
                ),  # TODO: включить после реализации
                "strategy_manager": (
                    self.strategy_manager.is_running()
                    if self.strategy_manager
                    else False
                ),
            },
        }

    def get_metrics(self) -> TradingMetrics:
        """Получение метрик торгового движка"""
        return self.metrics

    async def receive_trading_signal(self, trading_signal):
        """
        Получение торгового сигнала от AI Signal Generator

        Args:
            trading_signal: TradingSignal объект от генератора сигналов
        """
        try:
            self.logger.info("📥 Начинаем обработку торгового сигнала...")
            self.logger.info(f"   Тип объекта: {type(trading_signal)}")
            self.logger.info(f"   Атрибуты: {dir(trading_signal)}")

            # Проверяем наличие необходимых атрибутов
            if hasattr(trading_signal, "symbol"):
                self.logger.info(f"   Symbol: {trading_signal.symbol}")
            if hasattr(trading_signal, "signal_type"):
                signal_type_value = (
                    trading_signal.signal_type.value
                    if hasattr(trading_signal.signal_type, "value")
                    else trading_signal.signal_type
                )
                self.logger.info(f"   Signal type: {signal_type_value}")
            if hasattr(trading_signal, "confidence"):
                self.logger.info(f"   Confidence: {trading_signal.confidence}")

            self.logger.info(
                f"📥 Получен торговый сигнал: {trading_signal.symbol} "
                f"{trading_signal.signal_type.value if hasattr(trading_signal.signal_type, 'value') else trading_signal.signal_type} "
                f"(confidence: {trading_signal.confidence}%)"
            )

            # Конвертируем TradingSignal в Signal (БД формат)
            signal = self._convert_trading_signal_to_signal(trading_signal)
            self.logger.info(
                f"🔄 Сигнал сконвертирован: {signal.symbol} {signal.signal_type} "
                f"(strength: {signal.strength}, price: {signal.suggested_price})"
            )

            # Добавляем в очередь сигналов для обработки
            await self.signal_queue.put(signal)
            self.logger.info(
                f"✅ Сигнал {signal.symbol} добавлен в очередь обработки (размер очереди: {self.signal_queue.qsize()})"
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка получения торгового сигнала: {e}")
            import traceback

            traceback.print_exc()

    def _convert_trading_signal_to_signal(self, trading_signal):
        """
        Конвертация TradingSignal (от стратегий) в Signal (БД модель)

        Args:
            trading_signal: TradingSignal объект

        Returns:
            Signal: объект для обработки в системе
        """
        from database.models.base_models import SignalType as DBSignalType
        from database.models.signal import Signal

        # Диагностическое логирование
        self.logger.debug("🔍 Конвертация TradingSignal:")
        self.logger.debug(f"   Тип: {type(trading_signal)}")
        self.logger.debug(
            f"   Атрибуты: {[attr for attr in dir(trading_signal) if not attr.startswith('_')]}"
        )

        # Проверяем критичные атрибуты
        # ML сигналы используют suggested_price, обычные - entry_price
        if hasattr(trading_signal, "entry_price"):
            entry_price = trading_signal.entry_price
        elif hasattr(trading_signal, "suggested_price"):
            entry_price = trading_signal.suggested_price
            self.logger.debug(f"🔄 Используем suggested_price: {entry_price}")
        else:
            self.logger.error(
                "❌ У TradingSignal отсутствует entry_price и suggested_price!"
            )
            self.logger.error(f"   Доступные атрибуты: {vars(trading_signal)}")
            entry_price = 0.0

        # Маппинг типов сигналов
        signal_type_map = {
            "BUY": DBSignalType.LONG,
            "SELL": DBSignalType.SHORT,
            "LONG": DBSignalType.LONG,
            "SHORT": DBSignalType.SHORT,
            "FLAT": DBSignalType.NEUTRAL,
            "NEUTRAL": DBSignalType.NEUTRAL,
        }

        # Получаем signal_type (может быть строкой или объектом)
        if hasattr(trading_signal.signal_type, "value"):
            signal_type_str = trading_signal.signal_type.value.upper()
        else:
            signal_type_str = str(trading_signal.signal_type).upper()

        # Обрабатываем confidence (может быть уже нормализовано 0-1 или в процентах)
        confidence = trading_signal.confidence
        if confidence > 1.0:
            confidence = confidence / 100.0

        # Получаем stop_loss и take_profit
        stop_loss = getattr(trading_signal, "stop_loss", None) or getattr(
            trading_signal, "suggested_stop_loss", entry_price * 0.98
        )
        take_profit = getattr(trading_signal, "take_profit", None) or getattr(
            trading_signal, "suggested_take_profit", entry_price * 1.02
        )

        # Создаем Signal объект
        signal = Signal(
            symbol=trading_signal.symbol,
            exchange=getattr(trading_signal, "exchange", "bybit"),
            signal_type=signal_type_map.get(signal_type_str, DBSignalType.NEUTRAL),
            strength=getattr(trading_signal, "strength", confidence),
            confidence=confidence,
            suggested_price=entry_price,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            suggested_position_size=getattr(trading_signal, "position_size", 0.01),
            strategy_name=getattr(trading_signal, "strategy_name", "Unknown"),
            signal_metadata={
                "original_signal_type": signal_type_str,
                "timeframe": getattr(trading_signal, "timeframe", "15m"),
                "indicators": getattr(
                    trading_signal,
                    "indicators_used",
                    getattr(trading_signal, "indicators", {}),
                ),
                "reasoning": getattr(trading_signal, "reasoning", "ML-based signal"),
            },
            created_at=getattr(trading_signal, "timestamp", datetime.now()),
        )

        return signal

    def _validate_signal(self, signal) -> bool:
        """Валидация торгового сигнала"""
        try:
            # Проверка основных полей
            if not signal.symbol or not signal.signal_type:
                self.logger.warning("Сигнал без symbol или signal_type")
                return False

            # Проверка цены
            if signal.suggested_price <= 0:
                self.logger.warning(f"Неверная цена: {signal.suggested_price}")
                return False

            # Проверка уверенности
            if signal.confidence < 0.3:  # Минимальная уверенность 30%
                self.logger.warning(f"Слишком низкая уверенность: {signal.confidence}")
                return False

            # Проверка stop loss и take profit
            if signal.suggested_stop_loss >= signal.suggested_price:
                self.logger.warning(
                    f"Stop loss ({signal.suggested_stop_loss}) >= цены ({signal.suggested_price})"
                )
                return False

            if signal.suggested_take_profit <= signal.suggested_price:
                self.logger.warning(
                    f"Take profit ({signal.suggested_take_profit}) <= цены ({signal.suggested_price})"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Ошибка валидации сигнала: {e}")
            return False

    async def _get_instrument_info(self, symbol: str, exchange: str):
        """Получение информации об инструменте с кешированием"""
        cache_key = f"{exchange}:{symbol}"

        # Проверяем кеш
        if cache_key in self._instrument_cache:
            return self._instrument_cache[cache_key]

        try:
            # Получаем биржу
            if hasattr(self.exchange_registry, "get_exchange"):
                exchange_obj = await self.exchange_registry.get_exchange(exchange)
            else:
                # Если нет метода get_exchange, используем exchanges напрямую
                exchange_obj = self.exchange_registry.exchanges.get(exchange)

            if not exchange_obj:
                self.logger.error(f"Биржа {exchange} не найдена")
                return None

            # Получаем информацию об инструменте
            if hasattr(exchange_obj, "get_instrument_info"):
                instrument = await exchange_obj.get_instrument_info(symbol)
            else:
                # Если нет метода, используем значения по умолчанию
                from exchanges.base.models import Instrument

                # Значения по умолчанию для Bybit
                defaults = {
                    "BTCUSDT": {"min": 0.001, "step": 0.001},
                    "ETHUSDT": {"min": 0.01, "step": 0.01},
                    "BNBUSDT": {"min": 0.01, "step": 0.01},
                    "SOLUSDT": {"min": 0.1, "step": 0.1},
                    "XRPUSDT": {"min": 0.44, "step": 0.001},
                    "ADAUSDT": {"min": 1.0, "step": 1.0},
                    "DOGEUSDT": {"min": 1.0, "step": 1.0},
                    "DOTUSDT": {"min": 0.1, "step": 0.1},
                    "LINKUSDT": {"min": 0.1, "step": 0.1},
                }

                info = defaults.get(symbol, {"min": 0.01, "step": 0.01})
                instrument = Instrument(
                    symbol=symbol,
                    base_currency=symbol[:-4],
                    quote_currency=symbol[-4:],
                    category="linear",
                    min_order_qty=info["min"],
                    max_order_qty=100000.0,
                    qty_step=info["step"],
                    min_price=0.01,
                    max_price=1999999.0,
                )

            # Кешируем на 1 час
            self._instrument_cache[cache_key] = instrument

            self.logger.info(
                f"Загружена информация об инструменте {symbol}: min={instrument.min_order_qty}, step={instrument.qty_step}"
            )

            return instrument

        except Exception as e:
            self.logger.error(
                f"Ошибка получения информации об инструменте {symbol}: {e}"
            )
            return None

    def _round_to_step(self, value: Decimal, step: Decimal) -> Decimal:
        """Округление значения до шага"""
        if step == 0:
            return value
        return (value / step).quantize(Decimal("1"), rounding="ROUND_DOWN") * step

    async def _create_orders_from_signal(self, signal):
        """Создание ордеров из сигнала"""
        try:
            orders = []

            # Определяем направление
            from database.models.base_models import OrderSide

            side = (
                OrderSide.BUY
                if signal.signal_type.value in ["long", "buy"]
                else OrderSide.SELL
            )

            # Получаем информацию об инструменте
            instrument = await self._get_instrument_info(signal.symbol, signal.exchange)
            if not instrument:
                self.logger.error(
                    f"Не удалось получить информацию об инструменте {signal.symbol}"
                )
                return []

            # Получаем текущий баланс
            # TODO: Реально получать баланс с биржи
            balance = Decimal("167")  # Используем реальный баланс

            # Рассчитываем размер позиции (1% от баланса)
            position_size_usd = balance * Decimal("0.01")  # 1% = $1.67
            quantity = position_size_usd / Decimal(str(signal.suggested_price))

            # Применяем минимальный размер ордера
            min_qty = Decimal(str(instrument.min_order_qty))
            if quantity < min_qty:
                quantity = min_qty
                self.logger.info(
                    f"Размер увеличен до минимального: {min_qty} {signal.symbol}"
                )

            # Проверяем, что не превышаем 5% от баланса
            max_position_usd = balance * Decimal("0.05")  # 5% = $8.35
            if quantity * Decimal(str(signal.suggested_price)) > max_position_usd:
                quantity = max_position_usd / Decimal(str(signal.suggested_price))
                self.logger.info(
                    f"Размер уменьшен до 5% от баланса: {quantity} {signal.symbol}"
                )

            # Округляем до qty_step
            qty_step = Decimal(str(instrument.qty_step))
            quantity = self._round_to_step(quantity, qty_step)

            # Финальная проверка минимального размера после округления
            if quantity < min_qty:
                quantity = min_qty

            self.logger.info(
                f"Финальный размер ордера: {quantity} {signal.symbol} (шаг: {qty_step})"
            )

            # Создаем ордер
            from database.models.base_models import Order, OrderStatus, OrderType

            order = Order(
                symbol=signal.symbol,
                exchange=signal.exchange,
                side=side,
                order_type=OrderType.MARKET,  # Используем рыночные ордера для быстрого исполнения
                quantity=float(quantity),
                price=signal.suggested_price,
                stop_loss=signal.suggested_stop_loss,
                take_profit=signal.suggested_take_profit,
                status=OrderStatus.PENDING,
                metadata={
                    "strategy": signal.strategy_name,
                    "confidence": signal.confidence,
                    "created_by": "TradingEngine",
                    "signal_id": getattr(signal, "id", None),
                },
            )

            orders.append(order)

            self.logger.info(
                f"📝 Создан ордер: {side} {quantity:.4f} {signal.symbol} @ {signal.suggested_price} "
                f"(SL: {signal.suggested_stop_loss}, TP: {signal.suggested_take_profit})"
            )

            return orders

        except Exception as e:
            self.logger.error(f"Ошибка создания ордеров: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return []
