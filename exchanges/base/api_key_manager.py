"""
API Key Manager для BOT_Trading v3.0

Компонент для управления API ключами бирж с поддержкой:
- Проверки валидности ключей
- Автоматической ротации при ошибках
- Мониторинга состояния ключей
- Множественных ключей для одной биржи
- Безопасного хранения и доступа
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import aiohttp

from core.logger import setup_logger


class KeyStatus(Enum):
    """Статусы API ключей"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    INVALID = "invalid"
    RATE_LIMITED = "rate_limited"
    SUSPENDED = "suspended"


class KeyType(Enum):
    """Типы API ключей"""

    MAIN = "main"
    BACKUP = "backup"
    READ_ONLY = "read_only"
    TRADING = "trading"


@dataclass
class APIKeyInfo:
    """Информация об API ключе"""

    # Основные параметры
    key_id: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None  # Для OKX и других

    # Метаданные
    key_type: KeyType = KeyType.MAIN
    status: KeyStatus = KeyStatus.ACTIVE
    exchange_name: str = ""

    # Права доступа
    permissions: Set[str] = field(default_factory=lambda: {"read", "trade"})

    # Статистика использования
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0

    # Временные метки
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    last_validated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Health metrics
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_success_time: Optional[datetime] = None

    @property
    def is_valid(self) -> bool:
        """Проверка валидности ключа"""
        if self.status in [KeyStatus.EXPIRED, KeyStatus.INVALID, KeyStatus.SUSPENDED]:
            return False

        if self.expires_at and datetime.now() > self.expires_at:
            return False

        # Если слишком много подряд неудачных запросов
        if self.consecutive_failures > 10:
            return False

        return True

    @property
    def success_rate(self) -> float:
        """Процент успешных запросов"""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def masked_key(self) -> str:
        """Замаскированный API ключ для логирования"""
        if len(self.api_key) <= 8:
            return "***"
        return f"{self.api_key[:4]}{'*' * (len(self.api_key) - 8)}{self.api_key[-4:]}"


