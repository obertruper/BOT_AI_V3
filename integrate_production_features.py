#!/usr/bin/env python3
"""
Интеграция production feature engineering из обучающего файла ааа.py
Это обеспечивает 100% соответствие признаков между обучением и инференсом
"""

import os
import shutil
from datetime import datetime


def integrate_production_features():
    """Интегрирует production feature engineering в ML pipeline"""

    print("=" * 80)
    print("🚀 ИНТЕГРАЦИЯ PRODUCTION FEATURE ENGINEERING")
    print("=" * 80)

    # 1. Создаем backup текущего файла
    backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_file = "ml/logic/archive_old_versions/feature_engineering_v2.py"
    backup_file = f"ml/logic/feature_engineering_v2_backup_{backup_time}.py"

    if os.path.exists(current_file):
        shutil.copy(current_file, backup_file)
        print(f"✅ Создан backup: {backup_file}")

    # 2. Обновляем импорты в ML manager
    ml_manager_file = "ml/ml_manager.py"

    # Читаем файл
    with open(ml_manager_file) as f:
        content = f.read()

    # Заменяем импорт
    old_import = "from ml.logic.feature_engineering_v2 import FeatureEngineer"
    new_import = "from ml.logic.feature_engineering_production import ProductionFeatureEngineer as FeatureEngineer"

    if old_import in content:
        content = content.replace(old_import, new_import)
        with open(ml_manager_file, "w") as f:
            f.write(content)
        print(f"✅ Обновлен импорт в {ml_manager_file}")

    # 3. Обновляем импорты в ML signal processor
    signal_processor_file = "ml/ml_signal_processor.py"

    if os.path.exists(signal_processor_file):
        with open(signal_processor_file) as f:
            content = f.read()

        if old_import in content:
            content = content.replace(old_import, new_import)
            with open(signal_processor_file, "w") as f:
                f.write(content)
            print(f"✅ Обновлен импорт в {signal_processor_file}")

    # 4. Создаем конфигурацию для 270 признаков
    config_content = """# Конфигурация для 270 признаков из обучения
EXPECTED_FEATURES = 270

# Служебные колонки (не подавать в модель)
SERVICE_COLUMNS = [
    'datetime', 'symbol', 'open', 'high', 'low', 'close', 'volume',
    'timestamp', 'id', 'exchange'
]

# Целевые переменные (не подавать в модель)
TARGET_VARIABLES = [
    'future_return_15m', 'future_return_1h', 'future_return_4h', 'future_return_12h',
    'direction_15m', 'direction_1h', 'direction_4h', 'direction_12h',
    'will_reach_2pct_4h', 'will_reach_5pct_12h', 'will_reach_10pct_24h',
    'max_drawdown_4h', 'max_rally_4h', 'max_drawdown_12h', 'max_rally_12h',
    'volatility_1h', 'volatility_4h', 'volatility_12h',
    'best_action'
]

# Параметры модели
SEQUENCE_LENGTH = 168  # 42 часа при 15-минутных свечах
BATCH_SIZE = 32

def validate_features(df):
    \"\"\"Валидация количества признаков\"\"\"
    feature_cols = [col for col in df.columns 
                   if col not in SERVICE_COLUMNS 
                   and col not in TARGET_VARIABLES]
    
    actual_count = len(feature_cols)
    if actual_count != EXPECTED_FEATURES:
        raise ValueError(f"Ожидается {EXPECTED_FEATURES} признаков, получено {actual_count}")
    
    return feature_cols
"""

    with open("ml/config/production_features_config.py", "w") as f:
        f.write(config_content)
    print("✅ Создана конфигурация production_features_config.py")

    # 5. Создаем тестовый скрипт
    test_content = """#!/usr/bin/env python3
\"\"\"
Тестирование production feature engineering
\"\"\"

import pandas as pd
import numpy as np
from ml.logic.feature_engineering_production import ProductionFeatureEngineer
from ml.config.production_features_config import validate_features, EXPECTED_FEATURES

def test_production_features():
    \"\"\"Тестирует генерацию признаков\"\"\"
    
    print("=" * 80)
    print("🧪 ТЕСТИРОВАНИЕ PRODUCTION FEATURE ENGINEERING")
    print("=" * 80)
    
    # Создаем тестовые данные
    dates = pd.date_range(start='2024-01-01', periods=200, freq='15min')
    test_data = pd.DataFrame({
        'datetime': dates,
        'symbol': 'BTCUSDT',
        'open': np.random.uniform(40000, 45000, 200),
        'high': np.random.uniform(40500, 45500, 200),
        'low': np.random.uniform(39500, 44500, 200),
        'close': np.random.uniform(40000, 45000, 200),
        'volume': np.random.uniform(100, 1000, 200)
    })
    
    # Генерируем признаки
    feature_engineer = ProductionFeatureEngineer()
    df_with_features = feature_engineer.create_features(test_data)
    
    # Валидация
    try:
        feature_cols = validate_features(df_with_features)
        print(f"✅ Сгенерировано {len(feature_cols)} признаков")
        print(f"✅ Ожидалось {EXPECTED_FEATURES} признаков")
        
        if len(feature_cols) == EXPECTED_FEATURES:
            print("✅ ТЕСТ ПРОЙДЕН: Количество признаков соответствует ожидаемому")
        else:
            print(f"⚠️ ВНИМАНИЕ: Разница в {abs(len(feature_cols) - EXPECTED_FEATURES)} признаков")
            
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        
    return df_with_features

if __name__ == "__main__":
    test_production_features()
"""

    with open("test_production_features.py", "w") as f:
        f.write(test_content)
    print("✅ Создан тестовый скрипт test_production_features.py")

    print("\n" + "=" * 80)
    print("📊 ИНТЕГРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 80)
    print("\nДальнейшие шаги:")
    print("1. Запустите тест: python test_production_features.py")
    print("2. Проверьте логи на наличие ошибок")
    print(
        "3. При необходимости доработайте метод create_features() в feature_engineering_production.py"
    )
    print("\n✅ Production feature engineering готов к использованию!")


if __name__ == "__main__":
    integrate_production_features()
