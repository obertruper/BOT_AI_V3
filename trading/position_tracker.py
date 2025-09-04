"""
Enhanced Position Tracker для BOT_AI_V3
Интегрирует лучшие решения из V2 с архитектурой V3
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

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
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    status: PositionStatus = PositionStatus.ACTIVE
    health: PositionHealth = PositionHealth.UNKNOWN
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metrics: PositionMetrics | None = None
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
        self.tracked_positions: dict[str, TrackedPosition] = {}

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
        self.monitoring_task: asyncio.Task | None = None

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
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
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

    async def get_position(self, position_id: str) -> TrackedPosition | None:
        """Получить позицию по ID"""
        return self.tracked_positions.get(position_id)

    async def get_active_positions(self) -> list[TrackedPosition]:
        """Получить все активные позиции"""
        return [
            pos for pos in self.tracked_positions.values() if pos.status == PositionStatus.ACTIVE
        ]

    async def get_positions_by_symbol(self, symbol: str) -> list[TrackedPosition]:
        """Получить позиции по символу"""
        return [pos for pos in self.tracked_positions.values() if pos.symbol == symbol]

    async def get_all_positions(self) -> list[TrackedPosition]:
        """Получить все позиции (алиас для get_active_positions для совместимости)"""
        return await self.get_active_positions()

    async def calculate_unrealized_pnl(self, position_id: str) -> Decimal | None:
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
            # exchange_data может быть либо dict (из fetch_positions), либо Position объект
            if isinstance(exchange_data, dict):
                position.current_price = Decimal(str(exchange_data.get("markPrice", 0)))
                position.size = Decimal(str(exchange_data.get("size", position.size)))
                size_value = exchange_data.get("size", 0)
            else:
                # Если это объект Position
                position.current_price = Decimal(str(getattr(exchange_data, "mark_price", 0)))
                position.size = Decimal(str(getattr(exchange_data, "size", position.size)))
                size_value = getattr(exchange_data, "size", 0)

            # Проверяем статус
            if size_value == 0:
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

    async def get_tracker_stats(self) -> dict[str, Any]:
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
            # Исправляем: используем get_ticker вместо несуществующего fetch_ticker
            ticker = await exchange_instance.get_ticker(symbol)
            return Decimal(str(ticker.last_price))
        except Exception as e:
            logger.error(f"❌ Ошибка получения цены {symbol}: {e}")
            return Decimal("0")

    async def _fetch_position_from_exchange(self, position: TrackedPosition) -> dict | None:
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

    async def sync_positions(self) -> None:
        """Синхронизирует позиции с биржей"""
        try:
            if not self.exchange_manager:
                logger.warning("ExchangeManager не установлен, пропускаем синхронизацию")
                return

            # Получаем позиции с всех бирж
            for exchange_name in self.exchange_manager.exchanges:
                try:
                    positions = await self.exchange_manager.get_positions(exchange_name)

                    # Сформируем множество актуальных символов с непустым размером на бирже
                    present_symbols: set[str] = set()

                    # Обновляем tracked_positions по фактическим данным биржи
                    for position_data in positions:
                        # position_data теперь объект Position из exchanges/base/models.py (либо dict в некоторых источниках)
                        symbol = (
                            position_data.symbol
                            if hasattr(position_data, "symbol")
                            else (
                                position_data.get("symbol")
                                if isinstance(position_data, dict)
                                else None
                            )
                        )

                        if not symbol:
                            continue

                        # Определяем размер позиции (contracts|size) и текущую/входную цену
                        size_val = (
                            getattr(position_data, "size", None)
                            if hasattr(position_data, "size")
                            else (
                                position_data.get("contracts")
                                if isinstance(position_data, dict)
                                else None
                            )
                        )
                        try:
                            size_val = Decimal(str(size_val or 0))
                        except Exception:
                            size_val = Decimal("0")

                        # Пропускаем нулевые позиции, но зафиксируем символ, чтобы ниже корректно обработать закрытие
                        if size_val and size_val != 0:
                            present_symbols.add(symbol)

                        # Если размер нулевой — на обновление/создание не тратим ресурсы (будет обработано удаление ниже)
                        if size_val == 0:
                            continue

                        # Создаем или обновляем локальную позицию
                        position_id = f"{exchange_name}_{symbol}"

                        if position_id not in self.tracked_positions:
                            # Создаем новую позицию
                            tracked_position = TrackedPosition(
                                position_id=position_id,
                                symbol=symbol,
                                side=(
                                    getattr(position_data, "side", "")
                                    if hasattr(position_data, "side")
                                    else position_data.get("side", "")
                                ),
                                size=size_val,
                                entry_price=Decimal(
                                    str(
                                        getattr(position_data, "entry_price", 0)
                                        if hasattr(position_data, "entry_price")
                                        else position_data.get("entry_price", 0)
                                    )
                                ),
                                current_price=Decimal(
                                    str(
                                        getattr(position_data, "mark_price", 0)
                                        if hasattr(position_data, "mark_price")
                                        else position_data.get("markPrice", 0)
                                    )
                                ),
                                stop_loss=(
                                    Decimal(str(position_data.stop_loss))
                                    if hasattr(position_data, "stop_loss")
                                    and position_data.stop_loss is not None
                                    else (
                                        Decimal(str(position_data.get("stop_loss")))
                                        if isinstance(position_data, dict)
                                        and position_data.get("stop_loss") is not None
                                        else None
                                    )
                                ),
                                take_profit=(
                                    Decimal(str(position_data.take_profit))
                                    if hasattr(position_data, "take_profit")
                                    and position_data.take_profit is not None
                                    else (
                                        Decimal(str(position_data.get("take_profit")))
                                        if isinstance(position_data, dict)
                                        and position_data.get("take_profit") is not None
                                        else None
                                    )
                                ),
                                exchange=exchange_name,
                            )
                            self.tracked_positions[position_id] = tracked_position
                        else:
                            # Обновляем существующую
                            tracked_position = self.tracked_positions[position_id]
                            tracked_position.current_price = Decimal(
                                str(
                                    getattr(position_data, "mark_price", 0)
                                    if hasattr(position_data, "mark_price")
                                    else position_data.get("markPrice", 0)
                                )
                            )
                            tracked_position.size = size_val
                            tracked_position.updated_at = datetime.now()

                            # Обновляем метрики PnL, если присутствуют
                            if tracked_position.metrics:
                                try:
                                    unreal = (
                                        getattr(position_data, "unrealised_pnl", None)
                                        if hasattr(position_data, "unrealised_pnl")
                                        else (
                                            position_data.get("unrealisedPnl")
                                            if isinstance(position_data, dict)
                                            else None
                                        )
                                    )
                                    real = (
                                        getattr(position_data, "realised_pnl", None)
                                        if hasattr(position_data, "realised_pnl")
                                        else (
                                            position_data.get("realisedPnl")
                                            if isinstance(position_data, dict)
                                            else None
                                        )
                                    )
                                    if unreal is not None:
                                        tracked_position.metrics.unrealized_pnl = Decimal(
                                            str(unreal)
                                        )
                                    if real is not None:
                                        tracked_position.metrics.realized_pnl = Decimal(str(real))
                                except Exception:
                                    pass

                    # Закрываем/удаляем из отслеживания локальные позиции, которых больше нет на бирже
                    # и те, у которых размер стал нулевым
                    stale_ids: list[str] = []
                    for pos_id, tracked in list(self.tracked_positions.items()):
                        if tracked.exchange != exchange_name:
                            continue
                        # Если символ не в списке актуальных с ненулевым размером — считаем позицию закрытой
                        if tracked.symbol not in present_symbols:
                            stale_ids.append(pos_id)

                    for pos_id in stale_ids:
                        await self.remove_position(pos_id, "closed")

                    logger.info(
                        f"✅ Синхронизировано {len(present_symbols)} активных позиций с {exchange_name}; "
                        f"закрыто: {len(stale_ids)}"
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка синхронизации с {exchange_name}: {e}")

        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации позиций: {e}")

    async def calculate_total_pnl(self) -> Decimal:
        """Рассчитывает общий PnL по всем позициям"""
        total_pnl = Decimal("0")

        for position in self.tracked_positions.values():
            # Суммируем realized и unrealized PnL из метрик
            if position.metrics:
                total_pnl += position.metrics.realized_pnl + position.metrics.unrealized_pnl

        logger.info(f"💰 Общий PnL: ${total_pnl:.2f}")
        return total_pnl


# Глобальный экземпляр для использования в системе
position_tracker: EnhancedPositionTracker | None = None


async def get_position_tracker() -> EnhancedPositionTracker:
    """Получить глобальный экземпляр position tracker"""
    global position_tracker

    if position_tracker is None:
        from core.config.config_manager import get_global_config_manager
        from exchanges.exchange_manager import ExchangeManager

        # Получаем конфигурацию для ExchangeManager
        try:
            config_manager = get_global_config_manager()
            config = config_manager.get_config()
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить конфигурацию: {e}, используем базовую")
            # Минимальная конфигурация для инициализации ExchangeManager
            config = {
                "exchanges": {
                    "bybit": {"enabled": True, "api_key": "", "api_secret": "", "testnet": False}
                }
            }

        exchange_manager = ExchangeManager(config)
        position_tracker = EnhancedPositionTracker(exchange_manager)

    return position_tracker
