#!/usr/bin/env python3
"""
Детальный анализ ML Pipeline - проверка входных данных и процесса принятия решений
"""

import asyncio

import numpy as np
import pandas as pd

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from ml.logic.feature_engineering_v2 import FeatureEngineer
from ml.ml_manager import MLManager

logger = setup_logger("ml_pipeline_analyzer")


async def check_model_version():
    """Проверка версии и конфигурации модели"""

    logger.info("\n" + "=" * 60)
    logger.info("🔍 ПРОВЕРКА ВЕРСИИ МОДЕЛИ")
    logger.info("=" * 60)

    try:
        # Читаем конфигурацию ML
        import yaml

        with open("config/ml/ml_config.yaml") as f:
            ml_config = yaml.safe_load(f)

        logger.info("📊 Конфигурация ML:")
        logger.info(f"  • Модель: {ml_config['model']['name']}")
        logger.info(f"  • Версия: {ml_config['model'].get('version', 'unknown')}")
        logger.info(f"  • Lookback: {ml_config['model']['lookback']} шагов")
        logger.info(f"  • Признаков: {ml_config['model']['n_features']}")
        logger.info(f"  • Патчей: {ml_config['model']['patch_len']}")

        # Проверяем путь к модели
        model_path = ml_config["model"]["path"]
        import os

        if os.path.exists(model_path):
            logger.info(f"  ✅ Файл модели найден: {model_path}")
            file_size = os.path.getsize(model_path) / 1024 / 1024
            logger.info(f"  • Размер: {file_size:.2f} MB")
        else:
            logger.error(f"  ❌ Файл модели не найден: {model_path}")

        return ml_config

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
        return None


async def analyze_input_data(symbol: str = "BTCUSDT"):
    """Анализ входных данных для модели"""

    logger.info("\n" + "=" * 60)
    logger.info(f"📊 АНАЛИЗ ВХОДНЫХ ДАННЫХ ДЛЯ {symbol}")
    logger.info("=" * 60)

    # Получаем последние данные из БД
    query = """
        SELECT *
        FROM raw_market_data
        WHERE symbol = $1
        ORDER BY timestamp DESC
        LIMIT 100
    """

    rows = await AsyncPGPool.fetch(query, symbol)

    if not rows:
        logger.error(f"❌ Нет данных для {symbol}")
        return None

    # Конвертируем в DataFrame
    df = pd.DataFrame([dict(row) for row in rows])
    df = df.sort_values("timestamp")

    logger.info(f"📈 Загружено {len(df)} свечей")

    # Базовая статистика
    logger.info("\n📊 Статистика цен:")
    logger.info(f"  • Последняя цена: ${df['close'].iloc[-1]:.2f}")
    logger.info(f"  • Средняя: ${df['close'].mean():.2f}")
    logger.info(f"  • Мин/Макс: ${df['close'].min():.2f} / ${df['close'].max():.2f}")
    logger.info(f"  • Волатильность: {df['close'].std():.2f}")

    # Проверка качества данных
    issues = []

    # Проверка на NaN
    nan_count = df.isna().sum().sum()
    if nan_count > 0:
        issues.append(f"NaN значений: {nan_count}")

    # Проверка на нули
    zero_volume = (df["volume"] == 0).sum()
    if zero_volume > 0:
        issues.append(f"Нулевой объем: {zero_volume} свечей")

    # Проверка временных интервалов
    time_diffs = df["timestamp"].diff().dropna()
    expected_interval = 15 * 60 * 1000  # 15 минут в миллисекундах
    gaps = (time_diffs > expected_interval * 2).sum()
    if gaps > 0:
        issues.append(f"Временные разрывы: {gaps}")

    if issues:
        logger.warning("⚠️ Найденные проблемы:")
        for issue in issues:
            logger.warning(f"  • {issue}")
    else:
        logger.info("✅ Данные в хорошем состоянии")

    return df


