#!/usr/bin/env python3
"""
Финальный анализ и очистка признаков из обучающего файла.
Создает точный список признаков для продакшена с правильным подсчетом.
"""

from exact_training_features import EXACT_TRAINING_FEATURES


def clean_feature_list(features: list) -> list:
    """Очищает список признаков от метаданных и служебных столбцов"""

    # Столбцы, которые не являются признаками (метаданные)
    metadata_columns = {
        "symbol",  # Идентификатор символа
        "datetime",  # Временная метка
        "timestamp",  # Альтернативная временная метка
        "date",  # Дата
        "time",  # Время
        "open",  # Базовые OHLCV данные (если есть в признаках)
        "high",
        "low",
        "close",
        "volume",
        "turnover",
    }

    # Целевые переменные (если есть)
    target_columns = {
        "target",
        "target_15m",
        "target_1h",
        "target_4h",
        "returns_15m",  # Если используется как таргет
        "direction",  # Если есть направление как таргет
        "price_change",  # Если есть изменение цены как таргет
    }

    # Временные/служебные столбцы
    temp_columns = {"temp_", "tmp_", "_temp", "_tmp"}

    cleaned_features = []
    removed_features = []

    for feature in features:
        # Пропускаем метаданные
        if feature in metadata_columns:
            removed_features.append(f"{feature} (metadata)")
            continue

        # Пропускаем целевые переменные
        if feature in target_columns:
            removed_features.append(f"{feature} (target)")
            continue

        # Пропускаем временные столбцы
        if any(temp in feature for temp in temp_columns):
            removed_features.append(f"{feature} (temporary)")
            continue

        # Пропускаем очевидно неправильные признаки
        if feature.startswith("_") or feature.endswith("_"):
            removed_features.append(f"{feature} (invalid name)")
            continue

        cleaned_features.append(feature)

    return cleaned_features, removed_features


def analyze_feature_categories(features: list) -> dict:
    """Анализирует признаки по категориям"""

    categories = {
        "basic": [],  # Базовые признаки (returns, ratios)
        "technical": [],  # Технические индикаторы
        "microstructure": [],  # Микроструктура рынка
        "volume": [],  # Объемные признаки
        "volatility": [],  # Волатильность
        "temporal": [],  # Временные признаки
        "correlation": [],  # Корреляционные признаки
        "momentum": [],  # Моментум
        "trend": [],  # Трендовые признаки
        "risk": [],  # Риск-метрики
        "other": [],  # Остальные
    }

    for feature in features:
        feature_lower = feature.lower()

        # Базовые признаки
        if any(
            word in feature_lower for word in ["returns", "ratio", "position", "spread", "vwap"]
        ):
            categories["basic"].append(feature)
        # Технические индикаторы
        elif any(
            word in feature_lower
            for word in [
                "rsi",
                "macd",
                "sma",
                "ema",
                "bb_",
                "atr",
                "stoch",
                "adx",
                "psar",
                "ichimoku",
                "keltner",
                "donchian",
                "mfi",
                "cci",
                "williams",
                "obv",
                "aroon",
                "roc",
                "trix",
            ]
        ):
            categories["technical"].append(feature)
        # Микроструктура
        elif any(
            word in feature_lower
            for word in [
                "impact",
                "kyle",
                "amihud",
                "toxicity",
                "imbalance",
                "liquidity",
                "illiquidity",
            ]
        ):
            categories["microstructure"].append(feature)
        # Объем
        elif any(
            word in feature_lower
            for word in ["volume", "obv", "cmf", "accumulation", "dollar_volume"]
        ):
            categories["volume"].append(feature)
        # Волатильность
        elif any(word in feature_lower for word in ["vol", "realized", "garch", "squeeze"]):
            categories["volatility"].append(feature)
        # Временные
        elif any(
            word in feature_lower
            for word in ["hour", "day", "month", "weekend", "session", "sin", "cos"]
        ):
            categories["temporal"].append(feature)
        # Корреляция
        elif any(word in feature_lower for word in ["btc", "correlation", "beta", "relative"]):
            categories["correlation"].append(feature)
        # Моментум
        elif any(word in feature_lower for word in ["momentum", "divergence"]):
            categories["momentum"].append(feature)
        # Тренд
        elif any(word in feature_lower for word in ["trend", "uptrend", "downtrend"]):
            categories["trend"].append(feature)
        # Риск
        elif any(
            word in feature_lower for word in ["risk", "leverage", "liquidation", "var", "cvar"]
        ):
            categories["risk"].append(feature)
        else:
            categories["other"].append(feature)

    return categories


