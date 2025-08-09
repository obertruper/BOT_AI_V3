#!/usr/bin/env python3

import signal
import sys
from datetime import datetime

import numpy as np
import pandas as pd


def timeout_handler(signum, frame):
    print("TIMEOUT! Процесс завис")
    sys.exit(1)


# Устанавливаем таймаут в 5 секунд
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)

try:
    print("Импортируем модули...")
    from ml.logic.feature_engineering import FeatureEngineer

    print("Создаем данные...")
    dates = pd.date_range(end=datetime.now(), periods=100, freq="15min")
    data = pd.DataFrame(
        {
            "datetime": dates,
            "open": np.random.uniform(45000, 46000, 100),
            "high": np.random.uniform(45500, 46500, 100),
            "low": np.random.uniform(44500, 45500, 100),
            "close": np.random.uniform(45000, 46000, 100),
            "volume": np.random.uniform(100, 1000, 100),
            "symbol": "BTCUSDT",
        }
    )

    print("Создаем FeatureEngineer...")
    fe = FeatureEngineer({})

    print("Вызываем create_features...")
    features = fe.create_features(data)

    print(f"Готово! Результат: {type(features)}")
    if isinstance(features, np.ndarray):
        print(f"Форма: {features.shape}")

except Exception as e:
    print(f"Ошибка: {e}")
    import traceback

    traceback.print_exc()
finally:
    # Отключаем таймер
    signal.alarm(0)

print("Программа завершена")
