"""
Дедупликатор сигналов для предотвращения создания дублирующих торговых сигналов
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as redis

from database.db_manager import get_db

logger = logging.getLogger(__name__)


@dataclass
class SignalFingerprint:
    """Отпечаток сигнала для определения уникальности"""

    symbol: str
    direction: str  # 'BUY' или 'SELL'
    strategy: str
    timestamp_minute: int  # Округленная до минуты метка времени
    signal_strength: float | None = None
    price_level: float | None = None

    def to_hash(self) -> str:
        """Создание хеша отпечатка"""
        data = {
            "symbol": self.symbol,
            "direction": self.direction,
            "strategy": self.strategy,
            "timestamp_minute": self.timestamp_minute,
            "signal_strength": round(self.signal_strength, 4) if self.signal_strength else None,
            "price_level": round(self.price_level, 4) if self.price_level else None,
        }

        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]


class SignalDeduplicator:
    """
    Дедупликатор сигналов для предотвращения дублирования

    Основные функции:
    - Проверка уникальности сигналов по отпечатку
    - Кеширование недавних сигналов в Redis и PostgreSQL
    - Автоматическая очистка старых записей
    - Статистика дублирования
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        self.db_manager = None
        self.redis_client = redis_client
        self.local_cache: dict[str, datetime] = {}  # Локальный кеш как fallback
        self.cache_ttl = timedelta(minutes=5)  # TTL для кеша
        self.max_local_cache_size = 10000
        self.stats = {
            "total_checks": 0,
            "duplicates_found": 0,
            "unique_signals": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Инициализация Redis если не передан
        if not self.redis_client:
            self._init_redis()

    def _init_redis(self):
        """Инициализация Redis клиента"""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379/2")  # DB 2 для сигналов
            logger.info("✅ Redis клиент инициализирован для дедупликатора сигналов")
        except Exception as e:
            logger.warning(f"⚠️  Redis недоступен для дедупликатора: {e}")
            self.redis_client = None

    async def check_and_register_signal(self, signal_data: dict[str, Any]) -> bool:
        """
        Проверка уникальности сигнала и его регистрация

        Args:
            signal_data: Данные сигнала (symbol, direction, strategy, etc.)

        Returns:
            True если сигнал уникален, False если дубликат
        """
        self.stats["total_checks"] += 1

        try:
            # Инициализируем DBManager если нужно
            if not self.db_manager:
                self.db_manager = await get_db()
            # Создаем отпечаток сигнала
            fingerprint = self._create_fingerprint(signal_data)
            signal_hash = fingerprint.to_hash()

            # Проверяем в кеше
            if await self._is_duplicate_cached(signal_hash):
                self.stats["duplicates_found"] += 1
                self.stats["cache_hits"] += 1
                logger.debug(
                    f"🔍 Найден дубликат сигнала: {fingerprint.symbol} {fingerprint.direction} ({signal_hash})"
                )
                return False

            # Проверяем в базе данных
            if await self._is_duplicate_database(fingerprint):
                self.stats["duplicates_found"] += 1
                self.stats["cache_misses"] += 1
                logger.debug(
                    f"🔍 Найден дубликат в БД: {fingerprint.symbol} {fingerprint.direction} ({signal_hash})"
                )
                # Добавляем в кеш для быстрой проверки в будущем
                await self._cache_signal_hash(signal_hash)
                return False

            # Сигнал уникален - регистрируем его
            await self._register_signal(fingerprint, signal_hash)
            self.stats["unique_signals"] += 1

            logger.debug(
                f"✅ Зарегистрирован уникальный сигнал: {fingerprint.symbol} {fingerprint.direction} ({signal_hash})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки дедупликации сигнала: {e}")
            # В случае ошибки разрешаем сигнал (безопасная сторона)
            return True

    async def get_recent_signals(
        self, symbol: str | None = None, minutes: int = 5
    ) -> list[dict[str, Any]]:
        """
        Получение недавних сигналов

        Args:
            symbol: Фильтр по символу (если None - все символы)
            minutes: За какое количество минут

        Returns:
            Список недавних сигналов
        """
        try:
            since_time = datetime.now() - timedelta(minutes=minutes)

            query = """
                SELECT signal_hash, symbol, direction, strategy, created_at,
                       signal_strength, price_level, metadata
                FROM signal_fingerprints
                WHERE created_at >= $1
            """
            params = [since_time]

            if symbol:
                query += " AND symbol = $2"
                params.append(symbol)

            query += " ORDER BY created_at DESC LIMIT 1000"

            rows = await self.db_manager.fetch_all(query, *params)

            signals = []
            for row in rows:
                signals.append(
                    {
                        "signal_hash": row["signal_hash"],
                        "symbol": row["symbol"],
                        "direction": row["direction"],
                        "strategy": row["strategy"],
                        "created_at": row["created_at"],
                        "signal_strength": row["signal_strength"],
                        "price_level": row["price_level"],
                        "metadata": row["metadata"],
                    }
                )

            return signals

        except Exception as e:
            logger.error(f"❌ Ошибка получения недавних сигналов: {e}")
            return []

    async def cleanup_old_records(self, older_than_hours: int = 24):
        """
        Очистка старых записей

        Args:
            older_than_hours: Удалить записи старше этого количества часов
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

            # Очистка базы данных
            query = "DELETE FROM signal_fingerprints WHERE created_at < $1"
            result = await self.db_manager.execute(query, cutoff_time)

            deleted_count = 0
            if result and result.startswith("DELETE"):
                deleted_count = int(result.split()[-1])

            # Очистка локального кеша
            now = datetime.now()
            to_remove = []
            for signal_hash, timestamp in self.local_cache.items():
                if (now - timestamp) > timedelta(hours=older_than_hours):
                    to_remove.append(signal_hash)

            for signal_hash in to_remove:
                del self.local_cache[signal_hash]

            logger.info(
                f"🧹 Очищены старые записи: {deleted_count} из БД, {len(to_remove)} из кеша"
            )

        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых записей: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Получение статистики дедупликатора"""
        stats = self.stats.copy()
        stats["local_cache_size"] = len(self.local_cache)
        stats["duplicate_rate"] = (
            self.stats["duplicates_found"] / self.stats["total_checks"]
            if self.stats["total_checks"] > 0
            else 0
        )
        stats["cache_hit_rate"] = (
            self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
            if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0
            else 0
        )

        return stats

    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            "total_checks": 0,
            "duplicates_found": 0,
            "unique_signals": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def _create_fingerprint(self, signal_data: dict[str, Any]) -> SignalFingerprint:
        """Создание отпечатка сигнала"""
        timestamp = signal_data.get("timestamp", datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # Округляем до минуты для группировки похожих сигналов
        timestamp_minute = int(timestamp.replace(second=0, microsecond=0).timestamp())

        return SignalFingerprint(
            symbol=signal_data["symbol"],
            direction=signal_data["direction"],
            strategy=signal_data.get("strategy", "unknown"),
            timestamp_minute=timestamp_minute,
            signal_strength=signal_data.get("signal_strength"),
            price_level=signal_data.get("price", signal_data.get("price_level")),
        )

    async def _is_duplicate_cached(self, signal_hash: str) -> bool:
        """Проверка дубликата в кеше"""
        now = datetime.now()

        # Проверяем локальный кеш
        if signal_hash in self.local_cache:
            if (now - self.local_cache[signal_hash]) <= self.cache_ttl:
                return True
            else:
                # Удаляем устаревшую запись
                del self.local_cache[signal_hash]

        # Проверяем Redis кеш
        if self.redis_client:
            try:
                exists = await self.redis_client.exists(f"signal:{signal_hash}")
                return bool(exists)
            except Exception as e:
                logger.warning(f"⚠️  Ошибка проверки Redis кеша: {e}")

        return False

    async def _is_duplicate_database(self, fingerprint: SignalFingerprint) -> bool:
        """Проверка дубликата в базе данных"""
        try:
            # Проверяем за последние 5 минут
            since_time = datetime.now() - self.cache_ttl

            query = """
                SELECT 1 FROM signal_fingerprints
                WHERE signal_hash = $1 AND created_at >= $2
                LIMIT 1
            """

            result = await self.db_manager.fetch_one(query, fingerprint.to_hash(), since_time)
            return result is not None

        except Exception as e:
            logger.error(f"❌ Ошибка проверки дубликата в БД: {e}")
            return False

    async def _cache_signal_hash(self, signal_hash: str):
        """Кеширование хеша сигнала"""
        now = datetime.now()

        # Добавляем в локальный кеш
        self.local_cache[signal_hash] = now

        # Ограничиваем размер локального кеша
        if len(self.local_cache) > self.max_local_cache_size:
            # Удаляем 10% самых старых записей
            sorted_items = sorted(self.local_cache.items(), key=lambda x: x[1])
            remove_count = int(self.max_local_cache_size * 0.1)
            for signal_hash_to_remove, _ in sorted_items[:remove_count]:
                del self.local_cache[signal_hash_to_remove]

        # Добавляем в Redis
        if self.redis_client:
            try:
                ttl_seconds = int(self.cache_ttl.total_seconds())
                await self.redis_client.setex(f"signal:{signal_hash}", ttl_seconds, "1")
            except Exception as e:
                logger.warning(f"⚠️  Ошибка кеширования в Redis: {e}")

    async def _register_signal(self, fingerprint: SignalFingerprint, signal_hash: str):
        """Регистрация нового уникального сигнала"""
        try:
            # Сохраняем в базу данных
            query = """
                INSERT INTO signal_fingerprints
                (signal_hash, symbol, direction, strategy, timestamp_minute,
                 signal_strength, price_level, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (signal_hash) DO NOTHING
            """

            await self.db_manager.execute(
                query,
                signal_hash,
                fingerprint.symbol,
                fingerprint.direction,
                fingerprint.strategy,
                fingerprint.timestamp_minute,
                fingerprint.signal_strength,
                fingerprint.price_level,
                datetime.now(),
            )

            # Кешируем
            await self._cache_signal_hash(signal_hash)

        except Exception as e:
            logger.error(f"❌ Ошибка регистрации сигнала: {e}")


# Глобальный экземпляр дедупликатора
signal_deduplicator = SignalDeduplicator()
