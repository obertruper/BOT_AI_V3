#!/usr/bin/env python3
"""Тестовый скрипт для проверки конфигурации"""

import asyncio

from core.config.config_manager import ConfigManager


async def test_config():
    config_manager = ConfigManager()
    await config_manager.initialize()

    # Проверяем, что конфигурация загружена
    print("Config loaded:", config_manager._is_initialized)
    print("Config path:", config_manager._config_path)

    # Получаем полную конфигурацию
    full_config = config_manager.get_config()
    print(
        "\nFull config keys:",
        list(full_config.keys())[:10],
        "..." if len(full_config.keys()) > 10 else "",
    )

    # Проверяем системную конфигурацию
    system_config = config_manager.get_system_config()
    print("\nSystem config keys:", list(system_config.keys()))

    # Проверяем трейдеры
    traders = full_config.get("traders", [])
    print(f"\nFound {len(traders)} traders:")

    for trader in traders:
        print(f"  - ID: {trader.get('id')}, Enabled: {trader.get('enabled')}")

    # Проверка multi_crypto_10
    multi_crypto_enabled = any(
        trader.get("id") == "multi_crypto_10" and trader.get("enabled")
        for trader in traders
    )
    print(f"\nmulti_crypto_10 enabled: {multi_crypto_enabled}")

    # Проверяем ML конфигурацию
    ml_config = full_config.get("ml_models", {})
    print(f"\nML models config: {list(ml_config.keys())}")


if __name__ == "__main__":
    asyncio.run(test_config())
