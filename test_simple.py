#!/usr/bin/env python3


print("Python запущен")

try:
    from ml.logic.feature_engineering import FeatureEngineer

    print("FeatureEngineer импортирован")

    import pandas as pd

    # Простые данные
    data = pd.DataFrame(
        {
            "open": [45000.0, 45100.0, 45200.0],
            "high": [45500.0, 45600.0, 45700.0],
            "low": [44500.0, 44600.0, 44700.0],
            "close": [45200.0, 45300.0, 45400.0],
            "volume": [100.0, 200.0, 300.0],
        }
    )

    print(f"Данные созданы: {data.shape}")

    fe = FeatureEngineer({})
    print("FeatureEngineer создан")

    # Тестируем отдельные методы
    print("Тестируем _calculate_price_features...")
    try:
        result = fe._calculate_price_features(data)
        print(
            f"Результат: {type(result)}, длина: {len(result) if hasattr(result, '__len__') else 'N/A'}"
        )
    except Exception as e:
        print(f"Ошибка в _calculate_price_features: {e}")
        import traceback

        traceback.print_exc()

except Exception as e:
    print(f"Общая ошибка: {e}")
    import traceback

    traceback.print_exc()

print("Тест завершен")
