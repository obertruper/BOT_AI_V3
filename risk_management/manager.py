"""
Основной менеджер управления рисками
Контролирует все аспекты риска в торговой системе
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from exchanges.registry import ExchangeRegistry
from trading.positions.position_manager import PositionManager

from .calculators import RiskCalculator
from .limits import RiskLimitsManager
from .portfolio.exposure import PortfolioExposureManager
from .position.manager import PositionRiskManager
from .sltp.enhanced_sltp import EnhancedSLTPManager


class RiskLevel(Enum):
    """Уровни риска"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAction(Enum):
    """Действия по риску"""

    NONE = "none"
    WARNING = "warning"
    REDUCE_POSITIONS = "reduce_positions"
    CLOSE_POSITIONS = "close_positions"
    PAUSE_TRADING = "pause_trading"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class RiskAlert:
    """Алерт по риску"""

    alert_id: str
    risk_type: str
    level: RiskLevel
    message: str
    action: RiskAction
    timestamp: datetime
    trader_id: Optional[str] = None
    symbol: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskStatus:
    """Статус риска системы"""

    overall_level: RiskLevel
    requires_action: bool
    action: RiskAction
    message: str
    alerts: List[RiskAlert] = field(default_factory=list)
    risk_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskMetrics:
    """Метрики риска"""

    portfolio_value: Decimal = Decimal("0")
    total_exposure: Decimal = Decimal("0")
    max_drawdown: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    correlation_risk: float = 0.0
    concentration_risk: float = 0.0
    leverage_ratio: float = 0.0
    margin_usage: float = 0.0
    daily_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    open_positions_count: int = 0
    risk_score: float = 0.0


