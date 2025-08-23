#!/usr/bin/env python3
"""
Визуализация работы ML системы оценки сигналов
"""

import asyncio
import sys
from pathlib import Path
import os
from datetime import datetime

from colorama import Fore, Style, init
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.offline import plot
import numpy as np

sys.path.append(str(Path(__file__).parent))

import pandas as pd

from database.connections.postgres import AsyncPGPool
from ml.ml_manager import MLManager

# Инициализация colorama для цветного вывода
init()

# Настройка matplotlib для работы без дисплея
plt.style.use('dark_background')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

# Создание директории для сохранения графиков
CHARTS_DIR = Path("data/charts")
CHARTS_DIR.mkdir(exist_ok=True)


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
        zip(timeframes, directions, probabilities, strict=False)
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
    for i, (d, w) in enumerate(zip(directions, weights, strict=False)):
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


def create_predictions_chart(symbol, prediction, df):
    """Создает интерактивный график предсказаний с помощью Plotly."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Извлекаем данные
    pred_details = prediction.get("predictions", {})
    timeframes = ["15m", "1h", "4h", "12h"]
    
    # Создаем subplots
    fig = sp.make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            f'{symbol} - Цена и Сигналы',
            'Вероятности по таймфреймам',
            'Предсказанные доходности',
            'Stop Loss / Take Profit',
            'Процесс принятия решения',
            'Распределение конфиденции'
        ),
        specs=[
            [{"secondary_y": True}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "scatter"}],
            [{"type": "bar"}, {"type": "indicator"}]
        ]
    )
    
    # График 1: Цена и сигналы
    recent_data = df.tail(50)
    fig.add_trace(
        go.Candlestick(
            x=recent_data.index,
            open=recent_data['open'],
            high=recent_data['high'],
            low=recent_data['low'],
            close=recent_data['close'],
            name="OHLC"
        ),
        row=1, col=1
    )
    
    # График 2: Вероятности по таймфреймам
    if "direction_probabilities" in pred_details:
        probs = pred_details["direction_probabilities"]
        for i, (tf, prob_dist) in enumerate(zip(timeframes, probs)):
            fig.add_trace(
                go.Bar(
                    x=['SHORT', 'NEUTRAL', 'LONG'],
                    y=prob_dist,
                    name=f'{tf}',
                    text=[f'{p:.2f}' for p in prob_dist],
                    textposition='auto',
                ),
                row=1, col=2
            )
    
    # График 3: Предсказанные доходности
    returns_data = [
        pred_details.get('returns_15m', 0),
        pred_details.get('returns_1h', 0),
        pred_details.get('returns_4h', 0),
        pred_details.get('returns_12h', 0)
    ]
    colors = ['red' if r < 0 else 'green' for r in returns_data]
    
    fig.add_trace(
        go.Bar(
            x=timeframes,
            y=returns_data,
            name='Доходности',
            marker_color=colors,
            text=[f'{r:.4f}' for r in returns_data],
            textposition='auto'
        ),
        row=2, col=1
    )
    
    # График 4: Уровни SL/TP
    current_price = df['close'].iloc[-1]
    if prediction.get("stop_loss_pct") and prediction.get("take_profit_pct"):
        signal_type = prediction["signal_type"]
        
        if signal_type == "LONG":
            sl_price = current_price * (1 - prediction["stop_loss_pct"])
            tp_price = current_price * (1 + prediction["take_profit_pct"])
        else:
            sl_price = current_price * (1 + prediction["stop_loss_pct"]) 
            tp_price = current_price * (1 - prediction["take_profit_pct"])
        
        fig.add_trace(
            go.Scatter(
                x=['Stop Loss', 'Current', 'Take Profit'],
                y=[sl_price, current_price, tp_price],
                mode='markers+lines+text',
                text=[f'${sl_price:.2f}', f'${current_price:.2f}', f'${tp_price:.2f}'],
                textposition="top center",
                name='Levels',
                line=dict(color='orange', width=3),
                marker=dict(size=12)
            ),
            row=2, col=2
        )
    
    # График 5: Взвешенное решение
    if "directions_by_timeframe" in pred_details:
        directions = pred_details["directions_by_timeframe"]
        weights = [0.4, 0.3, 0.2, 0.1]
        
        weighted_values = [d * w for d, w in zip(directions, weights)]
        
        fig.add_trace(
            go.Bar(
                x=timeframes,
                y=weighted_values,
                name='Взвешенные значения',
                text=[f'{v:.3f}' for v in weighted_values],
                textposition='auto'
            ),
            row=3, col=1
        )
    
    # График 6: Индикатор конфиденции
    confidence = prediction.get("confidence", 0)
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=confidence * 100,
            title={'text': f"Конфиденция<br>{prediction.get('signal_type', 'NEUTRAL')}"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "green" if prediction.get('signal_type') == 'LONG' else 
                              "red" if prediction.get('signal_type') == 'SHORT' else "yellow"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "gray"}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80}
            }
        ),
        row=3, col=2
    )
    
    # Обновляем layout
    fig.update_layout(
        title=f'ML Система анализа - {symbol} - {timestamp}',
        height=1000,
        showlegend=True,
        template='plotly_dark'
    )
    
    # Сохраняем в файл
    filename = CHARTS_DIR / f'ml_predictions_{symbol}_{timestamp}.html'
    plot(fig, filename=str(filename), auto_open=False)
    
    print(f"📊 График сохранен: {filename}")
    return filename


def create_features_heatmap(symbol, features_data, timestamp):
    """Создает тепловую карту важности признаков."""
    if not features_data or len(features_data) == 0:
        print("⚠️ Нет данных о признаках для визуализации")
        return None
        
    # Обрабатываем разные форматы входных данных
    if isinstance(features_data, list) and features_data:
        if isinstance(features_data[0], dict):
            # Если это список словарей с 'name' и 'value'
            names = [f.get('name', f'feature_{i}') for i, f in enumerate(features_data)]
            values = [float(f.get('value', 0)) for f in features_data]
        else:
            # Если это просто список значений
            names = [f'feature_{i}' for i in range(len(features_data))]
            values = [float(v) for v in features_data]
    elif isinstance(features_data, pd.DataFrame):
        # Если это уже DataFrame
        names = features_data.index.tolist()
        values = features_data.values.flatten().tolist()
    else:
        print(f"⚠️ Неподдерживаемый формат данных признаков: {type(features_data)}")
        return None
    
    # Создаем фигуру matplotlib с темным фоном
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(20, 8))
    
    # Выбираем топ-50 признаков для лучшей читаемости
    max_features = 50
    if len(values) > max_features:
        # Сортируем по абсолютному значению и берем топ-50
        sorted_indices = sorted(range(len(values)), key=lambda i: abs(values[i]), reverse=True)[:max_features]
        display_names = [names[i] for i in sorted_indices]
        display_values = [values[i] for i in sorted_indices]
    else:
        display_names = names
        display_values = values
    
    # Преобразуем в numpy array для heatmap
    values_array = np.array(display_values).reshape(1, -1)
    
    # Создаем heatmap
    sns.heatmap(
        values_array,
        xticklabels=display_names,
        yticklabels=['Значения признаков'],
        cmap='RdYlBu_r',
        center=0,
        annot=False,
        fmt='.3f',
        cbar_kws={'label': 'Нормализованное значение'},
        ax=ax
    )
    
    plt.title(f'Тепловая карта топ-{len(display_values)} признаков модели - {symbol} - {timestamp}', 
              fontsize=16, color='white', pad=20)
    plt.xlabel('Признаки модели', fontsize=12, color='white')
    plt.ylabel('', fontsize=12)
    
    # Улучшаем читаемость меток
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
    
    # Добавляем сетку для лучшей читаемости
    ax.grid(False)
    
    plt.tight_layout()
    
    # Сохраняем с темным фоном
    filename = CHARTS_DIR / f'features_heatmap_{symbol}_{timestamp}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight', 
                facecolor='#0a0a0a', edgecolor='none')
    plt.close()
    
    print(f"🔥 Тепловая карта признаков сохранена: {filename}")
    return filename


def create_market_data_analysis(symbol, df, timestamp):
    """Создает комплексный анализ рыночных данных."""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.patch.set_facecolor('black')
    
    # График 1: OHLC свечи (последние 100 периодов)
    recent_data = df.tail(100).copy()
    recent_data['MA20'] = recent_data['close'].rolling(20).mean()
    recent_data['MA50'] = recent_data['close'].rolling(50).mean()
    
    axes[0,0].plot(recent_data.index, recent_data['close'], color='white', linewidth=1.5, label='Close')
    axes[0,0].plot(recent_data.index, recent_data['MA20'], color='orange', linewidth=1, label='MA20')
    axes[0,0].plot(recent_data.index, recent_data['MA50'], color='red', linewidth=1, label='MA50')
    axes[0,0].set_title(f'{symbol} - Цена и скользящие средние', color='white', fontsize=12)
    axes[0,0].legend()
    axes[0,0].grid(True, alpha=0.3)
    
    # График 2: Объем торгов
    axes[0,1].bar(recent_data.index, recent_data['volume'], color='cyan', alpha=0.7)
    axes[0,1].set_title(f'{symbol} - Объем торгов', color='white', fontsize=12)
    axes[0,1].grid(True, alpha=0.3)
    
    # График 3: Волатильность
    recent_data['returns'] = recent_data['close'].pct_change()
    recent_data['volatility'] = recent_data['returns'].rolling(20).std()
    
    axes[1,0].plot(recent_data.index, recent_data['volatility'], color='yellow', linewidth=1.5)
    axes[1,0].set_title(f'{symbol} - Волатильность (20-период)', color='white', fontsize=12)
    axes[1,0].grid(True, alpha=0.3)
    
    # График 4: Распределение доходностей
    returns_clean = recent_data['returns'].dropna()
    axes[1,1].hist(returns_clean, bins=30, color='green', alpha=0.7, edgecolor='white')
    axes[1,1].set_title(f'{symbol} - Распределение доходностей', color='white', fontsize=12)
    axes[1,1].axvline(returns_clean.mean(), color='red', linestyle='--', 
                     label=f'Среднее: {returns_clean.mean():.4f}')
    axes[1,1].legend()
    axes[1,1].grid(True, alpha=0.3)
    
    # Настройка общего вида
    for ax in axes.flat:
        ax.set_facecolor('black')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
    
    plt.tight_layout()
    
    # Сохраняем
    filename = CHARTS_DIR / f'market_analysis_{symbol}_{timestamp}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight',
                facecolor='black', edgecolor='black')
    plt.close()
    
    print(f"📈 Анализ рыночных данных сохранен: {filename}")
    return filename


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
            if col in df.columns:
                df[col] = df[col].astype(float)

        # Исправление проблемы с datetime
        if 'datetime' in df.columns:
            df = df.sort_values("datetime")
            df = df.set_index('datetime', drop=True)  # Устанавливаем datetime как индекс
        
        # Убеждаемся, что нет дублирующихся колонок
        df = df.loc[:, ~df.columns.duplicated()]

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
        
        # Создание временной отметки для файлов
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n🎨 Создание графических визуализаций для {symbol}...")
        
        # 1. Интерактивный график предсказаний (Plotly)
        try:
            chart_file = create_predictions_chart(symbol, prediction, df)
            print(f"✅ Интерактивный график: {chart_file}")
        except Exception as e:
            print(f"❌ Ошибка создания графика предсказаний: {e}")
        
        # 2. Анализ рыночных данных (Matplotlib)
        try:
            market_file = create_market_data_analysis(symbol, df, timestamp)
            print(f"✅ Анализ рыночных данных: {market_file}")
        except Exception as e:
            print(f"❌ Ошибка анализа рыночных данных: {e}")
        
        # 3. Тепловая карта признаков (если есть данные)
        try:
            # Попытаемся получить данные о признаках из ML менеджера
            if hasattr(ml_manager, 'get_latest_features'):
                features_data = await ml_manager.get_latest_features(symbol)
                if features_data:
                    heatmap_file = create_features_heatmap(symbol, features_data, timestamp)
                    print(f"✅ Тепловая карта признаков: {heatmap_file}")
                else:
                    print("⚠️ Данные о признаках недоступны")
            else:
                print("⚠️ Метод получения признаков не доступен в ML менеджере")
        except Exception as e:
            print(f"❌ Ошибка создания тепловой карты: {e}")
        
        print(f"\n📁 Все графики сохранены в: {CHARTS_DIR.absolute()}")

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
                weighted_sum, decision = calculate_weighted_decision(directions, weights)

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
            print(f"Take Profit:  ${tp_price:,.2f} ({prediction['take_profit_pct']:.1%})")

        # Риск
        print(f"\nУровень риска: {prediction['risk_level']}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(visualize_ml_system())
