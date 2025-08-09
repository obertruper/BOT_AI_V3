#!/usr/bin/env python3

import pickle
from pathlib import Path

import numpy as np

# Проверяем scaler
scaler_path = Path("models/saved/data_scaler.pkl")
print(f"Файл scaler существует: {scaler_path.exists()}")

if scaler_path.exists():
    print("Загружаем scaler...")
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    print(f"Тип scaler: {type(scaler)}")
    print(
        f"n_features_in_: {scaler.n_features_in_ if hasattr(scaler, 'n_features_in_') else 'N/A'}"
    )

    # Тестовые данные
    test_data = np.random.randn(96, 240)  # 96 временных точек, 240 признаков

    print("Пробуем transform...")
    try:
        result = scaler.transform(test_data)
        print(f"Успешно! Результат: {result.shape}")
    except Exception as e:
        print(f"Ошибка: {e}")

print("Тест завершен")
