#!/usr/bin/env python3
"""
Анализ разнообразия сигналов для диагностики проблемы с SHORT-only сигналами
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку в path
sys.path.insert(0, str(Path(__file__).parent))


# Импорты из проекта
from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from database.connections.postgres import AsyncPGPool
from ml.ml_manager import MLManager

logger = setup_logger("signal_analysis")


class SignalDiversityAnalyzer:
    """Анализатор разнообразия сигналов ML модели"""

    def __init__(self, config):
        self.config = config
        self.ml_manager = None
        self.data_loader = None

    async def initialize(self):
        """Инициализация компонентов"""
        # Инициализируем ML менеджер
        self.ml_manager = MLManager(self.config)
        await self.ml_manager.initialize()

        # Инициализируем data loader
        self.data_loader = DataLoader(self.config)

        logger.info("SignalDiversityAnalyzer initialized")

    async def analyze_recent_signals(self, days_back=7, symbol="BTCUSDT"):
        """Анализируем недавние сигналы из базы данных"""
        try:
            # Получаем недавние сигналы из БД
            query = (
                """
            SELECT
                symbol,
                signal_type,
                side,
                confidence,
                extra_data,
                created_at,
                EXTRACT(EPOCH FROM (NOW() - created_at))/3600 as hours_ago
            FROM signals
            WHERE symbol = $1
                AND created_at >= NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC
            LIMIT 100
            """
                % days_back
            )

            signals = await AsyncPGPool.fetch(query, symbol)

            if not signals:
                logger.warning(f"No recent signals found for {symbol}")
                return None

            # Анализ направлений
            directions = [s["signal_type"] for s in signals]
            direction_counts = {
                "LONG": directions.count("LONG"),
                "SHORT": directions.count("SHORT"),
                "NEUTRAL": directions.count("NEUTRAL"),
            }

            total_signals = len(signals)
            direction_percentages = {
                direction: (count / total_signals) * 100
                for direction, count in direction_counts.items()
            }

            logger.warning(
                f"""
📊 АНАЛИЗ РАЗНООБРАЗИЯ СИГНАЛОВ ({symbol}, последние {days_back} дней):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Общая статистика:
   Всего сигналов: {total_signals}

📊 Распределение направлений:
   LONG:    {direction_counts["LONG"]:3d} ({direction_percentages["LONG"]:5.1f}%)
   SHORT:   {direction_counts["SHORT"]:3d} ({direction_percentages["SHORT"]:5.1f}%)
   NEUTRAL: {direction_counts["NEUTRAL"]:3d} ({direction_percentages["NEUTRAL"]:5.1f}%)