def generate_production_config(features: list) -> str:
    """Генерирует конфигурацию для продакшена"""

    categories = analyze_feature_categories(features)

    config = []
    config.append('"""')
    config.append("Точная конфигурация признаков из обучающего файла BOT_AI_V2/ааа.py")
    config.append("Используется для продакшена в точном соответствии с обученной моделью.")
    config.append('"""')
    config.append("")
    config.append("# КРИТИЧНО: Эти признаки должны создаваться В ТОЧНОМ ПОРЯДКЕ!")
    config.append("# Модель была обучена именно на этих признаках в этом порядке.")
    config.append("")
    config.append("PRODUCTION_FEATURES = [")
    for feature in features:
        config.append(f'    "{feature}",')
    config.append("]")
    config.append("")
    config.append(f"# Общее количество: {len(features)} признаков")
    config.append("")

    # Добавляем категории
    config.append("# Признаки по категориям:")
    for category, cat_features in categories.items():
        if cat_features:
            config.append(f"# {category}: {len(cat_features)} признаков")
    config.append("")

    # Детальная разбивка по категориям
    for category, cat_features in categories.items():
        if cat_features:
            category_name = f"{category.upper()}_FEATURES"
            config.append(f"{category_name} = [")
            for feature in cat_features:
                config.append(f'    "{feature}",')
            config.append("]")
            config.append("")

    # Критические формулы
    config.append("# КРИТИЧЕСКИЕ ФОРМУЛЫ (должны быть точно такими же как в обучении):")
    config.append("CRITICAL_FORMULAS = {")
    config.append('    "macd": "macd / close * 100",  # Нормализованный MACD')
    config.append('    "macd_signal": "macd_signal / close * 100",')
    config.append('    "macd_diff": "macd_diff / close * 100",')
    config.append('    "btc_correlation": "window=96, min_periods=50",')
    config.append('    "returns": "np.log(close / close.shift(1))",  # LOG возвраты')
    config.append('    "amihud_illiquidity": "abs(returns) * 1e6 / turnover",  # * 1e6')
    config.append('    "price_impact": "abs(returns) * 100 / log10(dollar_volume + 100)",')
    config.append('    "volume_cumsum_log": "log1p transformation",')
    config.append('    "realized_vol_1h": "rolling(240).std() * sqrt(240)",  # 1h = 240 periods')
    config.append("}")
    config.append("")

    # Конфигурация для inference
    config.append("INFERENCE_CONFIG = {")
    config.append(f'    "expected_features": {len(features)},')
    config.append('    "feature_order_critical": True,')
    config.append('    "normalize_features": True,')
    config.append('    "handle_missing": "forward_fill",')
    config.append('    "min_history_required": 240,  # Для расчета всех индикаторов')
    config.append("}")

    return "\n".join(config)


def main():
    """Основная функция финального анализа"""

    print("🔧 ФИНАЛЬНАЯ ОЧИСТКА И АНАЛИЗ ПРИЗНАКОВ")
    print("=" * 50)

    # Исходный список
    print(f"📊 Исходное количество признаков: {len(EXACT_TRAINING_FEATURES)}")

    # Очистка
    cleaned_features, removed_features = clean_feature_list(EXACT_TRAINING_FEATURES)

    print(f"✅ Очищенное количество признаков: {len(cleaned_features)}")
    print(f"🗑️  Удалено признаков: {len(removed_features)}")

    if removed_features:
        print("\n🗑️  УДАЛЕННЫЕ ПРИЗНАКИ:")
        for feature in removed_features:
            print(f"  - {feature}")

    # Анализ по категориям
    categories = analyze_feature_categories(cleaned_features)

    print("\n📋 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:")
    total_categorized = 0
    for category, features in categories.items():
        if features:
            print(f"  {category:15}: {len(features):3d} признаков")
            total_categorized += len(features)

    print(f"  {'ИТОГО':<15}: {total_categorized:3d} признаков")

    # Генерация конфигурации для продакшена
    production_config = generate_production_config(cleaned_features)

    # Сохранение
    with open("production_features_config.py", "w", encoding="utf-8") as f:
        f.write(production_config)

    # Сохранение простого списка
    with open("final_features_list.txt", "w", encoding="utf-8") as f:
        f.write(f"# Финальный список {len(cleaned_features)} признаков из обучающего файла\n")
        f.write("# КРИТИЧНО: Порядок должен быть сохранен!\n\n")
        for i, feature in enumerate(cleaned_features, 1):
            f.write(f"{i:3d}. {feature}\n")

    print("\n✅ Финальный анализ завершен!")
    print("🐍 Конфигурация для продакшена: production_features_config.py")
    print("📝 Список признаков: final_features_list.txt")
    print(f"📊 ФИНАЛЬНОЕ КОЛИЧЕСТВО ПРИЗНАКОВ: {len(cleaned_features)}")

    # Проверка соответствия ожидаемому количеству
    expected_count = 208  # или 240
    if len(cleaned_features) != expected_count:
        print(
            f"\n⚠️  ВНИМАНИЕ: Найдено {len(cleaned_features)} признаков, ожидалось {expected_count}"
        )
        print("    Необходимо проверить:")
        print("    1. Правильность извлечения признаков из кода")
        print("    2. Соответствие с реально обученной моделью")
        print("    3. Возможно модель была обучена на подмножестве признаков")

    return cleaned_features


if __name__ == "__main__":
    final_features = main()
