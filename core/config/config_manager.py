#!/usr/bin/env python3
"""Модуль ConfigManager для управления конфигурацией.

Обеспечивает централизованный доступ к параметрам системы, поддерживает
загрузку из нескольких файлов, кеширование и валидацию.
"""

import asyncio
import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import yaml

from core.config.loader import ConfigLoader
from core.config.models import RootConfig
from core.exceptions import ConfigurationError
from utils.helpers import safe_float


@dataclass
class ConfigInfo:
    """Содержит мета-информацию о загруженной конфигурации."""

    path: str
    loaded_at: datetime
    is_valid: bool
    errors: list[str] = field(default_factory=list)


class ConfigManager:
    """Управляет конфигурацией для мульти-трейдерной системы.

    Загружает, объединяет и предоставляет доступ к системным и трейдерским
    конфигурациям. Поддерживает иерархическую структуру и кеширование.
    """

    def __init__(self, config_path: str | None = None):
        """Инициализирует ConfigManager.

        Args:
            config_path: Прямой путь к основному файлу конфигурации.
        """
        self._config: RootConfig | None = None
        self._config_path = config_path or "config/config.yaml"
        self._config_info: ConfigInfo | None = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """Асинхронно инициализирует менеджер, загружая все конфигурации."""
        try:
            await self._load_config_async()
            self._is_initialized = True
        except Exception as e:
            raise ConfigurationError(f"Ошибка инициализации ConfigManager: {e}")

    def get_config(self, key: str = None, default: Any = None, force_reload: bool = False) -> Any:
        """Получает значение из конфигурации.

        Поддерживает вложенные ключи через точку (например, 'trading.orders.default_leverage').

        Args:
            key: Ключ для поиска.
            default: Значение по умолчанию, если ключ не найден.
            force_reload: Принудительно перезагрузить конфигурацию с диска.

        Returns:
            Найденное значение, валидированный RootConfig или значение по умолчанию.
        """
        if force_reload or not self._is_initialized or not self._config:
            self._load_config()
        
        if key is None:
            return self._config  # Возвращаем полный RootConfig объект
        
        return self._get_nested_value_from_pydantic(self._config, key, default)

    def get_trader_config(self, trader_id: str, key: str = None, default: Any = None) -> Any:
        """Получает конфигурацию для конкретного трейдера.

        Args:
            trader_id: Идентификатор трейдера.
            key: Ключ для поиска в конфигурации трейдера.
            default: Значение по умолчанию.

        Returns:
            Полная конфигурация трейдера или конкретное значение по ключу.
        """
        try:
            if not self._is_initialized or not self._config:
                self._load_config()
            
            # Ищем трейдера в списке traders из RootConfig
            for trader in self._config.traders:
                if trader.id == trader_id:
                    if key:
                        # Получаем значение по ключу из Pydantic объекта
                        return getattr(trader, key, default)
                    return trader  # Возвращаем полный объект TraderSettings
            
            # Трейдер не найден
            if default is not None:
                return default
            raise KeyError(f"Трейдер с ID '{trader_id}' не найден в конфигурации")
                
        except Exception as e:
            raise ConfigurationError(
                f"Ошибка при получении конфигурации трейдера {trader_id}: {e}",
                config_key=key,
                trader_id=trader_id
            )

    def get_system_config(self):
        """Получает системную конфигурацию.
        
        Returns:
            SystemSettings объект с системной конфигурацией.
        """
        if not self._is_initialized or not self._config:
            self._load_config()
        
        return self._config.system

    def _load_config(self) -> None:
        """Синхронная загрузка конфигурации через ConfigLoader с Pydantic валидацией."""
        try:
            config_path = Path(self._config_path)
            
            if not config_path.exists():
                raise ConfigurationError(f"Конфигурационный файл не найден: {config_path}")
            
            # Используем ConfigLoader для полной Pydantic валидации
            loader = ConfigLoader(config_dir=config_path.parent)
            self._config = loader.load()  # Возвращает валидированный RootConfig
            
            self._config_info = ConfigInfo(
                path=str(config_path),
                loaded_at=datetime.now(),
                is_valid=True
            )
            self._is_initialized = True
            
        except Exception as e:
            self._config_info = ConfigInfo(
                path=str(config_path) if 'config_path' in locals() else self._config_path,
                loaded_at=datetime.now(),
                is_valid=False,
                errors=[str(e)]
            )
            raise ConfigurationError(f"Ошибка загрузки конфигурации: {e}")

    async def _load_config_async(self) -> None:
        """Асинхронная загрузка конфигурации."""
        # Для простоты используем синхронную версию
        # В будущем можно добавить асинхронную загрузку
        self._load_config()

    def _get_nested_value_from_pydantic(self, config: RootConfig, key: str, default: Any = None) -> Any:
        """Получает значение по вложенному ключу из Pydantic объекта (например, 'trading.orders.default_leverage')."""
        try:
            keys = key.split('.')
            current = config
            
            for k in keys:
                if hasattr(current, k):
                    current = getattr(current, k)
                else:
                    return default
            
            return current
        except Exception:
            return default

    # Методы обратной совместимости для старого API
    def get_exchange_config(self, exchange_name: str = None) -> dict[str, Any]:
        """Получает конфигурацию биржи.
        
        Args:
            exchange_name: Имя биржи (bybit, binance, etc.). Если None, возвращает все биржи.
            
        Returns:
            Словарь с конфигурацией биржи или всех бирж.
        """
        if exchange_name:
            return self.get_config(f"exchanges.{exchange_name}", {})
        return self.get_config("exchanges", {})
    
    def get_ml_config(self) -> dict[str, Any]:
        """Получает конфигурацию ML системы."""
        return self.get_config("ml", {})
    
    def get_risk_management_config(self) -> dict[str, Any]:
        """Получает конфигурацию риск-менеджмента."""
        return self.get_config("risk_management", {})
    
    def get_monitoring_config(self) -> dict[str, Any]:
        """Получает конфигурацию мониторинга."""
        return self.get_config("monitoring", {})
    
    def get_ml_integration_config(self) -> dict[str, Any]:
        """Получает конфигурацию интеграции ML."""
        return self.get_config("ml.integration", {})
    
    def update_system_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Обновляет системную конфигурацию и сохраняет изменения.
        
        Args:
            updates: Словарь с обновлениями для применения к конфигурации
            
        Returns:
            Обновленная конфигурация
            
        Raises:
            ConfigurationError: Если не удалось обновить или сохранить конфигурацию
        """
        try:
            if not self._is_initialized or not self._config:
                self._load_config()
            
            # Создаем резервную копию текущей конфигурации
            backup_path = Path(self._config_path).with_suffix('.backup')
            import shutil
            shutil.copy2(self._config_path, backup_path)
            
            # Преобразуем конфигурацию в словарь для обновления
            if hasattr(self._config, 'model_dump'):
                config_dict = self._config.model_dump()
            elif hasattr(self._config, 'dict'):
                config_dict = self._config.dict()
            else:
                # Если это уже словарь
                config_dict = dict(self._config) if isinstance(self._config, dict) else {}
            
            # Применяем обновления (плоское обновление верхнего уровня)
            for key, value in updates.items():
                config_dict[key] = value
            
            # Сохраняем обновленную конфигурацию
            import yaml
            with open(self._config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config_dict, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            # Перезагружаем конфигурацию
            self._load_config()
            
            return config_dict
            
        except Exception as e:
            # В случае ошибки восстанавливаем из резервной копии
            if backup_path.exists():
                shutil.copy2(backup_path, self._config_path)
                backup_path.unlink()  # Удаляем резервную копию
            raise ConfigurationError(f"Ошибка обновления конфигурации: {e}")
    
    def _get_nested_value(self, data: dict, key: str, default: Any = None) -> Any:
        """Получает значение по вложенному ключу (обратная совместимость для dict)."""
        try:
            keys = key.split('.')
            current = data
            
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            
            return current
        except Exception:
            return default


# Глобальный экземпляр для обратной совместимости
_global_config_manager: ConfigManager | None = None


def get_global_config_manager() -> ConfigManager:
    """Получение глобального экземпляра ConfigManager."""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager
