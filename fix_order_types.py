#!/usr/bin/env python3
"""
Исправление типов ордеров на рыночные
"""

import os

import yaml

print("🔧 Исправление конфигурации для использования рыночных ордеров...")

# 1. Обновляем system.yaml
system_config_path = "config/system.yaml"

with open(system_config_path, "r") as f:
    config = yaml.safe_load(f)

# Убедимся что используются рыночные ордера
if "trading" not in config:
    config["trading"] = {}

if "order_execution" not in config["trading"]:
    config["trading"]["order_execution"] = {}

# Устанавливаем рыночные ордера
config["trading"]["order_execution"]["use_limit_orders"] = False
config["trading"]["order_execution"]["default_order_type"] = "MARKET"

# Убираем настройки лимитных ордеров
if "limit_order_offset_buy" in config["trading"]["order_execution"]:
    del config["trading"]["order_execution"]["limit_order_offset_buy"]
if "limit_order_offset_sell" in config["trading"]["order_execution"]:
    del config["trading"]["order_execution"]["limit_order_offset_sell"]

# Сохраняем
with open(system_config_path, "w") as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print("✅ system.yaml обновлен")

# 2. Проверяем и обновляем стратегии
strategies_path = "config/strategies/ml_signal.yaml"

if os.path.exists(strategies_path):
    with open(strategies_path, "r") as f:
        strategy_config = yaml.safe_load(f)

    # Убедимся что стратегия использует рыночные ордера
    if "order_type" not in strategy_config:
        strategy_config["order_type"] = "MARKET"
    else:
        strategy_config["order_type"] = "MARKET"

    with open(strategies_path, "w") as f:
        yaml.dump(strategy_config, f, default_flow_style=False, sort_keys=False)

    print("✅ ml_signal.yaml обновлен")

print("\n📊 Текущие настройки:")
print("   - Тип ордеров: MARKET (рыночные)")
print("   - Лимитные ордера: ОТКЛЮЧЕНЫ")
print("\n✅ Конфигурация исправлена!")
print("\n💡 Теперь перезапустите бота для применения изменений")
