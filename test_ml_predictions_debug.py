#!/usr/bin/env python3
"""
Детальная отладка ML предсказаний
"""

import asyncio

import numpy as np
from sqlalchemy import and_, select

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.connections import get_async_db
from database.models.market_data import RawMarketData
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

logger = setup_logger(__name__)


async def test_single_symbol_detailed(symbol: str = "BTCUSDT"):
    """Детальная проверка обработки одного символа"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    logger.info(f"\n{'=' * 60}")
    logger.info(f"🔍 Детальная проверка {symbol}")
    logger.info(f"{'=' * 60}\n")

    # 1. Проверяем данные в БД
    async with get_async_db() as db:
        stmt = (
            select(RawMarketData)
            .where(
                and_(
                    RawMarketData.symbol == symbol,
                    RawMarketData.exchange == "bybit",
                    RawMarketData.interval_minutes == 15,
                )
            )
            .order_by(RawMarketData.datetime.desc())
            .limit(200)
        )

        result = await db.execute(stmt)
        data = result.scalars().all()

        logger.info("📊 Данные в БД:")
        logger.info(f"   Записей: {len(data)}")
        if data:
            logger.info(f"   Последняя: {data[0].datetime}")
            logger.info(f"   Первая: {data[-1].datetime}")

    # 2. Инициализируем компоненты
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    indicator_calculator = RealTimeIndicatorCalculator(cache_ttl=900, config=config)

    # 3. Подготавливаем DataFrame
    import pandas as pd

    if data:
        df = pd.DataFrame(
            [
                {
                    "datetime": d.datetime,
                    "open": float(d.open),
                    "high": float(d.high),
                    "low": float(d.low),
                    "close": float(d.close),
                    "volume": float(d.volume),
                    "turnover": float(d.turnover) if d.turnover else 0,
                }
                for d in reversed(data)  # Реверс для правильного порядка
            ]
        )
        df.set_index("datetime", inplace=True)

        logger.info("\n📈 DataFrame подготовлен:")
        logger.info(f"   Форма: {df.shape}")
        logger.info(f"   Колонки: {list(df.columns)}")

        # 4. Рассчитываем признаки
        try:
            features_dict = await indicator_calculator.get_features_for_ml(symbol, df)

            logger.info("\n🔢 Признаки рассчитаны:")
            logger.info(f"   Количество: {len(features_dict)}")
            logger.info(
                f"   Типы: {set(type(v).__name__ for v in features_dict.values())}"
            )

            # Преобразуем в массив
            features_array = np.array(list(features_dict.values())).reshape(1, -1)
            logger.info(f"   Массив: {features_array.shape}")

            # 5. Получаем предсказание
            prediction = await ml_manager.predict(features_array)

            logger.info("\n🤖 ML предсказание:")
            logger.info(
                f"   Сырое: {prediction['predictions'][:8]}"
            )  # Первые 8 значений
            logger.info(f"   Направления: {prediction['predictions'][4:8]}")
            logger.info(f"   Тип сигнала: {prediction.get('signal_type', 'N/A')}")
            logger.info(f"   Уверенность: {prediction.get('confidence', 0):.2%}")

            # 6. Проверяем создание сигнала
            signal_processor = MLSignalProcessor(
                ml_manager=ml_manager, config=config, config_manager=config_manager
            )
            await signal_processor.initialize()

            signal = await signal_processor.process_realtime_signal(
                symbol=symbol, exchange="bybit"
            )

            if signal:
                logger.info("\n✅ Сигнал сгенерирован:")
                logger.info(f"   Тип: {signal.signal_type.value}")
                logger.info(f"   Уверенность: {signal.confidence:.2%}")
                logger.info(f"   Сила: {signal.strength:.2f}")
            else:
                logger.info("\n❌ Сигнал не сгенерирован")
                logger.info(
                    f"   Минимальная уверенность: {signal_processor.min_confidence}"
                )
                logger.info(
                    f"   Минимальная сила: {signal_processor.min_signal_strength}"
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке: {e}", exc_info=True)


async def test_feature_engineering():
    """Тест feature engineering"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Создаем тестовые данные
    import pandas as pd

    dates = pd.date_range(start="2024-01-01", periods=200, freq="15min")

    test_df = pd.DataFrame(
        {
            "datetime": dates,
            "symbol": "BTCUSDT",  # Добавляем symbol
            "open": np.random.uniform(40000, 45000, 200),
            "high": np.random.uniform(40100, 45100, 200),
            "low": np.random.uniform(39900, 44900, 200),
            "close": np.random.uniform(40000, 45000, 200),
            "volume": np.random.uniform(100, 1000, 200),
            "turnover": np.random.uniform(4000000, 45000000, 200),
        }
    )
    # Не устанавливаем datetime как индекс - feature_engineering_v2 ожидает его как колонку
    # test_df.set_index('datetime', inplace=True)

    # Инициализируем feature engineer
    from ml.logic.feature_engineering_v2 import FeatureEngineer

    fe = FeatureEngineer(config)

    logger.info("\n🧪 Тест Feature Engineering")
    logger.info(f"   Входные данные: {test_df.shape}")

    # Создаем признаки
    features = fe.create_features(test_df)

    logger.info(f"   Результат: {type(features)}")
    if isinstance(features, np.ndarray):
        logger.info(f"   Форма: {features.shape}")
        logger.info(
            f"   Первые 10 признаков: {features[:10] if features.ndim == 1 else features[0, :10]}"
        )

    # Проверяем названия признаков
    feature_names = fe.get_feature_names()
    logger.info(f"   Количество названий: {len(feature_names)}")
    logger.info(f"   Примеры: {feature_names[:5]}")


async def main():
    """Основная функция"""

    logger.info("\n" + "=" * 80)
    logger.info("🔍 Детальная отладка ML предсказаний")
    logger.info("=" * 80 + "\n")

    # Тест feature engineering
    await test_feature_engineering()

    # Детальная проверка BTCUSDT
    await test_single_symbol_detailed("BTCUSDT")

    # Проверяем еще несколько символов
    for symbol in ["ETHUSDT", "SOLUSDT"]:
        await test_single_symbol_detailed(symbol)


if __name__ == "__main__":
    asyncio.run(main())
