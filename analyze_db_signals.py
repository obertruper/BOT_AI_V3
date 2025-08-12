#!/usr/bin/env python3
"""Анализ сигналов из базы данных для проверки confidence"""

import asyncio

import numpy as np
from sqlalchemy import desc, select

from database.connections import get_async_db
from database.models.signal import Signal


async def analyze():
    """Анализ сигналов из БД"""

    print("=" * 80)
    print("АНАЛИЗ CONFIDENCE ИЗ БАЗЫ ДАННЫХ")
    print("=" * 80)

    async with get_async_db() as db:
        # Получаем последние 100 ML сигналов
        result = await db.execute(
            select(Signal)
            .where(Signal.strategy_name == "PatchTST_ML")
            .order_by(desc(Signal.created_at))
            .limit(100)
        )
        signals = result.scalars().all()

        if not signals:
            print("Нет ML сигналов в базе данных")
            return

        print(f"\nНайдено {len(signals)} ML сигналов")
        print("-" * 40)

        # Собираем статистику
        confidence_values = []
        strength_values = []
        symbols_data = {}

        for signal in signals:
            confidence_values.append(signal.confidence)
            strength_values.append(signal.strength)

            if signal.symbol not in symbols_data:
                symbols_data[signal.symbol] = {
                    "confidences": [],
                    "strengths": [],
                    "types": [],
                }

            symbols_data[signal.symbol]["confidences"].append(signal.confidence)
            symbols_data[signal.symbol]["strengths"].append(signal.strength)
            symbols_data[signal.symbol]["types"].append(signal.signal_type.value)

        # Общая статистика
        conf_array = np.array(confidence_values)
        strength_array = np.array(strength_values)

        print("\n📊 ОБЩАЯ СТАТИСТИКА:")
        print("Confidence:")
        print(f"  Среднее: {conf_array.mean():.6f}")
        print(f"  Стд. откл.: {conf_array.std():.6f}")
        print(f"  Минимум: {conf_array.min():.6f}")
        print(f"  Максимум: {conf_array.max():.6f}")
        print(f"  Медиана: {np.median(conf_array):.6f}")

        print("\nStrength:")
        print(f"  Среднее: {strength_array.mean():.6f}")
        print(f"  Стд. откл.: {strength_array.std():.6f}")
        print(f"  Минимум: {strength_array.min():.6f}")
        print(f"  Максимум: {strength_array.max():.6f}")

        # Гистограмма confidence значений
        print("\n📈 РАСПРЕДЕЛЕНИЕ CONFIDENCE:")
        bins = [0.55, 0.58, 0.59, 0.595, 0.60, 0.605, 0.61, 0.62, 0.65, 1.0]
        hist, _ = np.histogram(conf_array, bins=bins)

        for i, count in enumerate(hist):
            if count > 0:
                print(f"  [{bins[i]:.3f} - {bins[i + 1]:.3f}]: {'█' * count} ({count})")

        # Проверяем концентрацию около 0.60
        near_0_60 = np.abs(conf_array - 0.60) < 0.005
        pct_near = near_0_60.sum() / len(conf_array) * 100

        print(f"\n⚠️ {pct_near:.1f}% значений в пределах ±0.005 от 0.60")

        if pct_near > 50:
            print("\n🚨 ПРОБЛЕМА ПОДТВЕРЖДЕНА!")
            print(
                "Большинство confidence значений сконцентрированы точно на пороге 0.60"
            )

        # Анализ по символам
        print("\n📊 СТАТИСТИКА ПО СИМВОЛАМ:")
        for symbol, data in symbols_data.items():
            conf = np.array(data["confidences"])
            print(f"\n{symbol}:")
            print(f"  Сигналов: {len(conf)}")
            print(f"  Confidence: {conf.mean():.6f} ± {conf.std():.6f}")
            print(
                f"  Типы: LONG={data['types'].count('LONG')}, SHORT={data['types'].count('SHORT')}"
            )

        # Детальный вывод последних 10 сигналов
        print("\n📋 ПОСЛЕДНИЕ 10 СИГНАЛОВ:")
        print("-" * 80)
        for signal in signals[:10]:
            print(
                f"{signal.created_at.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"{signal.symbol:12} | {signal.signal_type.value:5} | "
                f"Conf: {signal.confidence:.6f} | Str: {signal.strength:.6f}"
            )

        # Проверяем формулу
        # combined_confidence = signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2
        print("\n🔍 АНАЛИЗ ФОРМУЛЫ CONFIDENCE:")
        print(
            "combined_confidence = signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2"
        )

        # Если все confidence ≈ 0.60, проверяем возможные комбинации
        if pct_near > 50:
            print("\nВозможные комбинации для confidence ≈ 0.60:")

            # Вариант 1: signal_strength = 1.0, model_conf = 0.35, risk = 0.30
            calc1 = 1.0 * 0.4 + 0.35 * 0.4 + 0.70 * 0.2
            print(f"1. strength=1.00, model_conf=0.35, (1-risk)=0.70 → {calc1:.3f}")

            # Вариант 2: signal_strength = 0.75, model_conf = 0.50, risk = 0.30
            calc2 = 0.75 * 0.4 + 0.50 * 0.4 + 0.70 * 0.2
            print(f"2. strength=0.75, model_conf=0.50, (1-risk)=0.70 → {calc2:.3f}")

            # Вариант 3: signal_strength = 0.50, model_conf = 0.65, risk = 0.30
            calc3 = 0.50 * 0.4 + 0.65 * 0.4 + 0.70 * 0.2
            print(f"3. strength=0.50, model_conf=0.65, (1-risk)=0.70 → {calc3:.3f}")

            print("\n💡 ВЫВОД:")
            print("Model_confidence скорее всего фиксирован или вычисляется так,")
            print("что компенсирует изменения signal_strength для получения ~0.60")


if __name__ == "__main__":
    asyncio.run(analyze())
