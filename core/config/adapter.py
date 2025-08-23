#!/usr/bin/env python3
"""Адаптер для обратной совместимости при миграции на систему конфигурации v3.

Обеспечивает работу старого кода с новой системой конфигурации,
позволяя постепенную миграцию компонентов.
"""

import logging
from typing import Any, Dict, Optional

from core.config.config_manager import ConfigManager, get_global_config_manager
from core.config.loader import ConfigLoader
from core.config.models import RootConfig
from core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigAdapter:
    """Адаптер для обратной совместимости со старым API конфигурации.
    
    Позволяет использовать как старый ConfigManager, так и новую систему
    с Pydantic моделями, обеспечивая плавную миграцию.
    """
    
    def __init__(self, use_new_system: bool = False, profile: str = "development"):
        """Инициализирует адаптер.
        
        Args:
            use_new_system: Использовать новую систему вместо старой
            profile: Профиль для загрузки (dev/staging/prod)
        """
        self.use_new_system = use_new_system
        self.profile = profile
        
        # Старая система (по умолчанию)
        self._old_manager: Optional[ConfigManager] = None
        
        # Новая система
        self._loader: Optional[ConfigLoader] = None
        self._config: Optional[RootConfig] = None
        
        # Кеш для производительности
        self._cache: Dict[str, Any] = {}
        
        # Маппинг старых ключей на новые (для миграции)
        self._key_mappings = self._create_key_mappings()
        
        # Инициализация
        self._initialize()
    
    def _create_key_mappings(self) -> Dict[str, str]:
        """Создает маппинг старых ключей конфигурации на новые.
        
        Returns:
            Словарь маппингов old_key -> new_key
        """
        return {
            # Старые ключи -> новые ключи
            "trading.leverage": "trading.orders.default_leverage",
            "trading.min_order_size": "trading.orders.min_order_size",
            "trading.risk_management": "risk_management",
            "ml.enabled": "ml.enabled",
            "ml.model_path": "ml.model.path",
            "ml.scaler_path": "ml.model.scaler_path",
            "database.postgres": "database",
            "system.database": "database",
            # Добавьте другие маппинги по мере необходимости
        }
    
    def _initialize(self) -> None:
        """Инициализирует выбранную систему конфигурации."""
        if self.use_new_system:
            try:
                # Пробуем новую систему
                self._loader = ConfigLoader()
                self._config = self._loader.load(profile=self.profile)
                logger.info(f"✅ Используется новая система конфигурации (профиль: {self.profile})")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить новую систему: {e}, переключаемся на старую")
                self.use_new_system = False
                self._initialize_old_system()
        else:
            self._initialize_old_system()
    
    def _initialize_old_system(self) -> None:
        """Инициализирует старую систему конфигурации."""
        try:
            self._old_manager = get_global_config_manager()
            logger.info("📦 Используется старая система конфигурации (ConfigManager)")
        except Exception as e:
            raise ConfigurationError(f"Не удалось инициализировать систему конфигурации: {e}")
    
    def get_config(self, key: str = None, default: Any = None, force_reload: bool = False) -> Any:
        """Получает значение конфигурации (совместимость со старым API).
        
        Args:
            key: Ключ конфигурации (поддерживает точечную нотацию)
            default: Значение по умолчанию
            force_reload: Принудительная перезагрузка
            
        Returns:
            Значение конфигурации или default
        """
        # Проверяем кеш
        if not force_reload and key in self._cache:
            return self._cache[key]
        
        value = None
        
        if self.use_new_system and self._config:
            # Используем новую систему
            value = self._get_from_new_system(key, default)
        else:
            # Используем старую систему
            value = self._get_from_old_system(key, default, force_reload)
        
        # Кешируем результат
        if key:
            self._cache[key] = value
        
        return value
    
    def _get_from_new_system(self, key: str = None, default: Any = None) -> Any:
        """Получает значение из новой системы конфигурации.
        
        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию
            
        Returns:
            Значение из конфигурации
        """
        if not self._config:
            return default
        
        if key is None:
            # Возвращаем всю конфигурацию
            return self._config.model_dump()
        
        # Проверяем маппинги
        if key in self._key_mappings:
            key = self._key_mappings[key]
        
        # Парсим вложенные ключи
        keys = key.split(".")
        value = self._config.model_dump()
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _get_from_old_system(self, key: str = None, default: Any = None, force_reload: bool = False) -> Any:
        """Получает значение из старой системы конфигурации.
        
        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию
            force_reload: Принудительная перезагрузка
            
        Returns:
            Значение из конфигурации
        """
        if not self._old_manager:
            return default
        
        return self._old_manager.get_config(key, default, force_reload)
    
    def get_leverage(self, model_score: int = None, default: float = None) -> float:
        """Получает leverage (совместимость со старым API).
        
        Args:
            model_score: Скор модели для поиска в score_configs
            default: Значение по умолчанию
            
        Returns:
            Значение leverage
        """
        if self.use_new_system and self._config:
            # Из новой системы
            return self._config.trading.orders.default_leverage
        elif self._old_manager:
            # Из старой системы
            return self._old_manager.get_leverage(model_score, default)
        else:
            return default if default is not None else 5.0
    
    def get_trader_config(self, trader_id: str, key: str = None, default: Any = None) -> Any:
        """Получает конфигурацию трейдера (совместимость со старым API).
        
        Args:
            trader_id: ID трейдера
            key: Ключ в конфигурации трейдера
            default: Значение по умолчанию
            
        Returns:
            Конфигурация трейдера или значение по ключу
        """
        if self._old_manager:
            return self._old_manager.get_trader_config(trader_id, key, default)
        
        # В новой системе трейдеры могут быть в другом месте
        # Это нужно адаптировать под конкретную структуру
        return default
    
    def migrate_to_new_system(self) -> bool:
        """Пытается мигрировать на новую систему конфигурации.
        
        Returns:
            True если миграция успешна, False иначе
        """
        if self.use_new_system:
            logger.info("✅ Уже используется новая система")
            return True
        
        try:
            # Пробуем загрузить новую систему
            self._loader = ConfigLoader()
            self._config = self._loader.load(profile=self.profile)
            
            # Проверяем, что основные параметры доступны
            test_keys = [
                "system.name",
                "database.port",
                "trading.orders.default_leverage"
            ]
            
            for key in test_keys:
                value = self._get_from_new_system(key)
                if value is None:
                    raise ConfigurationError(f"Не удалось получить {key} из новой системы")
            
            # Переключаемся на новую систему
            self.use_new_system = True
            self._cache.clear()  # Очищаем кеш
            
            logger.info("✅ Успешная миграция на новую систему конфигурации")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка миграции на новую систему: {e}")
            return False
    
    def get_validation_report(self) -> str:
        """Возвращает отчет о валидации конфигурации.
        
        Returns:
            Отчет валидации или сообщение об использовании старой системы
        """
        if self.use_new_system and self._loader:
            return self._loader.get_validation_report()
        else:
            return "⚠️ Используется старая система конфигурации без валидации"
    
    def clear_cache(self) -> None:
        """Очищает кеш конфигурации."""
        self._cache.clear()
        logger.debug("🗑️ Кеш конфигурации очищен")
    
    # Методы для совместимости с ConfigManager
    
    def get_system_config(self) -> dict:
        """Получает системную конфигурацию."""
        return self.get_config("system", {})
    
    def get_database_config(self) -> dict:
        """Получает конфигурацию БД."""
        return self.get_config("database", {})
    
    def get_ml_config(self) -> dict:
        """Получает ML конфигурацию."""
        return self.get_config("ml", {})
    
    def get_risk_management_config(self) -> dict:
        """Получает конфигурацию управления рисками."""
        return self.get_config("risk_management", {})
    
    def get_exchange_config(self, exchange_name: str = None) -> dict:
        """Получает конфигурацию биржи."""
        if exchange_name:
            return self.get_config(f"exchanges.{exchange_name}", {})
        return self.get_config("exchanges", {})