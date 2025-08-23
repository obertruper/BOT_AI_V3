#!/usr/bin/env python3
"""Примеры базового использования новой системы конфигурации."""

import asyncio
from pathlib import Path
from typing import Optional

from core.config.loader import ConfigLoader
from core.config.models import RootConfig, TradingSettings
from core.config.secrets import get_secret, get_secrets_manager


def example_basic_loading():
    """Пример базовой загрузки конфигурации."""
    print("\n=== Базовая загрузка конфигурации ===\n")
    
    # Создаем загрузчик
    loader = ConfigLoader()
    
    # Загружаем конфигурацию (по умолчанию профиль development)
    config: RootConfig = loader.load()
    
    # Типизированный доступ к параметрам
    print(f"Система: {config.system.name} v{config.system.version}")
    print(f"Окружение: {config.system.environment}")
    print(f"База данных: {config.database.name} на порту {config.database.port}")
    print(f"Leverage: {config.trading.orders.default_leverage}x")
    print(f"ML включен: {config.ml.enabled}")
    
    # Валидационный отчет
    print("\n" + loader.get_validation_report())


def example_profile_loading():
    """Пример загрузки с разными профилями."""
    print("\n=== Загрузка с профилями ===\n")
    
    loader = ConfigLoader()
    
    # Загрузка development профиля
    dev_config = loader.load(profile="development")
    print(f"Dev окружение: {dev_config.system.environment}")
    print(f"Dev debug mode: {dev_config.system.environment == 'development'}")
    
    # Загрузка production профиля (если существует)
    try:
        prod_config = loader.load(profile="production")
        print(f"Prod окружение: {prod_config.system.environment}")
        print(f"Prod leverage: {prod_config.trading.orders.default_leverage}x")
    except Exception as e:
        print(f"Production профиль не найден: {e}")


def example_secrets_management():
    """Пример работы с секретами."""
    print("\n=== Управление секретами ===\n")
    
    # Получение секрета с значением по умолчанию
    api_key = get_secret("BYBIT_API_KEY", default="demo-key")
    print(f"API Key (маскирован): {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
    
    # Проверка обязательного секрета
    try:
        db_password = get_secret("DB_PASSWORD", required=True)
        print("✅ Пароль БД установлен")
    except Exception as e:
        print(f"⚠️ Пароль БД отсутствует: {e}")
    
    # Статус всех секретов
    manager = get_secrets_manager()
    print("\nСтатус секретов:")
    validation = manager.validate_required()
    for key, exists in validation.items():
        status = "✅" if exists else "❌"
        print(f"  {status} {key}")


def example_validation():
    """Пример валидации конфигурации."""
    print("\n=== Валидация конфигурации ===\n")
    
    loader = ConfigLoader()
    config = loader.load()
    
    # Проверка консистентности
    warnings = config.validate_consistency()
    
    if warnings:
        print("⚠️ Предупреждения валидации:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("✅ Конфигурация валидна")
    
    # Проверка критических параметров
    if config.database.port != 5555:
        print(f"❌ КРИТИЧНО: PostgreSQL должен использовать порт 5555, а не {config.database.port}")
    
    if config.trading.orders.default_leverage != 5:
        print(f"⚠️ Leverage {config.trading.orders.default_leverage}x отличается от рекомендуемых 5x")


def example_typed_access():
    """Пример типизированного доступа к конфигурации."""
    print("\n=== Типизированный доступ ===\n")
    
    loader = ConfigLoader()
    config = loader.load()
    
    # Работа с типизированными настройками
    trading: TradingSettings = config.trading
    
    print(f"Hedge mode: {trading.hedge_mode}")
    print(f"Категория: {trading.category}")
    print(f"Минимальный размер ордера: ${trading.orders.min_order_size}")
    print(f"Максимальное проскальзывание: {trading.orders.max_slippage * 100}%")
    
    # ML настройки с проверкой включения
    if config.ml.enabled:
        print(f"\nML модель: {config.ml.model.path}")
        print(f"ML устройство: {config.ml.model.device}")
        print(f"Минимальная уверенность: {config.ml.filters.min_confidence}")
    
    # Risk management
    risk = config.risk_management
    print(f"\nМаксимальный риск: {risk.global_risk.max_total_risk * 100}%")
    print(f"Максимальная дневная потеря: {risk.global_risk.max_daily_loss * 100}%")
    print(f"SL по умолчанию: {risk.position.default_stop_loss * 100}%")
    print(f"TP по умолчанию: {risk.position.default_take_profit * 100}%")


def example_export_config():
    """Пример экспорта конфигурации."""
    print("\n=== Экспорт конфигурации ===\n")
    
    loader = ConfigLoader()
    config = loader.load()
    
    # Безопасный экспорт (без секретов)
    safe_export_path = Path("config_export_safe.yaml")
    loader.export_config(safe_export_path, safe_mode=True)
    print(f"✅ Безопасная конфигурация экспортирована в {safe_export_path}")
    
    # Получение конфигурации для frontend
    frontend_config = config.get_frontend_safe_config()
    print(f"\nКонфигурация для frontend (без секретов):")
    print(f"  - Система: {frontend_config['system']['name']}")
    print(f"  - Торговля включена: {frontend_config['trading']['hedge_mode']}")
    print(f"  - ML включен: {frontend_config['ml']['enabled']}")


async def example_config_reload():
    """Пример перезагрузки конфигурации."""
    print("\n=== Перезагрузка конфигурации ===\n")
    
    from core.config.config_manager import get_global_config_manager
    
    manager = get_global_config_manager()
    
    # Инициализация
    await manager.initialize()
    print("✅ Конфигурация загружена")
    
    # Получение параметра
    leverage = manager.get_config("trading.orders.default_leverage")
    print(f"Текущий leverage: {leverage}")
    
    # Перезагрузка
    await manager.reload_config()
    print("✅ Конфигурация перезагружена")
    
    # Проверка после перезагрузки
    new_leverage = manager.get_config("trading.orders.default_leverage")
    print(f"Leverage после перезагрузки: {new_leverage}")


def main():
    """Запуск всех примеров."""
    print("=" * 60)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ СИСТЕМЫ КОНФИГУРАЦИИ V3")
    print("=" * 60)
    
    # Базовые примеры
    example_basic_loading()
    example_profile_loading()
    example_secrets_management()
    example_validation()
    example_typed_access()
    example_export_config()
    
    # Асинхронный пример
    print("\n" + "=" * 60)
    asyncio.run(example_config_reload())
    
    print("\n" + "=" * 60)
    print("Все примеры выполнены успешно!")


if __name__ == "__main__":
    main()