#!/usr/bin/env python3
"""
Демонстрация переключения стратегий фильтрации и анализа их эффективности
"""


# Добавляем путь к проекту
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger
from ml.logic.signal_quality_analyzer import SignalQualityAnalyzer

logger = setup_logger("demo_strategy_switching")


def load_config():
    """Загружает конфигурацию из файла"""
    config_path = Path("config/ml/ml_config.yaml")

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    else:
        logger.error("❌ Файл конфигурации не найден!")
        return None


def create_sample_signal():
    """Создает пример реального сигнала с умеренным качеством"""
    return {
        "name": "Real-world example",
        "directions": np.array([0, 0, 1, 2]),  # LONG, LONG, SHORT, NEUTRAL
        "direction_probs": [
            np.array([0.65, 0.25, 0.10]),  # 15m: хороший LONG
            np.array([0.70, 0.20, 0.10]),  # 1h: хороший LONG
            np.array([0.30, 0.60, 0.10]),  # 4h: средний SHORT
            np.array([0.35, 0.30, 0.35]),  # 12h: неопределенность
        ],
        "future_returns": np.array([0.008, 0.006, -0.004, 0.002]),
        "risk_metrics": np.array([0.3, 0.4, 0.5, 0.35]),
    }


def analyze_with_strategy(analyzer: SignalQualityAnalyzer, signal: dict, strategy: str):
    """Анализирует сигнал с заданной стратегией"""
    logger.info(f"\n{'='*50}")
    logger.info(f"🔍 АНАЛИЗ С СТРАТЕГИЕЙ: {strategy.upper()}")
    logger.info(f"{'='*50}")

    # Переключаем стратегию
    analyzer.switch_strategy(strategy)

    # Рассчитываем weighted_direction
    weights = np.array([0.4, 0.3, 0.2, 0.1])
    weighted_direction = np.sum(signal["directions"] * weights)

    # Анализируем качество
    result = analyzer.analyze_signal_quality(
        directions=signal["directions"],
        direction_probs=signal["direction_probs"],
        future_returns=signal["future_returns"],
        risk_metrics=signal["risk_metrics"],
        weighted_direction=weighted_direction,
    )

    # Выводим результат
    if result.passed:
        logger.info(f"✅ СИГНАЛ ПРИНЯТ: {result.signal_type}")
        metrics = result.quality_metrics
        logger.info(f"📊 Качество: {metrics.quality_score:.3f}")
        logger.info(f"🎯 Согласованность: {metrics.agreement_score:.3f}")
        logger.info(f"🎲 Уверенность: {metrics.confidence_score:.3f}")
        logger.info(f"📈 Доходность: {metrics.return_score:.3f}")
        logger.info(f"⚠️ Риск: {metrics.risk_level}")
    else:
        logger.info("❌ СИГНАЛ ОТКЛОНЕН")
        logger.info("🚫 Причины:")
        for reason in result.rejection_reasons:
            logger.info(f"   - {reason}")

    return result


def main():
    """Основная функция демонстрации"""
    logger.info("🚀 Демонстрация переключения стратегий фильтрации")

    # Загружаем конфигурацию
    config = load_config()
    if not config:
        return

    # Создаем анализатор
    analyzer = SignalQualityAnalyzer(config)

    # Создаем пример сигнала
    signal = create_sample_signal()

    logger.info("\n📊 ИСХОДНЫЕ ДАННЫЕ СИГНАЛА:")
    logger.info(f"   Направления по ТФ: {signal['directions']} [0=LONG, 1=SHORT, 2=NEUTRAL]")
    logger.info(f"   Доходности: {signal['future_returns']}")
    logger.info(f"   Максимальные вероятности: {[np.max(p) for p in signal['direction_probs']]}")

    # Тестируем все стратегии
    strategies = ["conservative", "moderate", "aggressive"]
    results = {}

    for strategy in strategies:
        result = analyze_with_strategy(analyzer, signal, strategy)
        results[strategy] = result

    # Сводная таблица
    logger.info(f"\n{'='*60}")
    logger.info("📋 СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    logger.info(f"{'='*60}")

    logger.info(f"{'Стратегия':<15} {'Результат':<15} {'Качество':<10} {'Причины отклонения'}")
    logger.info("-" * 80)

    for strategy, result in results.items():
        if result.passed:
            status = f"✅ {result.signal_type}"
            quality = f"{result.quality_metrics.quality_score:.3f}"
            reasons = "Н/Д"
        else:
            status = "❌ ОТКЛОНЕН"
            quality = "0.000"
            reasons = "; ".join(result.rejection_reasons[:2])  # Первые 2 причины
            if len(result.rejection_reasons) > 2:
                reasons += "..."

        logger.info(f"{strategy:<15} {status:<15} {quality:<10} {reasons}")

    # Статистика анализатора
    logger.info(f"\n{'='*40}")
    logger.info("📊 СТАТИСТИКА АНАЛИЗАТОРА")
    logger.info(f"{'='*40}")

    stats = analyzer.get_strategy_statistics()
    for key, value in stats.items():
        if key != "top_rejection_reasons":
            logger.info(f"{key}: {value}")

    if stats.get("top_rejection_reasons"):
        logger.info("\n🚫 Топ причины отклонения:")
        for reason, count in stats["top_rejection_reasons"].items():
            logger.info(f"   - {reason}: {count}")

    # Рекомендации
    logger.info(f"\n{'='*50}")
    logger.info("💡 РЕКОМЕНДАЦИИ ПО ИСПОЛЬЗОВАНИЮ")
    logger.info(f"{'='*50}")

    passed_strategies = [s for s, r in results.items() if r.passed]

    if len(passed_strategies) == 3:
        logger.info("✅ Сигнал высокого качества - подходят все стратегии")
        logger.info("💰 Рекомендация: Используйте conservative для максимальной надежности")
    elif len(passed_strategies) == 2:
        logger.info(f"⚡ Сигнал среднего качества - подходят: {', '.join(passed_strategies)}")
        logger.info("🎯 Рекомендация: Moderate стратегия для сбалансированного подхода")
    elif len(passed_strategies) == 1:
        logger.info(f"⚠️ Сигнал низкого качества - подходит только: {passed_strategies[0]}")
        logger.info("🚨 Рекомендация: Используйте с осторожностью")
    else:
        logger.info("❌ Сигнал очень низкого качества - отклонен всеми стратегиями")
        logger.info("🛑 Рекомендация: НЕ торговать по этому сигналу")

    logger.info("\n🎉 Демонстрация завершена!")


if __name__ == "__main__":
    main()
