#!/usr/bin/env python3
"""
Тест для воспроизведения ошибки sqrt
"""

import asyncio
import traceback

import numpy as np
import pandas as pd


async def test_sqrt_error():
    """Тестируем возможные причины ошибки sqrt"""

    print("🔍 Тестируем возможные причины ошибки sqrt...")

    # Создаем тестовые данные как в реальной системе
    dates = pd.date_range(start="2024-01-01", periods=500, freq="15min")

    # Тестовые OHLCV данные
    np.random.seed(42)
    close_prices = 50000 + np.cumsum(np.random.randn(500) * 100)

    df = pd.DataFrame(
        {
            "datetime": dates,
            "open": close_prices * (1 + np.random.randn(500) * 0.001),
            "high": close_prices * (1 + np.abs(np.random.randn(500)) * 0.002),
            "low": close_prices * (1 - np.abs(np.random.randn(500)) * 0.002),
            "close": close_prices,
            "volume": np.random.rand(500) * 1000000,
            "symbol": "BTCUSDT",
        }
    )

    print(f"✅ Создан тестовый DataFrame: {df.shape}")

    # Тест 1: Базовые операции с sqrt
    print("\n🧪 Тест 1: Базовые numpy sqrt операции")
    try:
        returns = df["close"].pct_change()
        vol_test = returns.rolling(20).std() * np.sqrt(20)
        print(f"✅ Тест 1 прошел: {type(vol_test)}, NaN count: {vol_test.isna().sum()}")
    except Exception as e:
        print(f"❌ Тест 1 FAILED: {e}")
        traceback.print_exc()

    # Тест 2: Операции с NaN значениями
    print("\n🧪 Тест 2: Операции с NaN")
    try:
        df_with_nan = df.copy()
        df_with_nan.loc[10:15, "close"] = np.nan
        returns_nan = df_with_nan["close"].pct_change()
        vol_test_nan = returns_nan.rolling(20).std() * np.sqrt(20)
        print(f"✅ Тест 2 прошел: NaN count: {vol_test_nan.isna().sum()}")
    except Exception as e:
        print(f"❌ Тест 2 FAILED: {e}")
        traceback.print_exc()

    # Тест 3: Rolling apply с lambda
    print("\n🧪 Тест 3: Rolling apply с lambda и sqrt")
    try:
        returns = df["close"].pct_change()
        garch_vol = returns.rolling(20).apply(
            lambda x: np.sqrt(0.94 * x.var() + 0.06 * x.iloc[-1] ** 2) if len(x) > 0 else 0
        )
        print(f"✅ Тест 3 прошел: {type(garch_vol)}, NaN count: {garch_vol.isna().sum()}")
    except Exception as e:
        print(f"❌ Тест 3 FAILED: {e}")
        traceback.print_exc()

    # Тест 4: Операции с пустыми сериями
    print("\n🧪 Тест 4: Операции с пустыми сериями")
    try:
        empty_series = pd.Series([], dtype=float)
        empty_vol = empty_series.rolling(20).std() * np.sqrt(20)
        print(f"✅ Тест 4 прошел: {type(empty_vol)}, length: {len(empty_vol)}")
    except Exception as e:
        print(f"❌ Тест 4 FAILED: {e}")
        traceback.print_exc()

    # Тест 5: Проблема с типами данных
    print("\n🧪 Тест 5: Проблемы с типами данных")
    try:
        # Создаем Series с разными типами
        mixed_series = pd.Series([1.0, 2.0, "3.0", 4.0])
        numeric_series = pd.to_numeric(mixed_series, errors="coerce")
        vol_mixed = numeric_series.rolling(2).std() * np.sqrt(2)
        print(f"✅ Тест 5 прошел: {type(vol_mixed)}, NaN count: {vol_mixed.isna().sum()}")
    except Exception as e:
        print(f"❌ Тест 5 FAILED: {e}")
        traceback.print_exc()

    # Тест 6: Попробуем воспроизвести точную ошибку
    print("\n🧪 Тест 6: Попытка воспроизвести ошибку 'loop of ufunc'")
    try:
        # Создаем условия, которые могут привести к ошибке
        test_val = 4.0  # float

        # Это должно работать
        result1 = np.sqrt(test_val)
        print(f"np.sqrt(float): {result1}")

        # Попробуем разные способы, которые могут дать ошибку
        test_array = np.array([test_val])

        # Возможно, проблема в применении ufunc к неправильному типу
        # Попробуем создать ситуацию с ufunc

        def bad_sqrt_func(x):
            # Если x это float, и мы пытаемся вызвать x.sqrt()
            try:
                return x.sqrt()  # Это должно дать ошибку для float
            except AttributeError as e:
                print(f"AttributeError: {e}")
                return np.sqrt(x)

        result6 = bad_sqrt_func(test_val)
        print(f"✅ Тест 6 прошел: {result6}")

    except Exception as e:
        print(f"❌ Тест 6 FAILED: {e}")
        traceback.print_exc()

    print("\n✅ Тестирование завершено")


if __name__ == "__main__":
    asyncio.run(test_sqrt_error())
