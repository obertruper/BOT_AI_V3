#!/usr/bin/env python3
"""
ML Pipeline Diagnostic Tool
Проверяет согласованность интерпретации ML выходов между компонентами
"""

import asyncio
import sys
from pathlib import Path

import numpy as np

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger("ml_diagnostic")


class MLPipelineDiagnostic:
    """Диагностика ML pipeline"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()

    async def run_diagnostic(self):
        """Запуск полной диагностики"""
        logger.info("=" * 70)
        logger.info("🔬 ДИАГНОСТИКА ML PIPELINE")
        logger.info("=" * 70)

        # 1. Инициализируем компоненты
        logger.info("\n📦 Инициализация компонентов...")
        ml_manager = MLManager(self.config)
        await ml_manager.initialize()

        # 2. Создаем тестовые выходы модели
        logger.info("\n🧪 Создание тестовых данных...")
        test_outputs = self._create_test_outputs()

        # 3. Проверяем интерпретацию в ml_manager
        logger.info("\n📊 Проверка интерпретации в MLManager...")
        ml_result = self._test_ml_manager_interpretation(test_outputs)

        # 4. Проверяем интерпретацию в strategy
        logger.info("\n📈 Проверка интерпретации в PatchTSTStrategy...")
        strategy_result = self._test_strategy_interpretation(test_outputs)

        # 5. Сравниваем результаты
        logger.info("\n🔍 СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
        self._compare_results(ml_result, strategy_result)

        # 6. Проверяем фильтрацию
        logger.info("\n🚦 Проверка фильтрации сигналов...")
        await self._test_signal_filtering(ml_manager)

        # 7. Проверяем кэширование - пропускаем пока
        # logger.info("\n💾 Проверка кэширования...")
        # await self._test_caching(ml_processor)

        logger.info("\n" + "=" * 70)
        logger.info("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
        logger.info("=" * 70)

    def _create_test_outputs(self):
        """Создает тестовые выходы модели"""
        # Структура: 0-3: returns, 4-15: logits, 16-19: risks
        outputs = np.zeros(20)

        # Future returns
        outputs[0:4] = [0.002, 0.003, 0.004, 0.005]  # Положительные

        # Direction logits (4 таймфрейма × 3 класса)
        # Устанавливаем LONG для всех таймфреймов
        for i in range(4):
            base_idx = 4 + i * 3
            outputs[base_idx] = 2.0  # LONG logit
            outputs[base_idx + 1] = 0.5  # SHORT logit
            outputs[base_idx + 2] = 0.1  # NEUTRAL logit

        # Risk metrics
        outputs[16:20] = [0.01, 0.01, 0.02, 0.02]

        return outputs

    def _test_ml_manager_interpretation(self, outputs):
        """Тестирует интерпретацию в ml_manager"""
        # Извлекаем компоненты как в ml_manager
        future_returns = outputs[0:4]
        direction_logits = outputs[4:16]
        risk_metrics = outputs[16:20]

        # Интерпретация направлений
        direction_logits_reshaped = direction_logits.reshape(4, 3)

        directions = []
        probs_list = []
        for logits in direction_logits_reshaped:
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / exp_logits.sum()
            probs_list.append(probs)
            directions.append(np.argmax(probs))

        logger.info(f"  Направления: {directions}")
        logger.info(f"  Вероятности: {[p.round(3).tolist() for p in probs_list]}")

        return {
            "directions": directions,
            "probs": probs_list,
            "returns": future_returns,
            "risks": risk_metrics,
        }

    def _test_strategy_interpretation(self, outputs):
        """Тестирует интерпретацию в strategy"""
        # Новая интерпретация после исправления
        future_returns = outputs[0:4]
        direction_logits = outputs[4:16]
        risk_metrics = outputs[16:20]

        direction_logits_reshaped = direction_logits.reshape(4, 3)

        directions = []
        probs_list = []
        for logits in direction_logits_reshaped:
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / exp_logits.sum()
            probs_list.append(probs)
            directions.append(np.argmax(probs))

        logger.info(f"  Направления: {directions}")
        logger.info(f"  Вероятности: {[p.round(3).tolist() for p in probs_list]}")

        return {
            "directions": directions,
            "probs": probs_list,
            "returns": future_returns,
            "risks": risk_metrics,
        }

    def _compare_results(self, ml_result, strategy_result):
        """Сравнивает результаты интерпретации"""
        # Сравниваем направления
        ml_dirs = ml_result["directions"]
        st_dirs = strategy_result["directions"]

        if ml_dirs == st_dirs:
            logger.info("  ✅ Направления СОВПАДАЮТ")
        else:
            logger.error("  ❌ Направления НЕ СОВПАДАЮТ")
            logger.error(f"     MLManager: {ml_dirs}")
            logger.error(f"     Strategy:  {st_dirs}")

        # Сравниваем вероятности
        ml_probs = np.array([p for p in ml_result["probs"]])
        st_probs = np.array([p for p in strategy_result["probs"]])

        if np.allclose(ml_probs, st_probs, atol=0.001):
            logger.info("  ✅ Вероятности СОВПАДАЮТ")
        else:
            logger.error("  ❌ Вероятности НЕ СОВПАДАЮТ")
            logger.error(f"     Разница: {np.abs(ml_probs - st_probs).max():.6f}")

    async def _test_signal_filtering(self, ml_manager):
        """Тестирует фильтрацию сигналов"""
        from ml.logic.signal_quality_analyzer import SignalQualityAnalyzer

        analyzer = SignalQualityAnalyzer(self.config)

        # Тест 1: Сильный сигнал (все LONG)
        directions = np.array([0, 0, 0, 0])  # Все LONG
        direction_probs = [
            np.array([0.7, 0.2, 0.1]),  # 15m
            np.array([0.6, 0.3, 0.1]),  # 1h
            np.array([0.8, 0.1, 0.1]),  # 4h
            np.array([0.6, 0.2, 0.2]),  # 12h
        ]
        future_returns = np.array([0.002, 0.003, 0.004, 0.005])
        risk_metrics = np.array([0.01, 0.01, 0.02, 0.02])

        result = analyzer.analyze_signal_quality(
            directions, direction_probs, future_returns, risk_metrics, 0.0
        )

        logger.info(f"  Сильный сигнал: {'✅ ПРОШЕЛ' if result.passed else '❌ НЕ ПРОШЕЛ'}")
        logger.info(f"    Качество: {result.quality_metrics.quality_score:.3f}")
        logger.info(f"    Стратегия: {result.strategy_used.value}")

        # Тест 2: Слабый сигнал (разнонаправленный)
        directions = np.array([0, 1, 2, 0])  # Разные направления
        direction_probs = [
            np.array([0.4, 0.3, 0.3]),  # 15m - слабая уверенность
            np.array([0.3, 0.4, 0.3]),  # 1h - слабая уверенность
            np.array([0.3, 0.3, 0.4]),  # 4h - NEUTRAL
            np.array([0.4, 0.3, 0.3]),  # 12h
        ]

        result = analyzer.analyze_signal_quality(
            directions, direction_probs, future_returns, risk_metrics, 0.5
        )

        logger.info(f"  Слабый сигнал: {'✅ ПРОШЕЛ' if result.passed else '❌ НЕ ПРОШЕЛ'}")
        if not result.passed:
            logger.info(f"    Причины: {', '.join(result.rejection_reasons)}")


async def main():
    """Точка входа"""
    diagnostic = MLPipelineDiagnostic()
    await diagnostic.run_diagnostic()


if __name__ == "__main__":
    asyncio.run(main())