async def test_feature_engineering(symbol: str = "BTCUSDT"):
    """Тестирование feature engineering"""

    logger.info("\n" + "=" * 60)
    logger.info("🔧 ТЕСТИРОВАНИЕ FEATURE ENGINEERING")
    logger.info("=" * 60)

    # Загружаем данные
    df = await analyze_input_data(symbol)
    if df is None:
        return None

    # Инициализируем feature engineer
    fe = FeatureEngineer()

    try:
        # Подготавливаем данные
        features = fe.prepare_features(df, symbol)

        logger.info("📊 Результат feature engineering:")
        logger.info(f"  • Форма данных: {features.shape}")
        logger.info(f"  • Признаков: {features.shape[1] if len(features.shape) > 1 else 1}")

        # Проверяем первые 10 признаков
        if len(features.shape) > 1:
            feature_names = features.columns[:10] if hasattr(features, "columns") else range(10)
            logger.info("\n📈 Примеры признаков:")
            for i, name in enumerate(feature_names):
                if hasattr(features, "iloc"):
                    value = features.iloc[-1, i]
                else:
                    value = features[-1, i] if len(features.shape) > 1 else features[-1]
                logger.info(f"  • {name}: {value:.6f}")

        # Проверка на NaN в признаках
        if hasattr(features, "isna"):
            nan_features = features.isna().sum()
            nan_cols = nan_features[nan_features > 0]
            if len(nan_cols) > 0:
                logger.warning(f"⚠️ NaN в {len(nan_cols)} признаках")
                for col in nan_cols.index[:5]:
                    logger.warning(f"  • {col}: {nan_cols[col]} NaN")

        return features

    except Exception as e:
        logger.error(f"❌ Ошибка feature engineering: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None


async def test_prediction_process(symbol: str = "BTCUSDT"):
    """Тестирование процесса предсказания"""

    logger.info("\n" + "=" * 60)
    logger.info("🎯 ТЕСТИРОВАНИЕ ПРОЦЕССА ПРЕДСКАЗАНИЯ")
    logger.info("=" * 60)

    try:
        # Инициализируем ML Manager
        ml_manager = MLManager()

        # Делаем тестовое предсказание
        logger.info(f"📊 Запуск предсказания для {symbol}...")

        # Создаем тестовый массив данных (96 шагов, 240 признаков)
        test_data = np.random.randn(1, 96, 240).astype(np.float32)

        # Заполняем реалистичными значениями
        test_data[0, :, 0] = np.linspace(100000, 101000, 96)  # Цены
        test_data[0, :, 1] = np.random.uniform(1000, 5000, 96)  # Объемы

        logger.info(f"  • Входные данные: {test_data.shape}")

        # Получаем предсказание
        prediction = ml_manager.predict(test_data, symbol)

        if prediction:
            logger.info("\n✅ Предсказание получено:")
            logger.info(f"  • Тип сигнала: {prediction.get('signal_type', 'UNKNOWN')}")
            logger.info(f"  • Уверенность: {prediction.get('confidence', 0):.2%}")
            logger.info(f"  • Сила: {prediction.get('signal_strength', 0):.2f}")

            # Анализ направлений по таймфреймам
            if "predictions" in prediction:
                preds = prediction["predictions"]
                logger.info("\n📈 Предсказания по таймфреймам:")
                logger.info(f"  • 15m: {preds.get('returns_15m', 0):.4f}")
                logger.info(f"  • 1h: {preds.get('returns_1h', 0):.4f}")
                logger.info(f"  • 4h: {preds.get('returns_4h', 0):.4f}")
                logger.info(f"  • 12h: {preds.get('returns_12h', 0):.4f}")

                # Направления
                logger.info("\n🎯 Направления:")
                logger.info(f"  • 15m: {prediction.get('direction_15m', 'UNKNOWN')}")
                logger.info(f"  • 1h: {prediction.get('direction_1h', 'UNKNOWN')}")
                logger.info(f"  • 4h: {prediction.get('direction_4h', 'UNKNOWN')}")
                logger.info(f"  • 12h: {prediction.get('direction_12h', 'UNKNOWN')}")
        else:
            logger.error("❌ Предсказание не получено")

        return prediction

    except Exception as e:
        logger.error(f"❌ Ошибка в процессе предсказания: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None


async def analyze_decision_logic():
    """Анализ логики принятия решений"""

    logger.info("\n" + "=" * 60)
    logger.info("🧠 АНАЛИЗ ЛОГИКИ ПРИНЯТИЯ РЕШЕНИЙ")
    logger.info("=" * 60)

    logger.info("\n📋 Правила принятия решений:")

    logger.info("\n1️⃣ STRONG LONG (confidence > 0.9):")
    logger.info("  • 3+ таймфрейма указывают LONG")
    logger.info("  • returns_15m > 0.001")
    logger.info("  • Все вероятности > 0.6")

    logger.info("\n2️⃣ LONG (confidence > 0.7):")
    logger.info("  • 2+ таймфрейма указывают LONG")
    logger.info("  • returns_15m > 0")
    logger.info("  • Основная вероятность > 0.55")

    logger.info("\n3️⃣ SHORT (confidence > 0.7):")
    logger.info("  • 2+ таймфрейма указывают SHORT")
    logger.info("  • returns_15m < 0")
    logger.info("  • Основная вероятность > 0.55")

    logger.info("\n4️⃣ NEUTRAL (остальные случаи):")
    logger.info("  • Смешанные сигналы")
    logger.info("  • Низкая уверенность (< 0.7)")
    logger.info("  • Нет явного направления")

    logger.info("\n📊 Параметры риска:")
    logger.info("  • Stop Loss: 1.2% - 1.5%")
    logger.info("  • Take Profit: 2.4% - 3.0%")
    logger.info("  • Risk/Reward: 1:2")


async def check_recent_predictions():
    """Проверка последних предсказаний из БД"""

    logger.info("\n" + "=" * 60)
    logger.info("📊 ПОСЛЕДНИЕ ПРЕДСКАЗАНИЯ В БД")
    logger.info("=" * 60)

    query = """
        SELECT
            symbol,
            signal_type,
            strength,
            confidence,
            strategy_name,
            created_at,
            suggested_stop_loss,
            suggested_take_profit
        FROM signals
        WHERE created_at > NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC
        LIMIT 20
    """

    rows = await AsyncPGPool.fetch(query)

    if not rows:
        logger.warning("⚠️ Нет сигналов за последний час")
        return

    # Анализ по типам
    signal_stats = {"BUY": 0, "SELL": 0, "NEUTRAL": 0, "LONG": 0, "SHORT": 0}

    logger.info(f"📈 Найдено {len(rows)} сигналов\n")

    for row in rows[:10]:
        signal_type = row["signal_type"]
        if signal_type in signal_stats:
            signal_stats[signal_type] += 1

        logger.info(f"• {row['symbol']}: {signal_type}")
        logger.info(f"  Уверенность: {row['confidence']:.2%}, Сила: {row['strength']:.2f}")

        if row["suggested_stop_loss"]:
            logger.info(
                f"  SL: {row['suggested_stop_loss']:.2f}, TP: {row['suggested_take_profit']:.2f}"
            )

        logger.info(f"  Время: {row['created_at'].strftime('%H:%M:%S')}")
        logger.info("")

    # Статистика
    logger.info("📊 Распределение сигналов:")
    for signal_type, count in signal_stats.items():
        if count > 0:
            pct = count / len(rows) * 100
            logger.info(f"  • {signal_type}: {count} ({pct:.1f}%)")


async def validate_ml_consistency():
    """Проверка консистентности ML предсказаний"""

    logger.info("\n" + "=" * 60)
    logger.info("🔄 ПРОВЕРКА КОНСИСТЕНТНОСТИ ML")
    logger.info("=" * 60)

    # Делаем несколько предсказаний для одних и тех же данных
    test_data = np.random.randn(1, 96, 240).astype(np.float32)
    test_data[0, :, 0] = np.linspace(100000, 101000, 96)

    ml_manager = MLManager()
    predictions = []

    logger.info("Делаем 5 предсказаний для одинаковых данных...")

    for i in range(5):
        pred = ml_manager.predict(test_data, f"TEST_{i}")
        if pred:
            predictions.append(pred)
            logger.info(
                f"  {i + 1}. {pred.get('signal_type', 'UNKNOWN')}: {pred.get('confidence', 0):.4f}"
            )

    # Проверяем консистентность
    if len(predictions) > 1:
        signal_types = [p.get("signal_type") for p in predictions]
        confidences = [p.get("confidence", 0) for p in predictions]

        if len(set(signal_types)) == 1:
            logger.info("✅ Предсказания консистентны (одинаковый тип)")
        else:
            logger.warning(f"⚠️ Разные типы сигналов: {set(signal_types)}")

        conf_std = np.std(confidences)
        if conf_std < 0.01:
            logger.info(f"✅ Уверенность стабильна (std={conf_std:.4f})")
        else:
            logger.warning(f"⚠️ Уверенность варьируется (std={conf_std:.4f})")


async def main():
    """Основная функция анализа"""

    logger.info("\n" + "=" * 80)
    logger.info("🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ML PIPELINE")
    logger.info("=" * 80)

    # 1. Проверка версии модели
    ml_config = await check_model_version()

    # 2. Анализ входных данных
    await analyze_input_data("BTCUSDT")

    # 3. Тест feature engineering
    await test_feature_engineering("BTCUSDT")

    # 4. Тест процесса предсказания
    await test_prediction_process("BTCUSDT")

    # 5. Анализ логики принятия решений
    await analyze_decision_logic()

    # 6. Проверка последних предсказаний
    await check_recent_predictions()

    # 7. Проверка консистентности
    await validate_ml_consistency()

    logger.info("\n" + "=" * 80)
    logger.info("✅ АНАЛИЗ ЗАВЕРШЕН")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
