#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Manager для BOT_Trading v3.0

Централизованная система управления конфигурацией с поддержкой:
- Мульти-трейдер конфигураций
- Иерархического наследования настроек
- Валидации и fallback значений
- Кеширования для производительности
- Обратной совместимости с v1.0/v2.0

Мигрировано из core/config.py с расширением функциональности.
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from core.exceptions import ConfigurationError
from utils.helpers import safe_float


@dataclass
class ConfigInfo:
    """Информация о загруженной конфигурации"""

    path: str
    loaded_at: datetime
    is_valid: bool
    errors: List[str] = field(default_factory=list)


class ConfigManager:
    """
    Менеджер конфигурации для мульти-трейдер системы BOT_Trading v3.0

    Обеспечивает:
    - Загрузку и кеширование конфигураций
    - Поддержку мульти-трейдер архитектуры
    - Валидацию конфигураций
    - Fallback механизмы
    - Обратную совместимость с v1.0/v2.0
    """

    def __init__(self, config_path: Optional[str] = None):
        self._config: Dict[str, Any] = {}
        self._config_path: Optional[str] = config_path
        self._db_path: Optional[str] = None
        self._trader_configs: Dict[str, Dict[str, Any]] = {}
        self._config_info: Optional[ConfigInfo] = None
        self._is_initialized = False

        # Пути поиска конфигураций (совместимость с v1.0/v2.0)
        self._default_config_paths = [
            "config.yaml",  # Корень проекта
            "config/system.yaml",  # v3.0 система
            "/root/trading/config.yaml",  # Стандартное расположение на сервере
            os.path.join(os.getcwd(), "config.yaml"),  # Текущая директория
        ]

        # Путь к PostgreSQL конфигурации
        self._postgres_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config",
            "postgres_config.yaml",
        )

    async def initialize(self) -> None:
        """Асинхронная инициализация менеджера конфигурации"""
        if self._is_initialized:
            return

        try:
            await self._load_system_config()
            await self._load_trader_configs()
            self._is_initialized = True
        except Exception as e:
            raise ConfigurationError(
                f"Не удалось инициализировать конфигурацию: {e}"
            ) from e

    async def _load_system_config(self) -> None:
        """Загрузка основной системной конфигурации"""
        config_loaded = False
        errors = []

        # Определяем пути для поиска конфигурации
        search_paths = []
        if self._config_path:
            search_paths.append(self._config_path)
        search_paths.extend(self._default_config_paths)

        # Поиск и загрузка конфигурации
        for config_path in search_paths:
            if not config_path:
                continue

            try:
                if os.path.exists(config_path):
                    self._config = await self._load_yaml_file(config_path)
                    if self._config:
                        self._config_path = config_path
                        config_loaded = True
                        break
            except Exception as e:
                errors.append(f"Ошибка загрузки {config_path}: {e}")

        # Загрузка дополнительных конфигурационных файлов и слияние
        await self._load_and_merge_configs()

        # Загрузка PostgreSQL конфигурации
        await self._load_postgres_config()

        # Загрузка traders.yaml если есть
        await self._load_traders_yaml()

        # Загрузка risk_management.yaml
        await self._load_risk_management_config()

        # Создание информации о конфигурации
        self._config_info = ConfigInfo(
            path=self._config_path or "not_found",
            loaded_at=datetime.now(),
            is_valid=config_loaded,
            errors=errors,
        )

        if not config_loaded:
            print(f"ВНИМАНИЕ: Конфигурация не загружена. Ошибки: {errors}")

    async def _load_postgres_config(self) -> None:
        """Загрузка конфигурации PostgreSQL"""
        if os.path.exists(self._postgres_config_path):
            try:
                postgres_config = await self._load_yaml_file(self._postgres_config_path)
                if "postgres" in postgres_config:
                    self._config["postgres"] = postgres_config["postgres"]
            except Exception as e:
                print(f"Ошибка загрузки PostgreSQL конфигурации: {e}")

    async def _load_traders_yaml(self) -> None:
        """Загрузка traders.yaml в основную конфигурацию"""
        if self._config_path:
            config_dir = os.path.dirname(self._config_path)
            traders_path = os.path.join(config_dir, "traders.yaml")

            if os.path.exists(traders_path):
                try:
                    traders_config = await self._load_yaml_file(traders_path)
                    if "traders" in traders_config:
                        self._config["traders"] = traders_config["traders"]
                    print(f"✅ Загружена конфигурация трейдеров из {traders_path}")
                except Exception as e:
                    print(f"Ошибка загрузки traders.yaml: {e}")

    async def _load_trader_configs(self) -> None:
        """Загрузка конфигураций отдельных трейдеров"""
        # Поиск конфигураций трейдеров
        traders_config_dir = os.path.join(
            os.path.dirname(self._config_path or ""), "traders"
        )

        if os.path.exists(traders_config_dir):
            for config_file in os.listdir(traders_config_dir):
                if config_file.endswith(".yaml"):
                    trader_id = config_file[:-5]  # Убираем .yaml
                    config_path = os.path.join(traders_config_dir, config_file)

                    try:
                        trader_config = await self._load_yaml_file(config_path)
                        self._trader_configs[trader_id] = trader_config
                    except Exception as e:
                        print(f"Ошибка загрузки конфигурации трейдера {trader_id}: {e}")

        # Загрузка трейдеров из системной конфигурации
        system_traders = self._config.get("traders", [])
        for trader_config in system_traders:
            trader_id = trader_config.get("id")
            if trader_id:
                self._trader_configs[trader_id] = trader_config

    async def _load_risk_management_config(self) -> None:
        """Загрузка конфигурации управления рисками"""
        if self._config_path:
            config_dir = os.path.dirname(self._config_path)
            risk_config_path = os.path.join(config_dir, "risk_management.yaml")

            if os.path.exists(risk_config_path):
                try:
                    risk_config = await self._load_yaml_file(risk_config_path)
                    if "risk_management" in risk_config:
                        self._config["risk_management"] = risk_config["risk_management"]
                    if "enhanced_sltp" in risk_config:
                        self._config["enhanced_sltp"] = risk_config["enhanced_sltp"]
                    if "ml_integration" in risk_config:
                        self._config["ml_integration"] = risk_config["ml_integration"]
                    if "monitoring" in risk_config:
                        self._config["monitoring"] = risk_config["monitoring"]
                    print(
                        f"✅ Загружена конфигурация управления рисками из {risk_config_path}"
                    )
                except Exception as e:
                    print(f"Ошибка загрузки risk_management.yaml: {e}")
            else:
                print(
                    f"⚠️ Файл risk_management.yaml не найден по пути: {risk_config_path}"
                )

    async def _load_and_merge_configs(self) -> None:
        """Загрузка и слияние всех конфигурационных файлов"""
        if not self._config_path:
            return

        config_dir = os.path.dirname(self._config_path)

        # Список файлов для загрузки и слияния
        config_files = [
            "system.yaml",
            "trading.yaml",
            "ml/ml_config.yaml",
            "database.yaml",
            "exchanges.yaml",
        ]

        for config_file in config_files:
            config_path = os.path.join(config_dir, config_file)

            if os.path.exists(config_path):
                try:
                    additional_config = await self._load_yaml_file(config_path)
                    # Слияние конфигураций (новые ключи добавляются, существующие обновляются)
                    self._merge_configs(self._config, additional_config)
                    print(f"✅ Загружена конфигурация из {config_file}")
                except Exception as e:
                    print(f"⚠️ Ошибка загрузки {config_file}: {e}")

    def _merge_configs(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Рекурсивное слияние конфигураций"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    async def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """Асинхронная загрузка YAML файла"""

        def _load_sync():
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _load_sync)

    def get_config(
        self, key: str = None, default: Any = None, force_reload: bool = False
    ) -> Any:
        """
        Получение значения из конфигурации (совместимость с v1.0/v2.0)

        Args:
            key: Ключ для получения значения (например, 'trading.leverage')
            default: Значение по умолчанию
            force_reload: Принудительная перезагрузка

        Returns:
            Значение из конфигурации
        """
        if force_reload or not self._is_initialized:
            # Синхронная загрузка для обратной совместимости
            asyncio.create_task(self.initialize())

        if key is None:
            return self._config.copy()

        # Поддержка вложенных ключей (например, 'trading.leverage')
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_leverage(
        self, model_score: Optional[int] = None, default: Optional[float] = None
    ) -> float:
        """
        Получение leverage с учетом приоритетов (совместимость с v1.0/v2.0)

        Приоритет:
        1. score_configs.TradingModel.{model_score}.leverage
        2. trading.leverage
        3. default значение
        4. 5.0 (финальное значение по умолчанию)

        Args:
            model_score: Скор модели для поиска в score_configs
            default: Значение по умолчанию

        Returns:
            Значение leverage
        """
        # Проверяем score_configs если указан model_score
        if model_score is not None:
            score_configs = self.get_config("score_configs", {})
            trading_model_configs = score_configs.get("TradingModel", {})

            # Пробуем integer ключ, затем string ключ
            model_config = trading_model_configs.get(model_score, {})
            if not model_config:
                model_config = trading_model_configs.get(str(model_score), {})

            if model_config and "leverage" in model_config:
                return safe_float(model_config.get("leverage"))

        # Проверяем trading.leverage
        trading_leverage = self.get_config("trading.leverage")
        if trading_leverage is not None:
            return safe_float(trading_leverage)

        # Используем default или финальное значение по умолчанию
        return default if default is not None else 5.0

    def get_trader_config(
        self, trader_id: str, key: str = None, default: Any = None
    ) -> Any:
        """
        Получение конфигурации конкретного трейдера

        Args:
            trader_id: Идентификатор трейдера
            key: Ключ в конфигурации трейдера
            default: Значение по умолчанию

        Returns:
            Конфигурация трейдера или значение по ключу
        """
        trader_config = self._trader_configs.get(trader_id, {})

        if key is None:
            return trader_config

        # Поддержка вложенных ключей
        keys = key.split(".")
        value = trader_config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_all_trader_ids(self) -> List[str]:
        """Получение списка всех идентификаторов трейдеров"""
        return list(self._trader_configs.keys())

    def get_system_config(self) -> Dict[str, Any]:
        """Получение системной конфигурации"""
        return self._config.get("system", {})

    # Новые методы: обновление и сохранение системной конфигурации
    def update_system_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет раздел system в конфигурации и возвращает актуальные данные.

        Примечание: метод выполняет in-memory обновление и пытается сохранить
        изменения в исходный YAML файл, если путь известен.
        """
        current = self._config.get("system", {})
        # Глубокое обновление верхнего уровня system
        if not isinstance(current, dict):
            current = {}
        if not isinstance(updates, dict):
            raise ConfigurationError("Обновление конфигурации должно быть словарём")
        # Плоское объединение (без рекурсивного мерджа для простоты и предсказуемости)
        current.update(updates)
        self._config["system"] = current
        # Пытаемся сохранить на диск (best effort)
        try:
            self.save_system_config()
        except Exception:
            # Не прерываем выполнение, сохранение best-effort
            pass
        return current

    def save_system_config(self) -> None:
        """Сохраняет текущую конфигурацию в YAML файл, если путь известен."""
        if not self._config_path:
            raise ConfigurationError(
                "Неизвестен путь к конфигурационному файлу для сохранения"
            )

        # Безопасная запись YAML
        data_to_write = self._config.copy()
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data_to_write, f, allow_unicode=True, sort_keys=False)

    def get_database_config(self) -> Dict[str, Any]:
        """Получение конфигурации базы данных"""
        # Приоритет: database > postgres (обратная совместимость)
        db_config = self._config.get("database")
        if db_config:
            return db_config

        return self._config.get("postgres", {})

    def get_logging_config(self) -> Dict[str, Any]:
        """Получение конфигурации логирования"""
        return self._config.get("logging", {})

    def get_redis_config(self) -> Dict[str, Any]:
        """Получение конфигурации Redis"""
        return self._config.get("redis", {})

    def get_ml_config(self) -> Dict[str, Any]:
        """Получение ML конфигурации"""
        return self.get_config("ml", {})

    def get_risk_management_config(self) -> Dict[str, Any]:
        """Получение конфигурации управления рисками"""
        return self.get_config("risk_management", {})

    def get_enhanced_sltp_config(self) -> Dict[str, Any]:
        """Получение конфигурации улучшенного SL/TP"""
        return self.get_config("enhanced_sltp", {})

    def get_ml_integration_config(self) -> Dict[str, Any]:
        """Получение конфигурации ML-интеграции"""
        return self.get_config("ml_integration", {})

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Получение конфигурации мониторинга"""
        return self.get_config("monitoring", {})

    def get_risk_profile(self, profile_name: str = "standard") -> Dict[str, Any]:
        """Получение профиля риска по имени"""
        risk_config = self.get_risk_management_config()
        risk_profiles = risk_config.get("risk_profiles", {})
        return risk_profiles.get(profile_name, {})

    def get_asset_category(self, symbol: str) -> Dict[str, Any]:
        """Получение категории актива по символу"""
        risk_config = self.get_risk_management_config()
        asset_categories = risk_config.get("asset_categories", {})

        for category_name, category_config in asset_categories.items():
            symbols = category_config.get("symbols", [])
            if symbol in symbols:
                return category_config

        # Возвращаем стандартную категорию если не найдена
        return asset_categories.get("stable_coins", {})

    def get_exchange_config(
        self, exchange_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получение конфигурации биржи"""
        exchanges = self._config.get("exchanges", {})
        if exchange_name:
            return exchanges.get(exchange_name, {})
        return exchanges

    def set_db_path(self, db_path: str) -> None:
        """Установка пути к БД (совместимость с v1.0/v2.0)"""
        self._db_path = db_path

    def get_db_path(self) -> str:
        """
        Получение информации о подключении к БД (совместимость с v1.0/v2.0)

        Returns:
            Строка вида "dbname on host:port"
        """
        if self._db_path:
            return self._db_path

        # Получаем параметры из конфигурации
        db_config = self.get_database_config()
        host = db_config.get("host", "")
        port = db_config.get("port", "")
        dbname = db_config.get("name") or db_config.get("dbname", "")

        return f"{dbname} on {host}:{port}"

    def is_trader_enabled(self, trader_id: str) -> bool:
        """Проверка, включен ли трейдер"""
        trader_config = self.get_trader_config(trader_id)
        return trader_config.get("enabled", False)

    def get_config_info(self) -> Optional[ConfigInfo]:
        """Получение информации о состоянии конфигурации"""
        return self._config_info

    async def reload_config(self) -> None:
        """Перезагрузка всех конфигураций"""
        self._is_initialized = False
        await self.initialize()

    def validate_config(self) -> List[str]:
        """
        Валидация конфигурации

        Returns:
            Список ошибок валидации
        """
        errors = []

        # Проверка системной конфигурации
        if not self._config:
            errors.append("Системная конфигурация пуста")

        # Проверка конфигурации БД
        db_config = self.get_database_config()
        if not db_config:
            errors.append("Конфигурация базы данных не найдена")
        elif not all(key in db_config for key in ["host", "port", "name"]):
            errors.append("Неполная конфигурация базы данных")

        # Проверка конфигураций трейдеров
        for trader_id, trader_config in self._trader_configs.items():
            if not trader_config.get("exchange"):
                errors.append(f"Трейдер {trader_id}: не указана биржа")
            if not trader_config.get("strategy"):
                errors.append(f"Трейдер {trader_id}: не указана стратегия")

        return errors


