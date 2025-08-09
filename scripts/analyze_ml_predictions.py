#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ ML предсказаний и причин отсутствия сигналов
"""

import asyncio
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import and_, select

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.connections import get_async_db, init_async_db
from database.models.signal import Signal
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger("ml_analyzer")


class MLPredictionAnalyzer:
    """Анализатор ML предсказаний"""

    def __init__(self):
        self.predictions = []
        self.filtered_predictions = []
        self.signals_generated = []

    async def analyze_predictions(self):
        """Основной метод анализа"""
        logger.info("🔍 Запуск анализа ML предсказаний...")

        # Инициализация
        await init_async_db()

        # Загрузка конфигурации
        config_manager = ConfigManager()
        await config_manager.initialize()
        config = config_manager._config

        # Инициализация ML Manager с перехватом логов
        ml_manager = MLManager(config)
        await ml_manager.initialize()

        # Инициализация Signal Processor
        signal_processor = MLSignalProcessor(ml_manager, config, config_manager)
        await signal_processor.initialize()

        # Сохраняем оригинальные пороги
        original_confidence = signal_processor.min_confidence
        original_strength = signal_processor.min_signal_strength

        logger.info("📊 Текущие пороги:")
        logger.info(f"   Min confidence: {original_confidence}")
        logger.info(f"   Min strength: {original_strength}")

        # Тестовые символы
        test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

        # Собираем все предсказания БЕЗ фильтрации
        signal_processor.min_confidence = 0.0
        signal_processor.min_signal_strength = 0.0

        all_predictions = []

        for symbol in test_symbols:
            logger.info(f"\n🎯 Анализ {symbol}...")

            # Получаем предсказание напрямую
            signal = await signal_processor.process_realtime_signal(
                symbol=symbol, exchange="bybit"
            )

            # Даже если сигнал не прошел фильтры, получаем raw предсказание
            # через прямой вызов ML Manager
            try:
                # Загружаем данные для символа
                from database.models.market_data import RawMarketData

                async with get_async_db() as session:
                    stmt = (
                        select(RawMarketData)
                        .where(
                            and_(
                                RawMarketData.symbol == symbol,
                                RawMarketData.exchange == "bybit",
                                RawMarketData.interval_minutes == 15,
                            )
                        )
                        .order_by(RawMarketData.timestamp.desc())
                        .limit(500)
                    )

                    result = await session.execute(stmt)
                    data = result.scalars().all()

                    if len(data) >= 96:
                        # Конвертируем в DataFrame
                        df = pd.DataFrame(
                            [
                                {
                                    "timestamp": d.timestamp,
                                    "open": float(d.open),
                                    "high": float(d.high),
                                    "low": float(d.low),
                                    "close": float(d.close),
                                    "volume": float(d.volume),
                                    "symbol": symbol,
                                }
                                for d in data[:96]
                            ]
                        )

                        df = df.sort_values("timestamp")

                        # Получаем предсказание
                        prediction = await ml_manager.predict(df)

                        all_predictions.append(
                            {
                                "symbol": symbol,
                                "signal_type": prediction["signal_type"],
                                "confidence": prediction["confidence"],
                                "strength": prediction["signal_strength"],
                                "success_probability": prediction[
                                    "success_probability"
                                ],
                                "risk_level": prediction["risk_level"],
                                "predictions": prediction["predictions"],
                                "passed_filters": signal is not None,
                            }
                        )

            except Exception as e:
                logger.error(f"Ошибка анализа {symbol}: {e}")

        # Анализ результатов
        self._analyze_results(all_predictions, original_confidence, original_strength)

        # Анализ сигналов в БД
        await self._analyze_database_signals()

        # Рекомендации
        self._generate_recommendations(all_predictions)

    def _analyze_results(self, predictions, min_conf, min_strength):
        """Анализ собранных предсказаний"""

        logger.info("\n📊 АНАЛИЗ ПРЕДСКАЗАНИЙ:")
        logger.info("=" * 60)

        # Общая статистика
        total = len(predictions)
        buy_signals = sum(1 for p in predictions if p["signal_type"] == "BUY")
        sell_signals = sum(1 for p in predictions if p["signal_type"] == "SELL")
        neutral_signals = sum(1 for p in predictions if p["signal_type"] == "NEUTRAL")

        logger.info(f"\n📈 Распределение сигналов (всего {total}):")
        logger.info(f"   BUY:     {buy_signals} ({buy_signals / total * 100:.1f}%)")
        logger.info(f"   SELL:    {sell_signals} ({sell_signals / total * 100:.1f}%)")
        logger.info(
            f"   NEUTRAL: {neutral_signals} ({neutral_signals / total * 100:.1f}%)"
        )

        # Анализ по символам
        logger.info("\n📊 Детали по символам:")
        for pred in predictions:
            logger.info(f"\n{pred['symbol']}:")
            logger.info(f"   Тип: {pred['signal_type']}")
            logger.info(
                f"   Уверенность: {pred['confidence']:.3f} {'✅' if pred['confidence'] >= min_conf else '❌'}"
            )
            logger.info(
                f"   Сила: {pred['strength']:.3f} {'✅' if pred['strength'] >= min_strength else '❌'}"
            )
            logger.info(f"   Вероятность успеха: {pred['success_probability']:.1%}")
            logger.info(f"   Риск: {pred['risk_level']}")
            logger.info(f"   Направления: {pred['predictions']['raw_directions']}")
            logger.info(
                f"   Прошел фильтры: {'✅' if pred['passed_filters'] else '❌'}"
            )

        # Анализ причин фильтрации
        logger.info("\n🚫 Причины отсутствия сигналов:")

        filtered_by_type = sum(1 for p in predictions if p["signal_type"] == "NEUTRAL")
        filtered_by_confidence = sum(
            1
            for p in predictions
            if p["signal_type"] != "NEUTRAL" and p["confidence"] < min_conf
        )
        filtered_by_strength = sum(
            1
            for p in predictions
            if p["signal_type"] != "NEUTRAL" and p["strength"] < min_strength
        )

        logger.info(f"   NEUTRAL сигналы: {filtered_by_type}")
        logger.info(f"   Низкая уверенность: {filtered_by_confidence}")
        logger.info(f"   Слабая сила: {filtered_by_strength}")

        # Статистика по метрикам
        if predictions:
            confidences = [p["confidence"] for p in predictions]
            strengths = [p["strength"] for p in predictions]
            success_probs = [p["success_probability"] for p in predictions]

            logger.info("\n📊 Статистика метрик:")
            logger.info(
                f"   Уверенность: min={min(confidences):.3f}, max={max(confidences):.3f}, avg={np.mean(confidences):.3f}"
            )
            logger.info(
                f"   Сила: min={min(strengths):.3f}, max={max(strengths):.3f}, avg={np.mean(strengths):.3f}"
            )
            logger.info(
                f"   Успех: min={min(success_probs):.1%}, max={max(success_probs):.1%}, avg={np.mean(success_probs):.1%}"
            )

    async def _analyze_database_signals(self):
        """Анализ сигналов в БД"""
        logger.info("\n🗄️ АНАЛИЗ СИГНАЛОВ В БД:")
        logger.info("=" * 60)

        async with get_async_db() as session:
            # Получаем последние сигналы
            stmt = (
                select(Signal)
                .where(Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"]))
                .order_by(Signal.created_at.desc())
                .limit(100)
            )

            result = await session.execute(stmt)
            signals = result.scalars().all()

            logger.info(f"Найдено сигналов в БД: {len(signals)}")

            if signals:
                # Группируем по типам
                by_type = defaultdict(int)
                by_symbol = defaultdict(int)

                for signal in signals:
                    by_type[signal.signal_type.value] += 1
                    by_symbol[signal.symbol] += 1

                logger.info("\nПо типам:")
                for sig_type, count in by_type.items():
                    logger.info(f"   {sig_type}: {count}")

                logger.info("\nПо символам:")
                for symbol, count in by_symbol.items():
                    logger.info(f"   {symbol}: {count}")

                # Анализ последнего сигнала
                last_signal = signals[0]
                logger.info("\nПоследний сигнал:")
                logger.info(f"   Время: {last_signal.created_at}")
                logger.info(f"   Символ: {last_signal.symbol}")
                logger.info(f"   Тип: {last_signal.signal_type.value}")
                logger.info(f"   Уверенность: {last_signal.confidence:.3f}")
                logger.info(f"   Сила: {last_signal.strength:.3f}")

    def _generate_recommendations(self, predictions):
        """Генерация рекомендаций"""
        logger.info("\n💡 РЕКОМЕНДАЦИИ:")
        logger.info("=" * 60)

        # Анализируем распределение
        if predictions:
            avg_confidence = np.mean([p["confidence"] for p in predictions])
            avg_strength = np.mean([p["strength"] for p in predictions])
            neutral_pct = sum(
                1 for p in predictions if p["signal_type"] == "NEUTRAL"
            ) / len(predictions)

            logger.info("\n1. Пороги:")
            logger.info(f"   Средняя уверенность: {avg_confidence:.3f}")
            logger.info(
                f"   Рекомендуемый порог confidence: {max(0.3, avg_confidence * 0.7):.3f}"
            )
            logger.info(f"   Средняя сила: {avg_strength:.3f}")
            logger.info(
                f"   Рекомендуемый порог strength: {max(0.1, avg_strength * 0.7):.3f}"
            )

            logger.info("\n2. Модель:")
            if neutral_pct > 0.8:
                logger.info("   ⚠️ Модель генерирует слишком много NEUTRAL сигналов")
                logger.info("   - Снизьте порог направления в ML Manager с 0.1 до 0.05")
                logger.info("   - Проверьте качество входных данных")
                logger.info(
                    "   - Рассмотрите переобучение модели на более волатильных данных"
                )

            logger.info("\n3. Конфигурация:")
            logger.info("   Обновите config/system.yaml:")
            logger.info(f"   min_confidence: {max(0.3, avg_confidence * 0.7):.2f}")
            logger.info(f"   min_signal_strength: {max(0.1, avg_strength * 0.7):.2f}")

            # Создаем визуализацию
            self._create_visualization(predictions)

    def _create_visualization(self, predictions):
        """Создание визуализации анализа"""
        try:
            import matplotlib

            matplotlib.use("Agg")  # Для работы без GUI

            fig, axes = plt.subplots(2, 2, figsize=(12, 10))

            # 1. Распределение типов сигналов
            signal_types = [p["signal_type"] for p in predictions]
            type_counts = pd.Series(signal_types).value_counts()
            axes[0, 0].pie(
                type_counts.values, labels=type_counts.index, autopct="%1.1f%%"
            )
            axes[0, 0].set_title("Распределение типов сигналов")

            # 2. Распределение уверенности
            confidences = [p["confidence"] for p in predictions]
            axes[0, 1].hist(confidences, bins=20, alpha=0.7, color="blue")
            axes[0, 1].axvline(
                x=0.45, color="red", linestyle="--", label="Текущий порог"
            )
            axes[0, 1].set_xlabel("Уверенность")
            axes[0, 1].set_ylabel("Количество")
            axes[0, 1].set_title("Распределение уверенности")
            axes[0, 1].legend()

            # 3. Распределение силы сигнала
            strengths = [p["strength"] for p in predictions]
            axes[1, 0].hist(strengths, bins=20, alpha=0.7, color="green")
            axes[1, 0].axvline(
                x=0.2, color="red", linestyle="--", label="Текущий порог"
            )
            axes[1, 0].set_xlabel("Сила сигнала")
            axes[1, 0].set_ylabel("Количество")
            axes[1, 0].set_title("Распределение силы сигнала")
            axes[1, 0].legend()

            # 4. Корреляция метрик
            df = pd.DataFrame(predictions)
            if not df.empty:
                scatter_data = df[df["signal_type"] != "NEUTRAL"]
                if not scatter_data.empty:
                    colors = {"BUY": "green", "SELL": "red"}
                    for sig_type in ["BUY", "SELL"]:
                        data = scatter_data[scatter_data["signal_type"] == sig_type]
                        if not data.empty:
                            axes[1, 1].scatter(
                                data["confidence"],
                                data["strength"],
                                c=colors[sig_type],
                                label=sig_type,
                                alpha=0.6,
                            )
                    axes[1, 1].axvline(x=0.45, color="red", linestyle="--", alpha=0.5)
                    axes[1, 1].axhline(y=0.2, color="red", linestyle="--", alpha=0.5)
                    axes[1, 1].set_xlabel("Уверенность")
                    axes[1, 1].set_ylabel("Сила сигнала")
                    axes[1, 1].set_title("Корреляция метрик")
                    axes[1, 1].legend()

            plt.tight_layout()

            # Сохраняем
            output_path = Path("data/analysis/ml_predictions_analysis.png")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path)
            plt.close()

            logger.info(f"\n📊 Визуализация сохранена: {output_path}")

        except Exception as e:
            logger.warning(f"Не удалось создать визуализацию: {e}")


async def main():
    """Запуск анализа"""
    analyzer = MLPredictionAnalyzer()
    await analyzer.analyze_predictions()


if __name__ == "__main__":
    asyncio.run(main())
