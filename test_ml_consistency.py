#!/usr/bin/env python3
"""
Простой тест согласованности ML pipeline
"""

import numpy as np


def test_ml_manager_interpretation(outputs):
    """Интерпретация как в ml_manager.py"""
    print("\n📊 ML Manager интерпретация:")
    
    # Извлекаем компоненты
    future_returns = outputs[0:4]
    direction_logits = outputs[4:16]  # 12 логитов
    risk_metrics = outputs[16:20]
    
    # Reshape логитов
    direction_logits_reshaped = direction_logits.reshape(4, 3)
    
    # Применяем softmax
    directions = []
    probs_list = []
    
    for i, logits in enumerate(direction_logits_reshaped):
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()
        probs_list.append(probs)
        direction = np.argmax(probs)
        directions.append(direction)
        
        print(f"  Таймфрейм {i}: логиты={logits.round(2)}, "
              f"вероятности={probs.round(3)}, направление={direction}")
    
    return directions, probs_list


def test_old_strategy_interpretation(outputs):
    """Старая интерпретация в strategy (неправильная)"""
    print("\n❌ Старая Strategy интерпретация (неправильная):")
    
    # Старый способ - НЕПРАВИЛЬНЫЙ
    directions = outputs[4:8]  # Берет только 4 значения вместо 12!
    long_probs = 1 / (1 + np.exp(-outputs[8:12]))  # Применяет sigmoid к логитам
    short_probs = 1 / (1 + np.exp(-outputs[12:16]))  # Применяет sigmoid к логитам
    
    print(f"  Directions (raw): {directions}")
    print(f"  Long probs (sigmoid): {long_probs.round(3)}")
    print(f"  Short probs (sigmoid): {short_probs.round(3)}")
    
    return directions, long_probs, short_probs


def test_new_strategy_interpretation(outputs):
    """Новая исправленная интерпретация в strategy"""
    print("\n✅ Новая Strategy интерпретация (исправленная):")
    
    # Новый способ - ПРАВИЛЬНЫЙ
    future_returns = outputs[0:4]
    direction_logits = outputs[4:16]  # 12 логитов
    risk_metrics = outputs[16:20]
    
    # Reshape и softmax как в ml_manager
    direction_logits_reshaped = direction_logits.reshape(4, 3)
    
    directions = []
    probs_list = []
    
    for i, logits in enumerate(direction_logits_reshaped):
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()
        probs_list.append(probs)
        direction = np.argmax(probs)
        directions.append(direction)
        
        print(f"  Таймфрейм {i}: логиты={logits.round(2)}, "
              f"вероятности={probs.round(3)}, направление={direction}")
    
    return directions, probs_list


def main():
    print("="*70)
    print("🔬 ТЕСТ СОГЛАСОВАННОСТИ ML PIPELINE")
    print("="*70)
    
    # Создаем тестовые выходы модели
    outputs = np.zeros(20)
    
    # Future returns
    outputs[0:4] = [0.002, 0.003, 0.004, 0.005]
    
    # Direction logits - устанавливаем явное направление LONG
    # Для каждого таймфрейма (4 штуки) по 3 логита [LONG, SHORT, NEUTRAL]
    for i in range(4):
        base_idx = 4 + i * 3
        outputs[base_idx] = 2.0      # LONG logit (высокий)
        outputs[base_idx + 1] = 0.5  # SHORT logit (низкий)
        outputs[base_idx + 2] = 0.1  # NEUTRAL logit (низкий)
    
    # Risk metrics
    outputs[16:20] = [0.01, 0.01, 0.02, 0.02]
    
    print(f"\n📥 Входные данные (20 выходов модели):")
    print(f"  [0-3] Returns: {outputs[0:4]}")
    print(f"  [4-15] Logits: {outputs[4:16]}")
    print(f"  [16-19] Risks: {outputs[16:20]}")
    
    # Тестируем разные интерпретации
    ml_dirs, ml_probs = test_ml_manager_interpretation(outputs)
    old_dirs, old_long, old_short = test_old_strategy_interpretation(outputs)
    new_dirs, new_probs = test_new_strategy_interpretation(outputs)
    
    # Сравнение результатов
    print("\n" + "="*70)
    print("📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
    print("="*70)
    
    print(f"\nНаправления:")
    print(f"  ML Manager:     {ml_dirs}")
    print(f"  Strategy (old): {old_dirs[:4] if len(old_dirs) >= 4 else 'ОШИБКА - только 4 значения!'}")
    print(f"  Strategy (new): {new_dirs}")
    
    if ml_dirs == new_dirs:
        print("\n✅ ML Manager и новая Strategy СОВПАДАЮТ!")
    else:
        print("\n❌ ML Manager и новая Strategy НЕ СОВПАДАЮТ!")
    
    # Проверяем проблему со старой интерпретацией
    print("\n⚠️  ПРОБЛЕМА со старой интерпретацией:")
    print(f"  - Использует только outputs[4:8] = {outputs[4:8]}")
    print(f"  - Это первые 4 логита из 12, а не направления!")
    print(f"  - Применяет sigmoid вместо softmax")
    print(f"  - Результат: неправильные направления и вероятности")


if __name__ == "__main__":
    main()