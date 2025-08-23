#!/usr/bin/env python3
"""
Фабрика для создания адаптеров ML моделей.
Централизованное создание и управление адаптерами.
"""

from typing import Any, Optional

from core.logger import setup_logger
from ml.adapters.base import BaseModelAdapter
from ml.adapters.patchtst import PatchTSTAdapter

logger = setup_logger(__name__)


class ModelAdapterFactory:
    """
    Фабрика для создания адаптеров моделей.
    Поддерживает различные типы моделей и обеспечивает единую точку создания.
    """
    
    # Реестр доступных адаптеров
    _adapters = {
        "PatchTST": PatchTSTAdapter,
        "UnifiedPatchTST": PatchTSTAdapter,  # Алиас для совместимости
        "patchtst": PatchTSTAdapter,  # Алиас в нижнем регистре
    }
    
    @classmethod
    def create_adapter(
        cls,
        model_type: str,
        config: dict[str, Any]
    ) -> BaseModelAdapter:
        """
        Создает адаптер для указанного типа модели.
        
        Args:
            model_type: Тип модели (PatchTST, LSTM, etc.)
            config: Конфигурация модели
            
        Returns:
            Экземпляр адаптера
            
        Raises:
            ValueError: Если тип модели не поддерживается
        """
        # Проверяем наличие адаптера
        if model_type not in cls._adapters:
            available = ", ".join(cls._adapters.keys())
            raise ValueError(
                f"Unknown model type: {model_type}. "
                f"Available types: {available}"
            )
        
        # Создаем адаптер
        adapter_class = cls._adapters[model_type]
        adapter = adapter_class(config)
        
        logger.info(f"Created {model_type} adapter: {adapter}")
        
        return adapter
    
    @classmethod
    def register_adapter(
        cls,
        model_type: str,
        adapter_class: type[BaseModelAdapter]
    ) -> None:
        """
        Регистрирует новый тип адаптера.
        
        Args:
            model_type: Название типа модели
            adapter_class: Класс адаптера
        """
        if not issubclass(adapter_class, BaseModelAdapter):
            raise ValueError(
                f"Adapter class must inherit from BaseModelAdapter, "
                f"got {adapter_class.__name__}"
            )
        
        cls._adapters[model_type] = adapter_class
        logger.info(f"Registered adapter: {model_type} -> {adapter_class.__name__}")
    
    @classmethod
    def get_available_types(cls) -> list[str]:
        """
        Возвращает список доступных типов моделей.
        
        Returns:
            Список названий типов
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def create_from_config(
        cls,
        config: dict[str, Any]
    ) -> Optional[BaseModelAdapter]:
        """
        Создает адаптер на основе конфигурации.
        Автоматически определяет тип модели из конфигурации.
        
        Args:
            config: Полная конфигурация с секцией ml
            
        Returns:
            Адаптер или None если модель отключена
        """
        # Проверяем, включена ли ML подсистема
        if hasattr(config, 'ml'):
            # Pydantic модель
            ml_config = config.ml
            logger.debug(f"🔍 Pydantic ML config detected: {type(ml_config)}")
            if hasattr(ml_config, 'model_dump'):
                ml_config = ml_config.model_dump()
            elif hasattr(ml_config, 'dict'):
                ml_config = ml_config.dict()
            else:
                # Прямой доступ к атрибутам
                ml_config = {
                    "enabled": getattr(ml_config, 'enabled', True),
                    "use_adapters": getattr(ml_config, 'use_adapters', True),
                    "active_model": getattr(ml_config, 'active_model', 'patchtst'),
                    "models": getattr(ml_config, 'models', {})
                }
        else:
            # Обычный dict
            ml_config = config.get("ml", {})
            logger.debug(f"🔍 Dict ML config: enabled={ml_config.get('enabled', False)}")
            
        if not ml_config.get("enabled", False):
            logger.warning(f"ML is disabled in configuration: enabled={ml_config.get('enabled', 'NOT_FOUND')}")
            return None
        
        # Определяем активную модель
        models_config = ml_config.get("models", {})
        active_model_name = ml_config.get("active_model", "patchtst")
        
        # Проверяем наличие конфигурации для активной модели
        if active_model_name not in models_config:
            # Fallback на старый формат конфигурации
            logger.info("Using legacy configuration format")
            model_config = ml_config.get("model", {})
            model_type = model_config.get("name", "UnifiedPatchTST")
            
            # Объединяем конфигурации
            full_config = {**config, **model_config}
            return cls.create_adapter(model_type, full_config)
        
        # Новый формат конфигурации
        model_config = models_config[active_model_name]
        logger.debug(f"🔍 Model {active_model_name} config: enabled={model_config.get('enabled', True)}")
        
        # Проверяем, включена ли модель
        if not model_config.get("enabled", True):
            logger.warning(f"Model {active_model_name} is disabled: enabled={model_config.get('enabled', 'NOT_FOUND')}")
            return None
        
        # Определяем тип адаптера
        model_type = model_config.get("type", active_model_name)
        adapter_class_name = model_config.get("adapter_class", model_type)
        
        # Объединяем конфигурации
        if hasattr(config, 'ml'):
            # Pydantic модель - преобразуем в dict
            if hasattr(config, 'model_dump'):
                config_dict = config.model_dump()
            elif hasattr(config, 'dict'):
                config_dict = config.dict()
            else:
                # Минимальная конфигурация 
                config_dict = {"ml": {"enabled": True}}
            full_config = {**config_dict, **model_config}
        else:
            full_config = {**config, **model_config}
        
        # Создаем адаптер
        return cls.create_adapter(adapter_class_name, full_config)
    
    @classmethod
    def validate_config(
        cls,
        config: dict[str, Any],
        model_type: str
    ) -> tuple[bool, list[str]]:
        """
        Валидирует конфигурацию для указанного типа модели.
        
        Args:
            config: Конфигурация для проверки
            model_type: Тип модели
            
        Returns:
            (valid, errors) - флаг валидности и список ошибок
        """
        errors = []
        
        # Проверяем наличие типа
        if model_type not in cls._adapters:
            errors.append(f"Unknown model type: {model_type}")
            return False, errors
        
        # Базовые проверки
        required_fields = ["model_file", "device"]
        for field in required_fields:
            if field not in config:
                logger.debug(f"Optional field {field} not in config, will use defaults")
        
        # Специфичные проверки для PatchTST
        if model_type in ["PatchTST", "UnifiedPatchTST", "patchtst"]:
            if "scaler_file" not in config:
                logger.debug("Scaler file not specified, will use default path")
        
        return len(errors) == 0, errors


# Пример регистрации будущих адаптеров
def register_future_adapters():
    """
    Регистрирует будущие адаптеры.
    Эта функция будет расширяться по мере добавления новых моделей.
    """
    # Пример: регистрация LSTM адаптера (когда будет реализован)
    # from ml.adapters.lstm import LSTMAdapter
    # ModelAdapterFactory.register_adapter("LSTM", LSTMAdapter)
    
    # Пример: регистрация Transformer адаптера
    # from ml.adapters.transformer import TransformerAdapter
    # ModelAdapterFactory.register_adapter("Transformer", TransformerAdapter)
    
    pass