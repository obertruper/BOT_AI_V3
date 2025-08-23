"""
Enhanced Position Tracker для BOT_AI_V3
Интегрирует лучшие решения из V2 с архитектурой V3
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from core.logger import setup_logger
from database.db_manager import get_db
from exchanges.exchange_manager import ExchangeManager

logger = setup_logger(__name__)


class PositionStatus(Enum):
    """Статусы позиций"""

    ACTIVE = "active"
    CLOSED = "closed"
    PARTIAL_CLOSED = "partial_closed"
    LIQUIDATED = "liquidated"
    ERROR = "error"


class PositionHealth(Enum):
    """Статусы здоровья позиций"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class PositionMetrics:
    """Метрики позиции"""

    position_id: str
    unrealized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    current_price: Decimal = field(default_factory=lambda: Decimal("0"))
    roi_percent: Decimal = field(default_factory=lambda: Decimal("0"))
    hold_time_minutes: int = 0
    max_profit: Decimal = field(default_factory=lambda: Decimal("0"))
    max_drawdown: Decimal = field(default_factory=lambda: Decimal("0"))
    health_score: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class TrackedPosition:
    """Отслеживаемая позиция"""

    position_id: str
    symbol: str
    side: str
    size: Decimal
    entry_price: Decimal
    current_price: Decimal = field(default_factory=lambda: Decimal("0"))
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    status: PositionStatus = PositionStatus.ACTIVE
    health: PositionHealth = PositionHealth.UNKNOWN
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metrics: Optional[PositionMetrics] = None
    exchange: str = "bybit"

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = PositionMetrics(self.position_id)


class EnhancedPositionTracker:
    """
    Улучшенный трекер позиций с функциональностью из V2

    Основные возможности:
    - Real-time отслеживание позиций
    - Расчет детальных метрик (PnL, ROI, Sharpe)
    - Health check позиций
    - Синхронизация с биржей
    - Автоматическое обновление БД
    """

    def __init__(
        self,
        exchange_manager: ExchangeManager,
        update_interval: int = 30,
    ):
        self.exchange_manager = exchange_manager
        self.update_interval = update_interval
        self.db_manager = None

        # Активные позиции
        self.tracked_positions: Dict[str, TrackedPosition] = {}

        # Настройки
        self.max_health_check_interval = 300  # 5 минут
        self.critical_pnl_threshold = -0.05  # -5%
        self.warning_pnl_threshold = -0.03  # -3%

        # Статистика
        self.stats = {
            "total_tracked": 0,
            "active_positions": 0,
            "updates_count": 0,
            "sync_errors": 0,
            "last_update": None,
        }

        # Флаги
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None

        logger.info("✅ Enhanced Position Tracker инициализирован")

    async def start_tracking(self):
        """Запуск мониторинга позиций"""
        if self.is_running:
            logger.warning("Position Tracker уже запущен")
            return

        self.is_running = True
        
        # Инициализируем DBManager
        self.db_manager = await get_db()

        # Загружаем активные позиции из БД
        await self._load_active_positions()

        # Запускаем фоновый мониторинг
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info(
            f"🚀 Position Tracker запущен, отслеживается {len(self.tracked_positions)} позиций"
        )

    async def stop_tracking(self):
        """Остановка мониторинга"""
        self.is_running = False

        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Position Tracker остановлен")

    async def track_position(
        self,
        position_id: str,
        symbol: str,
        side: str,
        size: Decimal,
        entry_price: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        exchange: str = "bybit",
    ) -> TrackedPosition:
        """
        Добавить позицию в отслеживание

        Args:
            position_id: Уникальный ID позиции
            symbol: Торговая пара
            side: long/short
            size: Размер позиции
            entry_price: Цена входа
            stop_loss: Стоп-лосс (опционально)
            take_profit: Тейк-профит (опционально)
            exchange: Биржа

        Returns:
            TrackedPosition: Объект отслеживаемой позиции
        """

        position = TrackedPosition(
            position_id=position_id,
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            exchange=exchange,
        )

        # Получаем текущую цену
        position.current_price = await self._get_current_price(symbol, exchange)

        # Добавляем в отслеживание
        self.tracked_positions[position_id] = position

        # Сохраняем в БД
        await self._save_position_to_db(position)

        # Обновляем статистику
        self.stats["total_tracked"] += 1
        self.stats["active_positions"] = len(self.tracked_positions)

        logger.info(
            f"📊 Добавлена позиция в отслеживание: {position_id} | "
            f"{symbol} {side} {size} @ {entry_price}"
        )

        return position

    async def remove_position(self, position_id: str, reason: str = "closed"):
        """
        Удалить позицию из отслеживания

        Args:
            position_id: ID позиции
            reason: Причина удаления
        """

        if position_id not in self.tracked_positions:
            logger.warning(f"Позиция {position_id} не найдена для удаления")
            return

        position = self.tracked_positions[position_id]

        # Обновляем статус
        if reason == "closed":
            position.status = PositionStatus.CLOSED
        elif reason == "liquidated":
            position.status = PositionStatus.LIQUIDATED
        else:
            position.status = PositionStatus.ERROR

        # Финальное обновление в БД
        await self._update_position_in_db(position)

        # Удаляем из отслеживания
        del self.tracked_positions[position_id]

        # Обновляем статистику
        self.stats["active_positions"] = len(self.tracked_positions)

        logger.info(f"🗑️ Позиция {position_id} удалена из отслеживания: {reason}")

    async def update_position_metrics(self, position_id: str) -> bool:
        """
        Обновить метрики позиции

        Args:
            position_id: ID позиции

        Returns:
            bool: Успех операции
        """

        if position_id not in self.tracked_positions:
            return False

        position = self.tracked_positions[position_id]

        try:
            # Получаем текущую цену
            current_price = await self._get_current_price(position.symbol, position.exchange)
            position.current_price = current_price

            # Рассчитываем метрики
            await self._calculate_position_metrics(position)

            # Проверяем здоровье позиции
            await self._check_position_health(position)

            # Обновляем временные метки
            position.updated_at = datetime.now()
            position.metrics.last_updated = datetime.now()

            # Сохраняем в БД
            await self._update_position_in_db(position)

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обновления метрик позиции {position_id}: {e}")
            return False

    async def get_position(self, position_id: str) -> Optional[TrackedPosition]:
        """Получить позицию по ID"""
        return self.tracked_positions.get(position_id)

    async def get_active_positions(self) -> List[TrackedPosition]:
        """Получить все активные позиции"""
        return [
            pos for pos in self.tracked_positions.values() if pos.status == PositionStatus.ACTIVE
        ]

    async def get_positions_by_symbol(self, symbol: str) -> List[TrackedPosition]:
        """Получить позиции по символу"""
        return [pos for pos in self.tracked_positions.values() if pos.symbol == symbol]

    async def calculate_unrealized_pnl(self, position_id: str) -> Optional[Decimal]:
        """
        Рассчитать нереализованный PnL позиции

        Args:
            position_id: ID позиции

        Returns:
            Decimal: Нереализованный PnL или None если позиция не найдена
        """

        position = self.tracked_positions.get(position_id)
        if not position:
            return None

        # Обновляем текущую цену если нужно
        if not position.current_price or position.current_price == 0:
            position.current_price = await self._get_current_price(
                position.symbol, position.exchange
            )

        # Рассчитываем PnL
        if position.side.lower() == "long":
            pnl = (position.current_price - position.entry_price) * position.size
        else:  # short
            pnl = (position.entry_price - position.current_price) * position.size

        return pnl

    async def sync_with_exchange(self, position_id: str) -> bool:
        """
        Синхронизировать позицию с биржей

        Args:
            position_id: ID позиции

        Returns:
            bool: Успех синхронизации
        """

        position = self.tracked_positions.get(position_id)
        if not position:
            return False

        try:
            # Получаем данные с биржи
            exchange_data = await self._fetch_position_from_exchange(position)

            if not exchange_data:
                logger.warning(f"Позиция {position_id} не найдена на бирже")
                return False

            # Обновляем локальные данные
            position.current_price = Decimal(str(exchange_data.get("markPrice", 0)))
            position.size = Decimal(str(exchange_data.get("size", position.size)))

            # Проверяем статус
            if exchange_data.get("size", 0) == 0:
                await self.remove_position(position_id, "closed")
                return True

            # Обновляем метрики
            await self._calculate_position_metrics(position)

            logger.debug(f"🔄 Позиция {position_id} синхронизирована с биржей")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации позиции {position_id}: {e}")
            self.stats["sync_errors"] += 1
            return False

    async def get_tracker_stats(self) -> Dict[str, Any]:
        """Получить статистику трекера"""

        healthy_count = sum(
            1 for pos in self.tracked_positions.values() if pos.health == PositionHealth.HEALTHY
        )

        warning_count = sum(
            1 for pos in self.tracked_positions.values() if pos.health == PositionHealth.WARNING
        )

        critical_count = sum(
            1 for pos in self.tracked_positions.values() if pos.health == PositionHealth.CRITICAL
        )

        total_unrealized_pnl = Decimal("0")
        for pos in self.tracked_positions.values():
            if pos.metrics and pos.metrics.unrealized_pnl:
                total_unrealized_pnl += pos.metrics.unrealized_pnl

        return {
            **self.stats,
            "health_distribution": {
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count,
            },
            "total_unrealized_pnl": float(total_unrealized_pnl),
            "avg_hold_time": self._calculate_avg_hold_time(),
            "is_running": self.is_running,
        }

    # Приватные методы

    async def _monitoring_loop(self):
        """Основной цикл мониторинга"""

        logger.info("🔄 Запущен цикл мониторинга позиций")

        while self.is_running:
            try:
                start_time = time.time()

                # Обновляем все активные позиции
                update_tasks = [
                    self.update_position_metrics(pos_id)
                    for pos_id in list(self.tracked_positions.keys())
                ]

                if update_tasks:
                    await asyncio.gather(*update_tasks, return_exceptions=True)

                # Обновляем статистику
                self.stats["updates_count"] += 1
                self.stats["last_update"] = datetime.now()

                elapsed = time.time() - start_time
                logger.debug(f"📊 Цикл мониторинга завершен за {elapsed:.2f}с")

                # Ждем следующий цикл
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(5)  # Короткая пауза при ошибке

        logger.info("⏹️ Цикл мониторинга позиций завершен")

    async def _calculate_position_metrics(self, position: TrackedPosition):
        """Рассчитать все метрики позиции"""

        if not position.metrics:
            position.metrics = PositionMetrics(position.position_id)

        metrics = position.metrics

        # Нереализованный PnL
        if position.side.lower() == "long":
            unrealized_pnl = (position.current_price - position.entry_price) * position.size
        else:
            unrealized_pnl = (position.entry_price - position.current_price) * position.size

        metrics.unrealized_pnl = unrealized_pnl
        metrics.current_price = position.current_price

        # ROI процент
        if position.entry_price > 0:
            if position.side.lower() == "long":
                roi = ((position.current_price - position.entry_price) / position.entry_price) * 100
            else:
                roi = ((position.entry_price - position.current_price) / position.entry_price) * 100
            metrics.roi_percent = Decimal(str(roi))

        # Время держания
        hold_time = datetime.now() - position.created_at
        metrics.hold_time_minutes = int(hold_time.total_seconds() / 60)

        # Максимальная прибыль/просадка
        if unrealized_pnl > metrics.max_profit:
            metrics.max_profit = unrealized_pnl
        if unrealized_pnl < metrics.max_drawdown:
            metrics.max_drawdown = unrealized_pnl

    async def _check_position_health(self, position: TrackedPosition):
        """Проверить здоровье позиции"""

        if not position.metrics:
            position.health = PositionHealth.UNKNOWN
            return

        roi = float(position.metrics.roi_percent)

        # Определяем статус здоровья на основе ROI
        if roi <= (self.critical_pnl_threshold * 100):
            position.health = PositionHealth.CRITICAL
            position.metrics.health_score = 0.1
        elif roi <= (self.warning_pnl_threshold * 100):
            position.health = PositionHealth.WARNING
            position.metrics.health_score = 0.5
        else:
            position.health = PositionHealth.HEALTHY
            position.metrics.health_score = 1.0

    async def _get_current_price(self, symbol: str, exchange: str) -> Decimal:
        """Получить текущую цену с биржи"""

        try:
            exchange_instance = await self.exchange_manager.get_exchange(exchange)
            ticker = await exchange_instance.fetch_ticker(symbol)
            return Decimal(str(ticker["last"]))
        except Exception as e:
            logger.error(f"❌ Ошибка получения цены {symbol}: {e}")
            return Decimal("0")

    async def _fetch_position_from_exchange(self, position: TrackedPosition) -> Optional[Dict]:
        """Получить данные позиции с биржи"""

        try:
            exchange_instance = await self.exchange_manager.get_exchange(position.exchange)
            positions = await exchange_instance.fetch_positions([position.symbol])

            for pos in positions:
                if (
                    pos["symbol"] == position.symbol
                    and pos["side"] == position.side
                    and float(pos["contracts"]) > 0
                ):
                    return pos

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения позиции с биржи: {e}")
            return None

    async def _load_active_positions(self):
        """Загрузить активные позиции из БД"""

        try:
            query = """
            SELECT position_id, symbol, side, size, entry_price, stop_loss, take_profit, exchange, created_at
            FROM tracked_positions 
            WHERE status = 'active'
            """

            rows = await self.db_manager.fetch_all(query)

            for row in rows:
                position = TrackedPosition(
                    position_id=row["position_id"],
                    symbol=row["symbol"],
                    side=row["side"],
                    size=Decimal(str(row["size"])),
                    entry_price=Decimal(str(row["entry_price"])),
                    stop_loss=Decimal(str(row["stop_loss"])) if row["stop_loss"] else None,
                    take_profit=Decimal(str(row["take_profit"])) if row["take_profit"] else None,
                    exchange=row["exchange"],
                    created_at=row["created_at"],
                )

                self.tracked_positions[position.position_id] = position

            logger.info(f"📥 Загружено {len(self.tracked_positions)} активных позиций из БД")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки позиций из БД: {e}")

    async def _save_position_to_db(self, position: TrackedPosition):
        """Сохранить позицию в БД"""

        try:
            query = """
            INSERT INTO tracked_positions 
            (position_id, symbol, side, size, entry_price, stop_loss, take_profit, 
             exchange, status, health, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (position_id) DO UPDATE SET
                updated_at = $12,
                status = $9,
                health = $10
            """

            await self.db_manager.execute(
                query,
                position.position_id,
                position.symbol,
                position.side,
                float(position.size),
                float(position.entry_price),
                float(position.stop_loss) if position.stop_loss else None,
                float(position.take_profit) if position.take_profit else None,
                position.exchange,
                position.status.value,
                position.health.value,
                position.created_at,
                position.updated_at,
            )

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения позиции в БД: {e}")

    async def _update_position_in_db(self, position: TrackedPosition):
        """Обновить позицию в БД"""

        try:
            query = """
            UPDATE tracked_positions SET
                current_price = $2,
                status = $3,
                health = $4,
                updated_at = $5,
                unrealized_pnl = $6,
                roi_percent = $7,
                hold_time_minutes = $8
            WHERE position_id = $1
            """

            unrealized_pnl = position.metrics.unrealized_pnl if position.metrics else 0
            roi_percent = position.metrics.roi_percent if position.metrics else 0
            hold_time = position.metrics.hold_time_minutes if position.metrics else 0

            await self.db_manager.execute(
                query,
                position.position_id,
                float(position.current_price),
                position.status.value,
                position.health.value,
                position.updated_at,
                float(unrealized_pnl),
                float(roi_percent),
                hold_time,
            )

        except Exception as e:
            logger.error(f"❌ Ошибка обновления позиции в БД: {e}")

    def _calculate_avg_hold_time(self) -> float:
        """Рассчитать среднее время держания позиций"""

        if not self.tracked_positions:
            return 0

        total_time = 0
        count = 0

        for position in self.tracked_positions.values():
            if position.metrics:
                total_time += position.metrics.hold_time_minutes
                count += 1

        return total_time / count if count > 0 else 0


# Глобальный экземпляр для использования в системе
position_tracker: Optional[EnhancedPositionTracker] = None


async def get_position_tracker() -> EnhancedPositionTracker:
    """Получить глобальный экземпляр position tracker"""
    global position_tracker

    if position_tracker is None:
        from exchanges.exchange_manager import ExchangeManager
        from core.config.config_manager import get_global_config_manager

        # Получаем конфигурацию для ExchangeManager
        try:
            config_manager = get_global_config_manager()
            config = config_manager.get_config()
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить конфигурацию: {e}, используем базовую")
            # Минимальная конфигурация для инициализации ExchangeManager
            config = {
                "exchanges": {
                    "bybit": {
                        "enabled": True,
                        "api_key": "",
                        "api_secret": "",
                        "testnet": False
                    }
                }
            }

        exchange_manager = ExchangeManager(config)
        position_tracker = EnhancedPositionTracker(exchange_manager)

    return position_tracker
