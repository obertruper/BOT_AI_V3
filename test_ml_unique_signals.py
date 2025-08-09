#!/usr/bin/env python3
"""
Тест уникальности ML сигналов
Проверяет что разные криптовалюты получают разные предсказания
"""

import asyncio
import hashlib
import sys
from pathlib import Path

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger(__name__)


async def test_ml_unique_signals():
    """Тест уникальности ML сигналов для разных криптовалют"""
    try:
        logger.info("🔍 Тестирование уникальности ML сигналов...")

        # Инициализация
        config_manager = ConfigManager()
        ml_manager = MLManager(config_manager._config)
        ml_processor = MLSignalProcessor(
            ml_manager=ml_manager,
            config=config_manager._config,
            config_manager=config_manager,
        )
        data_loader = DataLoader(config_manager)

        # Инициализируем компоненты
        await ml_manager.initialize()
        await ml_processor.initialize()

        # Список криптовалют для тестирования
        test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]

        predictions = {}
        input_hashes = {}

        for symbol in test_symbols:
            logger.info(f"🔄 Тестируем {symbol}...")

            # Загружаем данные
            ohlcv_data = await data_loader.get_data_for_ml(symbol, limit=500)

            if ohlcv_data is None or len(ohlcv_data) < 240:
                logger.warning(f"❌ Недостаточно данных для {symbol}")
                continue

            # Добавляем symbol колонку для корректной обработки
            ohlcv_data = ohlcv_data.copy()
            ohlcv_data["symbol"] = symbol

            # Вычисляем хэш входных данных для проверки уникальности
            last_100_candles = ohlcv_data.tail(100)
            input_hash = hashlib.md5(
                str(
                    last_100_candles[
                        ["open", "high", "low", "close", "volume", "symbol"]
                    ].values
                ).encode()
            ).hexdigest()
            input_hashes[symbol] = input_hash

            # Генерируем предсказание
            prediction = await ml_manager.predict(ohlcv_data)

            if prediction:
                predictions[symbol] = prediction

                logger.info(
                    f"✅ {symbol} - Сигнал: {prediction.get('signal_type', 'UNKNOWN')}"
                )
                logger.info(f"   Уверенность: {prediction.get('confidence', 0):.3f}")
                logger.info(
                    f"   15m returns: {prediction.get('predictions', {}).get('returns_15m', 0):.6f}"
                )
                logger.info(f"   Input hash: {input_hash[:8]}...")
            else:
                logger.warning(f"❌ Нет предсказания для {symbol}")

        # Анализ уникальности
        logger.info("\n" + "=" * 60)
        logger.info("📊 АНАЛИЗ УНИКАЛЬНОСТИ СИГНАЛОВ")
        logger.info("=" * 60)

        # 1. Проверка уникальности входных данных
        unique_input_hashes = set(input_hashes.values())
        logger.info(
            f"🔍 Уникальных входных наборов данных: {len(unique_input_hashes)}/{len(input_hashes)}"
        )

        if len(unique_input_hashes) < len(input_hashes):
            logger.warning("⚠️  Обнаружены дублированные входные данные!")
            for symbol, hash_val in input_hashes.items():
                duplicates = [
                    s for s, h in input_hashes.items() if h == hash_val and s != symbol
                ]
                if duplicates:
                    logger.warning(
                        f"   {symbol} имеет такие же данные как: {duplicates}"
                    )
        else:
            logger.info("✅ Все входные данные уникальны")

        # 2. Проверка уникальности предсказаний
        signal_types = [p.get("signal_type", "UNKNOWN") for p in predictions.values()]
        unique_signals = set(signal_types)
        logger.info(f"🎯 Уникальных типов сигналов: {len(unique_signals)}")
        logger.info(f"   Типы сигналов: {list(unique_signals)}")

        # Статистика по сигналам
        from collections import Counter

        signal_counts = Counter(signal_types)
        logger.info("📈 Распределение сигналов:")
        for signal_type, count in signal_counts.items():
            logger.info(
                f"   {signal_type}: {count} ({count / len(signal_types) * 100:.1f}%)"
            )

        # 3. Проверка уникальности предсказанных доходностей
        returns_15m = [
            p.get("predictions", {}).get("returns_15m", 0) for p in predictions.values()
        ]
        unique_returns = len(set(returns_15m))
        logger.info(f"💰 Уникальных 15m returns: {unique_returns}/{len(returns_15m)}")

        if unique_returns < len(returns_15m):
            logger.warning("⚠️  Обнаружены дублированные предсказания доходности!")
            return_counts = Counter(returns_15m)
            for return_val, count in return_counts.items():
                if count > 1:
                    symbols_with_return = [
                        s
                        for s, p in predictions.items()
                        if p.get("predictions", {}).get("returns_15m", 0) == return_val
                    ]
                    logger.warning(f"   Return {return_val:.6f}: {symbols_with_return}")
        else:
            logger.info("✅ Все предсказания доходности уникальны")

        # 4. Детальная проверка различий
        logger.info("\n📋 ДЕТАЛЬНЫЕ ПРЕДСКАЗАНИЯ:")
        for symbol, prediction in predictions.items():
            pred_data = prediction.get("predictions", {})
            logger.info(f"🪙 {symbol}:")
            logger.info(f"   Signal: {prediction.get('signal_type', 'UNKNOWN')}")
            logger.info(f"   Confidence: {prediction.get('confidence', 0):.3f}")
            logger.info(
                f"   Returns: 15m={pred_data.get('returns_15m', 0):.6f}, 1h={pred_data.get('returns_1h', 0):.6f}"
            )
            logger.info(
                f"   Direction score: {pred_data.get('direction_score', 0):.3f}"
            )
            logger.info(f"   Stop Loss %: {prediction.get('stop_loss_pct', 0)}")
            logger.info(f"   Take Profit %: {prediction.get('take_profit_pct', 0)}")

        # 5. Проверка кэширования
        logger.info("\n🗄️  ПРОВЕРКА КЭШИРОВАНИЯ:")
        logger.info(f"Размер кэша предсказаний: {len(ml_processor.prediction_cache)}")
        logger.info(f"Ключи кэша: {list(ml_processor.prediction_cache.keys())}")

        # Тестируем повторный вызов для проверки кэширования
        logger.info("\n🔄 ТЕСТ ПОВТОРНОГО ВЫЗОВА (проверка кэша):")
        prediction_btc_2 = await ml_manager.predict(
            ohlcv_data
        )  # Последний symbol (может быть не BTC)

        # Проверяем, используется ли кэш правильно
        cache_keys_after = list(ml_processor.prediction_cache.keys())
        logger.info(f"Ключи кэша после повторного вызова: {cache_keys_after}")

        return {
            "total_symbols": len(test_symbols),
            "successful_predictions": len(predictions),
            "unique_signal_types": len(unique_signals),
            "unique_returns": unique_returns,
            "cache_size": len(ml_processor.prediction_cache),
        }

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}", exc_info=True)
        return None


async def main():
    """Главная функция"""
    results = await test_ml_unique_signals()

    if results:
        logger.info("\n" + "=" * 60)
        logger.info("✅ ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
        logger.info("=" * 60)
        logger.info(f"Протестировано символов: {results['total_symbols']}")
        logger.info(f"Успешных предсказаний: {results['successful_predictions']}")
        logger.info(f"Уникальных типов сигналов: {results['unique_signal_types']}")
        logger.info(f"Уникальных доходностей: {results['unique_returns']}")
        logger.info(f"Размер кэша: {results['cache_size']}")

        if results["unique_signal_types"] > 1:
            logger.info("🎉 ТЕСТ ПРОЙДЕН: Сигналы уникальны!")
        else:
            logger.warning("⚠️  ПРОБЛЕМА: Все сигналы одинаковы")
    else:
        logger.error("❌ Тест не завершен из-за ошибок")


if __name__ == "__main__":
    asyncio.run(main())
