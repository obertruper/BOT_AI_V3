#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации работы улучшенной системы фильтрации сигналов
"""

import numpy as np
import asyncio
from pathlib import Path
import yaml

# Добавляем путь к проекту
import sys
sys.path.append(str(Path(__file__).parent))

from ml.logic.signal_quality_analyzer import SignalQualityAnalyzer, FilterStrategy
from core.logger import setup_logger

logger = setup_logger("test_signal_filtering")


def load_test_config():
    """Загружает тестовую конфигурацию"""
    config_path = Path("config/ml/ml_config.yaml")
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        # Базовая конфигурация для теста
        return {
            "signal_filtering": {
                "strategy": "moderate",
                "timeframe_weights": [0.25, 0.25, 0.35, 0.15],
                "main_timeframe_index": 2,
                "conservative": {
                    "min_timeframe_agreement": 3,
                    "required_confidence_per_timeframe": 0.65,
                    "main_timeframe_required_confidence": 0.70,
                    "min_expected_return_pct": 0.008,
                    "min_signal_strength": 0.7,
                    "max_risk_level": "MEDIUM",
                    "min_quality_score": 0.75,
                },
                "moderate": {
                    "min_timeframe_agreement": 2,
                    "required_confidence_per_timeframe": 0.55,
                    "main_timeframe_required_confidence": 0.65,
                    "alternative_main_plus_one": True,
                    "alternative_confidence_threshold": 0.75,
                    "min_expected_return_pct": 0.005,
                    "min_signal_strength": 0.5,
                    "max_risk_level": "HIGH",
                    "min_quality_score": 0.60,
                },
                "aggressive": {
                    "min_timeframe_agreement": 1,
                    "required_confidence_per_timeframe": 0.45,
                    "main_timeframe_required_confidence": 0.55,
                    "min_expected_return_pct": 0.003,
                    "min_signal_strength": 0.4,
                    "max_risk_level": "HIGH",
                    "min_quality_score": 0.45,
                },
                "quality_weights": {
                    "agreement": 0.35,
                    "confidence": 0.30,
                    "return_expectation": 0.20,
                    "risk_adjustment": 0.15,
                }
            }
        }


def create_test_scenarios():
    """Создает тестовые сценарии с разными типами сигналов"""
    scenarios = []
    
    # Сценарий 1: Сильный LONG сигнал (все таймфреймы согласны)
    scenarios.append({
        "name": "Strong LONG - All timeframes agree",
        "directions": np.array([0, 0, 0, 0]),  # Все LONG
        "direction_probs": [
            np.array([0.8, 0.1, 0.1]),  # 15m: сильный LONG
            np.array([0.75, 0.15, 0.1]), # 1h: сильный LONG
            np.array([0.9, 0.05, 0.05]), # 4h: очень сильный LONG
            np.array([0.7, 0.2, 0.1])    # 12h: сильный LONG
        ],
        "future_returns": np.array([0.012, 0.015, 0.020, 0.018]),  # Хорошие доходности
        "risk_metrics": np.array([0.2, 0.15, 0.1, 0.25]),  # Низкий риск
    })
    
    # Сценарий 2: Конфликтующие сигналы
    scenarios.append({
        "name": "Conflicting signals - Mixed directions",
        "directions": np.array([2, 1, 0, 0]),  # NEUTRAL, SHORT, LONG, LONG
        "direction_probs": [
            np.array([0.3, 0.3, 0.4]),   # 15m: слабый NEUTRAL
            np.array([0.2, 0.6, 0.2]),   # 1h: средний SHORT
            np.array([0.7, 0.2, 0.1]),   # 4h: сильный LONG
            np.array([0.65, 0.25, 0.1])  # 12h: сильный LONG
        ],
        "future_returns": np.array([0.006, 0.008, 0.008, 0.006]),
        "risk_metrics": np.array([0.4, 0.5, 0.3, 0.35]),
    })
    
    # Сценарий 3: Слабый сигнал (низкая уверенность)
    scenarios.append({
        "name": "Weak signal - Low confidence",
        "directions": np.array([0, 0, 1, 2]),  # LONG, LONG, SHORT, NEUTRAL
        "direction_probs": [
            np.array([0.4, 0.35, 0.25]),  # 15m: слабый LONG
            np.array([0.45, 0.3, 0.25]),  # 1h: слабый LONG
            np.array([0.3, 0.5, 0.2]),    # 4h: средний SHORT
            np.array([0.3, 0.3, 0.4])     # 12h: слабый NEUTRAL
        ],
        "future_returns": np.array([0.003, 0.002, 0.004, 0.001]),
        "risk_metrics": np.array([0.6, 0.7, 0.8, 0.65]),  # Высокий риск
    })
    
    # Сценарий 4: Умеренный LONG (основной ТФ поддерживает)
    scenarios.append({
        "name": "Moderate LONG - Main timeframe supports",
        "directions": np.array([1, 0, 0, 2]),  # SHORT, LONG, LONG, NEUTRAL
        "direction_probs": [
            np.array([0.2, 0.6, 0.2]),   # 15m: средний SHORT
            np.array([0.7, 0.2, 0.1]),   # 1h: сильный LONG
            np.array([0.8, 0.15, 0.05]), # 4h: очень сильный LONG (основной!)
            np.array([0.3, 0.3, 0.4])    # 12h: слабый NEUTRAL
        ],
        "future_returns": np.array([0.002, 0.008, 0.012, 0.005]),
        "risk_metrics": np.array([0.3, 0.25, 0.2, 0.35]),
    })
    
    return scenarios


def test_strategy_filtering(analyzer: SignalQualityAnalyzer, scenario: dict, strategy: str):
    """Тестирует фильтрацию для конкретной стратегии"""
    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 ТЕСТ: {scenario['name']} | Стратегия: {strategy.upper()}")
    logger.info(f"{'='*80}")
    
    # Переключаем стратегию
    analyzer.switch_strategy(strategy)
    
    # Рассчитываем weighted_direction
    weights = np.array([0.4, 0.3, 0.2, 0.1])
    weighted_direction = np.sum(scenario['directions'] * weights)
    
    # Анализируем качество
    result = analyzer.analyze_signal_quality(
        directions=scenario['directions'],
        direction_probs=scenario['direction_probs'],
        future_returns=scenario['future_returns'],
        risk_metrics=scenario['risk_metrics'],
        weighted_direction=weighted_direction
    )
    
    # Выводим результат
    status = "✅ ПРИНЯТ" if result.passed else "❌ ОТКЛОНЕН"
    logger.info(f"{status} - {result.signal_type}")
    
    if result.passed:
        metrics = result.quality_metrics
        logger.info(f"📊 Метрики качества:")
        logger.info(f"   Agreement: {metrics.agreement_score:.3f}")
        logger.info(f"   Confidence: {metrics.confidence_score:.3f}")
        logger.info(f"   Return: {metrics.return_score:.3f}")
        logger.info(f"   Risk: {metrics.risk_score:.3f}")
        logger.info(f"   Quality: {metrics.quality_score:.3f}")
    else:
        logger.info(f"🚫 Причины отклонения:")
        for reason in result.rejection_reasons:
            logger.info(f"   - {reason}")
    
    return result


def main():
    """Основная функция тестирования"""
    logger.info("🚀 Запуск тестирования системы фильтрации сигналов")
    
    # Загружаем конфигурацию
    config = load_test_config()
    
    # Создаем анализатор
    analyzer = SignalQualityAnalyzer(config)
    
    # Загружаем тестовые сценарии
    scenarios = create_test_scenarios()
    strategies = ["conservative", "moderate", "aggressive"]
    
    # Результаты тестов
    results = {}
    
    # Тестируем каждый сценарий с каждой стратегией
    for scenario in scenarios:
        scenario_name = scenario['name']
        results[scenario_name] = {}
        
        for strategy in strategies:
            result = test_strategy_filtering(analyzer, scenario, strategy)
            results[scenario_name][strategy] = {
                "passed": result.passed,
                "signal_type": result.signal_type,
                "quality_score": result.quality_metrics.quality_score if result.passed else 0.0,
                "rejection_reasons": result.rejection_reasons
            }
    
    # Выводим сводную таблицу
    logger.info(f"\n{'='*100}")
    logger.info("📋 СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    logger.info(f"{'='*100}")
    
    header = f"{'Сценарий':<40} {'Conservative':<15} {'Moderate':<15} {'Aggressive':<15}"
    logger.info(header)
    logger.info("-" * 100)
    
    for scenario_name, scenario_results in results.items():
        row = f"{scenario_name:<40}"
        
        for strategy in strategies:
            result = scenario_results[strategy]
            if result['passed']:
                status = f"✅ {result['signal_type']}"
                quality = f"({result['quality_score']:.2f})"
                cell = f"{status} {quality}"
            else:
                cell = "❌ ОТКЛОНЕН"
            
            row += f" {cell:<15}"
        
        logger.info(row)
    
    # Выводим статистику анализатора
    logger.info(f"\n{'='*60}")
    logger.info("📊 СТАТИСТИКА АНАЛИЗАТОРА")
    logger.info(f"{'='*60}")
    
    stats = analyzer.get_strategy_statistics()
    for key, value in stats.items():
        logger.info(f"{key}: {value}")
    
    logger.info("\n🎉 Тестирование завершено!")


if __name__ == "__main__":
    main()