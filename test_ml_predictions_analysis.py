#!/usr/bin/env python3
"""
Тестирование и анализ ML предсказаний с боевыми компонентами
Проверяет корректность интерпретации выходов модели
"""

import asyncio
import json
import sys
from pathlib import Path

import numpy as np
import torch
from dotenv import load_dotenv

# Добавляем корневую папку в path
sys.path.insert(0, str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from ml.logic.archive_old_versions.feature_engineering import FeatureEngineering
from ml.ml_manager import MLManager

logger = setup_logger("ml_prediction_analyzer")


class MLPredictionAnalyzer:
    """Анализатор ML предсказаний и их интерпретации"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.ml_manager = None
        self.feature_engineer = None
        self.model = None

    async def initialize(self):
        """Инициализация компонентов"""
        try:
            # Инициализация базы данных
            await AsyncPGPool.initialize(
                host=self.config["database"]["host"],
                port=self.config["database"]["port"],
                user=self.config["database"]["user"],
                password=self.config["database"]["password"],
                database=self.config["database"]["database"],
            )

            # Инициализация ML компонентов
            self.ml_manager = MLManager(self.config)
            await self.ml_manager.initialize()

            # Загружаем feature engineer
            self.feature_engineer = FeatureEngineering(self.config)

            logger.info("✅ Компоненты инициализированы")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise

    async def test_model_outputs(self, symbol="BTCUSDT"):
        """Тестирует выходы модели и их интерпретацию"""

        logger.info(f"\n{'=' * 60}")
        logger.info(f"🔬 АНАЛИЗ ПРЕДСКАЗАНИЙ ДЛЯ {symbol}")
        logger.info(f"{'=' * 60}")

        try:
            # 1. Получаем данные из БД
            query = """
                SELECT * FROM raw_market_data
                WHERE symbol = $1
                ORDER BY timestamp DESC
                LIMIT 100
            """
            candles = await AsyncPGPool.fetch(query, symbol)

            if not candles:
                logger.error(f"Нет данных для {symbol}")
                return

            logger.info(f"📊 Загружено {len(candles)} свечей")

            # 2. Подготавливаем features
            df = self.ml_manager._prepare_dataframe(candles, symbol)

            if df is None or df.empty:
                logger.error("Не удалось подготовить данные")
                return

            # 3. Генерируем признаки
            features_df = await self.feature_engineer.generate_features(df, symbol)

            logger.info(f"📈 Сгенерировано {len(features_df.columns)} признаков")

            # 4. Получаем предсказания модели
            with torch.no_grad():
                # Подготовка входных данных
                feature_cols = [
                    col
                    for col in features_df.columns
                    if col not in ["timestamp", "symbol", "close"]
                ]

                if len(feature_cols) < 240:
                    logger.warning(f"⚠️ Недостаточно признаков: {len(feature_cols)}/240")
                    # Дополняем нулями
                    for i in range(240 - len(feature_cols)):
                        features_df[f"dummy_{i}"] = 0
                    feature_cols = [
                        col
                        for col in features_df.columns
                        if col not in ["timestamp", "symbol", "close"]
                    ]

                X = features_df[feature_cols[:240]].values

                # Проверяем размерность
                if len(X) < 96:
                    logger.error(f"Недостаточно данных: {len(X)}/96")
                    return

                # Берем последние 96 точек
                X_input = X[-96:].reshape(1, 96, 240)
                X_tensor = torch.FloatTensor(X_input)

                if torch.cuda.is_available():
                    X_tensor = X_tensor.cuda()

                # Получаем raw предсказания
                outputs = self.ml_manager.model(X_tensor)
                predictions = outputs.cpu().numpy()[0]

            # 5. Анализируем выходы
            logger.info("\n📊 АНАЛИЗ 20 ВЫХОДОВ МОДЕЛИ:")
            logger.info(f"{'=' * 50}")

            # Future returns (0-3)
            logger.info("📈 Future Returns (ожидаемая доходность):")
            timeframes = ["15m", "1h", "4h", "12h"]
            for i, tf in enumerate(timeframes):
                value = predictions[i]
                logger.info(f"  {tf}: {value:+.4f} ({value * 100:+.2f}%)")

            # Directions (4-7) - это raw scores, не классы!
            logger.info("\n🎯 Direction Scores (сырые оценки направления):")
            for i, tf in enumerate(timeframes):
                score = predictions[4 + i]
                # Интерпретируем score
                if score < -0.5:
                    direction = "STRONG LONG"
                elif score < 0:
                    direction = "LONG"
                elif score < 0.5:
                    direction = "WEAK LONG"
                elif score < 1.0:
                    direction = "WEAK SHORT"
                elif score < 1.5:
                    direction = "SHORT"
                else:
                    direction = "STRONG SHORT"
                logger.info(f"  {tf}: {score:+.4f} → {direction}")

            # Long levels (8-11)
            logger.info("\n📊 Long Target Probabilities (вероятность достижения целей лонга):")
            long_targets = ["1% за 4ч", "2% за 4ч", "3% за 12ч", "5% за 12ч"]
            for i, target in enumerate(long_targets):
                prob = 1 / (1 + np.exp(-predictions[8 + i]))  # Sigmoid
                logger.info(f"  {target}: {prob:.1%}")

            # Short levels (12-15)
            logger.info("\n📉 Short Target Probabilities (вероятность достижения целей шорта):")
            for i, target in enumerate(long_targets):
                prob = 1 / (1 + np.exp(-predictions[12 + i]))  # Sigmoid
                logger.info(f"  {target}: {prob:.1%}")

            # Risk metrics (16-19)
            logger.info("\n⚠️ Risk Metrics (метрики риска):")
            risk_names = [
                "Max Drawdown 1h",
                "Max Rally 1h",
                "Max Drawdown 4h",
                "Max Rally 4h",
            ]
            for i, name in enumerate(risk_names):
                value = predictions[16 + i]
                logger.info(f"  {name}: {value:+.4f} ({value * 100:+.2f}%)")

            # 6. Проверяем интерпретацию в ML Manager
            logger.info(f"\n{'=' * 50}")
            logger.info("🔄 ИНТЕРПРЕТАЦИЯ ML MANAGER:")
            logger.info(f"{'=' * 50}")

            # Вычисляем взвешенное направление (как в ml_manager.py)
            direction_scores = predictions[4:8]

            # Используем веса для временных фреймов
            timeframe_weights = np.array([0.4, 0.3, 0.2, 0.1])  # Больший вес коротким TF
            weighted_direction = np.average(direction_scores, weights=timeframe_weights)

            logger.info(f"\n📊 Взвешенное направление: {weighted_direction:.4f}")

            # Интерпретация по правилам ml_manager.py
            if weighted_direction < 0.5:
                signal_type = "LONG"
                logger.info(f"✅ Сигнал: {signal_type} (покупка)")
            elif weighted_direction < 1.5:
                signal_type = "SHORT"
                logger.info(f"📉 Сигнал: {signal_type} (продажа)")
            else:
                signal_type = "NEUTRAL"
                logger.info(f"⏸️ Сигнал: {signal_type} (пропуск)")

            # 7. Рассчитываем SL/TP
            current_price = float(candles[0]["close"])
            logger.info(f"\n💰 Текущая цена: ${current_price:.2f}")

            future_returns = predictions[0:4]

            if signal_type == "LONG":
                # Для лонга
                min_return = float(np.min(future_returns))
                max_return = float(np.max(future_returns))

                stop_loss_pct = np.clip(abs(min_return) * 100, 1.0, 5.0) / 100.0
                take_profit_pct = np.clip(max_return * 100, 2.0, 10.0) / 100.0

                stop_loss = current_price * (1 - stop_loss_pct)
                take_profit = current_price * (1 + take_profit_pct)

                logger.info(f"📍 Stop Loss: ${stop_loss:.2f} (-{stop_loss_pct * 100:.1f}%)")
                logger.info(f"🎯 Take Profit: ${take_profit:.2f} (+{take_profit_pct * 100:.1f}%)")

            elif signal_type == "SHORT":
                # Для шорта
                min_return = float(np.min(future_returns))
                max_return = float(np.max(future_returns))

                stop_loss_pct = np.clip(abs(max_return) * 100, 1.0, 5.0) / 100.0
                take_profit_pct = np.clip(abs(min_return) * 100, 2.0, 10.0) / 100.0

                stop_loss = current_price * (1 + stop_loss_pct)
                take_profit = current_price * (1 - take_profit_pct)

                logger.info(f"📍 Stop Loss: ${stop_loss:.2f} (+{stop_loss_pct * 100:.1f}%)")
                logger.info(f"🎯 Take Profit: ${take_profit:.2f} (-{take_profit_pct * 100:.1f}%)")

            # 8. Проверяем пороги уверенности
            logger.info(f"\n{'=' * 50}")
            logger.info("🎚️ АНАЛИЗ ПОРОГОВ:")
            logger.info(f"{'=' * 50}")

            # Считаем уверенность как максимальное отклонение от нейтрального (1.0)
            confidence = abs(weighted_direction - 1.0)

            logger.info(f"📊 Уверенность модели: {confidence:.3f}")

            # Проверяем пороги из конфига
            config_thresholds = {
                "direction_confidence": self.config["model"].get(
                    "direction_confidence_threshold", 0.25
                ),
                "min_confidence": self.config["model"].get("confidence_threshold", 0.0),
                "trading_min": self.config["trading"].get("min_confidence_threshold", 0.3),
            }

            logger.info("\n⚙️ Настроенные пороги:")
            for name, value in config_thresholds.items():
                status = "✅" if confidence >= value else "❌"
                logger.info(f"  {name}: {value:.2f} {status}")

            # 9. Анализ проблем
            logger.info(f"\n{'=' * 50}")
            logger.info("⚠️ ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:")
            logger.info(f"{'=' * 50}")

            problems = []

            # Проверка 1: Слишком низкие пороги
            if config_thresholds["min_confidence"] < 0.2:
                problems.append("❌ Слишком низкий confidence_threshold (< 0.2)")

            # Проверка 2: Противоречивые сигналы
            if signal_type in ["LONG", "SHORT"]:
                # Проверяем согласованность future returns с направлением
                avg_return = np.mean(future_returns)
                if signal_type == "LONG" and avg_return < 0:
                    problems.append(f"⚠️ LONG сигнал при отрицательном avg return: {avg_return:.4f}")
                elif signal_type == "SHORT" and avg_return > 0:
                    problems.append(
                        f"⚠️ SHORT сигнал при положительном avg return: {avg_return:.4f}"
                    )

            # Проверка 3: Несбалансированные SL/TP
            if signal_type in ["LONG", "SHORT"]:
                risk_reward = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0
                if risk_reward < 1.5:
                    problems.append(
                        f"❌ Плохое соотношение риск/прибыль: {risk_reward:.2f} (должно быть > 1.5)"
                    )

            # Проверка 4: Экстремальные значения
            if any(abs(v) > 0.5 for v in future_returns):
                problems.append("⚠️ Экстремальные значения future returns (> 50%)")

            if problems:
                for problem in problems:
                    logger.warning(problem)
            else:
                logger.info("✅ Критических проблем не обнаружено")

            # 10. Рекомендации
            logger.info(f"\n{'=' * 50}")
            logger.info("💡 РЕКОМЕНДАЦИИ:")
            logger.info(f"{'=' * 50}")

            recommendations = []

            if config_thresholds["min_confidence"] < 0.3:
                recommendations.append("1. Увеличить confidence_threshold до 0.3-0.4")

            if config_thresholds["direction_confidence"] < 0.4:
                recommendations.append("2. Увеличить direction_confidence_threshold до 0.4-0.5")

            if signal_type != "NEUTRAL" and confidence < 0.5:
                recommendations.append("3. Рассмотреть пропуск сделок с уверенностью < 0.5")

            recommendations.append("4. Использовать адаптивные SL/TP на основе волатильности")
            recommendations.append("5. Добавить фильтрацию по risk metrics")

            for rec in recommendations:
                logger.info(f"  {rec}")

            return {
                "symbol": symbol,
                "signal": signal_type,
                "confidence": confidence,
                "weighted_direction": weighted_direction,
                "future_returns": future_returns.tolist(),
                "stop_loss_pct": stop_loss_pct if signal_type != "NEUTRAL" else None,
                "take_profit_pct": take_profit_pct if signal_type != "NEUTRAL" else None,
                "problems": problems,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"❌ Ошибка тестирования: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return None

    async def test_multiple_symbols(self):
        """Тестирует несколько символов"""

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        results = []

        for symbol in symbols:
            result = await self.test_model_outputs(symbol)
            if result:
                results.append(result)
            await asyncio.sleep(1)  # Небольшая пауза

        # Анализ общей статистики
        logger.info(f"\n{'=' * 60}")
        logger.info("📊 ОБЩАЯ СТАТИСТИКА:")
        logger.info(f"{'=' * 60}")

        if results:
            signals = [r["signal"] for r in results]
            confidences = [r["confidence"] for r in results]

            logger.info(f"Протестировано символов: {len(results)}")
            logger.info(f"LONG сигналов: {signals.count('LONG')}")
            logger.info(f"SHORT сигналов: {signals.count('SHORT')}")
            logger.info(f"NEUTRAL сигналов: {signals.count('NEUTRAL')}")
            logger.info(f"Средняя уверенность: {np.mean(confidences):.3f}")

            # Сохраняем результаты
            with open("ml_analysis_results.json", "w") as f:
                json.dump(results, f, indent=2, default=str)
            logger.info("\n💾 Результаты сохранены в ml_analysis_results.json")

    async def cleanup(self):
        """Очистка ресурсов"""
        await AsyncPGPool.close()


async def main():
    """Основная функция"""
    load_dotenv()

    analyzer = MLPredictionAnalyzer()

    try:
        await analyzer.initialize()

        # Тестируем один символ подробно
        await analyzer.test_model_outputs("BTCUSDT")

        # Тестируем несколько символов
        await analyzer.test_multiple_symbols()

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await analyzer.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
