#!/usr/bin/env python3
"""
Финальное сравнение:
1. Что ожидает модель (features_240.py)
2. Что было при обучении (ааа.py)
3. Что генерируется сейчас (feature_engineering_v2.py)

Цель: точное понимание несоответствий
"""

import re

from ml.config.features_240 import REQUIRED_FEATURES_240


def analyze_training_file():
    """Анализирует обучающий файл и возвращает список признаков"""
    with open("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/BOT_AI_V2/ааа.py") as f:
        content = f.read()

    # Ищем все присваивания df['feature'] =
    features = re.findall(r"df\['([^']+)'\]\s*=", content)
    return list(set(features))


def analyze_current_implementation():
    """Анализирует текущую реализацию"""
    # Из REQUIRED_FEATURES_240
    return REQUIRED_FEATURES_240


def main():
    print("=" * 80)
    print("🔍 ФИНАЛЬНОЕ СРАВНЕНИЕ ПРИЗНАКОВ")
    print("=" * 80)

    # 1. Что ожидает модель
    model_expects = REQUIRED_FEATURES_240
    print(f"\n1️⃣ МОДЕЛЬ ОЖИДАЕТ (features_240.py): {len(model_expects)} признаков")

    # 2. Что было при обучении
    training_features = analyze_training_file()
    print(f"\n2️⃣ ПРИ ОБУЧЕНИИ (ааа.py): {len(training_features)} признаков")

    # 3. Найдем критические различия
    print("\n3️⃣ КРИТИЧЕСКИЕ РАЗЛИЧИЯ:")

    # RSI
    rsi_in_model = [f for f in model_expects if "rsi" in f.lower()]
    rsi_in_training = [f for f in training_features if "rsi" in f.lower()]
    print("\n📊 RSI:")
    print(f"  Модель ожидает: {rsi_in_model[:5]}")
    print(f"  При обучении: {rsi_in_training[:5]}")

    # BTC features
    btc_in_model = [f for f in model_expects if "btc" in f.lower()]
    btc_in_training = [f for f in training_features if "btc" in f.lower()]
    print("\n📊 BTC features:")
    print(f"  Модель ожидает: {btc_in_model}")
    print(f"  При обучении: {btc_in_training}")

    # ETH features
    eth_in_model = [f for f in model_expects if "eth" in f.lower()]
    eth_in_training = [f for f in training_features if "eth" in f.lower()]
    print("\n📊 ETH features:")
    print(f"  Модель ожидает: {eth_in_model}")
    print(f"  При обучении: {eth_in_training}")

    # Returns
    returns_in_model = [f for f in model_expects if "returns" in f.lower()]
    returns_in_training = [f for f in training_features if "returns" in f.lower()]
    print("\n📊 Returns:")
    print(f"  Модель ожидает: {len(returns_in_model)} returns признаков")
    print(f"  При обучении: {len(returns_in_training)} returns признаков")

    # 4. Вывод
    print("\n" + "=" * 80)
    print("📌 ГЛАВНАЯ ПРОБЛЕМА:")
    print("=" * 80)

    if len(eth_in_model) > 0 and len(eth_in_training) == 0:
        print("❌ Модель ожидает ETH признаки, но при обучении их НЕ БЫЛО!")
        print("   РЕШЕНИЕ: Заполнить ETH признаки заглушками (0.5)")

    if len(rsi_in_model) != len(rsi_in_training):
        print("❌ Несоответствие количества RSI признаков!")
        print(f"   Модель ожидает: {len(rsi_in_model)}, при обучении: {len(rsi_in_training)}")

    if "btc_correlation" in training_features:
        print("✅ BTC correlation была при обучении")
        print("   ВАЖНО: Использовать window=96, min_periods=50")

    print("\n📝 РЕКОМЕНДАЦИЯ:")
    print("Модель была обучена с ДРУГИМ набором признаков, чем указано в features_240.py")
    print("Нужно либо:")
    print("1. Переобучить модель с правильными признаками")
    print("2. Адаптировать генерацию признаков под обучающий набор")
    print("3. Создать маппинг между ожидаемыми и фактическими признаками")


if __name__ == "__main__":
    main()
