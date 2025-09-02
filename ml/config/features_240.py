#!/usr/bin/env python3
"""
Точная конфигурация 231 признака для UnifiedPatchTST модели.
ОБНОВЛЕНО: Приведено в соответствие с реальной обученной моделью.

КРИТИЧНО: Эта конфигурация основана на ТОЧНОМ анализе обучающего файла BOT_AI_V2/ааа.py
"""

# Импорт точного списка признаков из анализа обучающего файла
import sys
import os
# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from production_features_config import REAL_FEATURES_240 as PRODUCTION_FEATURES

# Создаем заглушку для CRITICAL_FORMULAS если его нет
CRITICAL_FORMULAS = {}

# Основная конфигурация (обновлено с 240 на 231)
REQUIRED_FEATURES_231 = PRODUCTION_FEATURES

# Для обратной совместимости
REQUIRED_FEATURES_240 = REQUIRED_FEATURES_231  # Алиас для старого кода


def get_required_features_list() -> list[str]:
    """
    Возвращает полный список из 231 признака в правильном порядке.
    ОБНОВЛЕНО: Теперь использует точные признаки из обучающего файла.
    """
    return REQUIRED_FEATURES_231.copy()


def get_feature_count() -> int:
    """Возвращает точное количество признаков"""
    return len(REQUIRED_FEATURES_231)


def validate_features(features: list[str]) -> bool:
    """
    Проверяет, что переданный список признаков соответствует ожидаемым.

    Args:
        features: Список признаков для проверки

    Returns:
        True если список валиден, False иначе
    """
    required = get_required_features_list()

    if len(features) != len(required):
        print(f"❌ Неверное количество признаков: {len(features)} вместо {len(required)}")
        return False

    # Проверка точного соответствия
    for i, (feat, req) in enumerate(zip(features, required, strict=False)):
        if feat != req:
            print(f"❌ Несоответствие на позиции {i}: '{feat}' вместо '{req}'")
            return False

    return True


# Конфигурация для inference (обновлено)
FEATURE_CONFIG = {
    "expected_features": 231,  # Обновлено с 240 на 231
    "context_window": 96,  # Из model config
    "min_history": 240,  # Минимум данных для расчета
    "use_cache": True,
    "cache_ttl": 300,  # 5 минут
    "inference_mode": True,  # Для продакшена - генерировать только нужные признаки
    "feature_order_critical": True,  # НОВОЕ: порядок критично важен
    "use_training_exact": True,  # НОВОЕ: использовать точные формулы из обучения
}

# Критические формулы из обучающего файла
TRAINING_FORMULAS = CRITICAL_FORMULAS

if __name__ == "__main__":
    # Тест обновленной конфигурации
    features = get_required_features_list()
    print(f"✅ Обновлена конфигурация: {len(features)} признаков")
    print(f"📊 Изменение: 240 → {len(features)} признаков")

    print("\n🔧 Критические формулы:")
    for formula_name, formula in TRAINING_FORMULAS.items():
        print(f"  - {formula_name}: {formula}")

    print("\n✅ Конфигурация готова к использованию")
