"""
Основной торговый движок BOT Trading v3
Координирует все торговые операции, обработку сигналов и управление рисками
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
import json

from core.system.orchestrator import SystemOrchestrator
from .signals.signal_processor import SignalProcessor
from .positions.position_manager import PositionManager
from .orders.order_manager import OrderManager
from .execution.executor import ExecutionEngine
from risk_management.manager import RiskManager
from strategies.manager import StrategyManager
from exchanges.registry import ExchangeRegistry
from database.repositories.trade_repository import TradeRepository
from database.repositories.signal_repository import SignalRepository


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
    total_pnl: Decimal = Decimal('0')
    win_rate: float = 0.0
    total_volume: Decimal = Decimal('0')
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
    
    def __init__(
        self,
        orchestrator: SystemOrchestrator,
        config: Dict[str, Any]
    ):
        self.orchestrator = orchestrator
        self.config = config
        self.logger = logging.getLogger(__name__)
        
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
        
        # Репозитории
        self.trade_repository: Optional[TradeRepository] = None
        self.signal_repository: Optional[SignalRepository] = None
        
        # Очереди для обработки
        self.signal_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.order_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # Кеш и состояние
        self._price_cache: Dict[str, Decimal] = {}
        self._last_sync: Optional[datetime] = None
        
    async def initialize(self) -> bool:
        """Инициализация торгового движка"""
        try:
            self.logger.info("Инициализация торгового движка...")
            self.state = TradingState.STARTING
            
            # Инициализация компонентов
            await self._initialize_components()
            
            # Инициализация репозиториев
            await self._initialize_repositories()
            
            # Проверка системы
            await self._health_check()
            
            self.logger.info("Торговый движок успешно инициализирован")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации торгового движка: {e}")
            self.state = TradingState.ERROR
            return False
    
    async def _initialize_components(self):
        """Инициализация основных компонентов"""
        
        # Exchange Registry
        self.exchange_registry = ExchangeRegistry(self.config.get('exchanges', {}))
        await self.exchange_registry.initialize()
        
        # Signal Processor
        self.signal_processor = SignalProcessor(
            config=self.config.get('signal_processing', {}),
            exchange_registry=self.exchange_registry
        )
        
        # Position Manager
        self.position_manager = PositionManager(
            config=self.config.get('position_management', {}),
            exchange_registry=self.exchange_registry
        )
        
        # Order Manager
        self.order_manager = OrderManager(
            config=self.config.get('order_management', {}),
            exchange_registry=self.exchange_registry
        )
        
        # Execution Engine
        self.execution_engine = ExecutionEngine(
            config=self.config.get('execution', {}),
            order_manager=self.order_manager,
            position_manager=self.position_manager
        )
        
        # Risk Manager
        self.risk_manager = RiskManager(
            config=self.config.get('risk_management', {}),
            position_manager=self.position_manager,
            exchange_registry=self.exchange_registry
        )
        
        # Strategy Manager
        self.strategy_manager = StrategyManager(
            config=self.config.get('strategies', {}),
            exchange_registry=self.exchange_registry,
            signal_processor=self.signal_processor
        )
        
        self.logger.info("Основные компоненты инициализированы")
    
    async def _initialize_repositories(self):
        """Инициализация репозиториев БД"""
        try:
            db_manager = self.orchestrator.get_database_manager()
            
            self.trade_repository = TradeRepository(db_manager)
            self.signal_repository = SignalRepository(db_manager)
            
            self.logger.info("Репозитории БД инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации репозиториев: {e}")
            raise
    
    async def _health_check(self):
        """Проверка здоровья всех компонентов"""
        checks = [
            ("Exchange Registry", self.exchange_registry.health_check()),
            ("Signal Processor", self.signal_processor.health_check()),
            ("Position Manager", self.position_manager.health_check()),
            ("Order Manager", self.order_manager.health_check()),
            ("Risk Manager", self.risk_manager.health_check()),
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
            await self.signal_processor.start()
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
                    timeout=timeout
                )
            
            # Остановка компонентов
            if self.execution_engine:
                await self.execution_engine.stop()
            if self.order_manager:
                await self.order_manager.stop()
            if self.position_manager:
                await self.position_manager.stop()
            if self.signal_processor:
                await self.signal_processor.stop()
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
                        self.signal_queue.get(),
                        timeout=1.0
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
    
    async def _process_signal(self, signal: Dict[str, Any]):
        """Обработка одного торгового сигнала"""
        try:
            signal_id = signal.get('id')
            self.logger.debug(f"Обработка сигнала {signal_id}")
            
            # Валидация сигнала
            if not self.signal_processor.validate_signal(signal):
                self.logger.warning(f"Сигнал {signal_id} не прошел валидацию")
                return
            
            # Проверка рисков
            if not await self.risk_manager.check_signal_risk(signal):
                self.logger.warning(f"Сигнал {signal_id} отклонен по риск-менеджменту")
                return
            
            # Обработка через процессор сигналов
            orders = await self.signal_processor.process_signal(signal)
            
            # Отправка ордеров на исполнение
            for order in orders:
                await self.order_queue.put(order)
            
            # Сохранение в БД
            if self.signal_repository:
                await self.signal_repository.save_signal(signal)
            
            self.logger.debug(f"Сигнал {signal_id} обработан, создано {len(orders)} ордеров")
            
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
                    order = await asyncio.wait_for(
                        self.order_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Исполнение ордера
                result = await self.execution_engine.execute_order(order)
                
                if result.success:
                    self.metrics.orders_executed += 1
                else:
                    self.logger.warning(f"Ошибка исполнения ордера: {result.error}")
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
                self.metrics.active_positions = len([p for p in positions if p.size != 0])
                
                self._last_sync = datetime.now()
                
                # Пауза между синхронизациями
                await asyncio.sleep(self.config.get('position_sync_interval', 30))
                
            except Exception as e:
                self.logger.error(f"Ошибка синхронизации позиций: {e}")
                self.metrics.errors_count += 1
                await asyncio.sleep(60)
    
    async def _metrics_update_loop(self):
        """Цикл обновления метрик"""
        while self._running:
            try:
                await self._update_trading_metrics()
                await asyncio.sleep(self.config.get('metrics_update_interval', 60))
                
            except Exception as e:
                self.logger.error(f"Ошибка обновления метрик: {e}")
                await asyncio.sleep(60)
    
    async def _risk_monitoring_loop(self):
        """Цикл мониторинга рисков"""
        while self._running:
            try:
                if self.state == TradingState.RUNNING:
                    # Проверка общих рисков
                    risk_status = await self.risk_manager.check_global_risks()
                    
                    if risk_status.requires_action:
                        self.logger.warning(f"Обнаружен риск: {risk_status.message}")
                        
                        if risk_status.action == "pause":
                            await self.pause()
                        elif risk_status.action == "reduce_positions":
                            await self._reduce_positions()
                
                await asyncio.sleep(self.config.get('risk_check_interval', 30))
                
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
                # Обновление статистики торговли
                trades_stats = await self.trade_repository.get_trading_stats()
                self.metrics.trades_completed = trades_stats.get('total_trades', 0)
                self.metrics.win_rate = trades_stats.get('win_rate', 0.0)
                self.metrics.total_volume = trades_stats.get('total_volume', Decimal('0'))
            
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
                alpha * processing_time + 
                (1 - alpha) * self.metrics.processing_time_avg
            )
    
    async def _reduce_positions(self):
        """Сокращение позиций при высоком риске"""
        try:
            self.logger.info("Начинаем сокращение позиций из-за высокого риска")
            
            positions = await self.position_manager.get_all_positions()
            
            for position in positions:
                if position.size != 0:
                    # Сокращение на 50%
                    reduce_size = abs(position.size) * Decimal('0.5')
                    
                    order = {
                        'symbol': position.symbol,
                        'side': 'sell' if position.size > 0 else 'buy',
                        'size': reduce_size,
                        'type': 'market',
                        'reason': 'risk_reduction'
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
            'state': self.state.value,
            'running': self._running,
            'metrics': {
                'signals_processed': self.metrics.signals_processed,
                'orders_executed': self.metrics.orders_executed,
                'trades_completed': self.metrics.trades_completed,
                'total_pnl': str(self.metrics.total_pnl),
                'win_rate': self.metrics.win_rate,
                'total_volume': str(self.metrics.total_volume),
                'active_positions': self.metrics.active_positions,
                'processing_time_avg': self.metrics.processing_time_avg,
                'errors_count': self.metrics.errors_count,
                'uptime_seconds': self.metrics.uptime.total_seconds(),
            },
            'queue_sizes': {
                'signals': self.signal_queue.qsize(),
                'orders': self.order_queue.qsize(),
            },
            'last_sync': self._last_sync.isoformat() if self._last_sync else None,
            'component_status': {
                'signal_processor': self.signal_processor.is_running() if self.signal_processor else False,
                'position_manager': self.position_manager.is_running() if self.position_manager else False,
                'order_manager': self.order_manager.is_running() if self.order_manager else False,
                'execution_engine': self.execution_engine.is_running() if self.execution_engine else False,
                'risk_manager': self.risk_manager.is_running() if self.risk_manager else False,
                'strategy_manager': self.strategy_manager.is_running() if self.strategy_manager else False,
            }
        }
    
    def get_metrics(self) -> TradingMetrics:
        """Получение метрик торгового движка"""
        return self.metrics