"""
Основной торговый движок BOT Trading v3
Координирует все торговые операции, обработку сигналов и управление рисками
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

# Удалено: UnifiedSignalProcessor пока не используется, signal_processor установлен в None
# from core.signals.unified_signal_processor import UnifiedSignalProcessor as SignalProcessor
from core.system.balance_manager import balance_manager
from core.system.process_monitor import process_monitor
from core.system.rate_limiter import rate_limiter
from core.system.signal_deduplicator import signal_deduplicator
from core.system.worker_coordinator import worker_coordinator

# Импортируем новую архитектуру БД
from database.database_manager import DatabaseManager

# Импортируем модели для создания ордеров
from database.models.base_models import Order, OrderSide, OrderStatus, OrderType, SignalType
from database.repositories.order_repository import OrderRepository
from database.repositories.signal_repository import SignalRepository
from database.repositories.trade_repository import TradeRepository
from exchanges.exchange_manager import ExchangeManager
from risk_management.manager import RiskManager
from strategies.manager import StrategyManager

from .execution.executor import ExecutionEngine
from .orders.order_manager import OrderManager

# from .positions.position_manager import PositionManager  # Удален legacy класс
from .position_tracker import EnhancedPositionTracker, get_position_tracker


class TradingState(Enum):
    """Состояния торгового движка"""

    STOPPED = "stopped"
    STARTING = "starting"
    INITIALIZED = "initialized"  # Инициализирован, но не запущен
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
    start_time: datetime | None = None
    # Добавляем недостающие атрибуты
    total_signals: int = 0
    total_orders: int = 0
    total_trades: int = 0


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

    def __init__(self, orchestrator: Any, config: dict[str, Any]):
        self.orchestrator = orchestrator
        self.config = config
        # Используем системный логгер
        from core.logger import setup_logger

        self.logger = setup_logger("trading_engine")

        # Состояние движка
        self.state = TradingState.STOPPED
        self.metrics = TradingMetrics()
        self._running = False
        self._tasks: set[asyncio.Task] = set()

        # Основные компоненты
        self.signal_processor = None  # Пока не используется, заменен на ML сигналы через ml_manager
        # self.position_manager: PositionManager | None = None  # Legacy, заменен на position_tracker
        self.position_tracker: EnhancedPositionTracker | None = None  # Enhanced Position Tracker
        self.order_manager: OrderManager | None = None
        self.execution_engine: ExecutionEngine | None = None
        self.risk_manager: RiskManager | None = None
        self.strategy_manager: StrategyManager | None = None
        self.exchange_registry: ExchangeManager | None = None
        self.enhanced_sltp_manager = None  # Будет инициализирован в initialize()

        # Менеджер БД и репозитории
        self._db_manager = None
        self.trade_repository: TradeRepository | None = None
        self.signal_repository: SignalRepository | None = None
        self.order_repository: OrderRepository | None = None

        # Очереди для обработки
        self.signal_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.order_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

        # Кеш и состояние
        self._price_cache: dict[str, Decimal] = {}
        self._instrument_cache: dict[str, Any] = {}  # Кеш информации об инструментах
        self._recent_signal_times: dict[str, float] = {}  # Защита от частых сигналов
        self._last_sync: datetime | None = None

    async def initialize(self) -> bool:
        """Инициализация торгового движка"""
        try:
            self.logger.info("Инициализация торгового движка...")
            self.state = TradingState.STARTING

            # Инициализация системных компонентов
            await self._initialize_system_components()

            # Инициализация компонентов
            await self._initialize_components()

            # Инициализация репозиториев
            await self._initialize_repositories()

            # Загрузка информации об инструментах
            await self._load_instruments_info()

            # Проверка системы
            await self._health_check()

            # Регистрируемся в координаторе воркеров
            self.worker_id = await worker_coordinator.register_worker(
                worker_type="trading_engine",
                metadata={
                    "state": self.state.value,
                    "active_exchanges": (
                        len(getattr(self.exchange_registry, "exchanges", {}))
                        if self.exchange_registry
                        else 0
                    ),
                    "signal_queue_size": self.signal_queue.qsize(),
                    "order_queue_size": self.order_queue.qsize(),
                },
            )

            if not self.worker_id:
                self.logger.error("❌ Другой Trading Engine уже активен")
                raise RuntimeError("Duplicate Trading Engine detected")

            # Регистрируем в мониторе процессов
            await process_monitor.register_component("trading_engine")

            # Устанавливаем состояние как инициализированный
            self.state = TradingState.INITIALIZED
            self.logger.info("✅ Торговый движок успешно инициализирован")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации торгового движка: {e}")
            self.state = TradingState.ERROR
            # Не прерываем инициализацию системы
            self.logger.warning("Trading Engine инициализирован с ошибками, но продолжаем работу")
            return True

    async def _initialize_system_components(self):
        """Инициализация системных компонентов мониторинга и контроля"""
        try:
            # Запускаем системные компоненты
            await worker_coordinator.start()
            await process_monitor.start()

            # Инициализируем и сохраняем balance_manager как атрибут класса
            from core.system.balance_manager import balance_manager

            self.balance_manager = balance_manager
            # НЕ запускаем balance_manager сразу - сначала нужно установить exchange_manager

            # Также сохраняем другие компоненты для удобства
            self.worker_coordinator = worker_coordinator
            self.process_monitor = process_monitor
            self.signal_deduplicator = signal_deduplicator
            self.rate_limiter = rate_limiter

            self.logger.info("✅ Системные компоненты инициализированы")
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации системных компонентов: {e}")
            raise

    async def _initialize_components(self):
        """Инициализация основных компонентов"""

        # Enhanced SL/TP Manager - инициализируем первым
        try:
            from core.config.config_manager import ConfigManager
            from trading.sltp.enhanced_manager import EnhancedSLTPManager

            config_manager = ConfigManager()
            self.enhanced_sltp_manager = EnhancedSLTPManager(config_manager=config_manager)
            self.logger.info("Enhanced SL/TP Manager инициализирован")
        except Exception as e:
            self.logger.warning(f"Не удалось инициализировать Enhanced SL/TP Manager: {e}")
            self.enhanced_sltp_manager = None

        # Exchange Registry берем из orchestrator если доступен
        if hasattr(self.orchestrator, "exchange_registry") and self.orchestrator.exchange_registry:
            self.exchange_registry = self.orchestrator.exchange_registry
        else:
            # Создаем свой если недоступен
            self.exchange_registry = ExchangeManager(self.config)
            await self.exchange_registry.initialize()

        # Order Manager - создаем с поддержкой SL/TP
        self.order_manager = OrderManager(
            exchange_registry=self.exchange_registry,
            sltp_manager=self.enhanced_sltp_manager,
        )

        # Signal Processor - создаем простой обработчик
        # Закомментируем пока, так как UnifiedSignalProcessor не подходит для наших нужд
        self.signal_processor = None  # Будем обрабатывать сигналы напрямую

        # Position Manager (обновлено на Enhanced Position Tracker)
        # Используем position_tracker вместо старого position_manager

        # Enhanced Position Tracker - инициализируем после Exchange Manager
        try:
            self.position_tracker = await get_position_tracker()
            self.position_tracker.exchange_manager = self.exchange_registry
            await self.position_tracker.start_tracking()
            self.logger.info("✅ Enhanced Position Tracker инициализирован и запущен")
            # Создаем alias для обратной совместимости
            self.position_manager = self.position_tracker
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Position Tracker: {e}")
            self.position_tracker = None
            self.position_manager = None

        # Execution Engine
        self.execution_engine = ExecutionEngine(
            order_manager=self.order_manager,
            exchange_registry=self.exchange_registry,
        )

        # Risk Manager - включен для расчета размеров позиций
        try:
            self.risk_manager = RiskManager(
                config=self.config.get("risk_management", {}),
                position_manager=self.position_manager,
                exchange_registry=self.exchange_registry,
            )
            self.logger.info("✅ RiskManager инициализирован")
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации RiskManager: {e}")
            self.risk_manager = None

        # Strategy Manager
        self.strategy_manager = StrategyManager(
            config=self.config.get("strategies", {}),
            exchange_registry=self.exchange_registry,
            signal_processor=self.signal_processor,
        )
        await self.strategy_manager.initialize()

        # Подключаем exchange_manager к balance_manager
        if self.balance_manager and self.exchange_registry:
            self.balance_manager.set_exchange_manager(self.exchange_registry)
            await self.balance_manager.start()
            self.logger.info("✅ BalanceManager подключен к Exchange Manager")

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
                    self.logger.warning(f"Не удалось загрузить {symbol} с {exchange_name}: {e}")

            self.logger.info(f"Загружено информации об инструментах: {len(self._instrument_cache)}")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки информации об инструментах: {e}")
            # Не прерываем инициализацию

    async def _initialize_repositories(self):
        """Инициализация репозиториев БД"""
        try:
            # Инициализируем менеджер БД
            self._db_manager = DatabaseManager()
            await self._db_manager.initialize()

            # Получаем репозитории через менеджер
            self.order_repository = self._db_manager.order_repository
            self.trade_repository = self._db_manager.trade_repository
            self.signal_repository = self._db_manager.signal_repository

            self.logger.info("✅ Репозитории БД инициализированы через DatabaseManager")

        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации репозиториев: {e}")
            # Не прерываем инициализацию - можем работать без БД
            self._db_manager = None
            self.order_repository = None
            self.trade_repository = None
            self.signal_repository = None
            self.logger.warning("⚠️ Trading Engine будет работать без БД")

    async def _health_check(self):
        """Проверка здоровья всех компонентов"""
        checks = []

        # Проверяем только существующие компоненты с методом health_check
        if self.exchange_registry and hasattr(self.exchange_registry, "health_check"):
            checks.append(("Exchange Registry", self.exchange_registry.health_check()))

        if self.position_manager and hasattr(self.position_manager, "health_check"):
            checks.append(("Position Manager", self.position_manager.health_check()))

        if self.order_manager and hasattr(self.order_manager, "health_check"):
            checks.append(("Order Manager", self.order_manager.health_check()))

        if self.risk_manager and hasattr(self.risk_manager, "health_check"):
            checks.append(("Risk Manager", self.risk_manager.health_check()))

        # Strategy Manager не имеет метода health_check, пропускаем проверку
        # if self.strategy_manager:
        #     self.logger.info("Strategy Manager инициализирован")

        for name, check in checks:
            try:
                result = await check
                if not result:
                    self.logger.warning(f"{name} health check failed")
                else:
                    self.logger.debug(f"{name} health check passed")
            except Exception as e:
                self.logger.error(f"{name} health check error: {e}")
                # Не прерываем инициализацию

        self.logger.info("Все компоненты прошли проверку здоровья")

    async def start(self) -> bool:
        """Запуск торгового движка"""
        try:
            if self.state == TradingState.RUNNING:
                self.logger.warning("Торговый движок уже запущен")
                return True

            self.logger.info("🚀 Запуск торгового движка...")
            self.logger.info(f"📊 Текущее состояние: {self.state.value}")

            # Инициализация если нужно
            if self.state in (TradingState.STOPPED, TradingState.STARTING):
                self.logger.info("📦 Требуется инициализация...")
                if not await self.initialize():
                    self.logger.error("❌ Инициализация не удалась")
                    return False
            elif self.state == TradingState.INITIALIZED:
                self.logger.info("✅ Уже инициализирован, пропускаем инициализацию")
            else:
                self.logger.warning(f"⚠️ Неожиданное состояние для запуска: {self.state.value}")

            # Запуск компонентов
            self.logger.info("🔧 Запуск компонентов...")
            # Компоненты не требуют явного запуска - они готовы к работе после инициализации
            # await self.strategy_manager.start()
            self.logger.info("✅ StrategyManager готов")
            # await self.position_manager.start()
            self.logger.info("✅ PositionManager готов")
            # await self.order_manager.start()
            self.logger.info("✅ OrderManager готов")
            # await self.execution_engine.start()
            self.logger.info("✅ ExecutionEngine готов")

            # Запуск основных циклов
            self._running = True
            self.state = TradingState.RUNNING
            self.metrics.start_time = datetime.now()
            self.logger.info("📊 Запуск основных циклов обработки...")

            # Создание задач
            self._tasks.add(asyncio.create_task(self._signal_processing_loop()))
            self.logger.info("✅ Цикл обработки сигналов запущен")
            self._tasks.add(asyncio.create_task(self._order_processing_loop()))
            self.logger.info("✅ Цикл обработки ордеров запущен")
            self._tasks.add(asyncio.create_task(self._position_sync_loop()))
            self.logger.info("✅ Цикл синхронизации позиций запущен")
            self._tasks.add(asyncio.create_task(self._metrics_update_loop()))
            self.logger.info("✅ Цикл обновления метрик запущен")
            self._tasks.add(asyncio.create_task(self._risk_monitoring_loop()))
            self.logger.info("✅ Цикл мониторинга рисков запущен")
            self._tasks.add(asyncio.create_task(self._heartbeat_loop()))
            self.logger.info("✅ Heartbeat цикл запущен")
            self._tasks.add(asyncio.create_task(self._balance_update_loop()))
            self.logger.info("✅ Цикл обновления баланса запущен")

            self.logger.info("🎉 Торговый движок успешно запущен и готов к работе!")
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
            # Компоненты не требуют явной остановки
            # if self.execution_engine:
            #     await self.execution_engine.stop()
            # if self.order_manager:
            #     await self.order_manager.stop()
            # if self.position_manager:
            #     await self.position_manager.stop()
            # if self.strategy_manager:
            #     await self.strategy_manager.stop()

            self.state = TradingState.STOPPED
            self._tasks.clear()

            # Обновление метрик
            if self.metrics.start_time:
                self.metrics.uptime = datetime.now() - self.metrics.start_time

            self.logger.info("Торговый движок остановлен")
            return True

        except TimeoutError:
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
        self.logger.info("🔄 Запуск цикла обработки сигналов...")

        processed_count = 0
        while self._running:
            try:
                if self.state != TradingState.RUNNING:
                    await asyncio.sleep(1)
                    continue

                # Получение сигнала из очереди
                try:
                    queue_size = self.signal_queue.qsize()
                    if queue_size > 0 and processed_count % 10 == 0:
                        self.logger.info(f"📬 Очередь сигналов: {queue_size} элементов")

                    signal = await asyncio.wait_for(self.signal_queue.get(), timeout=1.0)
                    processed_count += 1
                    self.logger.info(
                        f"📥 Получен сигнал #{processed_count} из очереди для обработки"
                    )
                except TimeoutError:
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

            # КРИТИЧНО: Проверяем и закрываем противоположные позиции
            opposite_position = await self._check_and_close_opposite_position(
                signal.symbol, signal.signal_type
            )
            if opposite_position:
                self.logger.info(
                    f"🔄 Закрыта противоположная позиция для {signal.symbol} перед открытием {signal.signal_type}"
                )
                # Даем время на закрытие позиции
                await asyncio.sleep(2)

            # Проверяем существующие позиции в том же направлении
            if await self._has_existing_position(signal.symbol, signal.signal_type):
                self.logger.info(
                    f"⚠️ Уже есть позиция {signal.signal_type} для {signal.symbol}, пропускаем сигнал"
                )
                return

            # Проверяем активные ордера в том же направлении
            if await self._has_pending_orders(signal.symbol, signal.signal_type):
                self.logger.info(
                    f"⚠️ Уже есть активные ордера {signal.signal_type} для {signal.symbol}, пропускаем сигнал"
                )
                return

            # Создание ордеров напрямую
            self.logger.info(f"📊 Создаем ордера для сигнала {signal.symbol}")
            orders = await self._create_orders_from_signal(signal)

            if orders:
                self.logger.info(f"✅ Создано {len(orders)} ордеров для {signal.symbol}")
                # Отправка ордеров на исполнение
                for order in orders:
                    self.logger.info(
                        f"📤 Отправляем ордер на исполнение: {order.side} {order.quantity} {order.symbol}"
                    )
                    await self.order_queue.put(order)
            else:
                self.logger.warning(f"⚠️ Не создано ни одного ордера для сигнала {signal.symbol}")

            # Сохранение в БД
            if self.signal_repository:
                try:
                    # Используем новый репозиторий
                    await self.signal_repository.save_signal(signal)
                    self.logger.debug(f"Сигнал {signal.symbol} сохранён в БД")
                except Exception as e:
                    # Игнорируем ошибки дубликатов
                    if "duplicate key" in str(e) or "idx_signals_unique" in str(e):
                        self.logger.debug(f"Сигнал {signal.symbol} уже существует в БД, пропускаем")
                    else:
                        self.logger.error(f"Ошибка сохранения сигнала в БД: {e}")

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
                except TimeoutError:
                    continue

                # Исполнение ордера
                success = await self.execution_engine.execute_order(order)

                if success:
                    self.metrics.orders_executed += 1
                    self.logger.info("✅ Ордер успешно исполнен")

                    # Обновляем статус в БД
                    if hasattr(order, "id") and order.id:
                        await self._update_order_status_in_db(order.id, OrderStatus.FILLED)
                    elif hasattr(order, "order_id"):
                        await self._update_order_status_in_db(order.order_id, OrderStatus.FILLED)

                    # Создаём запись Trade
                    await self._create_trade_record(order)

                    # Отслеживаем позицию
                    if self.position_tracker:
                        fill_price = Decimal(str(order.price)) if order.price else Decimal("0")
                        await self.on_position_opened(order, fill_price)
                else:
                    self.logger.warning("❌ Ошибка исполнения ордера")
                    self.metrics.errors_count += 1

                    # Обновляем статус в БД
                    if hasattr(order, "order_id"):
                        await self._update_order_status_in_db(order.order_id, OrderStatus.REJECTED)

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

                # ДОБАВЛЕНО: Синхронизация статусов ордеров
                # Исправляет проблему когда ордера остаются в статусе OPEN
                if self.order_manager:
                    try:
                        await self.order_manager.sync_orders_with_exchange("bybit")
                        self.logger.debug("Синхронизация ордеров выполнена")
                    except Exception as e:
                        self.logger.error(f"Ошибка синхронизации ордеров: {e}")

                # Обновление метрик позиций
                positions = await self.position_manager.get_all_positions()
                self.metrics.active_positions = len([p for p in positions if p.size != 0])

                # Проверка enhanced SL/TP для активных позиций
                if self.enhanced_sltp_manager:
                    for position in positions:
                        if position.size != 0:  # Только для активных позиций
                            try:
                                # Получаем текущую цену для позиции
                                current_price = 0.0
                                # Получаем клиент биржи для данной позиции
                                exchange_name = getattr(position, "exchange", "bybit")
                                # Исправляем: используем orchestrator.exchange_manager вместо несуществующего self.exchange_manager
                                if hasattr(self.orchestrator, "exchange_manager"):
                                    exchange_client = (
                                        self.orchestrator.exchange_manager.exchanges.get(
                                            exchange_name
                                        )
                                    )
                                else:
                                    exchange_client = None
                                if exchange_client:
                                    ticker = await exchange_client.get_ticker(position.symbol)
                                    current_price = ticker.last_price
                                else:
                                    self.logger.warning(
                                        f"Не найден клиент биржи {exchange_name} для {position.symbol}"
                                    )
                                    continue

                                # Назначаем exchange клиент для enhanced manager
                                # Используем тот же клиент для всех операций
                                self.enhanced_sltp_manager.exchange_client = exchange_client

                                # Применяем enhanced SL/TP функции
                                # Сначала проверяем частичное закрытие
                                partial_tp_executed = (
                                    await self.enhanced_sltp_manager.check_partial_tp(position)
                                )
                                if partial_tp_executed:
                                    self.logger.info(
                                        f"Выполнено частичное закрытие для {position.symbol}"
                                    )

                                # Затем обновляем защиту прибыли (может переопределить SL после partial TP)
                                profit_protection_updated = (
                                    await self.enhanced_sltp_manager.update_profit_protection(
                                        position, current_price
                                    )
                                )
                                if profit_protection_updated:
                                    self.logger.info(
                                        f"Обновлена защита прибыли для {position.symbol}"
                                    )

                                # Применяем трейлинг стоп
                                trailing_updated = (
                                    await self.enhanced_sltp_manager.update_trailing_stop(
                                        position, current_price
                                    )
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

            if self.trade_repository:
                try:
                    # Обновление статистики торговли через новый репозиторий
                    trades_stats = await self.trade_repository.get_trading_stats()
                    self.metrics.trades_completed = trades_stats.get("total_trades", 0)
                    self.metrics.win_rate = trades_stats.get("win_rate", 0.0)
                    self.metrics.total_volume = trades_stats.get("total_volume", Decimal("0"))
                except Exception as e:
                    self.logger.error(f"Ошибка получения статистики торговли: {e}")

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

    async def add_signal(self, signal: dict[str, Any]) -> bool:
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

    def get_status(self) -> dict[str, Any]:
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
                    self.position_manager.is_running() if self.position_manager else False
                ),
                "order_manager": self.order_manager.is_running() if self.order_manager else False,
                "execution_engine": (
                    self.execution_engine.is_running() if self.execution_engine else False
                ),
                "risk_manager": (self.risk_manager.is_running() if self.risk_manager else False),
                "strategy_manager": (
                    self.strategy_manager.is_running() if self.strategy_manager else False
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
            self.logger.error("❌ У TradingSignal отсутствует entry_price и suggested_price!")
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

        # Получаем stop_loss и take_profit - они уже правильно рассчитаны в ml_signal_processor
        signal_type = getattr(trading_signal, "signal_type", None)

        # Используем уже рассчитанные значения SL/TP без пересчета
        # ml_signal_processor уже правильно применил проценты к текущей цене
        stop_loss = getattr(trading_signal, "stop_loss", None) or getattr(
            trading_signal, "suggested_stop_loss", None
        )
        take_profit = getattr(trading_signal, "take_profit", None) or getattr(
            trading_signal, "suggested_take_profit", None
        )

        # Если SL/TP не заданы, рассчитываем с правильной логикой для каждого типа
        if stop_loss is None or take_profit is None:
            if signal_type == DBSignalType.SHORT:
                stop_loss = stop_loss or entry_price * 1.02  # Для SHORT: SL выше цены
                take_profit = take_profit or entry_price * 0.98  # Для SHORT: TP ниже цены
            else:  # LONG или неопределенный
                stop_loss = stop_loss or entry_price * 0.98  # Для LONG: SL ниже цены
                take_profit = take_profit or entry_price * 1.02  # Для LONG: TP выше цены

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
            suggested_quantity=getattr(trading_signal, "suggested_quantity", 0.01),
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

            # Проверка уверенности - еще немного снижен порог для текущей модели
            if signal.confidence < 0.25:  # Снижено до 0.25, чтобы соответствовать мягкому ML-режиму
                self.logger.warning(
                    f"Слишком низкая уверенность: {signal.confidence:.2%} (требуется > 25%)"
                )
                return False

            # Проверка stop loss и take profit в зависимости от направления
            from database.models.signal import SignalType

            if signal.signal_type == SignalType.LONG:
                # Для LONG: SL должен быть ниже цены, TP выше цены
                if (
                    signal.suggested_stop_loss
                    and signal.suggested_stop_loss >= signal.suggested_price
                ):
                    self.logger.warning(
                        f"LONG: Stop loss ({signal.suggested_stop_loss}) >= цены ({signal.suggested_price})"
                    )
                    return False

                if (
                    signal.suggested_take_profit
                    and signal.suggested_take_profit <= signal.suggested_price
                ):
                    self.logger.warning(
                        f"LONG: Take profit ({signal.suggested_take_profit}) <= цены ({signal.suggested_price})"
                    )
                    return False

            elif signal.signal_type == SignalType.SHORT:
                # Для SHORT: SL должен быть выше цены, TP ниже цены
                if (
                    signal.suggested_stop_loss
                    and signal.suggested_stop_loss <= signal.suggested_price
                ):
                    self.logger.warning(
                        f"SHORT: Stop loss ({signal.suggested_stop_loss}) <= цены ({signal.suggested_price})"
                    )
                    return False

                if (
                    signal.suggested_take_profit
                    and signal.suggested_take_profit >= signal.suggested_price
                ):
                    self.logger.warning(
                        f"SHORT: Take profit ({signal.suggested_take_profit}) >= цены ({signal.suggested_price})"
                    )
                    return False

            # ДОПОЛНИТЕЛЬНЫЕ КРИТЕРИИ КАЧЕСТВА - "закручиваем гайки"

            # Проверяем signal_strength если есть
            if hasattr(signal, "signal_strength") and signal.signal_strength:
                if signal.signal_strength < 0.40:  # Минимальная сила сигнала 40%
                    self.logger.warning(
                        f"Слишком слабый сигнал: {signal.signal_strength:.2%} (требуется > 40%)"
                    )
                    return False

            # Проверяем quality_score если есть
            if hasattr(signal, "quality_score") and signal.quality_score:
                if signal.quality_score < 0.30:  # Минимальный качественный балл снижен до 30%
                    self.logger.warning(
                        f"Слишком низкое качество сигнала: {signal.quality_score:.2%} (требуется > 30%)"
                    )
                    return False

            # Проверяем минимальное соотношение риск/прибыль (адаптивно по типу сигнала)
            if signal.suggested_stop_loss and signal.suggested_take_profit:
                if signal.signal_type == SignalType.LONG:
                    risk = signal.suggested_price - signal.suggested_stop_loss
                    reward = signal.suggested_take_profit - signal.suggested_price
                elif signal.signal_type == SignalType.SHORT:
                    risk = signal.suggested_stop_loss - signal.suggested_price
                    reward = signal.suggested_price - signal.suggested_take_profit
                else:
                    # NEUTRAL сигналы - используем более мягкие требования
                    # Подход из BOT_AI_V2: разные пороги для разных типов сигналов
                    risk = (
                        abs(signal.suggested_price - signal.suggested_stop_loss)
                        if signal.suggested_stop_loss
                        else 1
                    )
                    reward = (
                        abs(signal.suggested_take_profit - signal.suggested_price)
                        if signal.suggested_take_profit
                        else 1
                    )

                if risk > 0 and reward > 0:
                    risk_reward_ratio = reward / risk

                    # Адаптивные пороги risk/reward по типу сигнала
                    if signal.signal_type == SignalType.NEUTRAL:
                        min_rr_ratio = 1.0  # Для NEUTRAL достаточно 1:1
                        required_text = "> 1.0"
                    else:
                        min_rr_ratio = 1.5  # Для LONG/SHORT требуем 1.5:1
                        required_text = "> 1.5"

                    if risk_reward_ratio < min_rr_ratio:
                        self.logger.warning(
                            f"Плохое соотношение риск/прибыль для {signal.signal_type.value}: {risk_reward_ratio:.2f} (требуется {required_text})"
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
            if exchange_obj and hasattr(exchange_obj, "get_instrument_info"):
                instrument = await exchange_obj.get_instrument_info(symbol)
            else:
                # Если нет метода, используем значения по умолчанию
                from exchanges.base.models import Instrument

                # Значения по умолчанию для Bybit (из instrument_settings.py)
                defaults = {
                    "BTCUSDT": {"min": 0.001, "step": 0.001},
                    "ETHUSDT": {"min": 0.01, "step": 0.01},
                    "BNBUSDT": {"min": 0.01, "step": 0.01},
                    "SOLUSDT": {"min": 0.1, "step": 0.1},
                    "XRPUSDT": {"min": 0.1, "step": 0.1},  # ИСПРАВЛЕНО: qtyStep = 0.1
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
            self.logger.error(f"Ошибка получения информации об инструменте {symbol}: {e}")
            return None

    def _round_to_step(self, value: Decimal, step: Decimal) -> Decimal:
        """Округление значения до шага"""
        if step == 0:
            return value
        return (value / step).quantize(Decimal("1"), rounding="ROUND_DOWN") * step

    async def _check_and_close_opposite_position(self, symbol: str, signal_type) -> bool:
        """Проверка и закрытие противоположной позиции"""
        try:
            # Получаем позицию с биржи
            exchange = await self.exchange_registry.get_exchange("bybit")
            if not exchange:
                self.logger.warning("Биржа bybit недоступна для проверки позиций")
                return False

            position = await exchange.get_position(symbol)
            if not position or position.size == 0:
                return False

            # Проверяем направление позиции
            from database.models.base_models import SignalType
            from exchanges.base.order_types import OrderRequest, OrderSide, OrderType

            position_long = position.size > 0
            signal_long = signal_type in [SignalType.LONG, "LONG", "long", "buy", "BUY"]

            # Если направления противоположны - закрываем текущую позицию
            if position_long != signal_long:
                self.logger.warning(
                    f"⚠️ Обнаружена противоположная позиция {symbol}: "
                    f"текущая={'LONG' if position_long else 'SHORT'}, "
                    f"новый сигнал={signal_type}"
                )

                # Создаем ордер на закрытие позиции
                close_order = OrderRequest(
                    symbol=symbol,
                    side=OrderSide.SELL if position_long else OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=abs(position.size),
                    reduce_only=True,  # Важно: только закрытие позиции
                )

                # Исполняем ордер на закрытие
                result = await exchange.place_order(close_order)

                if result.success:
                    self.logger.info(
                        f"✅ Успешно закрыта противоположная позиция {symbol}: "
                        f"размер={abs(position.size)}, направление={'LONG' if position_long else 'SHORT'}"
                    )
                    return True
                else:
                    self.logger.error(
                        f"❌ Не удалось закрыть противоположную позицию {symbol}: {result.error}"
                    )
                    return False

            return False

        except Exception as e:
            self.logger.error(f"Ошибка при закрытии противоположной позиции {symbol}: {e}")
            return False

    async def _has_existing_position(self, symbol: str, signal_type) -> bool:
        """Проверка существования позиции в том же направлении"""
        try:
            # Получаем позицию с биржи
            exchange = await self.exchange_registry.get_exchange("bybit")
            if not exchange:
                self.logger.warning("Биржа bybit недоступна для проверки позиций")
                return False

            position = await exchange.get_position(symbol)
            if not position or position.size == 0:
                return False

            # Проверяем направление позиции
            from database.models.base_models import SignalType

            position_long = position.size > 0
            signal_long = signal_type in [SignalType.LONG, "LONG", "long", "buy", "BUY"]

            # Если направления совпадают - позиция уже есть
            if position_long == signal_long:
                self.logger.info(
                    f"📍 Найдена существующая позиция {symbol}: "
                    f"размер={position.size}, направление={'LONG' if position_long else 'SHORT'}"
                )
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка проверки позиции {symbol}: {e}")
            return False

    async def _has_pending_orders(self, symbol: str, signal_type) -> bool:
        """Проверка существования активных ордеров в том же направлении"""
        try:
            # Получаем активные ордера с биржи
            exchange = await self.exchange_registry.get_exchange("bybit")
            if not exchange:
                self.logger.warning("Биржа bybit недоступна для проверки ордеров")
                return False

            orders = await exchange.get_open_orders(symbol)
            if not orders:
                return False

            # Проверяем направление ордеров

            signal_long = signal_type in [SignalType.LONG, "LONG", "long", "buy", "BUY"]
            target_side = OrderSide.BUY if signal_long else OrderSide.SELL

            for order in orders:
                # Если есть активный ордер в том же направлении
                if order.side == target_side:
                    self.logger.info(
                        f"📋 Найден активный ордер {symbol}: "
                        f"{order.side} {order.quantity} @ {order.price}"
                    )
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка проверки ордеров {symbol}: {e}")
            return False

    async def _create_orders_from_signal(self, signal):
        """Создание ордеров из сигнала"""
        try:
            orders = []

            # Определяем направление

            # ИСПРАВЛЕНО: Правильная обработка NEUTRAL сигналов
            signal_type_lower = signal.signal_type.value.lower()

            # Для NEUTRAL сигналов не создаем ордера
            if signal_type_lower in ["neutral", "flat"]:
                self.logger.info(f"🔸 NEUTRAL сигнал для {signal.symbol} - не создаем ордера")
                return []

            side = OrderSide.BUY if signal_type_lower in ["long", "buy"] else OrderSide.SELL

            # ПРОВЕРКА СУЩЕСТВУЮЩИХ ПОЗИЦИЙ - предотвращаем дублирование
            try:
                # Проверяем активные позиции через position_manager
                if self.position_manager:
                    # Ищем позиции по символу
                    existing_positions = await self.position_manager.get_positions_by_symbol(
                        signal.symbol
                    )
                    existing_position = existing_positions[0] if existing_positions else None
                    if existing_position:
                        position_side = existing_position.get("side", "").lower()
                        position_size = existing_position.get("quantity", 0)

                        # Если есть позиция в том же направлении - пропускаем
                        if (position_side == "long" and side == OrderSide.BUY) or (
                            position_side == "short" and side == OrderSide.SELL
                        ):
                            self.logger.warning(
                                f"⚠️ Уже есть {position_side} позиция для {signal.symbol} "
                                f"размером {position_size}. Пропускаем новый сигнал."
                            )
                            return []

                        # Если позиция в противоположном направлении - можем открыть хедж или закрыть
                        if (position_side == "long" and side == OrderSide.SELL) or (
                            position_side == "short" and side == OrderSide.BUY
                        ):
                            self.logger.info(
                                f"📊 Обнаружена противоположная позиция {position_side} для {signal.symbol}. "
                                f"Создаем ордер для закрытия/хеджирования."
                            )

                # Дополнительная проверка через недавние ордера (защита от частых сигналов)
                last_order_time = self._recent_signal_times.get(signal.symbol, 0)
                current_time = asyncio.get_event_loop().time()
                # Увеличиваем минимальный интервал до 5 минут для предотвращения дублирования
                min_signal_interval = self.config.get("trading", {}).get(
                    "min_signal_interval", 300
                )  # 5 минут по умолчанию
                if current_time - last_order_time < min_signal_interval:
                    time_passed = current_time - last_order_time
                    time_remaining = min_signal_interval - time_passed
                    self.logger.warning(
                        f"⚠️ Слишком частые сигналы для {signal.symbol}. "
                        f"Последний был {time_passed:.1f}с назад. "
                        f"Ждите еще {time_remaining:.1f}с."
                    )
                    return []

                # Обновляем время последнего сигнала
                self._recent_signal_times[signal.symbol] = current_time

            except Exception as check_error:
                self.logger.error(f"❌ Ошибка проверки существующих позиций: {check_error}")
                # Продолжаем, но с осторожностью

            # Применяем rate limiting перед любыми API вызовами
            try:
                wait_time = await rate_limiter.acquire(signal.exchange, "get_positions")
                if wait_time > 0:
                    self.logger.debug(
                        f"⏱️ Rate limit задержка: {wait_time:.2f}с для {signal.exchange}"
                    )
            except Exception as rate_error:
                self.logger.warning(f"⚠️ Ошибка rate limiting: {rate_error}")

            # Получаем информацию об инструменте
            instrument = await self._get_instrument_info(signal.symbol, signal.exchange)
            if not instrument:
                self.logger.error(f"Не удалось получить информацию об инструменте {signal.symbol}")
                return []

            # Получаем минимальный объем ордера в USDT из конфигурации
            min_order_value_usdt = Decimal(
                str(self.config.get("trading", {}).get("min_order_value_usdt", 5.0))
            )

            # Используем RiskManager для расчета размера позиции
            if self.risk_manager:
                # Получаем актуальный баланс USDT для этой биржи
                current_balance = None
                if self.balance_manager:
                    try:
                        balances = await self.balance_manager.get_all_balances(signal.exchange)
                        if signal.exchange in balances and "USDT" in balances[signal.exchange]:
                            usdt_balance = balances[signal.exchange]["USDT"]
                            current_balance = Decimal(str(usdt_balance["effective_available"]))
                            self.logger.debug(
                                f"💰 Актуальный баланс USDT на {signal.exchange}: ${current_balance}"
                            )
                        else:
                            self.logger.warning(f"⚠️ Баланс USDT не найден для {signal.exchange}")
                    except Exception as e:
                        self.logger.error(f"❌ Ошибка получения баланса: {e}")

                # Преобразуем сигнал в словарь для RiskManager
                signal_dict = {
                    "symbol": signal.symbol,
                    "side": signal.signal_type.value,
                    "price": float(signal.suggested_price),
                    "confidence": getattr(signal, "confidence", 0.6),
                }

                # Рассчитываем размер позиции через RiskManager (в USDT)
                position_size_usdt = self.risk_manager.calculate_position_size(
                    signal_dict, balance=current_balance
                )

                # Конвертируем USDT в количество монет
                quantity = Decimal(str(position_size_usdt)) / Decimal(str(signal.suggested_price))

                self.logger.info(
                    f"RiskManager рассчитал размер: ${position_size_usdt:.2f} USDT = "
                    f"{quantity:.8f} {signal.symbol} @ ${signal.suggested_price}"
                )
            else:
                # Fallback: минимальный размер для $5
                quantity = min_order_value_usdt / Decimal(str(signal.suggested_price))
                self.logger.warning(
                    f"RiskManager недоступен! Используем минимальный размер ${min_order_value_usdt}: "
                    f"{quantity} {signal.symbol}"
                )

            # Проверяем минимальный объем в USDT
            order_value_usdt = quantity * Decimal(str(signal.suggested_price))
            if order_value_usdt < min_order_value_usdt:
                # Увеличиваем до минимального объема
                quantity = min_order_value_usdt / Decimal(str(signal.suggested_price))
                order_value_usdt = quantity * Decimal(str(signal.suggested_price))
                self.logger.info(
                    f"Размер увеличен для минимального объема ${min_order_value_usdt}: "
                    f"{quantity} {signal.symbol} (${order_value_usdt:.2f})"
                )

            # Проверяем минимальный размер ордера биржи
            min_qty = Decimal(str(instrument.min_order_qty))
            if quantity < min_qty:
                quantity = min_qty
                order_value_usdt = quantity * Decimal(str(signal.suggested_price))
                self.logger.info(
                    f"Размер увеличен до минимального биржи: {min_qty} {signal.symbol} "
                    f"(${order_value_usdt:.2f})"
                )

            # Округляем до qty_step
            qty_step = Decimal(str(instrument.qty_step))
            quantity = self._round_to_step(quantity, qty_step)

            # Финальная проверка минимального размера после округления
            if quantity < min_qty:
                quantity = min_qty

            # Проверяем баланс перед созданием ордера
            try:
                # ИСПРАВЛЕНО: Для фьючерсной торговли всегда нужен USDT (для маржи)
                # Независимо от направления (LONG/SHORT), используется USDT как маржа
                required_currency = "USDT"  # Всегда USDT для фьючерсов
                required_amount = order_value_usdt  # Размер в USDT

                # Примечание: для спотовой торговли логика была бы другой:
                # - BUY: нужен USDT
                # - SELL: нужна базовая валюта (BTC, ETH и т.д.)
                # Но мы торгуем фьючерсами, где всегда используется USDT

                # Проверяем доступность баланса
                balance_available, balance_error = await balance_manager.check_balance_availability(
                    exchange=signal.exchange, symbol=required_currency, amount=required_amount
                )

                if not balance_available:
                    self.logger.warning(f"⚠️ Недостаточно баланса для ордера: {balance_error}")
                    return []

                # Резервируем баланс на время создания ордера
                reservation_id = await balance_manager.reserve_balance(
                    exchange=signal.exchange,
                    symbol=required_currency,
                    amount=required_amount,
                    purpose="order",
                    metadata={
                        "signal_id": getattr(signal, "id", None),
                        "symbol": signal.symbol,
                        "side": side.value,
                        "quantity": float(quantity),
                    },
                )

                if not reservation_id:
                    self.logger.warning("⚠️ Не удалось зарезервировать баланс для ордера")
                    return []

                self.logger.info(
                    f"✅ Баланс зарезервирован: {required_amount} {required_currency} (ID: {reservation_id})"
                )

            except Exception as balance_error:
                self.logger.error(f"❌ Ошибка проверки баланса: {balance_error}")
                return []

            self.logger.info(
                f"Финальный размер ордера: {quantity} {signal.symbol} (шаг: {qty_step})"
            )

            # Создаем ордер

            # Генерируем уникальный ID для ордера
            order_id = f"order_{uuid.uuid4().hex[:12]}_{signal.symbol}"

            order = Order(
                order_id=order_id,  # Добавляем ID ордера
                symbol=signal.symbol,
                exchange=signal.exchange,
                side=side,
                order_type=OrderType.MARKET,  # Используем рыночные ордера для быстрого исполнения
                quantity=float(quantity),
                price=signal.suggested_price,
                stop_loss=signal.suggested_stop_loss,
                take_profit=signal.suggested_take_profit,
                status=OrderStatus.PENDING,
                order_metadata={
                    "strategy": signal.strategy_name,
                    "confidence": signal.confidence,
                    "created_by": "TradingEngine",
                    "signal_id": getattr(signal, "id", None),
                    "balance_reservation_id": (
                        reservation_id if "reservation_id" in locals() else None
                    ),
                },
            )

            orders.append(order)

            # Сохраняем ордер в БД через репозиторий
            try:
                if not self.order_repository:
                    self.logger.warning("⚠️ OrderRepository недоступен, пропускаем сохранение в БД")
                else:
                    # Создаём объект Order для репозитория
                    from database.repositories.order_repository import Order as RepoOrder

                    repo_order = RepoOrder(
                        symbol=order.symbol,
                        exchange=order.exchange,
                        side=(
                            order.side.value
                            if hasattr(order.side, "value")
                            else str(order.side).lower()
                        ),
                        order_type=(
                            order.order_type.value
                            if hasattr(order.order_type, "value")
                            else str(order.order_type).lower()
                        ),
                        quantity=Decimal(str(order.quantity)),
                        price=Decimal(str(order.price)) if order.price else None,
                        status=(
                            order.status.value
                            if hasattr(order.status, "value")
                            else str(order.status).lower()
                        ),
                        stop_loss=(
                            Decimal(str(order.stop_loss))
                            if hasattr(order, "stop_loss") and order.stop_loss
                            else None
                        ),
                        take_profit=(
                            Decimal(str(order.take_profit))
                            if hasattr(order, "take_profit") and order.take_profit
                            else None
                        ),
                        exchange_order_id=order.order_id if hasattr(order, "order_id") else None,
                        # leverage убран - нет в таблице
                        metadata=order.order_metadata if hasattr(order, "order_metadata") else {},
                    )

                    # Сохраняем через метод create_order
                    saved_order_id = await self.order_repository.create_order(repo_order)
                    self.logger.info(f"✅ Ордер {order.symbol} сохранён в БД с ID {saved_order_id}")

                    # Сохраняем ID в оригинальном ордере для дальнейшего использования
                    order.id = saved_order_id
            except Exception as db_error:
                self.logger.error(f"Ошибка сохранения ордера в БД: {db_error}")
                import traceback

                self.logger.error(traceback.format_exc())
                # Продолжаем работу, даже если не удалось сохранить в БД

            self.logger.info(
                f"📝 Создан ордер: {side} {float(quantity)} {signal.symbol} @ {signal.suggested_price} "
                f"(SL: {signal.suggested_stop_loss}, TP: {signal.suggested_take_profit})"
            )

            return orders

        except Exception as e:
            self.logger.error(f"Ошибка создания ордеров: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return []

    async def _create_trade_record(self, order):
        """Создание записи о сделке в БД"""
        try:
            if not self.trade_repository:
                self.logger.warning("⚠️ TradeRepository недоступен, пропускаем создание trade")
                return

            # Генерируем trade_id
            trade_id = f"TRADE_{uuid.uuid4().hex[:12]}_{order.symbol}"
            order_id = (
                str(order.order_id)
                if hasattr(order, "order_id")
                else f"order_{uuid.uuid4().hex[:12]}"
            )

            # Создаём объект Trade для репозитория
            from database.repositories.trade_repository import Trade as RepoTrade

            # Получаем order_id (должен быть числом из БД)
            if hasattr(order, "id") and order.id:
                db_order_id = int(order.id)
            else:
                db_order_id = None  # Или можно пропустить создание trade

            repo_trade = RepoTrade(
                exchange_trade_id=trade_id,  # Используем exchange_trade_id вместо trade_id
                exchange=order.exchange if hasattr(order, "exchange") else "bybit",
                symbol=order.symbol,
                order_id=db_order_id,  # Числовой ID из БД
                side=order.side.value if hasattr(order.side, "value") else str(order.side).lower(),
                price=Decimal(str(order.price)) if order.price else Decimal("0"),
                quantity=Decimal(str(order.quantity)),
                # Убираем fee и commission, добавим позже если нужно
                realized_pnl=Decimal("0"),
                executed_at=datetime.now(),
                metadata={
                    "strategy": (
                        order.order_metadata.get("strategy", "TradingEngine")
                        if hasattr(order, "order_metadata")
                        else "TradingEngine"
                    ),
                    "trader_id": (
                        order.order_metadata.get("created_by", "TradingEngine")
                        if hasattr(order, "order_metadata")
                        else "TradingEngine"
                    ),
                },
            )

            # Сохраняем через репозиторий
            await self.trade_repository.create_trade(repo_trade)
            self.logger.info(f"📈 Trade {trade_id} создан в БД для {order.symbol}")

            # Обновляем метрики
            self.metrics.total_trades += 1

        except Exception as e:
            self.logger.error(f"❌ Ошибка создания trade в БД: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    async def _update_order_status_in_db(self, order_id: str, status: OrderStatus):
        """Обновление статуса ордера в БД"""
        try:
            # Если order_id - это ID из базы (число)
            if isinstance(order_id, (int, str)) and str(order_id).isdigit():
                if not self.order_repository:
                    self.logger.warning(
                        "⚠️ OrderRepository недоступен, пропускаем обновление статуса"
                    )
                    return
                # Обновляем статус по ID
                success = await self.order_repository.update_order_status(
                    order_id=int(order_id),
                    new_status=status.value if hasattr(status, "value") else str(status).lower(),
                )
                if success:
                    self.logger.debug(
                        f"Статус ордера {order_id} обновлён на {status.value if hasattr(status, 'value') else status}"
                    )
                else:
                    self.logger.warning(f"Не удалось обновить статус ордера {order_id}")
            else:
                # Если это exchange_order_id (строка)
                self.logger.warning(
                    f"Не могу обновить статус - используется exchange_order_id: {order_id}"
                )
        except Exception as e:
            self.logger.error(f"Ошибка обновления статуса ордера {order_id} в БД: {e}")

    async def _balance_update_loop(self):
        """Цикл обновления балансов"""
        while self._running:
            try:
                # Обновляем балансы через BalanceManager
                if self.balance_manager:
                    for exchange_name in self.exchange_registry.exchanges.keys():
                        try:
                            exchange = await self.exchange_registry.get_exchange(exchange_name)
                            balances = await exchange.get_balances()

                            for balance in balances:
                                await self.balance_manager.update_balance(
                                    exchange=exchange_name,
                                    symbol=balance.currency,
                                    total=balance.total,
                                    available=balance.available,
                                    locked=balance.frozen,
                                )

                            self.logger.debug(
                                f"Обновлены балансы для {exchange_name}: {len(balances)} валют"
                            )

                        except Exception as e:
                            self.logger.warning(f"Ошибка обновления балансов {exchange_name}: {e}")

                await asyncio.sleep(30)  # Обновляем каждые 30 секунд

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в цикле обновления балансов: {e}")
                await asyncio.sleep(30)

    async def _heartbeat_loop(self):
        """Цикл отправки heartbeat и мониторинга"""
        while self._running:
            try:
                if hasattr(self, "worker_id") and self.worker_id:
                    # Отправляем heartbeat с текущими метриками
                    active_tasks = len([task for task in self._tasks if not task.done()])
                    await worker_coordinator.heartbeat(
                        self.worker_id,
                        status="running" if self.state == TradingState.RUNNING else "warning",
                        active_tasks=active_tasks,
                        tasks={f"task_{i}" for i in range(active_tasks)},
                    )

                    # Отправляем heartbeat в process monitor
                    await process_monitor.heartbeat(
                        "trading_engine",
                        status="healthy" if self.state == TradingState.RUNNING else "warning",
                        active_tasks=active_tasks,
                        metadata={
                            "signal_queue_size": self.signal_queue.qsize(),
                            "order_queue_size": self.order_queue.qsize(),
                            "total_signals_processed": self.metrics.total_signals,
                            "total_orders_created": self.metrics.total_orders,
                            "total_trades_executed": self.metrics.total_trades,
                        },
                    )

                await asyncio.sleep(30)  # Heartbeat каждые 30 секунд

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в heartbeat loop: {e}")
                await asyncio.sleep(30)

    async def on_position_opened(self, order: Order, fill_price: Decimal) -> None:
        """
        Callback при открытии новой позиции

        Args:
            order: Исполненный ордер
            fill_price: Цена исполнения
        """

        if not self.position_tracker:
            return

        try:
            # Определяем параметры позиции
            position_id = f"{order.symbol}_{order.side.value}_{order.order_id}"
            side = "long" if order.side.value.lower() in ["buy", "long"] else "short"

            # Добавляем позицию в отслеживание
            await self.position_tracker.track_position(
                position_id=position_id,
                symbol=order.symbol,
                side=side,
                size=order.quantity,
                entry_price=fill_price,
                exchange=getattr(order, "exchange", "bybit"),
            )

            self.logger.info(
                f"📊 Позиция добавлена в отслеживание: {position_id} | "
                f"{order.symbol} {side} {order.quantity} @ {fill_price}"
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка добавления позиции в отслеживание: {e}")

    async def on_position_closed(self, position_id: str, reason: str = "closed") -> None:
        """
        Callback при закрытии позиции

        Args:
            position_id: ID позиции
            reason: Причина закрытия
        """

        if not self.position_tracker:
            return

        try:
            await self.position_tracker.remove_position(position_id, reason)

            self.logger.info(f"📊 Позиция удалена из отслеживания: {position_id} ({reason})")

        except Exception as e:
            self.logger.error(f"❌ Ошибка удаления позиции из отслеживания: {e}")

    async def get_position_metrics(self) -> dict:
        """Получить метрики отслеживания позиций"""

        if not self.position_tracker:
            return {}

        try:
            return await self.position_tracker.get_tracker_stats()
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения метрик позиций: {e}")
            return {}
