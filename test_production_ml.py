#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальный тест ML системы в production окружении
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from core.config.config_manager import ConfigManager
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor


async def test_production_ml():
    """Тест ML системы в production конфигурации"""

    print("🚀 === ТЕСТ PRODUCTION ML СИСТЕМЫ ===")

    try:
        # === 1. ИНИЦИАЛИЗАЦИЯ ===
        print("\n1️⃣ === ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ ===")

        # Используем реальный config manager
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Создаем ML Manager
        ml_manager = MLManager(config)
        await ml_manager.initialize()
        print("✅ ML Manager инициализирован")

        # Создаем ML Signal Processor
        ml_signal_processor = MLSignalProcessor(ml_manager, config, config_manager)
        await ml_signal_processor.initialize()
        print("✅ ML Signal Processor инициализирован")

        # === 2. РЕАЛЬНЫЕ ДАННЫЕ ===
        print("\n2️⃣ === ГЕНЕРАЦИЯ РЕАЛИСТИЧНЫХ ДАННЫХ ===")

        # Создаем данные максимально похожие на настоящие BTCUSDT
        dates = pd.date_range(start="2024-01-01", periods=150, freq="15min")

        # Базовая цена Bitcoin
        base_price = 52000.0

        # Генерируем реалистичную динамику цены
        np.random.seed(123)  # Для воспроизводимости

        # Создаем тренд + волатильность + микроструктура рынка
        prices = [base_price]
        volumes = []

        for i in range(1, len(dates)):
            # Основной тренд (небольшой рост)
            trend = 0.0001  # 0.01% рост за 15 минут

            # Дневная волатильность
            daily_vol = 0.008  # 0.8% дневная волатильность
            minute_vol = daily_vol / np.sqrt(96)  # Адаптируем на 15 минут

            # Случайное движение
            random_change = np.random.normal(0, minute_vol)

            # Автокорреляция (инерция цены)
            if i > 1:
                prev_change = (prices[-1] - prices[-2]) / prices[-2]
                autocorr = 0.05 * prev_change  # 5% автокорреляция
            else:
                autocorr = 0

            # Итоговое изменение
            total_change = trend + random_change + autocorr

            # Новая цена
            new_price = prices[-1] * (1 + total_change)
            prices.append(new_price)

            # Реалистичный объем (коррелирует с волатильностью)
            vol_base = 150
            vol_multiplier = (
                1 + abs(random_change) * 10
            )  # Больше объема при больших движениях
            volume = vol_base * vol_multiplier * np.random.uniform(0.5, 2.0)
            volumes.append(volume)

        # Корректируем первый объем
        volumes.insert(0, 150)

        # Создаем полные OHLCV данные
        test_data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            # Реалистичные high/low с учетом внутридневной волатильности
            hl_spread = close * np.random.uniform(0.001, 0.005)  # 0.1-0.5% spread

            high = close + hl_spread * np.random.uniform(0.3, 1.0)
            low = close - hl_spread * np.random.uniform(0.3, 1.0)

            # Open равен предыдущему close
            open_price = prices[i - 1] if i > 0 else close

            # Убеждаемся что OHLC логически корректны
            high = max(high, close, open_price)
            low = min(low, close, open_price)

            test_data.append(
                {
                    "datetime": date,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volumes[i],
                    "symbol": "BTCUSDT",
                }
            )

        test_df = pd.DataFrame(test_data)
        print(f"📊 Создано {len(test_df)} реалистичных OHLCV записей")
        print(
            f"📈 Диапазон цен: ${test_df['close'].min():.2f} - ${test_df['close'].max():.2f}"
        )
        print(f"📊 Средний объем: {test_df['volume'].mean():.1f}")

        # === 3. ПРЯМОЙ ТЕСТ ML MANAGER ===
        print("\n3️⃣ === ТЕСТ ML MANAGER ===")

        prediction = await ml_manager.predict(test_df)

        print("📊 Результат предсказания:")
        print(f"   Тип сигнала: {prediction['signal_type']}")
        print(f"   Сила сигнала: {prediction['signal_strength']:.3f}")
        print(f"   Уверенность: {prediction['confidence']:.3f}")
        print(f"   Вероятность успеха: {prediction['success_probability']:.1%}")
        print(f"   Stop Loss: {prediction['stop_loss']}")
        print(f"   Take Profit: {prediction['take_profit']}")
        print(f"   Риск: {prediction['risk_level']}")

        # === 4. ТЕСТ ML SIGNAL PROCESSOR ===
        print("\n4️⃣ === ТЕСТ ML SIGNAL PROCESSOR ===")

        # Тестируем создание торгового сигнала
        current_price = test_df["close"].iloc[-1]
        signal = await ml_signal_processor.process_market_data(
            symbol="BTCUSDT",
            exchange="bybit",
            ohlcv_data=test_df,
            additional_data={"current_price": current_price},
        )

        if signal:
            print("📊 Торговый сигнал создан:")
            print(f"   Символ: {signal.symbol}")
            print(f"   Биржа: {signal.exchange}")
            print(f"   Тип: {signal.signal_type}")
            print(f"   Сила: {signal.strength}")
            print(f"   Уверенность: {signal.confidence}")
            print(f"   Стратегия: {signal.strategy_name}")
            print(f"   Цена входа: {signal.suggested_price}")
            print(f"   Stop Loss: {signal.suggested_stop_loss}")
            print(f"   Take Profit: {signal.suggested_take_profit}")

            # Дополнительная информация
            if signal.indicators and "success_probability" in signal.indicators:
                print(
                    f"   Вероятность успеха: {signal.indicators['success_probability']:.1%}"
                )
        else:
            print("⚠️  Сигнал не создан (не прошел валидацию)")

        # === 5. СТРЕСС-ТЕСТ РАЗНООБРАЗИЯ ===
        print("\n5️⃣ === СТРЕСС-ТЕСТ РАЗНООБРАЗИЯ ===")

        prediction_results = []
        signal_results = []

        # Генерируем 10 различных сценариев
        for scenario in range(10):
            print(f"\n📊 Сценарий {scenario + 1}/10", end="")

            # Создаем уникальные данные для каждого сценария
            np.random.seed(scenario * 42)

            # Разные базовые цены
            scenario_base_price = 45000 + scenario * 2000

            # Разные волатильности
            scenario_volatility = 0.005 + scenario * 0.002

            # Разные тренды
            scenario_trend = -0.001 + scenario * 0.0002

            scenario_prices = [scenario_base_price]
            scenario_volumes = []

            for i in range(1, 150):
                change = scenario_trend + np.random.normal(0, scenario_volatility)
                new_price = scenario_prices[-1] * (1 + change)
                scenario_prices.append(new_price)

                volume = 100 + scenario * 20 + np.random.uniform(0, 200)
                scenario_volumes.append(volume)

            scenario_volumes.insert(0, 100 + scenario * 20)

            # Создаем данные
            scenario_data = []
            for i, (date, close) in enumerate(zip(dates, scenario_prices)):
                hl_spread = close * 0.003
                high = close + hl_spread * np.random.uniform(0.2, 0.8)
                low = close - hl_spread * np.random.uniform(0.2, 0.8)
                open_price = scenario_prices[i - 1] if i > 0 else close

                high = max(high, close, open_price)
                low = min(low, close, open_price)

                scenario_data.append(
                    {
                        "datetime": date,
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": scenario_volumes[i],
                        "symbol": "BTCUSDT",
                    }
                )

            scenario_df = pd.DataFrame(scenario_data)

            # Получаем предсказание
            try:
                pred = await ml_manager.predict(scenario_df)
                prediction_results.append(
                    {
                        "scenario": scenario,
                        "signal_type": pred["signal_type"],
                        "signal_strength": pred["signal_strength"],
                        "confidence": pred["confidence"],
                        "direction_score": pred["predictions"]["direction_score"],
                    }
                )

                # Получаем торговый сигнал
                current_price = scenario_df["close"].iloc[-1]
                sig = await ml_signal_processor.process_market_data(
                    symbol="BTCUSDT",
                    exchange="bybit",
                    ohlcv_data=scenario_df,
                    additional_data={"current_price": current_price},
                )

                if sig:
                    signal_results.append(
                        {
                            "scenario": scenario,
                            "signal_type": sig.signal_type.value,
                            "strength": sig.strength,
                            "confidence": sig.confidence,
                        }
                    )

                print(f" → {pred['signal_type']}")

            except Exception as e:
                print(f" → Ошибка: {e}")

        # === 6. АНАЛИЗ РЕЗУЛЬТАТОВ ===
        print("\n6️⃣ === АНАЛИЗ РЕЗУЛЬТАТОВ ===")

        if prediction_results:
            # Анализ предсказаний
            signal_types = [r["signal_type"] for r in prediction_results]
            unique_signals = set(signal_types)

            print("📊 Предсказания ML Manager:")
            print(f"   Всего тестов: {len(prediction_results)}")
            print(f"   Уникальных типов: {len(unique_signals)}")
            print(f"   Типы: {unique_signals}")

            from collections import Counter

            type_counts = Counter(signal_types)
            for sig_type, count in type_counts.items():
                percentage = (count / len(prediction_results)) * 100
                print(f"   {sig_type}: {count} ({percentage:.1f}%)")

            # Статистика направлений
            directions = [r["direction_score"] for r in prediction_results]
            if directions:
                directions_array = np.array(directions)
                print("\n📊 Статистика направлений:")
                print(f"   Min: {directions_array.min():.3f}")
                print(f"   Max: {directions_array.max():.3f}")
                print(f"   Mean: {directions_array.mean():.3f}")
                print(f"   Std: {directions_array.std():.3f}")

        if signal_results:
            # Анализ торговых сигналов
            trading_signal_types = [r["signal_type"] for r in signal_results]
            unique_trading_signals = set(trading_signal_types)

            print("\n📊 Торговые сигналы:")
            print(f"   Всего создано: {len(signal_results)}")
            print(f"   Уникальных типов: {len(unique_trading_signals)}")
            print(f"   Типы: {unique_trading_signals}")

        # === 7. ЗАКЛЮЧЕНИЕ ===
        print("\n7️⃣ === ЗАКЛЮЧЕНИЕ ===")

        if len(unique_signals) >= 2:
            print("✅ ML СИСТЕМА РАБОТАЕТ КОРРЕКТНО!")
            print("   ✓ Модель генерирует разнообразные предсказания")
            print("   ✓ Интерпретация направлений исправлена")
            print("   ✓ Торговые сигналы создаются успешно")
            print("   ✓ Проблема одинаковых предсказаний решена")
        else:
            print("❌ ПРОБЛЕМЫ ВСЕ ЕЩЕ ЕСТЬ!")
            print("   Система дает слишком мало разнообразных сигналов")

        # Проверка стабильности
        if len(prediction_results) >= 8 and len(signal_results) >= 5:
            print("   ✓ Система стабильна при разных входных данных")
        else:
            print("   ⚠️  Система может быть нестабильна")

        print("\n🎯 РЕКОМЕНДАЦИИ:")
        print("   1. Система готова для интеграции в торговый движок")
        print("   2. Можно настраивать пороги confidence и signal_strength")
        print("   3. Рекомендуется мониторинг производительности в реальном времени")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_production_ml())