class RiskManager:
    """
    Основной менеджер управления рисками

    Функции:
    - Мониторинг рисков в реальном времени
    - Управление лимитами и экспозицией
    - Автоматические действия по рискам
    - Расчет риск-метрик
    - Уведомления и алерты
    """

    def __init__(
        self,
        config: Dict[str, Any],
        position_manager: PositionManager,
        exchange_registry: ExchangeRegistry,
    ):
        self.config = config
        self.position_manager = position_manager
        self.exchange_registry = exchange_registry
        self.logger = logging.getLogger(__name__)

        # Подсистемы управления рисками
        self.position_risk: Optional[PositionRiskManager] = None
        self.sltp_manager: Optional[EnhancedSLTPManager] = None
        self.portfolio_exposure: Optional[PortfolioExposureManager] = None
        self.limits_manager: Optional[RiskLimitsManager] = None
        self.calculator: Optional[RiskCalculator] = None

        # Состояние
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None

        # Алерты и история
        self.active_alerts: Dict[str, RiskAlert] = {}
        self.alert_history: List[RiskAlert] = []
        self.max_alert_history = config.get("max_alert_history", 1000)

        # Настройки мониторинга
        self.monitoring_interval = config.get("monitoring_interval", 10)  # секунд
        self.emergency_cooldown = config.get("emergency_cooldown", 300)  # 5 минут

        # Пороги риска
        self.risk_thresholds = config.get(
            "risk_thresholds",
            {"low": 30.0, "medium": 60.0, "high": 80.0, "critical": 95.0},
        )

        # Кеш метрик
        self._metrics_cache: Optional[RiskMetrics] = None
        self._last_metrics_update: Optional[datetime] = None
        self._metrics_cache_ttl = 30  # секунд

        # Последние экстренные действия
        self._last_emergency_action: Optional[datetime] = None

    async def initialize(self) -> bool:
        """Инициализация менеджера рисков"""
        try:
            self.logger.info("Инициализация менеджера рисков...")

            # Инициализация подсистем
            await self._initialize_subsystems()

            # Проверка начальных рисков
            await self._initial_risk_check()

            self.logger.info("Менеджер рисков инициализирован")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации менеджера рисков: {e}")
            return False

    async def _initialize_subsystems(self):
        """Инициализация подсистем управления рисками"""

        # Position Risk Manager
        self.position_risk = PositionRiskManager(
            config=self.config.get("position_risk", {}),
            position_manager=self.position_manager,
        )
        await self.position_risk.initialize()

        # Enhanced SLTP Manager
        self.sltp_manager = EnhancedSLTPManager(
            config=self.config.get("sltp", {}),
            position_manager=self.position_manager,
            exchange_registry=self.exchange_registry,
        )
        await self.sltp_manager.initialize()

        # Portfolio Exposure Manager
        self.portfolio_exposure = PortfolioExposureManager(
            config=self.config.get("portfolio_exposure", {}),
            position_manager=self.position_manager,
            exchange_registry=self.exchange_registry,
        )
        await self.portfolio_exposure.initialize()

        # Risk Limits Manager
        self.limits_manager = RiskLimitsManager(
            config=self.config.get("limits", {}), position_manager=self.position_manager
        )
        await self.limits_manager.initialize()

        # Risk Calculator
        self.calculator = RiskCalculator(
            config=self.config.get("calculator", {}),
            position_manager=self.position_manager,
            exchange_registry=self.exchange_registry,
        )

        self.logger.info("Подсистемы риск-менеджмента инициализированы")

    async def _initial_risk_check(self):
        """Начальная проверка рисков"""
        try:
            risk_status = await self.check_global_risks()

            if risk_status.overall_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                self.logger.warning(
                    f"Обнаружен высокий уровень риска при инициализации: {risk_status.message}"
                )

                # Если критический риск - может потребоваться немедленное действие
                if risk_status.overall_level == RiskLevel.CRITICAL:
                    await self._handle_critical_risk(risk_status)

        except Exception as e:
            self.logger.error(f"Ошибка начальной проверки рисков: {e}")

    async def start(self) -> bool:
        """Запуск менеджера рисков"""
        try:
            if self._running:
                return True

            self.logger.info("Запуск менеджера рисков...")

            # Запуск подсистем
            await self.sltp_manager.start()
            await self.portfolio_exposure.start()

            # Запуск мониторинга
            self._running = True
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

            self.logger.info("Менеджер рисков запущен")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка запуска менеджера рисков: {e}")
            return False

    async def stop(self) -> bool:
        """Остановка менеджера рисков"""
        try:
            if not self._running:
                return True

            self.logger.info("Остановка менеджера рисков...")
            self._running = False

            # Остановка мониторинга
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

            # Остановка подсистем
            if self.sltp_manager:
                await self.sltp_manager.stop()
            if self.portfolio_exposure:
                await self.portfolio_exposure.stop()

            self.logger.info("Менеджер рисков остановлен")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка остановки менеджера рисков: {e}")
            return False

    async def check_signal_risk(self, signal: Dict[str, Any]) -> bool:
        """Проверка риска торгового сигнала"""
        try:
            # Проверка лимитов
            if not await self.limits_manager.check_signal_limits(signal):
                self.logger.warning(f"Сигнал отклонен по лимитам: {signal.get('id')}")
                return False

            # Проверка позиционного риска
            if not await self.position_risk.check_signal_risk(signal):
                self.logger.warning(
                    f"Сигнал отклонен по позиционному риску: {signal.get('id')}"
                )
                return False

            # Проверка портфельного риска
            if not await self.portfolio_exposure.check_signal_risk(signal):
                self.logger.warning(
                    f"Сигнал отклонен по портфельному риску: {signal.get('id')}"
                )
                return False

            # Проверка концентрации
            concentration_risk = await self._calculate_concentration_risk(signal)
            if concentration_risk > self.config.get("max_concentration_risk", 0.3):
                self.logger.warning(
                    f"Сигнал отклонен по концентрации риска: {concentration_risk:.2f}"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Ошибка проверки риска сигнала: {e}")
            return False

    async def check_global_risks(self) -> RiskStatus:
        """Проверка глобальных рисков системы"""
        try:
            alerts = []
            risk_scores = []

            # Проверка рисков по категориям

            # 1. Портфельные риски
            portfolio_risk = await self._check_portfolio_risks()
            if portfolio_risk:
                alerts.extend(portfolio_risk)
                risk_scores.extend(
                    [alert.current_value or 0 for alert in portfolio_risk]
                )

            # 2. Позиционные риски
            position_risks = await self._check_position_risks()
            if position_risks:
                alerts.extend(position_risks)
                risk_scores.extend(
                    [alert.current_value or 0 for alert in position_risks]
                )

            # 3. Риски ликвидности
            liquidity_risks = await self._check_liquidity_risks()
            if liquidity_risks:
                alerts.extend(liquidity_risks)
                risk_scores.extend(
                    [alert.current_value or 0 for alert in liquidity_risks]
                )

            # 4. Корреляционные риски
            correlation_risks = await self._check_correlation_risks()
            if correlation_risks:
                alerts.extend(correlation_risks)
                risk_scores.extend(
                    [alert.current_value or 0 for alert in correlation_risks]
                )

            # 5. Системные риски
            system_risks = await self._check_system_risks()
            if system_risks:
                alerts.extend(system_risks)
                risk_scores.extend([alert.current_value or 0 for alert in system_risks])

            # Расчет общего уровня риска
            overall_risk_score = max(risk_scores) if risk_scores else 0.0
            overall_level = self._calculate_risk_level(overall_risk_score)

            # Определение необходимых действий
            requires_action, action = self._determine_risk_action(overall_level, alerts)

            # Создание общего сообщения
            if not alerts:
                message = "Все риски в пределах нормы"
            else:
                critical_count = len(
                    [a for a in alerts if a.level == RiskLevel.CRITICAL]
                )
                high_count = len([a for a in alerts if a.level == RiskLevel.HIGH])
                message = f"Обнаружено рисков: критических {critical_count}, высоких {high_count}"

            return RiskStatus(
                overall_level=overall_level,
                requires_action=requires_action,
                action=action,
                message=message,
                alerts=alerts,
                risk_score=overall_risk_score,
            )

        except Exception as e:
            self.logger.error(f"Ошибка проверки глобальных рисков: {e}")
            return RiskStatus(
                overall_level=RiskLevel.CRITICAL,
                requires_action=True,
                action=RiskAction.EMERGENCY_STOP,
                message=f"Ошибка проверки рисков: {e}",
                risk_score=100.0,
            )

    async def _check_portfolio_risks(self) -> List[RiskAlert]:
        """Проверка портфельных рисков"""
        alerts = []

        try:
            # Получение метрик
            metrics = await self.get_risk_metrics()

            # Проверка максимального просадки
            max_drawdown_limit = self.config.get("max_drawdown_percent", 20.0)
            if metrics.max_drawdown > max_drawdown_limit:
                alerts.append(
                    RiskAlert(
                        alert_id=f"drawdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        risk_type="portfolio_drawdown",
                        level=(
                            RiskLevel.HIGH
                            if metrics.max_drawdown < max_drawdown_limit * 1.5
                            else RiskLevel.CRITICAL
                        ),
                        message=f"Превышена максимальная просадка: {metrics.max_drawdown:.2f}% (лимит: {max_drawdown_limit}%)",
                        action=RiskAction.REDUCE_POSITIONS,
                        timestamp=datetime.now(),
                        current_value=metrics.max_drawdown,
                        threshold_value=max_drawdown_limit,
                    )
                )

            # Проверка использования маржи
            margin_limit = self.config.get("max_margin_usage", 80.0)
            if metrics.margin_usage > margin_limit:
                alerts.append(
                    RiskAlert(
                        alert_id=f"margin_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        risk_type="margin_usage",
                        level=(
                            RiskLevel.HIGH
                            if metrics.margin_usage < margin_limit * 1.2
                            else RiskLevel.CRITICAL
                        ),
                        message=f"Превышено использование маржи: {metrics.margin_usage:.2f}% (лимит: {margin_limit}%)",
                        action=RiskAction.REDUCE_POSITIONS,
                        timestamp=datetime.now(),
                        current_value=metrics.margin_usage,
                        threshold_value=margin_limit,
                    )
                )

            # Проверка концентрации
            concentration_limit = self.config.get("max_concentration", 30.0)
            if metrics.concentration_risk > concentration_limit:
                alerts.append(
                    RiskAlert(
                        alert_id=f"concentration_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        risk_type="concentration_risk",
                        level=(
                            RiskLevel.MEDIUM
                            if metrics.concentration_risk < concentration_limit * 1.5
                            else RiskLevel.HIGH
                        ),
                        message=f"Превышена концентрация портфеля: {metrics.concentration_risk:.2f}% (лимит: {concentration_limit}%)",
                        action=RiskAction.WARNING,
                        timestamp=datetime.now(),
                        current_value=metrics.concentration_risk,
                        threshold_value=concentration_limit,
                    )
                )

        except Exception as e:
            self.logger.error(f"Ошибка проверки портфельных рисков: {e}")

        return alerts

    async def _check_position_risks(self) -> List[RiskAlert]:
        """Проверка позиционных рисков"""
        alerts = []

        try:
            positions = await self.position_manager.get_all_positions()

            for position in positions:
                if position.size == 0:
                    continue

                # Проверка размера позиции
                position_value = abs(position.size * position.mark_price)
                portfolio_value = (
                    await self.position_manager.get_total_portfolio_value()
                )

                if portfolio_value > 0:
                    position_percent = (position_value / portfolio_value) * 100
                    max_position_percent = self.config.get("max_position_percent", 10.0)

                    if position_percent > max_position_percent:
                        alerts.append(
                            RiskAlert(
                                alert_id=f"position_size_{position.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                risk_type="position_size",
                                level=(
                                    RiskLevel.MEDIUM
                                    if position_percent < max_position_percent * 1.5
                                    else RiskLevel.HIGH
                                ),
                                message=f"Превышен размер позиции {position.symbol}: {position_percent:.2f}% (лимит: {max_position_percent}%)",
                                action=RiskAction.WARNING,
                                timestamp=datetime.now(),
                                symbol=position.symbol,
                                current_value=position_percent,
                                threshold_value=max_position_percent,
                            )
                        )

                # Проверка PnL позиции
                if position.unrealized_pnl_percent < -self.config.get(
                    "max_position_loss_percent", 15.0
                ):
                    alerts.append(
                        RiskAlert(
                            alert_id=f"position_loss_{position.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            risk_type="position_loss",
                            level=RiskLevel.HIGH,
                            message=f"Большая убыточная позиция {position.symbol}: {position.unrealized_pnl_percent:.2f}%",
                            action=RiskAction.REDUCE_POSITIONS,
                            timestamp=datetime.now(),
                            symbol=position.symbol,
                            current_value=position.unrealized_pnl_percent,
                        )
                    )

        except Exception as e:
            self.logger.error(f"Ошибка проверки позиционных рисков: {e}")

        return alerts

    async def _check_liquidity_risks(self) -> List[RiskAlert]:
        """Проверка рисков ликвидности"""
        alerts = []

        try:
            # Проверка количества открытых позиций
            positions = await self.position_manager.get_all_positions()
            active_positions = [p for p in positions if p.size != 0]

            max_positions = self.config.get("max_open_positions", 20)
            if len(active_positions) > max_positions:
                alerts.append(
                    RiskAlert(
                        alert_id=f"too_many_positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        risk_type="liquidity_positions",
                        level=RiskLevel.MEDIUM,
                        message=f"Слишком много открытых позиций: {len(active_positions)} (лимит: {max_positions})",
                        action=RiskAction.WARNING,
                        timestamp=datetime.now(),
                        current_value=len(active_positions),
                        threshold_value=max_positions,
                    )
                )

            # Проверка баланса свободных средств
            for exchange_name in self.exchange_registry.get_exchange_names():
                exchange = self.exchange_registry.get_exchange(exchange_name)
                if exchange:
                    balance = await exchange.get_balance()

                    # Проверка минимального свободного баланса
                    total_balance = balance.get("total", 0)
                    free_balance = balance.get("free", 0)

                    if total_balance > 0:
                        free_percent = (free_balance / total_balance) * 100
                        min_free_percent = self.config.get(
                            "min_free_balance_percent", 10.0
                        )

                        if free_percent < min_free_percent:
                            alerts.append(
                                RiskAlert(
                                    alert_id=f"low_balance_{exchange_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                    risk_type="liquidity_balance",
                                    level=RiskLevel.MEDIUM,
                                    message=f"Низкий свободный баланс на {exchange_name}: {free_percent:.2f}% (мин: {min_free_percent}%)",
                                    action=RiskAction.WARNING,
                                    timestamp=datetime.now(),
                                    current_value=free_percent,
                                    threshold_value=min_free_percent,
                                    metadata={"exchange": exchange_name},
                                )
                            )

        except Exception as e:
            self.logger.error(f"Ошибка проверки рисков ликвидности: {e}")

        return alerts

    async def _check_correlation_risks(self) -> List[RiskAlert]:
        """Проверка корреляционных рисков"""
        alerts = []

        try:
            correlation_risk = await self.calculator.calculate_correlation_risk()
            max_correlation = self.config.get("max_correlation_risk", 0.7)

            if correlation_risk > max_correlation:
                alerts.append(
                    RiskAlert(
                        alert_id=f"correlation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        risk_type="correlation_risk",
                        level=(
                            RiskLevel.MEDIUM
                            if correlation_risk < max_correlation * 1.2
                            else RiskLevel.HIGH
                        ),
                        message=f"Высокая корреляция между позициями: {correlation_risk:.2f} (лимит: {max_correlation})",
                        action=RiskAction.WARNING,
                        timestamp=datetime.now(),
                        current_value=correlation_risk,
                        threshold_value=max_correlation,
                    )
                )

        except Exception as e:
            self.logger.error(f"Ошибка проверки корреляционных рисков: {e}")

        return alerts

    async def _check_system_risks(self) -> List[RiskAlert]:
        """Проверка системных рисков"""
        alerts = []

        try:
            # Проверка времени последнего обновления цен
            last_price_update = await self.position_manager.get_last_price_update()
            if last_price_update:
                time_since_update = (datetime.now() - last_price_update).total_seconds()
                max_price_age = self.config.get("max_price_age_seconds", 60)

                if time_since_update > max_price_age:
                    alerts.append(
                        RiskAlert(
                            alert_id=f"stale_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            risk_type="system_data",
                            level=RiskLevel.HIGH,
                            message=f"Устаревшие ценовые данные: {time_since_update:.0f}с (лимит: {max_price_age}с)",
                            action=RiskAction.PAUSE_TRADING,
                            timestamp=datetime.now(),
                            current_value=time_since_update,
                            threshold_value=max_price_age,
                        )
                    )

            # Проверка подключения к биржам
            for exchange_name in self.exchange_registry.get_exchange_names():
                exchange = self.exchange_registry.get_exchange(exchange_name)
                if exchange:
                    if not await exchange.is_connected():
                        alerts.append(
                            RiskAlert(
                                alert_id=f"exchange_disconnect_{exchange_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                risk_type="system_connection",
                                level=RiskLevel.HIGH,
                                message=f"Потеряно соединение с биржей {exchange_name}",
                                action=RiskAction.PAUSE_TRADING,
                                timestamp=datetime.now(),
                                metadata={"exchange": exchange_name},
                            )
                        )

        except Exception as e:
            self.logger.error(f"Ошибка проверки системных рисков: {e}")

        return alerts

    def _calculate_risk_level(self, risk_score: float) -> RiskLevel:
        """Расчет уровня риска по скору"""
        if risk_score >= self.risk_thresholds["critical"]:
            return RiskLevel.CRITICAL
        elif risk_score >= self.risk_thresholds["high"]:
            return RiskLevel.HIGH
        elif risk_score >= self.risk_thresholds["medium"]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _determine_risk_action(
        self, level: RiskLevel, alerts: List[RiskAlert]
    ) -> tuple[bool, RiskAction]:
        """Определение необходимых действий по уровню риска"""
        if level == RiskLevel.CRITICAL:
            return True, RiskAction.EMERGENCY_STOP
        elif level == RiskLevel.HIGH:
            # Проверяем типы алертов для более точного действия
            has_system_risk = any(a.risk_type.startswith("system_") for a in alerts)
            if has_system_risk:
                return True, RiskAction.PAUSE_TRADING
            else:
                return True, RiskAction.REDUCE_POSITIONS
        elif level == RiskLevel.MEDIUM:
            return True, RiskAction.WARNING
        else:
            return False, RiskAction.NONE

    async def _handle_critical_risk(self, risk_status: RiskStatus):
        """Обработка критического риска"""
        try:
            # Проверка cooldown для экстренных действий
            if self._last_emergency_action:
                time_since_last = (
                    datetime.now() - self._last_emergency_action
                ).total_seconds()
                if time_since_last < self.emergency_cooldown:
                    self.logger.warning(
                        f"Экстренное действие отложено (cooldown: {time_since_last:.0f}с)"
                    )
                    return

            self.logger.critical(f"КРИТИЧЕСКИЙ РИСК: {risk_status.message}")

            # Выполнение экстренного действия
            if risk_status.action == RiskAction.EMERGENCY_STOP:
                await self._emergency_stop()
            elif risk_status.action == RiskAction.CLOSE_POSITIONS:
                await self._close_all_positions()
            elif risk_status.action == RiskAction.REDUCE_POSITIONS:
                await self._reduce_positions()

            self._last_emergency_action = datetime.now()

        except Exception as e:
            self.logger.error(f"Ошибка обработки критического риска: {e}")

    async def _emergency_stop(self):
        """Экстренная остановка торговли"""
        self.logger.critical("ЭКСТРЕННАЯ ОСТАНОВКА ТОРГОВЛИ")

        # Здесь должна быть логика экстренной остановки
        # Например, отправка сигнала оркестратору для остановки всех трейдеров
        pass

    async def _close_all_positions(self):
        """Закрытие всех позиций"""
        self.logger.warning("Закрытие всех позиций")

        try:
            positions = await self.position_manager.get_all_positions()

            for position in positions:
                if position.size != 0:
                    await self.position_manager.close_position(position.symbol)

        except Exception as e:
            self.logger.error(f"Ошибка закрытия позиций: {e}")

    async def _reduce_positions(self):
        """Сокращение позиций"""
        self.logger.warning("Сокращение позиций")

        try:
            positions = await self.position_manager.get_all_positions()

            # Сокращаем позиции на 50%
            for position in positions:
                if position.size != 0:
                    new_size = position.size * Decimal("0.5")
                    await self.position_manager.reduce_position(
                        position.symbol, abs(new_size)
                    )

        except Exception as e:
            self.logger.error(f"Ошибка сокращения позиций: {e}")

    async def _calculate_concentration_risk(self, signal: Dict[str, Any]) -> float:
        """Расчет риска концентрации для сигнала"""
        try:
            symbol = signal.get("symbol")
            if not symbol:
                return 0.0

            # Получение текущего портфеля
            positions = await self.position_manager.get_all_positions()
            total_value = await self.position_manager.get_total_portfolio_value()

            if total_value <= 0:
                return 0.0

            # Расчет текущей концентрации по символу
            symbol_value = Decimal("0")
            for position in positions:
                if position.symbol == symbol:
                    symbol_value += abs(position.size * position.mark_price)

            # Добавление нового сигнала
            signal_size = Decimal(str(signal.get("size", 0)))
            signal_price = Decimal(str(signal.get("price", 0)))
            signal_value = abs(signal_size * signal_price)

            new_symbol_value = symbol_value + signal_value
            concentration = float(new_symbol_value / total_value)

            return concentration

        except Exception as e:
            self.logger.error(f"Ошибка расчета концентрации: {e}")
            return 1.0  # Максимальный риск при ошибке

    async def _monitoring_loop(self):
        """Основной цикл мониторинга рисков"""
        self.logger.info("Запуск мониторинга рисков")

        while self._running:
            try:
                # Проверка рисков
                risk_status = await self.check_global_risks()

                # Обработка новых алертов
                await self._process_new_alerts(risk_status.alerts)

                # Обработка критических рисков
                if risk_status.overall_level == RiskLevel.CRITICAL:
                    await self._handle_critical_risk(risk_status)

                await asyncio.sleep(self.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в мониторинге рисков: {e}")
                await asyncio.sleep(60)

    async def _process_new_alerts(self, alerts: List[RiskAlert]):
        """Обработка новых алертов"""
        for alert in alerts:
            # Добавление в активные алерты
            self.active_alerts[alert.alert_id] = alert

            # Добавление в историю
            self.alert_history.append(alert)

            # Ограничение истории
            if len(self.alert_history) > self.max_alert_history:
                self.alert_history = self.alert_history[-self.max_alert_history :]

            # Логирование
            log_level = {
                RiskLevel.LOW: logging.INFO,
                RiskLevel.MEDIUM: logging.WARNING,
                RiskLevel.HIGH: logging.ERROR,
                RiskLevel.CRITICAL: logging.CRITICAL,
            }.get(alert.level, logging.INFO)

            self.logger.log(
                log_level, f"RISK ALERT [{alert.level.value.upper()}]: {alert.message}"
            )

    async def get_risk_metrics(self) -> RiskMetrics:
        """Получение метрик риска"""
        try:
            # Проверка кеша
            now = datetime.now()
            if (
                self._metrics_cache
                and self._last_metrics_update
                and (now - self._last_metrics_update).total_seconds()
                < self._metrics_cache_ttl
            ):
                return self._metrics_cache

            # Расчет новых метрик
            metrics = RiskMetrics()

            # Портфельные метрики
            metrics.portfolio_value = (
                await self.position_manager.get_total_portfolio_value()
            )
            metrics.total_exposure = (
                await self.portfolio_exposure.calculate_total_exposure()
            )

            # Метрики производительности
            metrics.max_drawdown = await self.calculator.calculate_max_drawdown()
            metrics.var_95 = await self.calculator.calculate_var_95()
            metrics.sharpe_ratio = await self.calculator.calculate_sharpe_ratio()
            metrics.sortino_ratio = await self.calculator.calculate_sortino_ratio()

            # Метрики риска
            metrics.correlation_risk = (
                await self.calculator.calculate_correlation_risk()
            )
            metrics.concentration_risk = (
                await self.calculator.calculate_concentration_risk()
            )
            metrics.leverage_ratio = await self.calculator.calculate_leverage_ratio()
            metrics.margin_usage = await self.calculator.calculate_margin_usage()

            # PnL метрики
            metrics.daily_pnl = await self.position_manager.get_daily_pnl()
            metrics.unrealized_pnl = await self.position_manager.get_unrealized_pnl()

            # Позиционные метрики
            positions = await self.position_manager.get_all_positions()
            metrics.open_positions_count = len([p for p in positions if p.size != 0])

            # Общий риск-скор
            metrics.risk_score = await self.calculator.calculate_overall_risk_score(
                metrics
            )

            # Кеширование
            self._metrics_cache = metrics
            self._last_metrics_update = now

            return metrics

        except Exception as e:
            self.logger.error(f"Ошибка получения метрик риска: {e}")
            return RiskMetrics()

    def get_active_alerts(self) -> List[RiskAlert]:
        """Получение активных алертов"""
        return list(self.active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[RiskAlert]:
        """Получение истории алертов"""
        return self.alert_history[-limit:]

    async def health_check(self) -> bool:
        """Проверка здоровья менеджера рисков"""
        try:
            # Проверка подсистем
            if self.sltp_manager and not await self.sltp_manager.health_check():
                return False

            if (
                self.portfolio_exposure
                and not await self.portfolio_exposure.health_check()
            ):
                return False

            # Проверка мониторинга
            if self._running and self._monitoring_task and self._monitoring_task.done():
                exception = self._monitoring_task.exception()
                if exception:
                    self.logger.error(
                        f"Задача мониторинга завершилась с ошибкой: {exception}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Ошибка проверки здоровья менеджера рисков: {e}")
            return False

    def is_running(self) -> bool:
        """Проверка работает ли менеджер"""
        return self._running