🔍 Проблема выявлена: {"ДА" if direction_percentages["SHORT"] > 80 else "НЕТ"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            )

            return {
                "total_signals": total_signals,
                "direction_counts": direction_counts,
                "direction_percentages": direction_percentages,
                "signals": signals,
            }

        except Exception as e:
            logger.error(f"Error analyzing recent signals: {e}")
            return None

    async def test_live_prediction(self, symbol="BTCUSDT"):
        """Тестируем живое предсказание модели"""
        try:
            # Получаем свежие данные
            candles = await self.data_loader.load_ohlcv(
                symbol=symbol,
                interval="15m",
                limit=200,  # Больше чем нужно для ML
            )

            if candles is None or len(candles) < 96:
                logger.error(f"Not enough data for prediction: {len(candles) if candles else 0}")
                return None

            logger.info(f"Loaded {len(candles)} candles for {symbol}")

            # Делаем предсказание
            prediction = await self.ml_manager.predict(candles)

            logger.warning(
                f"""
🔮 ЖИВОЕ ПРЕДСКАЗАНИЕ МОДЕЛИ ({symbol}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Результат:
   Направление: {prediction.get("signal_type", "UNKNOWN")}
   Уверенность: {prediction.get("confidence", 0):.1%}

📈 Предсказания по таймфреймам:
   Returns 15m: {prediction.get("predictions", {}).get("returns_15m", 0):.6f}
   Returns 1h:  {prediction.get("predictions", {}).get("returns_1h", 0):.6f}
   Returns 4h:  {prediction.get("predictions", {}).get("returns_4h", 0):.6f}
   Returns 12h: {prediction.get("predictions", {}).get("returns_12h", 0):.6f}

🎯 Направление по таймфреймам:
   Direction Score: {prediction.get("predictions", {}).get("direction_score", 0):.3f}
   Directions: {prediction.get("predictions", {}).get("directions_by_timeframe", [])}

🔍 Детали для диагностики:
   Timestamp: {prediction.get("timestamp", "N/A")}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            )

            return prediction

        except Exception as e:
            logger.error(f"Error testing live prediction: {e}")
            return None

    async def test_multiple_symbols(self, symbols=["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]):
        """Тестируем предсказания для нескольких символов"""
        results = {}

        for symbol in symbols:
            logger.info(f"Testing prediction for {symbol}")
            try:
                prediction = await self.test_live_prediction(symbol)
                if prediction:
                    results[symbol] = {
                        "direction": prediction.get(
                            "signal_type"
                        ),  # FIXED: use signal_type instead of direction
                        "confidence": prediction.get("confidence"),
                        "direction_score": prediction.get("predictions", {}).get("direction_score"),
                        "directions_by_timeframe": prediction.get("predictions", {}).get(
                            "directions_by_timeframe", []
                        ),
                    }

            except Exception as e:
                logger.error(f"Error testing {symbol}: {e}")
                results[symbol] = None

        # Анализируем результаты
        directions = [r["direction"] for r in results.values() if r and r["direction"]]
        direction_counts = {
            "LONG": directions.count("LONG"),
            "SHORT": directions.count("SHORT"),
            "NEUTRAL": directions.count("NEUTRAL"),
        }

        logger.warning(
            """
🌐 АНАЛИЗ ПРЕДСКАЗАНИЙ ПО НЕСКОЛЬКИМ СИМВОЛАМ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Результаты по символам:
"""
        )

        for symbol, result in results.items():
            if result and result["direction"]:
                logger.warning(
                    f"   {symbol:8s}: {result['direction']:7s} ({result['confidence']:5.1%}) score={result['direction_score']:5.2f}"
                )
            elif result:
                logger.warning(
                    f"   {symbol:8s}: NO_DIRECTION ({result['confidence']:5.1%}) score={result['direction_score']:5.2f}"
                )
            else:
                logger.warning(f"   {symbol:8s}: ERROR")

        logger.warning(
            f"""
📈 Общее распределение направлений:
   LONG:    {direction_counts["LONG"]}
   SHORT:   {direction_counts["SHORT"]}
   NEUTRAL: {direction_counts["NEUTRAL"]}

🚨 Проблема SHORT-only: {"ДА" if direction_counts["SHORT"] == len(directions) and len(directions) > 0 else "НЕТ"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        )

        return results


async def main():
    """Главная функция анализа"""
    try:
        logger.info("🔍 Начинаем анализ разнообразия сигналов...")

        # Загружаем конфигурацию
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Инициализируем анализатор
        analyzer = SignalDiversityAnalyzer(config)
        await analyzer.initialize()

        # 1. Анализируем недавние сигналы из БД
        logger.info("📊 Анализ недавних сигналов из БД...")
        recent_analysis = await analyzer.analyze_recent_signals(days_back=3, symbol="BTCUSDT")

        # 2. Тестируем живые предсказания
        logger.info("🔮 Тестирование живых предсказаний...")
        live_results = await analyzer.test_multiple_symbols()

        # 3. Выводы
        logger.warning(
            f"""
🎯 ИТОГОВЫЙ АНАЛИЗ ПРОБЛЕМЫ РАЗНООБРАЗИЯ СИГНАЛОВ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Недавние сигналы из БД: {recent_analysis["direction_percentages"] if recent_analysis else "НЕ НАЙДЕНЫ"}

🔮 Живые предсказания: {len([r for r in live_results.values() if r])} успешных из {len(live_results)}

💡 РЕКОМЕНДАЦИИ:
   1. Проверить пороги weighted_direction (сейчас: <0.5=LONG, <1.5=SHORT, >=1.5=NEUTRAL)
   2. Проверить веса таймфреймов (сейчас: [0.4, 0.3, 0.2, 0.1])
   3. Анализировать model predictions более детально
   4. Рассмотреть калибровку модели или threshold tuning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        )

    except Exception as e:
        logger.error(f"Error in main analysis: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
