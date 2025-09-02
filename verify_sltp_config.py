#!/usr/bin/env python3
"""
Проверка загрузки конфигурации SL/TP
"""

import yaml
from pathlib import Path

# Загружаем конфигурацию
config_path = Path("config/config.yaml")
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

print("=" * 80)
print("ПРОВЕРКА КОНФИГУРАЦИИ SL/TP")
print("=" * 80)

# Проверяем enhanced_sltp
enhanced_sltp = config.get('enhanced_sltp', {})
initial = enhanced_sltp.get('initial', {})

print("\n📋 enhanced_sltp.initial:")
print(f"  stop_loss_percent_min: {initial.get('stop_loss_percent_min')}%")
print(f"  stop_loss_percent_max: {initial.get('stop_loss_percent_max')}%")
print(f"  take_profit_percent_min: {initial.get('take_profit_percent_min')}%")
print(f"  take_profit_percent_max: {initial.get('take_profit_percent_max')}%")

# Проверяем trading
trading = config.get('trading', {})
print("\n📋 trading:")
print(f"  default_stop_loss: {trading.get('default_stop_loss')}")
print(f"  default_take_profit: {trading.get('default_take_profit')}")
print(f"  stop_loss_percentage: {trading.get('stop_loss_percentage')}")
print(f"  take_profit_percentage: {trading.get('take_profit_percentage')}")

# Проверяем partial_take_profit
partial_tp = enhanced_sltp.get('partial_take_profit', {})
print("\n📋 partial_take_profit:")
print(f"  enabled: {partial_tp.get('enabled')}")
if partial_tp.get('levels'):
    print("  levels:")
    for level in partial_tp['levels']:
        print(f"    - {level['percent']}% -> закрыть {level['close_ratio']*100}%")

# Проверяем profit_protection
profit_protection = enhanced_sltp.get('profit_protection', {})
print("\n📋 profit_protection:")
print(f"  enabled: {profit_protection.get('enabled')}")
print(f"  breakeven_percent: {profit_protection.get('breakeven_percent')}%")

# Проверяем trailing_stop
trailing = enhanced_sltp.get('trailing_stop', {})
print("\n📋 trailing_stop:")
print(f"  enabled: {trailing.get('enabled')}")
print(f"  activation_percent: {trailing.get('activation_percent')}%")
print(f"  step_percent: {trailing.get('step_percent')}%")

print("\n" + "=" * 80)
print("✅ Конфигурация загружена корректно")
print("=" * 80)