# Глобальный экземпляр для обратной совместимости
_global_config_manager: Optional[ConfigManager] = None


def get_global_config_manager() -> ConfigManager:
    """Получение глобального экземпляра ConfigManager"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


# Функции обратной совместимости с v1.0/v2.0
def load_config(config_path: str) -> Dict[str, Any]:
    """Загрузка конфигурации (совместимость с v1.0/v2.0)"""
    manager = ConfigManager(config_path)
    asyncio.create_task(manager.initialize())
    return manager.get_config()


def get_config(key: str = None, default: Any = None, force_reload: bool = False) -> Any:
    """Получение конфигурации (совместимость с v1.0/v2.0)"""
    manager = get_global_config_manager()
    return manager.get_config(key, default, force_reload)


def get_leverage(
    model_score: Optional[int] = None, default: Optional[float] = None
) -> float:
    """Получение leverage (совместимость с v1.0/v2.0)"""
    manager = get_global_config_manager()
    return manager.get_leverage(model_score, default)


def set_db_path(db_path: str) -> None:
    """Установка пути к БД (совместимость с v1.0/v2.0)"""
    manager = get_global_config_manager()
    manager.set_db_path(db_path)


def get_db_path() -> str:
    """Получение пути к БД (совместимость с v1.0/v2.0)"""
    manager = get_global_config_manager()
    return manager.get_db_path()
