"""
Менеджер торговых стратегий
Управляет жизненным циклом стратегий, их взаимодействием и производительностью
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from exchanges.registry import ExchangeRegistry
from trading.signals.signal_processor import SignalProcessor

from .base.strategy_abc import StrategyABC
from .factory import StrategyFactory
from .registry import StrategyRegistry


class StrategyState(Enum):
    """Состояния стратегии"""

    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class StrategyMetrics:
    """Метрики стратегии"""

    signals_generated: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_trade_duration: timedelta = field(default_factory=lambda: timedelta(0))
    last_signal_time: Optional[datetime] = None
    error_count: int = 0
    uptime: timedelta = field(default_factory=lambda: timedelta(0))
    start_time: Optional[datetime] = None


@dataclass
class StrategyInstance:
    """Экземпляр стратегии"""

    strategy_id: str
    strategy_name: str
    strategy: StrategyABC
    config: Dict[str, Any]
    state: StrategyState = StrategyState.INACTIVE
    metrics: StrategyMetrics = field(default_factory=StrategyMetrics)
    task: Optional[asyncio.Task] = None
    error_message: Optional[str] = None
    trader_id: Optional[str] = None
    exchange_name: Optional[str] = None
    symbols: List[str] = field(default_factory=list)


class StrategyManager:
    """
    Менеджер торговых стратегий

    Функции:
    - Загрузка и инициализация стратегий
    - Управление жизненным циклом стратегий
    - Мониторинг производительности
    - Координация между стратегиями
    - Управление ресурсами
    """

    def __init__(
        self,
        config: Dict[str, Any],
        exchange_registry: ExchangeRegistry,
        signal_processor: SignalProcessor,
    ):
        self.config = config
        self.exchange_registry = exchange_registry
        self.signal_processor = signal_processor
        self.logger = logging.getLogger(__name__)

        # Реестр и фабрика стратегий
        self.registry = StrategyRegistry()
        self.factory = StrategyFactory(self.registry)

        # Активные стратегии
        self.strategies: Dict[str, StrategyInstance] = {}

        # Состояние менеджера
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None

        # Настройки
        self.max_strategies = config.get("max_strategies", 10)
        self.monitoring_interval = config.get("monitoring_interval", 30)
        self.restart_failed_strategies = config.get("restart_failed_strategies", True)
        self.max_restart_attempts = config.get("max_restart_attempts", 3)

        # Метрики
        self._restart_attempts: Dict[str, int] = {}

    async def initialize(self) -> bool:
        """Инициализация менеджера стратегий"""
        try:
            self.logger.info("Инициализация менеджера стратегий...")

            # Загрузка доступных стратегий
            await self._load_available_strategies()

            # Создание стратегий из конфигурации
            await self._create_configured_strategies()

            self.logger.info(
                f"Менеджер стратегий инициализирован. Загружено {len(self.strategies)} стратегий"
            )
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации менеджера стратегий: {e}")
            return False

    async def _load_available_strategies(self):
        """Загрузка доступных стратегий"""
        try:
            # Загрузка стратегий из модулей
            strategy_configs = self.config.get("available_strategies", [])

            for strategy_config in strategy_configs:
                strategy_name = strategy_config["name"]
                strategy_class = strategy_config["class"]

                # Динамический импорт стратегии
                module_path, class_name = strategy_class.rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                strategy_cls = getattr(module, class_name)

                # Регистрация стратегии
                self.registry.register_strategy(strategy_name, strategy_cls)

                self.logger.debug(f"Загружена стратегия: {strategy_name}")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки стратегий: {e}")
            raise

    async def _create_configured_strategies(self):
        """Создание стратегий из конфигурации"""
        try:
            strategy_instances = self.config.get("instances", [])

            for instance_config in strategy_instances:
                await self.create_strategy(instance_config)

        except Exception as e:
            self.logger.error(f"Ошибка создания стратегий: {e}")
            raise

    async def create_strategy(self, config: Dict[str, Any]) -> Optional[str]:
        """Создание новой стратегии"""
        try:
            strategy_id = config["id"]
            strategy_name = config["strategy_name"]
            trader_id = config.get("trader_id")
            exchange_name = config.get("exchange")
            symbols = config.get("symbols", [])

            if strategy_id in self.strategies:
                self.logger.warning(f"Стратегия {strategy_id} уже существует")
                return None

            if len(self.strategies) >= self.max_strategies:
                self.logger.error(f"Достигнут лимит стратегий: {self.max_strategies}")
                return None

            # Создание стратегии через фабрику
            strategy = await self.factory.create_strategy(
                strategy_name=strategy_name,
                config=config.get("strategy_config", {}),
                exchange_registry=self.exchange_registry,
                signal_processor=self.signal_processor,
                trader_id=trader_id,
                exchange_name=exchange_name,
                symbols=symbols,
            )

            if not strategy:
                self.logger.error(f"Не удалось создать стратегию {strategy_name}")
                return None

            # Создание экземпляра стратегии
            instance = StrategyInstance(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                strategy=strategy,
                config=config,
                trader_id=trader_id,
                exchange_name=exchange_name,
                symbols=symbols,
            )

            self.strategies[strategy_id] = instance
            self._restart_attempts[strategy_id] = 0

            self.logger.info(f"Создана стратегия {strategy_id} ({strategy_name})")
            return strategy_id

        except Exception as e:
            self.logger.error(f"Ошибка создания стратегии: {e}")
            return None

    async def start_strategy(self, strategy_id: str) -> bool:
        """Запуск стратегии"""
        try:
            if strategy_id not in self.strategies:
                self.logger.error(f"Стратегия {strategy_id} не найдена")
                return False

            instance = self.strategies[strategy_id]

            if instance.state == StrategyState.ACTIVE:
                self.logger.warning(f"Стратегия {strategy_id} уже активна")
                return True

            self.logger.info(f"Запуск стратегии {strategy_id}")
            instance.state = StrategyState.INITIALIZING

            # Инициализация стратегии
            if not await instance.strategy.initialize():
                instance.state = StrategyState.ERROR
                instance.error_message = "Ошибка инициализации"
                return False

            # Создание задачи для стратегии
            instance.task = asyncio.create_task(self._run_strategy(instance))
            instance.state = StrategyState.ACTIVE
            instance.metrics.start_time = datetime.now()

            self.logger.info(f"Стратегия {strategy_id} запущена")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка запуска стратегии {strategy_id}: {e}")
            if strategy_id in self.strategies:
                self.strategies[strategy_id].state = StrategyState.ERROR
                self.strategies[strategy_id].error_message = str(e)
            return False

    async def stop_strategy(self, strategy_id: str, timeout: float = 30.0) -> bool:
        """Остановка стратегии"""
        try:
            if strategy_id not in self.strategies:
                self.logger.error(f"Стратегия {strategy_id} не найдена")
                return False

            instance = self.strategies[strategy_id]

            if instance.state == StrategyState.INACTIVE:
                self.logger.warning(f"Стратегия {strategy_id} уже неактивна")
                return True

            self.logger.info(f"Остановка стратегии {strategy_id}")
            instance.state = StrategyState.STOPPING

            # Остановка стратегии
            await instance.strategy.stop()

            # Отмена задачи
            if instance.task and not instance.task.done():
                instance.task.cancel()
                try:
                    await asyncio.wait_for(instance.task, timeout=timeout)
                except asyncio.TimeoutError:
                    self.logger.warning(f"Таймаут остановки стратегии {strategy_id}")
                except asyncio.CancelledError:
                    pass

            instance.state = StrategyState.INACTIVE
            instance.task = None

            # Обновление метрик
            if instance.metrics.start_time:
                instance.metrics.uptime = datetime.now() - instance.metrics.start_time

            self.logger.info(f"Стратегия {strategy_id} остановлена")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка остановки стратегии {strategy_id}: {e}")
            return False

    async def pause_strategy(self, strategy_id: str) -> bool:
        """Приостановка стратегии"""
        try:
            if strategy_id not in self.strategies:
                return False

            instance = self.strategies[strategy_id]

            if instance.state == StrategyState.ACTIVE:
                await instance.strategy.pause()
                instance.state = StrategyState.PAUSED
                self.logger.info(f"Стратегия {strategy_id} приостановлена")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка приостановки стратегии {strategy_id}: {e}")
            return False

    async def resume_strategy(self, strategy_id: str) -> bool:
        """Возобновление стратегии"""
        try:
            if strategy_id not in self.strategies:
                return False

            instance = self.strategies[strategy_id]

            if instance.state == StrategyState.PAUSED:
                await instance.strategy.resume()
                instance.state = StrategyState.ACTIVE
                self.logger.info(f"Стратегия {strategy_id} возобновлена")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка возобновления стратегии {strategy_id}: {e}")
            return False

    async def remove_strategy(self, strategy_id: str) -> bool:
        """Удаление стратегии"""
        try:
            if strategy_id not in self.strategies:
                return False

            # Остановка стратегии
            await self.stop_strategy(strategy_id)

            # Очистка стратегии
            instance = self.strategies[strategy_id]
            await instance.strategy.cleanup()

            # Удаление из реестра
            del self.strategies[strategy_id]
            if strategy_id in self._restart_attempts:
                del self._restart_attempts[strategy_id]

            self.logger.info(f"Стратегия {strategy_id} удалена")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка удаления стратегии {strategy_id}: {e}")
            return False

    async def start(self) -> bool:
        """Запуск менеджера стратегий"""
        try:
            if self._running:
                return True

            self.logger.info("Запуск менеджера стратегий...")

            # Запуск всех настроенных стратегий
            for strategy_id in self.strategies:
                if self.strategies[strategy_id].config.get("auto_start", False):
                    await self.start_strategy(strategy_id)

            # Запуск мониторинга
            self._running = True
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

            self.logger.info("Менеджер стратегий запущен")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка запуска менеджера стратегий: {e}")
            return False

    async def stop(self) -> bool:
        """Остановка менеджера стратегий"""
        try:
            if not self._running:
                return True

            self.logger.info("Остановка менеджера стратегий...")
            self._running = False

            # Остановка мониторинга
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

            # Остановка всех стратегий
            tasks = []
            for strategy_id in list(self.strategies.keys()):
                tasks.append(self.stop_strategy(strategy_id))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            self.logger.info("Менеджер стратегий остановлен")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка остановки менеджера стратегий: {e}")
            return False

    async def pause(self) -> bool:
        """Приостановка всех стратегий"""
        try:
            for strategy_id in self.strategies:
                await self.pause_strategy(strategy_id)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка приостановки стратегий: {e}")
            return False

    async def resume(self) -> bool:
        """Возобновление всех стратегий"""
        try:
            for strategy_id in self.strategies:
                if self.strategies[strategy_id].state == StrategyState.PAUSED:
                    await self.resume_strategy(strategy_id)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка возобновления стратегий: {e}")
            return False

    async def _run_strategy(self, instance: StrategyInstance):
        """Запуск стратегии в отдельной задаче"""
        try:
            self.logger.debug(f"Запуск задачи стратегии {instance.strategy_id}")

            while instance.state == StrategyState.ACTIVE and self._running:
                try:
                    # Выполнение шага стратегии
                    await instance.strategy.run_step()

                    # Обновление времени последнего сигнала
                    if hasattr(instance.strategy, "last_signal_time"):
                        instance.metrics.last_signal_time = (
                            instance.strategy.last_signal_time
                        )

                    # Пауза между шагами
                    step_delay = instance.config.get("step_delay", 1.0)
                    await asyncio.sleep(step_delay)

                except Exception as e:
                    self.logger.error(f"Ошибка в стратегии {instance.strategy_id}: {e}")
                    instance.metrics.error_count += 1
                    instance.state = StrategyState.ERROR
                    instance.error_message = str(e)
                    break

        except asyncio.CancelledError:
            self.logger.debug(f"Задача стратегии {instance.strategy_id} отменена")
        except Exception as e:
            self.logger.error(
                f"Критическая ошибка в стратегии {instance.strategy_id}: {e}"
            )
            instance.state = StrategyState.ERROR
            instance.error_message = str(e)

    async def _monitoring_loop(self):
        """Цикл мониторинга стратегий"""
        self.logger.info("Запуск мониторинга стратегий")

        while self._running:
            try:
                await self._monitor_strategies()
                await asyncio.sleep(self.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в мониторинге стратегий: {e}")
                await asyncio.sleep(60)

    async def _monitor_strategies(self):
        """Мониторинг состояния стратегий"""
        try:
            for strategy_id, instance in self.strategies.items():
                # Обновление метрик времени работы
                if (
                    instance.metrics.start_time
                    and instance.state == StrategyState.ACTIVE
                ):
                    instance.metrics.uptime = (
                        datetime.now() - instance.metrics.start_time
                    )

                # Проверка на зависшие стратегии
                if instance.state == StrategyState.ACTIVE and instance.task:
                    if instance.task.done():
                        exception = instance.task.exception()
                        if exception:
                            self.logger.error(
                                f"Стратегия {strategy_id} завершилась с ошибкой: {exception}"
                            )
                            instance.state = StrategyState.ERROR
                            instance.error_message = str(exception)

                # Автоматический перезапуск упавших стратегий
                if (
                    instance.state == StrategyState.ERROR
                    and self.restart_failed_strategies
                    and self._restart_attempts.get(strategy_id, 0)
                    < self.max_restart_attempts
                ):
                    self.logger.info(f"Попытка перезапуска стратегии {strategy_id}")
                    self._restart_attempts[strategy_id] += 1

                    await asyncio.sleep(5)  # Пауза перед перезапуском
                    await self.start_strategy(strategy_id)

                # Обновление метрик производительности
                await self._update_strategy_metrics(instance)

        except Exception as e:
            self.logger.error(f"Ошибка мониторинга стратегий: {e}")

    async def _update_strategy_metrics(self, instance: StrategyInstance):
        """Обновление метрик стратегии"""
        try:
            # Получение метрик от стратегии
            if hasattr(instance.strategy, "get_metrics"):
                strategy_metrics = await instance.strategy.get_metrics()

                if strategy_metrics:
                    instance.metrics.signals_generated = strategy_metrics.get(
                        "signals_generated", 0
                    )
                    instance.metrics.successful_trades = strategy_metrics.get(
                        "successful_trades", 0
                    )
                    instance.metrics.failed_trades = strategy_metrics.get(
                        "failed_trades", 0
                    )
                    instance.metrics.total_pnl = strategy_metrics.get("total_pnl", 0.0)
                    instance.metrics.win_rate = strategy_metrics.get("win_rate", 0.0)
                    instance.metrics.sharpe_ratio = strategy_metrics.get(
                        "sharpe_ratio", 0.0
                    )
                    instance.metrics.max_drawdown = strategy_metrics.get(
                        "max_drawdown", 0.0
                    )

                    # Обновление времени последнего сигнала
                    last_signal = strategy_metrics.get("last_signal_time")
                    if last_signal:
                        if isinstance(last_signal, str):
                            instance.metrics.last_signal_time = datetime.fromisoformat(
                                last_signal
                            )
                        elif isinstance(last_signal, datetime):
                            instance.metrics.last_signal_time = last_signal

        except Exception as e:
            self.logger.error(
                f"Ошибка обновления метрик стратегии {instance.strategy_id}: {e}"
            )

    def get_strategy_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Получение статуса стратегии"""
        if strategy_id not in self.strategies:
            return None

        instance = self.strategies[strategy_id]

        return {
            "strategy_id": instance.strategy_id,
            "strategy_name": instance.strategy_name,
            "state": instance.state.value,
            "trader_id": instance.trader_id,
            "exchange": instance.exchange_name,
            "symbols": instance.symbols,
            "error_message": instance.error_message,
            "restart_attempts": self._restart_attempts.get(strategy_id, 0),
            "metrics": {
                "signals_generated": instance.metrics.signals_generated,
                "successful_trades": instance.metrics.successful_trades,
                "failed_trades": instance.metrics.failed_trades,
                "total_pnl": instance.metrics.total_pnl,
                "win_rate": instance.metrics.win_rate,
                "sharpe_ratio": instance.metrics.sharpe_ratio,
                "max_drawdown": instance.metrics.max_drawdown,
                "error_count": instance.metrics.error_count,
                "uptime_seconds": instance.metrics.uptime.total_seconds(),
                "last_signal_time": (
                    instance.metrics.last_signal_time.isoformat()
                    if instance.metrics.last_signal_time
                    else None
                ),
            },
            "config": instance.config,
        }

    def get_all_strategies_status(self) -> Dict[str, Dict[str, Any]]:
        """Получение статуса всех стратегий"""
        return {
            strategy_id: self.get_strategy_status(strategy_id)
            for strategy_id in self.strategies
        }

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Получение сводных метрик"""
        total_strategies = len(self.strategies)
        active_strategies = len(
            [s for s in self.strategies.values() if s.state == StrategyState.ACTIVE]
        )
        error_strategies = len(
            [s for s in self.strategies.values() if s.state == StrategyState.ERROR]
        )

        total_signals = sum(
            s.metrics.signals_generated for s in self.strategies.values()
        )
        total_trades = sum(
            s.metrics.successful_trades + s.metrics.failed_trades
            for s in self.strategies.values()
        )
        total_pnl = sum(s.metrics.total_pnl for s in self.strategies.values())

        # Средний винрейт
        win_rates = [
            s.metrics.win_rate
            for s in self.strategies.values()
            if s.metrics.win_rate > 0
        ]
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0.0

        return {
            "total_strategies": total_strategies,
            "active_strategies": active_strategies,
            "error_strategies": error_strategies,
            "paused_strategies": len(
                [s for s in self.strategies.values() if s.state == StrategyState.PAUSED]
            ),
            "total_signals_generated": total_signals,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "average_win_rate": avg_win_rate,
            "manager_running": self._running,
        }

    async def health_check(self) -> bool:
        """Проверка здоровья менеджера стратегий"""
        try:
            # Проверка состояния менеджера
            if not self._running:
                return False

            # Проверка задачи мониторинга
            if self._monitoring_task and self._monitoring_task.done():
                exception = self._monitoring_task.exception()
                if exception:
                    self.logger.error(
                        f"Задача мониторинга завершилась с ошибкой: {exception}"
                    )
                    return False

            # Проверка критических стратегий
            critical_strategies = [
                s
                for s in self.strategies.values()
                if s.config.get("critical", False) and s.state == StrategyState.ERROR
            ]

            if critical_strategies:
                self.logger.warning(
                    f"Обнаружены неработающие критические стратегии: {[s.strategy_id for s in critical_strategies]}"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Ошибка проверки здоровья менеджера стратегий: {e}")
            return False

    def is_running(self) -> bool:
        """Проверка работает ли менеджер"""
        return self._running
