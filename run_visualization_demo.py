#!/usr/bin/env python3
"""
Демонстрация работы системы визуализации ML без запуска полной системы
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from visualize_ml_predictions import (
    create_predictions_chart,
    create_market_data_analysis,
    create_features_heatmap,
    CHARTS_DIR
)

def generate_demo_data(symbol: str = "BTCUSDT"):
    """Генерирует демо данные для визуализации"""
    
    # Создаем демо OHLCV данные
    periods = 200
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='15min')
    
    # Симулируем реалистичные ценовые данные
    base_price = 95000 if symbol == "BTCUSDT" else 3200 if symbol == "ETHUSDT" else 150
    prices = []
    current_price = base_price
    
    for _ in range(periods):
        change = np.random.randn() * base_price * 0.002  # 0.2% волатильность
        current_price += change
        prices.append(current_price)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(periods) * base_price * 0.001,
        'high': [p + abs(np.random.randn()) * base_price * 0.003 for p in prices],
        'low': [p - abs(np.random.randn()) * base_price * 0.003 for p in prices],
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, periods)
    }, index=dates)
    
    return df

def generate_demo_prediction(signal_type="LONG", confidence=0.75):
    """Генерирует демо предсказание"""
    
    return {
        'signal_type': signal_type,
        'confidence': confidence,
        'signal_strength': confidence * 0.8,
        'predictions': {
            'directions_by_timeframe': [2, 2, 1, 2],  # 0=SHORT, 1=NEUTRAL, 2=LONG
            'direction_probabilities': [
                [0.15, 0.25, 0.60],  # 15m: 60% LONG
                [0.20, 0.30, 0.50],  # 1h: 50% LONG
                [0.25, 0.40, 0.35],  # 4h: 40% NEUTRAL
                [0.10, 0.30, 0.60],  # 12h: 60% LONG
            ],
            'returns_15m': 0.0025,
            'returns_1h': 0.0048,
            'returns_4h': 0.0032,
            'returns_12h': 0.0089
        },
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.04,
        'risk_level': 'medium'
    }

def generate_demo_features(num_features=240):
    """Генерирует демо данные признаков"""
    
    feature_names = [
        'rsi_14', 'macd_signal', 'bb_upper', 'bb_lower', 'ema_9', 'ema_21',
        'volume_sma', 'atr_14', 'stoch_k', 'stoch_d', 'obv', 'adx',
        'cci', 'williams_r', 'mfi', 'roc', 'trix', 'keltner_upper',
        'donchian_upper', 'ichimoku_a', 'vwap', 'pvt', 'eom', 'cmf'
    ]
    
    # Расширяем список до 240 признаков
    all_features = []
    for i in range(num_features):
        if i < len(feature_names):
            name = feature_names[i]
        else:
            name = f'feature_{i}'
        
        value = np.random.randn() * 0.5 + 0.5  # Нормализованные значения
        all_features.append({'name': name, 'value': value})
    
    return all_features

async def run_demo():
    """Запускает демонстрацию визуализации"""
    
    print("=" * 80)
    print("ML VISUALIZATION DEMO - Демонстрация графических возможностей")
    print("=" * 80)
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    signal_types = ["LONG", "SHORT", "NEUTRAL"]
    
    for i, symbol in enumerate(symbols):
        print(f"\n📊 Генерация визуализации для {symbol}...")
        print("-" * 40)
        
        # Генерируем данные
        market_data = generate_demo_data(symbol)
        signal_type = signal_types[i % 3]
        confidence = 0.65 + np.random.random() * 0.3
        prediction = generate_demo_prediction(signal_type, confidence)
        features_data = generate_demo_features()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # 1. Интерактивный график предсказаний
            print(f"  📈 Создание интерактивного графика...")
            chart_file = create_predictions_chart(symbol, prediction, market_data)
            if chart_file and Path(chart_file).exists():
                size_kb = Path(chart_file).stat().st_size / 1024
                print(f"    ✅ Создан: {chart_file.name} ({size_kb:.1f} KB)")
            
            # 2. Анализ рыночных данных  
            print(f"  📊 Создание анализа рыночных данных...")
            market_file = create_market_data_analysis(symbol, market_data, timestamp)
            if market_file and Path(market_file).exists():
                size_kb = Path(market_file).stat().st_size / 1024
                print(f"    ✅ Создан: {market_file.name} ({size_kb:.1f} KB)")
            
            # 3. Тепловая карта признаков
            print(f"  🔥 Создание тепловой карты признаков...")
            heatmap_file = create_features_heatmap(symbol, features_data, timestamp)
            if heatmap_file and Path(heatmap_file).exists():
                size_kb = Path(heatmap_file).stat().st_size / 1024
                print(f"    ✅ Создан: {heatmap_file.name} ({size_kb:.1f} KB)")
            
            # Выводим детали предсказания
            print(f"\n  📌 Детали предсказания:")
            print(f"    • Сигнал: {signal_type}")
            print(f"    • Конфиденция: {confidence:.1%}")
            print(f"    • Stop Loss: {prediction['stop_loss_pct']:.1%}")
            print(f"    • Take Profit: {prediction['take_profit_pct']:.1%}")
            print(f"    • Уровень риска: {prediction['risk_level']}")
            
        except Exception as e:
            print(f"  ❌ Ошибка создания визуализации: {e}")
            import traceback
            traceback.print_exc()
    
    # Показываем статистику
    print("\n" + "=" * 80)
    print("📁 СТАТИСТИКА СОЗДАННЫХ ФАЙЛОВ")
    print("=" * 80)
    
    if CHARTS_DIR.exists():
        all_files = list(CHARTS_DIR.glob("*"))
        demo_files = [f for f in all_files if any(s in f.name for s in symbols)]
        
        print(f"Всего файлов в директории: {len(all_files)}")
        print(f"Создано в этой сессии: {len(demo_files)}")
        
        if demo_files:
            print("\nПоследние созданные файлы:")
            for f in sorted(demo_files, key=lambda x: x.stat().st_mtime)[-10:]:
                size_kb = f.stat().st_size / 1024
                mod_time = datetime.fromtimestamp(f.stat().st_mtime)
                print(f"  • {f.name} ({size_kb:.1f} KB) - {mod_time.strftime('%H:%M:%S')}")
        
        # Общий размер
        total_size = sum(f.stat().st_size for f in demo_files) / (1024 * 1024)
        print(f"\nОбщий размер созданных файлов: {total_size:.2f} MB")
    
    print("\n" + "=" * 80)
    print("✨ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
    print("=" * 80)
    print(f"\n📂 Файлы сохранены в: {CHARTS_DIR.absolute()}")
    print("\n🌐 Для просмотра интерактивных графиков откройте HTML файлы в браузере")
    print("🖼️ PNG файлы можно открыть в любом просмотрщике изображений")
    print("\n💡 Совет: Используйте веб-интерфейс http://localhost:5173/ml для")
    print("   интерактивного просмотра и управления ML системой")

if __name__ == "__main__":
    asyncio.run(run_demo())