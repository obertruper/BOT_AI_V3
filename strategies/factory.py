"""
Фабрика для создания экземпляров торговых стратегий
Обеспечивает единообразное создание и конфигурирование стратегий
"""
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path
import yaml
import json

from .base import StrategyABC
from .registry import StrategyRegistry, StrategyRegistryError

logger = logging.getLogger(__name__)


class StrategyFactoryError(Exception):
    """Ошибка фабрики стратегий"""
    pass


class StrategyFactory:
    """Фабрика для создания и конфигурирования торговых стратегий"""
    
    def __init__(self, registry: Optional[StrategyRegistry] = None):
        """
        Инициализация фабрики
        
        Args:
            registry: Реестр стратегий (если не указан, используется глобальный)
        """
        self.registry = registry or StrategyRegistry()
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        
    def create_strategy(self, 
                       name: str, 
                       config: Optional[Dict[str, Any]] = None,
                       config_file: Optional[str] = None) -> StrategyABC:
        """
        Создание экземпляра стратегии
        
        Args:
            name: Имя стратегии из реестра
            config: Конфигурация стратегии
            config_file: Путь к файлу конфигурации
            
        Returns:
            Экземпляр стратегии
            
        Raises:
            StrategyFactoryError: При ошибке создания
        """
        try:
            # Получение класса стратегии
            strategy_class = self.registry.get_strategy_class(name)
            
            # Загрузка конфигурации
            if config_file:
                config = self._load_config_file(config_file)
            elif config is None:
                config = self._get_default_config(name)
                
            # Валидация конфигурации
            config = self._validate_and_merge_config(name, config)
            
            # Создание экземпляра
            strategy = strategy_class(config)
            
            logger.info(f"Created strategy instance: {name}")
            return strategy
            
        except StrategyRegistryError as e:
            raise StrategyFactoryError(f"Failed to create strategy: {e}")
        except Exception as e:
            logger.error(f"Error creating strategy {name}: {e}")
            raise StrategyFactoryError(f"Failed to create strategy {name}: {e}")
            
    def create_multiple(self, 
                       strategies_config: List[Dict[str, Any]]) -> List[StrategyABC]:
        """
        Создание нескольких стратегий
        
        Args:
            strategies_config: Список конфигураций стратегий
            
        Returns:
            Список созданных стратегий
        """
        strategies = []
        
        for config in strategies_config:
            if 'name' not in config:
                logger.warning("Skipping strategy without name")
                continue
                
            try:
                strategy = self.create_strategy(
                    name=config['name'],
                    config=config.get('config', {})
                )
                strategies.append(strategy)
            except Exception as e:
                logger.error(f"Failed to create strategy {config['name']}: {e}")
                
        return strategies
        
    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации из файла"""
        path = Path(file_path)
        
        if not path.exists():
            raise StrategyFactoryError(f"Config file not found: {file_path}")
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                elif path.suffix == '.json':
                    return json.load(f)
                else:
                    raise StrategyFactoryError(
                        f"Unsupported config file format: {path.suffix}"
                    )
        except Exception as e:
            raise StrategyFactoryError(f"Failed to load config file: {e}")
            
    def _get_default_config(self, strategy_name: str) -> Dict[str, Any]:
        """Получение конфигурации по умолчанию для стратегии"""
        # Попытка загрузить из кэша
        if strategy_name in self._config_cache:
            return self._config_cache[strategy_name].copy()
            
        # Базовая конфигурация
        default_config = {
            'name': strategy_name,
            'enabled': True,
            'symbols': ['BTCUSDT'],
            'timeframes': ['1h'],
            'risk_management': {
                'max_position_size_pct': 5.0,
                'max_risk_per_trade_pct': 2.0,
                'stop_loss_type': 'fixed',
                'stop_loss_value': 3.0,
                'take_profit_type': 'fixed',
                'take_profit_value': 6.0
            }
        }
        
        # Попытка загрузить конфигурацию из файла стратегии
        config_path = Path(f"strategies/{strategy_name}/config/default.yaml")
        if config_path.exists():
            try:
                loaded_config = self._load_config_file(str(config_path))
                default_config.update(loaded_config)
                self._config_cache[strategy_name] = default_config
            except Exception as e:
                logger.warning(f"Failed to load default config for {strategy_name}: {e}")
                
        return default_config
        
    def _validate_and_merge_config(self, 
                                 strategy_name: str, 
                                 config: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация и объединение с конфигурацией по умолчанию"""
        # Получение конфигурации по умолчанию
        default_config = self._get_default_config(strategy_name)
        
        # Глубокое объединение конфигураций
        merged_config = self._deep_merge(default_config, config)
        
        # Добавление обязательных полей
        if 'name' not in merged_config:
            merged_config['name'] = strategy_name
            
        return merged_config
        
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Глубокое объединение словарей"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """Получение информации о доступных стратегиях"""
        strategies = []
        
        for name in self.registry.list_strategies():
            metadata = self.registry.get_metadata(name)
            strategies.append({
                'name': name,
                'description': metadata.get('description', ''),
                'version': metadata.get('version', 'unknown'),
                'author': metadata.get('author', 'unknown'),
                'tags': metadata.get('tags', [])
            })
            
        return strategies
        
    def validate_config(self, strategy_name: str, config: Dict[str, Any]) -> bool:
        """
        Валидация конфигурации для стратегии
        
        Args:
            strategy_name: Имя стратегии
            config: Конфигурация для проверки
            
        Returns:
            True если конфигурация валидна
        """
        try:
            # Попытка создать стратегию с данной конфигурацией
            strategy = self.create_strategy(strategy_name, config)
            
            # Вызов встроенной валидации стратегии
            is_valid, error = strategy.validate_config()
            
            if not is_valid:
                logger.error(f"Config validation failed for {strategy_name}: {error}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Config validation error for {strategy_name}: {e}")
            return False
            
    def export_config(self, 
                     strategy: StrategyABC, 
                     file_path: str,
                     format: str = 'yaml') -> None:
        """
        Экспорт конфигурации стратегии в файл
        
        Args:
            strategy: Экземпляр стратегии
            file_path: Путь для сохранения
            format: Формат файла ('yaml' или 'json')
        """
        config = strategy.config
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                if format == 'yaml':
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                elif format == 'json':
                    json.dump(config, f, indent=2, ensure_ascii=False)
                else:
                    raise StrategyFactoryError(f"Unsupported format: {format}")
                    
            logger.info(f"Exported config to {file_path}")
            
        except Exception as e:
            raise StrategyFactoryError(f"Failed to export config: {e}")


# Глобальная фабрика стратегий
strategy_factory = StrategyFactory()