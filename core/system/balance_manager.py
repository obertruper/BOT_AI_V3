"""
Менеджер балансов для предотвращения ошибок недостаточности средств
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class ExchangeBalance:
    """Баланс на бирже"""

    exchange: str
    symbol: str  # 'USDT', 'BTC', etc.
    total: Decimal
    available: Decimal  # Доступно для торговли
    locked: Decimal  # Заблокировано в ордерах
    last_updated: datetime


@dataclass
class BalanceReservation:
    """Резервирование баланса для ордера"""

    reservation_id: str
    exchange: str
    symbol: str
    amount: Decimal
    reserved_at: datetime
    expires_at: datetime
    purpose: str  # 'order', 'withdraw', etc.
    metadata: dict[str, Any] = field(default_factory=dict)


class BalanceManager:
    """
    Менеджер балансов для предотвращения ошибок недостаточности средств

    Основные функции:
    - Кеширование балансов всех бирж
    - Резервирование средств перед созданием ордеров
    - Предотвращение превышения доступного баланса
    - Автоматическое обновление балансов
    - Мониторинг использования средств
    - Защита от race conditions при множественных ордерах
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis_client = redis_client
        self.balances: dict[str, dict[str, ExchangeBalance]] = {}  # exchange -> symbol -> balance
        self.reservations: dict[str, BalanceReservation] = {}  # reservation_id -> reservation
        self.update_intervals: dict[str, int] = {}  # exchange -> interval in seconds
        self.last_updates: dict[str, datetime] = {}  # exchange -> last_update_time

        # Настройки
        self.default_update_interval = 30  # секунд
        self.reservation_ttl = timedelta(minutes=5)
        self.balance_cache_ttl = timedelta(minutes=1)
        self.minimum_balance_threshold = Decimal("0.001")  # Минимальный остаток

        # Статистика
        self.stats = {
            "total_checks": 0,
            "successful_reservations": 0,
            "failed_reservations": 0,
            "balance_updates": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Задачи обновления
        self._update_tasks: dict[str, asyncio.Task] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

        # Инициализация Redis
        if not self.redis_client:
            self._init_redis()

    def _init_redis(self):
        """Инициализация Redis клиента"""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379/5")  # DB 5 для балансов
            logger.info("✅ Redis клиент инициализирован для менеджера балансов")
        except Exception as e:
            logger.warning(f"⚠️  Redis недоступен для менеджера балансов: {e}")
            self.redis_client = None

    def set_exchange_manager(self, exchange_manager):
        """Установка менеджера бирж для получения балансов"""
        self.exchange_manager = exchange_manager
        logger.info("✅ Exchange Manager установлен в BalanceManager")

    async def start(self):
        """Запуск менеджера балансов"""
        if self._running:
            logger.warning("BalanceManager уже запущен")
            return

        self._running = True
        logger.info("🚀 Запуск BalanceManager")

        # Запуск задач обновления для каждой биржи - ТОЛЬКО если есть exchange_manager
        if self.exchange_manager:
            exchanges = ["bybit", "binance", "okx", "gate", "kucoin", "htx", "bingx"]
            for exchange in exchanges:
                self.update_intervals[exchange] = self.default_update_interval
                self._update_tasks[exchange] = asyncio.create_task(
                    self._balance_update_loop(exchange)
                )
            logger.info("✅ Запущены задачи обновления балансов для всех бирж")
        else:
            logger.warning("⚠️ Exchange Manager не установлен, обновление балансов отключено")

        # Запуск задачи очистки
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("✅ BalanceManager запущен")

    async def stop(self):
        """Остановка менеджера балансов"""
        if not self._running:
            return

        self._running = False
        logger.info("🛑 Остановка BalanceManager")

        # Отмена всех задач обновления
        for task in self._update_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Отмена задачи очистки
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        self._update_tasks.clear()
        logger.info("✅ BalanceManager остановлен")

    async def check_balance_availability(
        self, exchange: str, symbol: str, amount: Decimal, include_reservations: bool = True
    ) -> tuple[bool, str]:
        """
        Проверка доступности баланса

        Args:
            exchange: Название биржи
            symbol: Символ валюты
            amount: Требуемое количество
            include_reservations: Учитывать ли резервирования

        Returns:
            (доступно, сообщение об ошибке если не доступно)
        """
        self.stats["total_checks"] += 1

        try:
            # Получаем актуальный баланс
            balance = await self._get_balance(exchange, symbol)
            if not balance:
                return False, f"Баланс для {symbol} на {exchange} не найден"

            # Конвертируем в Decimal для безопасных операций
            available = Decimal(str(balance.available))

            # Учитываем резервирования
            if include_reservations:
                reserved_amount = self._get_reserved_amount(exchange, symbol)
                available -= reserved_amount

            # Конвертируем amount в Decimal если необходимо
            amount_decimal = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount

            # Проверяем достаточность средств
            if available < amount_decimal:
                return (
                    False,
                    f"Недостаточно средств: доступно {available}, требуется {amount_decimal}",
                )

            # Проверяем минимальный остаток
            remaining = available - amount_decimal
            if remaining < self.minimum_balance_threshold:
                return False, f"Операция оставит слишком мало средств: {remaining}"

            return True, ""

        except Exception as e:
            logger.error(f"❌ Ошибка проверки доступности баланса: {e}")
            return False, f"Ошибка проверки баланса: {e!s}"

    async def reserve_balance(
        self,
        exchange: str,
        symbol: str,
        amount: Decimal,
        purpose: str = "order",
        metadata: dict[str, Any] | None = None,
        ttl_minutes: int = 5,
    ) -> str | None:
        """
        Резервирование баланса

        Args:
            exchange: Название биржи
            symbol: Символ валюты
            amount: Количество для резервирования
            purpose: Цель резервирования
            metadata: Дополнительные метаданные
            ttl_minutes: Время жизни резервирования в минутах

        Returns:
            ID резервирования или None если не удалось
        """
        try:
            # Проверяем доступность
            available, error_msg = await self.check_balance_availability(exchange, symbol, amount)
            if not available:
                logger.warning(
                    f"⚠️  Невозможно зарезервировать {amount} {symbol} на {exchange}: {error_msg}"
                )
                self.stats["failed_reservations"] += 1
                return None

            # Создаем резервирование
            reservation_id = f"{exchange}_{symbol}_{int(datetime.now().timestamp())}_{id(self)}"

            reservation = BalanceReservation(
                reservation_id=reservation_id,
                exchange=exchange,
                symbol=symbol,
                amount=amount,
                reserved_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=ttl_minutes),
                purpose=purpose,
                metadata=metadata or {},
            )

            self.reservations[reservation_id] = reservation
            self.stats["successful_reservations"] += 1

            # Сохраняем в Redis если доступен
            if self.redis_client:
                await self._save_reservation_to_redis(reservation)

            logger.info(
                f"✅ Зарезервировано {amount} {symbol} на {exchange} (ID: {reservation_id})"
            )
            return reservation_id

        except Exception as e:
            logger.error(f"❌ Ошибка резервирования баланса: {e}")
            self.stats["failed_reservations"] += 1
            return None

    async def release_reservation(self, reservation_id: str) -> bool:
        """
        Освобождение резервирования

        Args:
            reservation_id: ID резервирования

        Returns:
            True если резервирование освобождено
        """
        try:
            if reservation_id not in self.reservations:
                logger.warning(f"⚠️  Резервирование {reservation_id} не найдено")
                return False

            reservation = self.reservations[reservation_id]
            del self.reservations[reservation_id]

            # Удаляем из Redis
            if self.redis_client:
                await self.redis_client.delete(f"reservation:{reservation_id}")

            logger.info(
                f"✅ Освобождено резервирование {reservation.amount} {reservation.symbol} на {reservation.exchange}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка освобождения резервирования: {e}")
            return False

    async def update_balance(
        self,
        exchange: str,
        symbol: str,
        total: Decimal,
        available: Decimal,
        locked: Decimal = Decimal("0"),
    ) -> bool:
        """
        Обновление баланса

        Args:
            exchange: Название биржи
            symbol: Символ валюты
            total: Общий баланс
            available: Доступный баланс
            locked: Заблокированный баланс

        Returns:
            True если обновление успешно
        """
        try:
            if exchange not in self.balances:
                self.balances[exchange] = {}

            balance = ExchangeBalance(
                exchange=exchange,
                symbol=symbol,
                total=total,
                available=available,
                locked=locked,
                last_updated=datetime.now(),
            )

            self.balances[exchange][symbol] = balance
            self.last_updates[exchange] = datetime.now()
            self.stats["balance_updates"] += 1

            # Сохраняем в Redis
            if self.redis_client:
                await self._save_balance_to_redis(balance)

            logger.debug(f"💰 Обновлен баланс {symbol} на {exchange}: доступно {available}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обновления баланса: {e}")
            return False

    async def get_all_balances(self, exchange: str | None = None) -> dict[str, dict[str, Any]]:
        """
        Получение всех балансов

        Args:
            exchange: Конкретная биржа (если None - все биржи)

        Returns:
            Словарь балансов
        """
        result = {}

        exchanges_to_check = [exchange] if exchange else list(self.balances.keys())

        for exch in exchanges_to_check:
            if exch not in self.balances:
                continue

            result[exch] = {}
            for symbol, balance in self.balances[exch].items():
                reserved = self._get_reserved_amount(exch, symbol)

                # 🛡️ Защита от смешивания float и Decimal типов
                try:
                    # Убеждаемся что все значения Decimal
                    balance_available = Decimal(str(balance.available))
                    reserved_decimal = Decimal(str(reserved))

                    result[exch][symbol] = {
                        "total": float(balance.total),
                        "available": float(balance.available),
                        "locked": float(balance.locked),
                        "reserved": float(reserved),
                        "effective_available": float(balance_available - reserved_decimal),
                        "last_updated": balance.last_updated.isoformat(),
                    }
                except Exception as e:
                    logger.error(f"❌ Ошибка конвертации типов для {exch} {symbol}: {e}")
                    # Fallback значения
                    result[exch][symbol] = {
                        "total": float(balance.total),
                        "available": float(balance.available),
                        "locked": float(balance.locked),
                        "reserved": 0.0,
                        "effective_available": float(balance.available),
                        "last_updated": balance.last_updated.isoformat(),
                    }

        return result

    async def get_balance_summary(self) -> dict[str, Any]:
        """Получение сводки по балансам"""
        total_exchanges = len(self.balances)
        total_symbols = sum(len(balances) for balances in self.balances.values())
        total_reservations = len(self.reservations)

        # Считаем общую стоимость в USDT (упрощенно)
        total_usdt_value = Decimal("0")
        for exchange_balances in self.balances.values():
            if "USDT" in exchange_balances:
                total_usdt_value += exchange_balances["USDT"].available

        # Активные резервирования по биржам
        reservations_by_exchange = {}
        for reservation in self.reservations.values():
            if reservation.exchange not in reservations_by_exchange:
                reservations_by_exchange[reservation.exchange] = 0
            reservations_by_exchange[reservation.exchange] += 1

        return {
            "total_exchanges": total_exchanges,
            "total_symbols": total_symbols,
            "total_reservations": total_reservations,
            "reservations_by_exchange": reservations_by_exchange,
            "estimated_usdt_value": float(total_usdt_value),
            "last_update_times": {
                exchange: update_time.isoformat()
                for exchange, update_time in self.last_updates.items()
            },
            "stats": self.stats.copy(),
        }

    def _get_reserved_amount(self, exchange: str, symbol: str) -> Decimal:
        """Получение зарезервированного количества"""
        reserved = Decimal("0")
        now = datetime.now()

        for reservation in self.reservations.values():
            if (
                reservation.exchange == exchange
                and reservation.symbol == symbol
                and reservation.expires_at > now
            ):
                reserved += reservation.amount

        return reserved

    async def _get_balance(self, exchange: str, symbol: str) -> ExchangeBalance | None:
        """Получение баланса с проверкой актуальности"""
        # Проверяем локальный кеш
        if exchange in self.balances and symbol in self.balances[exchange]:
            balance = self.balances[exchange][symbol]

            # Проверяем актуальность
            if (datetime.now() - balance.last_updated) <= self.balance_cache_ttl:
                self.stats["cache_hits"] += 1
                return balance

        # Пытаемся загрузить из Redis
        if self.redis_client:
            try:
                balance_data = await self.redis_client.get(f"balance:{exchange}:{symbol}")
                if balance_data:
                    # Десериализация из Redis
                    import json

                    data = json.loads(balance_data)
                    balance = ExchangeBalance(
                        exchange=exchange,
                        symbol=symbol,
                        total=Decimal(data.get("total", "0")),
                        available=Decimal(data.get("available", "0")),
                        locked=Decimal(data.get("locked", "0")),
                        last_updated=datetime.now(),  # Обновляем время
                    )

                    # Сохраняем в локальный кеш
                    if exchange not in self.balances:
                        self.balances[exchange] = {}
                    self.balances[exchange][symbol] = balance

                    self.stats["cache_hits"] += 1
                    logger.debug(
                        f"💰 Загружен баланс {symbol} на {exchange} из Redis: {balance.available}"
                    )
                    return balance
            except Exception as e:
                logger.warning(f"⚠️  Ошибка загрузки баланса из Redis: {e}")

        self.stats["cache_misses"] += 1

        # Возвращаем устаревший баланс если есть, иначе None
        if exchange in self.balances and symbol in self.balances[exchange]:
            return self.balances[exchange][symbol]

        return None

    async def _balance_update_loop(self, exchange: str):
        """Цикл обновления балансов для биржи"""
        while self._running:
            try:
                await self._update_exchange_balances(exchange)
                interval = self.update_intervals.get(exchange, self.default_update_interval)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка обновления балансов для {exchange}: {e}")
                await asyncio.sleep(self.default_update_interval)

    async def _update_exchange_balances(self, exchange: str):
        """Обновление балансов конкретной биржи"""
        try:
            logger.debug(f"🔄 Обновление балансов для {exchange}")

            # Проверяем наличие exchange_manager
            if not self.exchange_manager:
                logger.debug(
                    f"⚠️ Пропуск обновления балансов для {exchange} - exchange_manager не установлен"
                )
                return

            # Получаем клиента биржи
            exchange_client = await self.exchange_manager.get_exchange(exchange)
            if not exchange_client:
                logger.warning(f"⚠️ Не удалось получить клиента для биржи {exchange}")
                return

            # Запрашиваем балансы через API
            try:
                balances = await exchange_client.get_balances()
                logger.debug(f"📊 Получено {len(balances)} балансов с {exchange}")
            except Exception as e:
                logger.error(f"❌ Ошибка получения балансов с {exchange}: {e}")
                return

            # Обновляем локальный кеш
            if exchange not in self.balances:
                self.balances[exchange] = {}

            for balance in balances:
                symbol = balance.currency.upper()

                # Создаем объект ExchangeBalance
                exchange_balance = ExchangeBalance(
                    exchange=exchange,
                    symbol=symbol,
                    total=Decimal(str(balance.total)),
                    available=Decimal(str(balance.available)),
                    locked=Decimal(str(balance.frozen)),
                    last_updated=datetime.now(),
                )

                self.balances[exchange][symbol] = exchange_balance

                # Сохраняем в Redis если доступен
                if self.redis_client:
                    try:
                        import json

                        balance_data = json.dumps(
                            {
                                "total": str(exchange_balance.total),
                                "available": str(exchange_balance.available),
                                "locked": str(exchange_balance.locked),
                            }
                        )
                        await self.redis_client.set(
                            f"balance:{exchange}:{symbol}",
                            balance_data,
                            ex=300,  # TTL 5 минут
                        )
                    except Exception as e:
                        logger.debug(f"⚠️ Не удалось сохранить баланс в Redis: {e}")

                # Логируем значимые балансы
                if exchange_balance.total > 0:
                    logger.info(
                        f"💰 {exchange} {symbol}: total={exchange_balance.total:.4f}, "
                        f"available={exchange_balance.available:.4f}, locked={exchange_balance.locked:.4f}"
                    )

            # Обновляем время последнего обновления
            self.last_updates[exchange] = datetime.now()
            logger.info(f"✅ Обновлены балансы для {exchange}: {len(balances)} валют")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления балансов для {exchange}: {e}")

    async def _cleanup_loop(self):
        """Цикл очистки просроченных резервирований"""
        while self._running:
            try:
                await self._cleanup_expired_reservations()
                await asyncio.sleep(60)  # Каждую минуту
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка очистки резервирований: {e}")
                await asyncio.sleep(60)

    async def _cleanup_expired_reservations(self):
        """Очистка просроченных резервирований"""
        now = datetime.now()
        expired_reservations = []

        for reservation_id, reservation in self.reservations.items():
            if reservation.expires_at <= now:
                expired_reservations.append(reservation_id)

        for reservation_id in expired_reservations:
            reservation = self.reservations[reservation_id]
            del self.reservations[reservation_id]

            # Удаляем из Redis
            if self.redis_client:
                try:
                    await self.redis_client.delete(f"reservation:{reservation_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Ошибка удаления резервирования из Redis: {e}")

            logger.info(
                f"🧹 Удалено просроченное резервирование: {reservation.amount} {reservation.symbol} на {reservation.exchange}"
            )

        if expired_reservations:
            logger.info(f"🧹 Очищено просроченных резервирований: {len(expired_reservations)}")

    async def _save_balance_to_redis(self, balance: ExchangeBalance):
        """Сохранение баланса в Redis"""
        try:
            if not self.redis_client:
                return

            balance_data = {
                "total": str(balance.total),
                "available": str(balance.available),
                "locked": str(balance.locked),
                "last_updated": balance.last_updated.isoformat(),
            }

            key = f"balance:{balance.exchange}:{balance.symbol}"
            await self.redis_client.setex(
                key, int(self.balance_cache_ttl.total_seconds()), str(balance_data)
            )

        except Exception as e:
            logger.warning(f"⚠️  Ошибка сохранения баланса в Redis: {e}")

    async def _save_reservation_to_redis(self, reservation: BalanceReservation):
        """Сохранение резервирования в Redis"""
        try:
            if not self.redis_client:
                return

            reservation_data = {
                "exchange": reservation.exchange,
                "symbol": reservation.symbol,
                "amount": str(reservation.amount),
                "reserved_at": reservation.reserved_at.isoformat(),
                "expires_at": reservation.expires_at.isoformat(),
                "purpose": reservation.purpose,
                "metadata": reservation.metadata,
            }

            ttl = int((reservation.expires_at - datetime.now()).total_seconds())
            if ttl > 0:
                await self.redis_client.setex(
                    f"reservation:{reservation.reservation_id}", ttl, str(reservation_data)
                )

        except Exception as e:
            logger.warning(f"⚠️  Ошибка сохранения резервирования в Redis: {e}")


# Глобальный экземпляр менеджера балансов
balance_manager = BalanceManager()
