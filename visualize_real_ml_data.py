#!/usr/bin/env python3
"""
Визуализация реальных данных ML системы из базы данных
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from database.connections.postgres import AsyncPGPool
from visualize_ml_predictions import (
    create_predictions_chart,
    create_market_data_analysis,
    create_features_heatmap,
    CHARTS_DIR
)

async def get_latest_market_data(symbol: str, limit: int = 200):
    """Получает последние рыночные данные из БД"""
    query = f"""
    SELECT datetime, open, high, low, close, volume 
    FROM raw_market_data
    WHERE symbol = '{symbol}'
    ORDER BY datetime DESC
    LIMIT {limit}
    """
    
    rows = await AsyncPGPool.fetch(query)
    if not rows:
        return None
    
    # Конвертируем в DataFrame
    data = [dict(row) for row in rows]
    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    df = df.sort_index()  # Сортируем по времени в правильном порядке
    
    # Конвертируем в float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df

async def get_latest_signal(symbol: str):
    """Получает последний сигнал для символа"""
    query = f"""
    SELECT * FROM signals
    WHERE symbol = '{symbol}'
    ORDER BY created_at DESC
    LIMIT 1
    """
    
    row = await AsyncPGPool.fetchrow(query)
    if not row:
        return None
    
    # Преобразуем в словарь для визуализации
    signal = dict(row)
    
    # Формируем структуру предсказания для визуализации
    prediction = {
        'signal_type': signal.get('signal_type', 'NEUTRAL'),
        'confidence': float(signal.get('confidence', 0)),
        'signal_strength': float(signal.get('signal_strength', 0)),
        'stop_loss_pct': float(signal.get('stop_loss_percentage', 0.02)),
        'take_profit_pct': float(signal.get('take_profit_percentage', 0.04)),
        'risk_level': signal.get('risk_level', 'medium'),
        'predictions': {
            'directions_by_timeframe': [2, 1, 1, 2],  # Примерные данные
            'direction_probabilities': [
                [0.15, 0.25, 0.60],  # 15m
                [0.20, 0.30, 0.50],  # 1h
                [0.25, 0.40, 0.35],  # 4h
                [0.10, 0.30, 0.60],  # 12h
            ],
            'returns_15m': 0.002,
            'returns_1h': 0.004,
            'returns_4h': 0.003,
            'returns_12h': 0.008
        }
    }
    
    # Добавляем дополнительные поля из сигнала если есть
    if 'prediction_data' in signal and signal['prediction_data']:
        import json
        try:
            pred_data = json.loads(signal['prediction_data']) if isinstance(signal['prediction_data'], str) else signal['prediction_data']
            if isinstance(pred_data, dict):
                prediction['predictions'].update(pred_data)
        except:
            pass
    
    return prediction

async def get_latest_features(symbol: str):
    """Получает последние обработанные признаки"""
    query = f"""
    SELECT ml_features FROM processed_market_data
    WHERE symbol = '{symbol}'
    ORDER BY datetime DESC
    LIMIT 1
    """
    
    row = await AsyncPGPool.fetchrow(query)
    if not row or not row['ml_features']:
        return None
    
    import json
    features = json.loads(row['ml_features']) if isinstance(row['ml_features'], str) else row['ml_features']
    
    # Преобразуем в формат для визуализации
    if isinstance(features, dict):
        features_list = []
        for name, value in features.items():
            if isinstance(value, (int, float)):
                features_list.append({'name': name, 'value': float(value)})
        return features_list[:240]  # Ограничиваем 240 признаками
    elif isinstance(features, list):
        return features[:240]
    
    return None

async def visualize_real_data():
    """Визуализация реальных данных из БД"""
    
    print("=" * 80)
    print("📊 ВИЗУАЛИЗАЦИЯ РЕАЛЬНЫХ ДАННЫХ ML СИСТЕМЫ")
    print("=" * 80)
    
    try:
        # Получаем пул соединений
        pool = await AsyncPGPool.get_pool()
        
        # Получаем список активных символов
        symbols_query = """
        SELECT DISTINCT s.symbol 
        FROM signals s
        INNER JOIN raw_market_data r ON s.symbol = r.symbol
        ORDER BY s.symbol
        LIMIT 5
        """
        
        symbol_rows = await AsyncPGPool.fetch(symbols_query)
        
        if not symbol_rows:
            print("⚠️ Нет данных для визуализации")
            return
        
        symbols = [row['symbol'] for row in symbol_rows]
        print(f"\n📈 Найдено {len(symbols)} символов с данными: {symbols}")
        
        for symbol in symbols[:3]:  # Визуализируем первые 3
            print(f"\n{'='*60}")
            print(f"🎯 Обработка {symbol}")
            print(f"{'='*60}")
            
            # Получаем данные
            print(f"  📥 Загрузка рыночных данных...")
            market_data = await get_latest_market_data(symbol)
            
            if market_data is None or len(market_data) < 50:
                print(f"  ⚠️ Недостаточно рыночных данных для {symbol}")
                continue
            
            print(f"    ✅ Загружено {len(market_data)} свечей")
            print(f"    📅 Период: {market_data.index[0]} - {market_data.index[-1]}")
            print(f"    💰 Текущая цена: ${market_data['close'].iloc[-1]:,.2f}")
            
            print(f"  📥 Загрузка последнего сигнала...")
            prediction = await get_latest_signal(symbol)
            
            if prediction:
                print(f"    ✅ Сигнал: {prediction['signal_type']}")
                print(f"    📊 Конфиденция: {prediction['confidence']:.1%}")
                print(f"    💪 Сила сигнала: {prediction['signal_strength']:.3f}")
            else:
                print(f"    ⚠️ Нет сигналов для {symbol}")
                # Создаем дефолтный сигнал для визуализации
                prediction = {
                    'signal_type': 'NEUTRAL',
                    'confidence': 0.5,
                    'signal_strength': 0.0,
                    'stop_loss_pct': 0.02,
                    'take_profit_pct': 0.04,
                    'risk_level': 'low',
                    'predictions': {
                        'directions_by_timeframe': [1, 1, 1, 1],
                        'direction_probabilities': [[0.33, 0.34, 0.33]] * 4,
                        'returns_15m': 0, 'returns_1h': 0, 
                        'returns_4h': 0, 'returns_12h': 0
                    }
                }
            
            print(f"  📥 Загрузка признаков модели...")
            features = await get_latest_features(symbol)
            
            if features:
                print(f"    ✅ Загружено {len(features)} признаков")
            else:
                print(f"    ⚠️ Нет обработанных признаков, генерируем примерные")
                # Генерируем примерные признаки
                feature_names = ['rsi', 'macd', 'bb_upper', 'bb_lower', 'ema_9', 'ema_21',
                               'volume_sma', 'atr', 'stoch_k', 'stoch_d', 'obv', 'adx']
                features = [{'name': f'{name}_{i}', 'value': np.random.randn() * 0.5} 
                           for i, name in enumerate(feature_names * 20)][:240]
            
            # Создаем временную метку
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            print(f"\n  🎨 Создание визуализаций...")
            
            try:
                # 1. Интерактивный график
                print(f"    📈 Создание интерактивного графика...")
                chart_file = create_predictions_chart(symbol, prediction, market_data)
                if chart_file and Path(chart_file).exists():
                    size_mb = Path(chart_file).stat().st_size / (1024 * 1024)
                    print(f"      ✅ {chart_file.name} ({size_mb:.1f} MB)")
                
                # 2. Анализ рынка
                print(f"    📊 Создание анализа рыночных данных...")
                market_file = create_market_data_analysis(symbol, market_data, timestamp)
                if market_file and Path(market_file).exists():
                    size_kb = Path(market_file).stat().st_size / 1024
                    print(f"      ✅ {market_file.name} ({size_kb:.1f} KB)")
                
                # 3. Тепловая карта
                if features:
                    print(f"    🔥 Создание тепловой карты признаков...")
                    heatmap_file = create_features_heatmap(symbol, features, timestamp)
                    if heatmap_file and Path(heatmap_file).exists():
                        size_kb = Path(heatmap_file).stat().st_size / 1024
                        print(f"      ✅ {heatmap_file.name} ({size_kb:.1f} KB)")
                
            except Exception as e:
                print(f"    ❌ Ошибка создания визуализации: {e}")
                import traceback
                traceback.print_exc()
        
        # Статистика
        print("\n" + "=" * 80)
        print("📊 СТАТИСТИКА ВИЗУАЛИЗАЦИИ")
        print("=" * 80)
        
        all_files = list(CHARTS_DIR.glob("*.html")) + list(CHARTS_DIR.glob("*.png"))
        recent_files = [f for f in all_files if 
                       (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)) < timedelta(minutes=5)]
        
        print(f"📁 Всего файлов визуализации: {len(all_files)}")
        print(f"🆕 Создано за последние 5 минут: {len(recent_files)}")
        
        if recent_files:
            total_size_mb = sum(f.stat().st_size for f in recent_files) / (1024 * 1024)
            print(f"💾 Общий размер новых файлов: {total_size_mb:.2f} MB")
        
        print(f"\n📂 Файлы сохранены в: {CHARTS_DIR.absolute()}")
        print(f"🌐 Веб-интерфейс доступен на: http://localhost:5173/ml")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()

if __name__ == "__main__":
    print("🚀 Запуск визуализации реальных данных ML системы...")
    asyncio.run(visualize_real_data())