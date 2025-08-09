#!/usr/bin/env python3
"""
Визуализация работы ML системы оценки сигналов
"""

import asyncio
import sys
from pathlib import Path

from colorama import Fore, Style, init

sys.path.append(str(Path(__file__).parent))

import pandas as pd

from database.connections.postgres import AsyncPGPool
from ml.ml_manager import MLManager

# Инициализация colorama для цветного вывода
init()


def print_header(text):
    """Печатает заголовок."""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text:^60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")


def print_signal(signal_type, confidence, strength):
    """Печатает сигнал с цветом."""
    colors = {"LONG": Fore.GREEN, "SHORT": Fore.RED, "NEUTRAL": Fore.YELLOW}
    color = colors.get(signal_type, Fore.WHITE)

    print(f"{color}Signal: {signal_type}{Style.RESET_ALL}")
    print(f"Confidence: {confidence:.1%}")
    print(f"Strength: {strength:.3f}")


def visualize_directions(directions, probabilities):
    """Визуализирует направления по таймфреймам."""
    timeframes = ["15m", "1h", "4h", "12h"]
    symbols = {0: "🔴 SHORT", 1: "🟡 NEUTRAL", 2: "🟢 LONG"}

    print("\nПредсказания по таймфреймам:")
    print("-" * 50)

    for i, (tf, dir_idx, probs) in enumerate(
        zip(timeframes, directions, probabilities)
    ):
        symbol = symbols[dir_idx]

        # Визуализация вероятностей
        bar_width = 30
        bars = []
        for j, prob in enumerate(probs):
            bar_len = int(prob * bar_width)
            if j == 0:  # SHORT
                bars.append(f"{Fore.RED}{'█' * bar_len}{Style.RESET_ALL}")
            elif j == 1:  # NEUTRAL
                bars.append(f"{Fore.YELLOW}{'█' * bar_len}{Style.RESET_ALL}")
            else:  # LONG
                bars.append(f"{Fore.GREEN}{'█' * bar_len}{Style.RESET_ALL}")

        print(f"{tf:>4}: {symbol} | S:{probs[0]:.2f} N:{probs[1]:.2f} L:{probs[2]:.2f}")


def calculate_weighted_decision(directions, weights):
    """Визуализирует процесс взвешенного решения."""
    print("\nПроцесс принятия решения:")
    print("-" * 50)

    weighted_sum = 0
    for i, (d, w) in enumerate(zip(directions, weights)):
        contribution = d * w
        weighted_sum += contribution
        print(f"Таймфрейм {i + 1}: {d} × {w:.1f} = {contribution:.2f}")

    print(f"\nВзвешенная сумма: {weighted_sum:.2f}")

    if weighted_sum < 0.5:
        decision = "SHORT"
        color = Fore.RED
    elif weighted_sum > 1.5:
        decision = "LONG"
        color = Fore.GREEN
    else:
        decision = "NEUTRAL"
        color = Fore.YELLOW

    print(f"Решение: {color}{decision}{Style.RESET_ALL}")

    return weighted_sum, decision


async def visualize_ml_system():
    """Визуализирует работу ML системы."""

    print_header("ВИЗУАЛИЗАЦИЯ ML СИСТЕМЫ ОЦЕНКИ")

    # Инициализация
    config = {"ml": {"model": {"device": "cuda"}, "model_directory": "models/saved"}}

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    # Тестовые символы
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    for symbol in symbols:
        print_header(f"Анализ {symbol}")

        # Загрузка данных
        query = f"""
        SELECT * FROM raw_market_data
        WHERE symbol = '{symbol}'
        ORDER BY datetime DESC
        LIMIT 100
        """

        raw_data = await AsyncPGPool.fetch(query)

        if len(raw_data) < 96:
            print(f"Недостаточно данных для {symbol}")
            continue

        # Преобразование в DataFrame
        df_data = [dict(row) for row in raw_data]
        df = pd.DataFrame(df_data)

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        df = df.sort_values("datetime")

        # Получение предсказания
        prediction = await ml_manager.predict(df)

        # Визуализация результатов
        print(f"Текущая цена: ${df['close'].iloc[-1]:,.2f}")

        # Основной сигнал
        print_signal(
            prediction["signal_type"],
            prediction["confidence"],
            prediction["signal_strength"],
        )

        # Детали предсказаний
        if "predictions" in prediction:
            pred_details = prediction["predictions"]

            # Направления по таймфреймам
            if "directions_by_timeframe" in pred_details:
                directions = pred_details["directions_by_timeframe"]
                probs = pred_details.get("direction_probabilities", [])

                if probs:
                    visualize_directions(directions, probs)

                # Процесс принятия решения
                weights = [0.4, 0.3, 0.2, 0.1]
                weighted_sum, decision = calculate_weighted_decision(
                    directions, weights
                )

            # Будущие доходности
            print("\nПредсказанные доходности:")
            print("-" * 50)
            print(f"15м: {pred_details.get('returns_15m', 0):.4f}")
            print(f"1ч:  {pred_details.get('returns_1h', 0):.4f}")
            print(f"4ч:  {pred_details.get('returns_4h', 0):.4f}")
            print(f"12ч: {pred_details.get('returns_12h', 0):.4f}")

        # Stop Loss и Take Profit
        if prediction.get("stop_loss_pct") and prediction.get("take_profit_pct"):
            current_price = df["close"].iloc[-1]

            if prediction["signal_type"] == "LONG":
                sl_price = current_price * (1 - prediction["stop_loss_pct"])
                tp_price = current_price * (1 + prediction["take_profit_pct"])
            else:
                sl_price = current_price * (1 + prediction["stop_loss_pct"])
                tp_price = current_price * (1 - prediction["take_profit_pct"])

            print("\nУровни управления риском:")
            print("-" * 50)
            print(f"Stop Loss:    ${sl_price:,.2f} ({prediction['stop_loss_pct']:.1%})")
            print(
                f"Take Profit:  ${tp_price:,.2f} ({prediction['take_profit_pct']:.1%})"
            )

        # Риск
        print(f"\nУровень риска: {prediction['risk_level']}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(visualize_ml_system())