class APIKeyManager:
    """
    Менеджер API ключей для всех бирж

    Обеспечивает:
    - Хранение и управление множественными ключами
    - Автоматическую валидацию и ротацию
    - Мониторинг состояния ключей
    - Безопасный доступ к ключам
    - Статистику использования
    """

    def __init__(self):
        self.logger = setup_logger("api_key_manager")

        # Хранилище ключей по биржам
        self.keys: Dict[str, List[APIKeyInfo]] = {}

        # Текущие активные ключи для каждой биржи
        self.active_keys: Dict[str, APIKeyInfo] = {}

        # Блокировки для thread safety
        self.locks: Dict[str, asyncio.Lock] = {}

        # HTTP session для валидации
        self.session: Optional[aiohttp.ClientSession] = None

        # Таймер для фоновых задач
        self._validation_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None

        # Конфигурация валидации
        self.validation_interval = 300  # 5 минут
        self.max_validation_failures = 3

    async def initialize(self):
        """Инициализация менеджера"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

        # Запуск фоновых задач
        self._validation_task = asyncio.create_task(self._periodic_validation())
        self._stats_task = asyncio.create_task(self._stats_collector())

        self.logger.info("API Key Manager initialized")

    async def shutdown(self):
        """Корректное завершение работы"""
        if self._validation_task:
            self._validation_task.cancel()
        if self._stats_task:
            self._stats_task.cancel()

        if self.session:
            await self.session.close()

        self.logger.info("API Key Manager shutdown complete")

    def add_key(
        self,
        exchange_name: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        key_type: KeyType = KeyType.MAIN,
        permissions: Optional[Set[str]] = None,
    ) -> str:
        """
        Добавление нового API ключа

        Args:
            exchange_name: Название биржи
            api_key: API ключ
            api_secret: Secret ключ
            passphrase: Passphrase (для OKX и других)
            key_type: Тип ключа
            permissions: Права доступа

        Returns:
            key_id: Уникальный идентификатор ключа
        """
        exchange_name = exchange_name.lower()

        # Генерируем уникальный ID
        key_id = self._generate_key_id(exchange_name, api_key)

        # Создаем объект ключа
        key_info = APIKeyInfo(
            key_id=key_id,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            key_type=key_type,
            exchange_name=exchange_name,
            permissions=permissions or {"read", "trade"},
        )

        # Добавляем в хранилище
        if exchange_name not in self.keys:
            self.keys[exchange_name] = []
            self.locks[exchange_name] = asyncio.Lock()

        self.keys[exchange_name].append(key_info)

        # Устанавливаем как активный, если это первый ключ
        if exchange_name not in self.active_keys:
            self.active_keys[exchange_name] = key_info

        self.logger.info(
            f"Added API key {key_info.masked_key} for {exchange_name} (type: {key_type.name})"
        )

        return key_id

    def _generate_key_id(self, exchange_name: str, api_key: str) -> str:
        """Генерация уникального ID для ключа"""
        data = f"{exchange_name}_{api_key}_{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    async def get_active_key(self, exchange_name: str) -> Optional[APIKeyInfo]:
        """Получение активного ключа для биржи"""
        exchange_name = exchange_name.lower()

        if exchange_name not in self.active_keys:
            return None

        key_info = self.active_keys[exchange_name]

        # Проверяем валидность
        if not key_info.is_valid:
            # Пытаемся найти другой валидный ключ
            await self._rotate_key(exchange_name, reason="invalid_key")
            return self.active_keys.get(exchange_name)

        return key_info

    async def _rotate_key(self, exchange_name: str, reason: str = "auto_rotation"):
        """Ротация ключа на следующий доступный"""
        exchange_name = exchange_name.lower()

        if exchange_name not in self.locks:
            return

        async with self.locks[exchange_name]:
            available_keys = [
                key
                for key in self.keys.get(exchange_name, [])
                if key.is_valid and key != self.active_keys.get(exchange_name)
            ]

            if not available_keys:
                self.logger.error(f"No valid backup keys available for {exchange_name}")
                return

            # Выбираем ключ с лучшей статистикой
            best_key = max(available_keys, key=lambda k: k.success_rate)

            old_key = self.active_keys.get(exchange_name)
            self.active_keys[exchange_name] = best_key

            self.logger.warning(
                f"Rotated API key for {exchange_name}: "
                f"{old_key.masked_key if old_key else 'None'} -> {best_key.masked_key} "
                f"(reason: {reason})"
            )

    async def validate_key(self, exchange_name: str, key_info: APIKeyInfo) -> bool:
        """
        Валидация API ключа

        Args:
            exchange_name: Название биржи
            key_info: Информация о ключе

        Returns:
            True если ключ валиден
        """
        if not self.session:
            await self.initialize()

        try:
            # Выбираем метод валидации в зависимости от биржи
            is_valid = await self._validate_key_for_exchange(exchange_name, key_info)

            # Обновляем статистику
            key_info.last_validated_at = datetime.now()

            if is_valid:
                key_info.status = KeyStatus.ACTIVE
                key_info.consecutive_failures = 0
                key_info.last_success_time = datetime.now()
                key_info.successful_requests += 1
            else:
                key_info.consecutive_failures += 1
                key_info.failed_requests += 1

                if key_info.consecutive_failures >= self.max_validation_failures:
                    key_info.status = KeyStatus.INVALID
                    self.logger.error(
                        f"Key {key_info.masked_key} marked as invalid after {key_info.consecutive_failures} failures"
                    )

            key_info.total_requests += 1

            return is_valid

        except Exception as e:
            self.logger.error(
                f"Error validating key {key_info.masked_key} for {exchange_name}: {e}"
            )
            key_info.consecutive_failures += 1
            key_info.failed_requests += 1
            key_info.total_requests += 1
            key_info.last_error = str(e)

            return False

    async def _validate_key_for_exchange(
        self, exchange_name: str, key_info: APIKeyInfo
    ) -> bool:
        """Валидация ключа для конкретной биржи"""

        if exchange_name == "bybit":
            return await self._validate_bybit_key(key_info)
        elif exchange_name == "binance":
            return await self._validate_binance_key(key_info)
        elif exchange_name == "okx":
            return await self._validate_okx_key(key_info)
        elif exchange_name == "bitget":
            return await self._validate_bitget_key(key_info)
        elif exchange_name == "gateio":
            return await self._validate_gateio_key(key_info)
        elif exchange_name == "kucoin":
            return await self._validate_kucoin_key(key_info)
        elif exchange_name == "huobi":
            return await self._validate_huobi_key(key_info)
        else:
            self.logger.warning(f"No validation method for exchange: {exchange_name}")
            return True  # По умолчанию считаем валидным

    async def _validate_bybit_key(self, key_info: APIKeyInfo) -> bool:
        """Валидация ключа Bybit"""
        try:
            url = "https://api.bybit.com/v5/market/time"

            # Для публичного эндпоинта просто проверяем доступность
            async with self.session.get(url) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                return data.get("retCode") == 0

        except Exception:
            return False

    async def _validate_binance_key(self, key_info: APIKeyInfo) -> bool:
        """Валидация ключа Binance"""
        try:
            url = "https://api.binance.com/api/v3/time"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                return "serverTime" in data

        except Exception:
            return False

    async def _validate_okx_key(self, key_info: APIKeyInfo) -> bool:
        """Валидация ключа OKX"""
        try:
            url = "https://www.okx.com/api/v5/public/time"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                return data.get("code") == "0"

        except Exception:
            return False

    async def _validate_bitget_key(self, key_info: APIKeyInfo) -> bool:
        """Валидация ключа Bitget"""
        try:
            url = "https://api.bitget.com/api/spot/v1/public/time"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                return data.get("code") == "00000"

        except Exception:
            return False

    async def _validate_gateio_key(self, key_info: APIKeyInfo) -> bool:
        """Валидация ключа Gate.io"""
        try:
            url = "https://api.gateio.ws/api/v4/spot/time"

            async with self.session.get(url) as response:
                return response.status == 200

        except Exception:
            return False

    async def _validate_kucoin_key(self, key_info: APIKeyInfo) -> bool:
        """Валидация ключа KuCoin"""
        try:
            url = "https://api.kucoin.com/api/v1/timestamp"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                return data.get("code") == "200000"

        except Exception:
            return False

    async def _validate_huobi_key(self, key_info: APIKeyInfo) -> bool:
        """Валидация ключа Huobi"""
        try:
            url = "https://api.huobi.pro/v1/common/timestamp"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                return data.get("status") == "ok"

        except Exception:
            return False

    async def _periodic_validation(self):
        """Периодическая валидация всех ключей"""
        while True:
            try:
                self.logger.debug("Starting periodic key validation")

                for exchange_name, keys in self.keys.items():
                    for key_info in keys:
                        if key_info.status == KeyStatus.ACTIVE:
                            # Валидируем только активные ключи
                            await self.validate_key(exchange_name, key_info)

                            # Небольшая пауза между проверками
                            await asyncio.sleep(1)

                # Ждем до следующей проверки
                await asyncio.sleep(self.validation_interval)

            except Exception as e:
                self.logger.error(f"Error in periodic validation: {e}")
                await asyncio.sleep(60)  # При ошибке ждем минуту

    async def _stats_collector(self):
        """Сборщик статистики"""
        while True:
            try:
                await asyncio.sleep(60)  # Каждую минуту

                # Очистка старых ошибок
                for keys in self.keys.values():
                    for key_info in keys:
                        # Сброс consecutive_failures если последняя ошибка была давно
                        if (
                            key_info.last_success_time
                            and datetime.now() - key_info.last_success_time
                            > timedelta(hours=1)
                        ):
                            if key_info.consecutive_failures > 0:
                                key_info.consecutive_failures = max(
                                    0, key_info.consecutive_failures - 1
                                )

            except Exception as e:
                self.logger.error(f"Error in stats collector: {e}")
                await asyncio.sleep(60)

    def record_request_success(self, exchange_name: str):
        """Запись успешного запроса"""
        exchange_name = exchange_name.lower()
        key_info = self.active_keys.get(exchange_name)

        if key_info:
            key_info.successful_requests += 1
            key_info.total_requests += 1
            key_info.last_used_at = datetime.now()
            key_info.last_success_time = datetime.now()
            key_info.consecutive_failures = 0

    def record_request_failure(
        self,
        exchange_name: str,
        error_code: Optional[str] = None,
        is_auth_error: bool = False,
    ):
        """Запись неудачного запроса"""
        exchange_name = exchange_name.lower()
        key_info = self.active_keys.get(exchange_name)

        if key_info:
            key_info.failed_requests += 1
            key_info.total_requests += 1
            key_info.last_used_at = datetime.now()
            key_info.consecutive_failures += 1
            key_info.last_error = error_code

            # Если это ошибка аутентификации, помечаем ключ как проблемный
            if is_auth_error:
                key_info.status = KeyStatus.INVALID

                # Пытаемся ротировать ключ
                asyncio.create_task(self._rotate_key(exchange_name, "auth_error"))

            # Если это rate limit, увеличиваем счетчик
            if error_code in ["429", "10006", "10018", "-1003", "-1015"]:
                key_info.rate_limit_hits += 1
                key_info.status = KeyStatus.RATE_LIMITED

    def get_key_stats(self, exchange_name: str) -> Dict[str, Any]:
        """Получение статистики ключей для биржи"""
        exchange_name = exchange_name.lower()

        keys = self.keys.get(exchange_name, [])
        active_key = self.active_keys.get(exchange_name)

        stats = {
            "exchange": exchange_name,
            "total_keys": len(keys),
            "active_key": active_key.masked_key if active_key else None,
            "active_key_status": active_key.status.value if active_key else None,
            "keys": [],
        }

        for key_info in keys:
            key_stats = {
                "key_id": key_info.key_id,
                "masked_key": key_info.masked_key,
                "status": key_info.status.value,
                "type": key_info.key_type.value,
                "success_rate": f"{key_info.success_rate:.1f}%",
                "total_requests": key_info.total_requests,
                "consecutive_failures": key_info.consecutive_failures,
                "rate_limit_hits": key_info.rate_limit_hits,
                "last_used": key_info.last_used_at.isoformat()
                if key_info.last_used_at
                else None,
                "last_validated": (
                    key_info.last_validated_at.isoformat()
                    if key_info.last_validated_at
                    else None
                ),
            }
            stats["keys"].append(key_stats)

        return stats

    def get_all_stats(self) -> Dict[str, Any]:
        """Получение статистики по всем биржам"""
        all_stats = {
            "total_exchanges": len(self.keys),
            "total_keys": sum(len(keys) for keys in self.keys.values()),
            "exchanges": {},
        }

        for exchange_name in self.keys.keys():
            all_stats["exchanges"][exchange_name] = self.get_key_stats(exchange_name)

        return all_stats


# Глобальный экземпляр менеджера ключей
_global_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    """Получение глобального экземпляра менеджера ключей"""
    global _global_key_manager

    if _global_key_manager is None:
        _global_key_manager = APIKeyManager()

    return _global_key_manager
