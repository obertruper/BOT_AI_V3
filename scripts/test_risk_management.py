#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки улучшенной системы управления рисками
"""

import asyncio
import os
import sys

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.config_manager import ConfigManager
from risk_management.manager import RiskManager


async def test_risk_management():
    """Тестирование системы управления рисками"""

    print("🚀 Тестирование улучшенной системы управления рисками")
    print("=" * 60)

    # Инициализация ConfigManager
    print("1. Инициализация ConfigManager...")
    config_manager = ConfigManager("config/system.yaml")
    await config_manager.initialize()

    # Проверка загрузки конфигурации
    print("2. Проверка загрузки конфигурации...")
    risk_config = config_manager.get_risk_management_config()
    if risk_config:
        print("✅ Конфигурация риск-менеджмента загружена")
        print(f"   - Включен: {risk_config.get('enabled', False)}")
        print(f"   - Риск на сделку: {risk_config.get('risk_per_trade', 0)}")
        print(f"   - Максимум позиций: {risk_config.get('max_positions', 0)}")
    else:
        print("❌ Конфигурация риск-менеджмента не загружена")
        return

    # Создание RiskManager
    print("\n3. Создание RiskManager...")
    risk_manager = RiskManager(risk_config)
    print("✅ RiskManager создан")
    print(f"   - Включен: {risk_manager.enabled}")
    print(f"   - Текущий профиль: {risk_manager.current_profile}")

    # Тестирование профилей риска
    print("\n4. Тестирование профилей риска...")
    profiles = ["standard", "conservative", "very_conservative"]
    for profile in profiles:
        profile_config = risk_manager.get_risk_profile(profile)
        if profile_config:
            print(
                f"   {profile}: множитель {profile_config.get('risk_multiplier', 1.0)}"
            )

    # Тестирование категорий активов
    print("\n5. Тестирование категорий активов...")
    test_symbols = ["BTCUSDT", "DOGEUSDT", "ETHUSDT", "PEPEUSDT"]
    for symbol in test_symbols:
        category = risk_manager.get_asset_category(symbol)
        if category:
            print(f"   {symbol}: множитель {category.get('risk_multiplier', 1.0)}")

    # Тестирование расчета размера позиции
    print("\n6. Тестирование расчета размера позиции...")
    test_signal = {
        "symbol": "BTCUSDT",
        "side": "buy",
        "leverage": 5,
        "position_size": 10.0,  # Добавляем размер позиции
        "ml_predictions": {"profit_probability": 0.7, "loss_probability": 0.3},
    }

    position_size = risk_manager.calculate_position_size(test_signal)
    print(f"   Размер позиции для BTCUSDT: ${position_size}")

    # Тестирование с разными профилями
    for profile in profiles:
        risk_manager.set_risk_profile(profile)
        position_size = risk_manager.calculate_position_size(test_signal)
        print(f"   {profile} профиль: ${position_size}")

    # Тестирование проверки рисков сигнала
    print("\n7. Тестирование проверки рисков сигнала...")
    risk_check = await risk_manager.check_signal_risk(test_signal)
    print(f"   Проверка рисков: {'✅ Прошла' if risk_check else '❌ Не прошла'}")

    # Тестирование глобальных рисков
    print("\n8. Тестирование глобальных рисков...")
    global_risk = await risk_manager.check_global_risks()
    print(
        f"   Глобальные риски: {'⚠️ Требует действий' if global_risk.requires_action else '✅ В норме'}"
    )
    if global_risk.requires_action:
        print(f"   Действие: {global_risk.action}")
        print(f"   Сообщение: {global_risk.message}")

    # Тестирование ML-интеграции
    print("\n9. Тестирование ML-интеграции...")
    if risk_manager.ml_enabled:
        print("   ✅ ML-интеграция включена")
        ml_config = config_manager.get_ml_integration_config()
        print(f"   Пороги: {ml_config.get('thresholds', {})}")
    else:
        print("   ⚠️ ML-интеграция отключена")

    # Тестирование мониторинга
    print("\n10. Тестирование мониторинга...")
    monitoring_config = config_manager.get_monitoring_config()
    if monitoring_config:
        print(
            f"   Ожидаемая точность покупки: {monitoring_config.get('expected_buy_accuracy', 0)}%"
        )
        print(
            f"   Ожидаемая точность продажи: {monitoring_config.get('expected_sell_accuracy', 0)}%"
        )
        print(
            f"   Порог алерта: {monitoring_config.get('accuracy_alert_threshold', 0)}%"
        )

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено успешно!")
    print("\n📊 Преимущества улучшенной системы:")
    print("   • Гибкие профили риска (standard, conservative, very_conservative)")
    print("   • Категории активов (мемкоины vs стабильные монеты)")
    print("   • ML-интеграция для корректировки рисков")
    print("   • Улучшенный SL/TP с трейлингом и защитой прибыли")
    print("   • Мониторинг производительности ML-модели")
    print("   • Автоматические алерты при отклонениях")


if __name__ == "__main__":
    asyncio.run(test_risk_management())
