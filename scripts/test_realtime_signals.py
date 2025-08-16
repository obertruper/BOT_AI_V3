#!/usr/bin/env python3
"""
Тестовый скрипт для проверки real-time генерации ML сигналов
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor
from ml.signal_scheduler import SignalScheduler

logger = setup_logger(__name__)


async def test_data_loader():
    """Тест загрузки данных"""
    logger.info("=" * 50)
    logger.info("Тест 1: Проверка DataLoader")
    logger.info("=" * 50)

    loader = DataLoader()

    try:
        await loader.initialize()

        # Обновляем последние данные
        symbols = ["BTCUSDT", "ETHUSDT"]
        results = await loader.update_latest_data(symbols=symbols)

        logger.info(f"✅ Обновлено данных: {results}")

        # Получаем данные для ML
        df = await loader.get_data_for_ml("BTCUSDT", limit=300)
        logger.info(f"✅ Загружено {len(df)} свечей для BTCUSDT")
        logger.info(f"   Последняя свеча: {df.index[-1]}")
        logger.info(f"   Цена close: {df['close'].iloc[-1]}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в DataLoader: {e}")
        return False
    finally:
        await loader.cleanup()


async def test_indicator_calculation():
    """Тест расчета индикаторов в реальном времени"""
    logger.info("=" * 50)
    logger.info("Тест 2: Расчет индикаторов real-time")
    logger.info("=" * 50)

    from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

    loader = DataLoader()
    calculator = RealTimeIndicatorCalculator()

    try:
        await loader.initialize()

        # Получаем данные
        df = await loader.get_data_for_ml("BTCUSDT", limit=300)

        # Рассчитываем индикаторы
        indicators = await calculator.calculate_indicators(
            symbol="BTCUSDT",
            ohlcv_df=df,
            save_to_db=False,  # Не сохраняем в тесте
        )

        logger.info("✅ Рассчитано индикаторов:")
        logger.info(f"   Технических: {len(indicators.get('technical_indicators', {}))}")
        logger.info(f"   ML признаков: {len(indicators.get('ml_features', {}))}")
        logger.info(f"   Микроструктура: {len(indicators.get('microstructure_features', {}))}")

        # Примеры индикаторов
        tech = indicators.get("technical_indicators", {})
        if tech:
            logger.info("   Примеры технических индикаторов:")
            for key in list(tech.keys())[:5]:
                logger.info(f"     {key}: {tech[key]:.4f}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка расчета индикаторов: {e}")
        return False
    finally:
        await loader.cleanup()


async def test_ml_prediction():
    """Тест ML предсказания"""
    logger.info("=" * 50)
    logger.info("Тест 3: ML предсказание")
    logger.info("=" * 50)

    config_manager = ConfigManager()
    config = config_manager.get_config()

    ml_manager = MLManager(config)

    try:
        await ml_manager.initialize()

        # Создаем тестовые данные
        import numpy as np

        # Симулируем входные данные [batch=1, seq_len=96, features=240]
        test_input = np.random.randn(1, 96, 240).astype(np.float32)

        # Получаем предсказание
        prediction = await ml_manager.predict(test_input)

        logger.info("✅ Получено предсказание:")
        logger.info(f"   Форма выхода: {prediction.shape}")
        logger.info(f"   Пример выходов: {prediction[0, :5]}")

        # Проверяем адаптер
        from ml.model_adapter import ModelOutputAdapter

        adapter = ModelOutputAdapter()
        adapted = adapter.adapt_model_outputs(prediction, symbols=["BTCUSDT"])

        btc_pred = adapted.get("BTCUSDT", {})
        logger.info("\n   Адаптированное предсказание для BTCUSDT:")
        logger.info(f"   Тип сигнала: {btc_pred.get('signal_type')}")
        logger.info(f"   Уверенность: {btc_pred.get('confidence', 0):.2%}")
        logger.info(f"   Сила сигнала: {btc_pred.get('signal_strength', 0):.2f}")
        logger.info(f"   Уровень риска: {btc_pred.get('risk_level')}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка ML предсказания: {e}")
        return False
    finally:
        await ml_manager.cleanup()


async def test_signal_generation():
    """Тест генерации сигнала"""
    logger.info("=" * 50)
    logger.info("Тест 4: Генерация торгового сигнала")
    logger.info("=" * 50)

    config_manager = ConfigManager()
    config = config_manager.get_config()

    ml_manager = MLManager(config)
    signal_processor = MLSignalProcessor(ml_manager, config)

    try:
        await ml_manager.initialize()
        await signal_processor.initialize()

        # Генерируем сигнал
        signal = await signal_processor.process_realtime_signal(symbol="BTCUSDT", exchange="bybit")

        if signal:
            logger.info("✅ Сгенерирован сигнал:")
            logger.info(f"   Символ: {signal.symbol}")
            logger.info(f"   Тип: {signal.signal_type.value}")
            logger.info(f"   Уверенность: {signal.confidence:.2f}")
            logger.info(f"   Сила: {signal.strength:.2f}")
            logger.info(f"   Stop Loss: {signal.stop_loss}")
            logger.info(f"   Take Profit: {signal.take_profit}")
        else:
            logger.warning("⚠️ Сигнал не сгенерирован (возможно, слабый сигнал)")

        # Получаем метрики
        metrics = await signal_processor.get_metrics()
        logger.info("\n📊 Метрики процессора:")
        logger.info(f"   Обработано: {metrics.get('total_processed')}")
        logger.info(f"   Успешность: {metrics.get('success_rate', 0):.1%}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка генерации сигнала: {e}")
        return False
    finally:
        await signal_processor.shutdown()
        await ml_manager.cleanup()


async def test_signal_scheduler():
    """Тест планировщика сигналов"""
    logger.info("=" * 50)
    logger.info("Тест 5: Планировщик сигналов (10 секунд)")
    logger.info("=" * 50)

    scheduler = SignalScheduler()

    # Устанавливаем короткий интервал для теста
    scheduler.interval_seconds = 5
    scheduler.symbols = ["BTCUSDT"]  # Только один символ для теста

    try:
        await scheduler.initialize()
        await scheduler.start()

        logger.info("⏱️ Ждем 10 секунд для генерации сигналов...")
        await asyncio.sleep(10)

        # Получаем статус
        status = await scheduler.get_status()
        logger.info("\n📊 Статус планировщика:")
        logger.info(f"   Запущен: {status['running']}")

        for symbol, data in status["symbols"].items():
            logger.info(f"   {symbol}:")
            logger.info(f"     Активен: {data['active']}")
            logger.info(f"     Ошибок: {data['errors']}")

            last_signal = data.get("last_signal", {})
            if last_signal:
                logger.info(f"     Последний сигнал: {last_signal.get('timestamp')}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в планировщике: {e}")
        return False
    finally:
        await scheduler.stop()


async def main():
    """Основная функция тестирования"""
    logger.info("🚀 Запуск тестов real-time ML системы")
    logger.info(f"Время запуска: {datetime.now()}")

    tests = [
        ("DataLoader", test_data_loader),
        ("Indicator Calculator", test_indicator_calculation),
        ("ML Prediction", test_ml_prediction),
        ("Signal Generation", test_signal_generation),
        ("Signal Scheduler", test_signal_scheduler),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            logger.info(f"\n🔄 Запуск теста: {test_name}")
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Критическая ошибка в тесте {test_name}: {e}")
            results.append((test_name, False))

    # Итоговый отчет
    logger.info("\n" + "=" * 50)
    logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
    logger.info("=" * 50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nВсего тестов: {total}")
    logger.info(f"Успешно: {passed}")
    logger.info(f"Провалено: {total - passed}")
    logger.info(f"Успешность: {passed / total * 100:.1f}%")

    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Тесты прерваны пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)
