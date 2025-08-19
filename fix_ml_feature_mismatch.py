#!/usr/bin/env python3
"""
Исправление несоответствия количества признаков в ML системе.

ПРОБЛЕМА:
- Система ожидает 240 признаков (features_240.py)
- Модель была обучена на 231 признаке (найдено в обучающем файле)
- Необходимо привести систему в соответствие с реальной моделью

РЕШЕНИЕ:
1. Обновить систему для работы с 231 признаком
2. Заменить текущую feature engineering на точную копию из обучения
3. Обновить конфигурацию ML системы
"""

import os
import shutil
import sys
from pathlib import Path

from core.logger import setup_logger
from production_features_config import PRODUCTION_FEATURES


class MLFeatureMismatchFixer:
    """Исправляет несоответствие количества признаков в ML системе"""

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.project_root = Path("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")
        self.backup_suffix = "_backup_240_features"

    def create_backup(self, file_path: Path) -> Path:
        """Создает резервную копию файла"""
        # Исправляем формат backup файла
        backup_path = file_path.parent / f"{file_path.stem}{self.backup_suffix}{file_path.suffix}"
        if not backup_path.exists():
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"📄 Создана резервная копия: {backup_path}")
        return backup_path

    def update_features_config(self) -> bool:
        """Обновляет конфигурацию признаков с 240 на 231"""

        config_file = self.project_root / "ml" / "config" / "features_240.py"

        if not config_file.exists():
            self.logger.error(f"❌ Файл конфигурации не найден: {config_file}")
            return False

        # Создаем backup
        self.create_backup(config_file)

        # Создаем новую конфигурацию
        new_config_content = f'''#!/usr/bin/env python3
"""
Точная конфигурация 231 признака для UnifiedPatchTST модели.
ОБНОВЛЕНО: Приведено в соответствие с реальной обученной моделью.

КРИТИЧНО: Эта конфигурация основана на ТОЧНОМ анализе обучающего файла BOT_AI_V2/ааа.py
"""

# Импорт точного списка признаков из анализа обучающего файла
from production_features_config import PRODUCTION_FEATURES, CRITICAL_FORMULAS

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
        print(f"❌ Неверное количество признаков: {{len(features)}} вместо {{len(required)}}")
        return False
    
    # Проверка точного соответствия
    for i, (feat, req) in enumerate(zip(features, required, strict=False)):
        if feat != req:
            print(f"❌ Несоответствие на позиции {{i}}: '{{feat}}' вместо '{{req}}'")
            return False
    
    return True


# Конфигурация для inference (обновлено)
FEATURE_CONFIG = {{
    "expected_features": {len(PRODUCTION_FEATURES)},  # Обновлено с 240 на 231
    "context_window": 96,  # Из model config
    "min_history": 240,  # Минимум данных для расчета
    "use_cache": True,
    "cache_ttl": 300,  # 5 минут
    "inference_mode": True,  # Для продакшена - генерировать только нужные признаки
    "feature_order_critical": True,  # НОВОЕ: порядок критично важен
    "use_training_exact": True,  # НОВОЕ: использовать точные формулы из обучения
}}

# Критические формулы из обучающего файла
TRAINING_FORMULAS = CRITICAL_FORMULAS

if __name__ == "__main__":
    # Тест обновленной конфигурации
    features = get_required_features_list()
    print(f"✅ Обновлена конфигурация: {{len(features)}} признаков")
    print(f"📊 Изменение: 240 → {{len(features)}} признаков")
    
    print("\\n🔧 Критические формулы:")
    for formula_name, formula in TRAINING_FORMULAS.items():
        print(f"  - {{formula_name}}: {{formula}}")
    
    print("\\n✅ Конфигурация готова к использованию")
'''

        # Записываем новую конфигурацию
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(new_config_content)

        self.logger.info(f"✅ Обновлена конфигурация признаков: {config_file}")
        return True

    def update_feature_engineering(self) -> bool:
        """Обновляет основной файл feature engineering"""

        fe_file = self.project_root / "ml" / "logic" / "feature_engineering_v2.py"

        if not fe_file.exists():
            self.logger.error(f"❌ Файл feature engineering не найден: {fe_file}")
            return False

        # Создаем backup
        self.create_backup(fe_file)

        # Патчим существующий файл для использования нового класса
        patch_content = '''
# === ПАТЧ ДЛЯ ИСПОЛЬЗОВАНИЯ ТОЧНЫХ ПРИЗНАКОВ ИЗ ОБУЧЕНИЯ ===
# Добавлено для исправления несоответствия 240 vs 231 признак

try:
    from ml.logic.training_exact_features import TrainingExactFeatures
    _TRAINING_EXACT_AVAILABLE = True
except ImportError:
    _TRAINING_EXACT_AVAILABLE = False

def create_features_exact_training(df, config, symbol=None):
    """Создает признаки используя ТОЧНЫЕ формулы из обучающего файла"""
    if not _TRAINING_EXACT_AVAILABLE:
        raise ImportError("TrainingExactFeatures не доступен")
    
    engineer = TrainingExactFeatures(config)
    return engineer.create_features(df, symbol)

# === КОНЕЦ ПАТЧА ===
'''

        # Читаем существующий файл
        with open(fe_file, encoding="utf-8") as f:
            content = f.read()

        # Добавляем патч в начало (после импортов)
        import_end = content.find("\n\nclass")
        if import_end == -1:
            import_end = content.find("\nclass")

        if import_end != -1:
            new_content = content[:import_end] + patch_content + content[import_end:]
        else:
            new_content = content + patch_content

        # Записываем обновленный файл
        with open(fe_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        self.logger.info(f"✅ Добавлен патч в feature engineering: {fe_file}")
        return True

    def update_ml_manager(self) -> bool:
        """Обновляет ML Manager для использования 231 признака"""

        ml_manager_file = self.project_root / "ml" / "ml_manager.py"

        if not ml_manager_file.exists():
            self.logger.warning(f"⚠️ ML Manager не найден: {ml_manager_file}")
            return True  # Не критично

        # Создаем backup
        self.create_backup(ml_manager_file)

        # Читаем файл
        with open(ml_manager_file, encoding="utf-8") as f:
            content = f.read()

        # Обновляем упоминания 240 на 231
        updated_content = content.replace("240", "231")
        updated_content = updated_content.replace("features_240", "features_231")

        # Добавляем импорт нового модуля
        if "from ml.logic.training_exact_features" not in updated_content:
            import_section = updated_content.find("from ml.logic.feature_engineering_v2")
            if import_section != -1:
                insert_point = updated_content.find("\n", import_section) + 1
                new_import = "from ml.logic.training_exact_features import create_production_feature_engineering\n"
                updated_content = (
                    updated_content[:insert_point] + new_import + updated_content[insert_point:]
                )

        # Записываем обновленный файл
        with open(ml_manager_file, "w", encoding="utf-8") as f:
            f.write(updated_content)

        self.logger.info(f"✅ Обновлен ML Manager: {ml_manager_file}")
        return True

    def create_verification_script(self) -> bool:
        """Создает скрипт для проверки исправлений"""

        verification_script = self.project_root / "verify_ml_fix.py"

        script_content = '''#!/usr/bin/env python3
"""
Проверка исправления несоответствия признаков в ML системе.
"""

import sys
import traceback
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

def test_feature_config():
    """Тестирует конфигурацию признаков"""
    try:
        from ml.config.features_240 import get_required_features_list, get_feature_count
        
        features = get_required_features_list()
        count = get_feature_count()
        
        print(f"✅ Конфигурация признаков: {count} признаков")
        print(f"   Первые 5: {features[:5]}")
        print(f"   Последние 5: {features[-5:]}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка в конфигурации признаков: {e}")
        traceback.print_exc()
        return False

def test_training_exact_features():
    """Тестирует класс точных признаков"""
    try:
        from ml.logic.training_exact_features import TrainingExactFeatures
        
        config = {"features": {}}
        engineer = TrainingExactFeatures(config)
        
        print(f"✅ TrainingExactFeatures инициализирован")
        print(f"   Ожидается признаков: {engineer.expected_feature_count}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка в TrainingExactFeatures: {e}")
        traceback.print_exc()
        return False

def test_production_config():
    """Тестирует производственную конфигурацию"""
    try:
        from production_features_config import PRODUCTION_FEATURES, CRITICAL_FORMULAS
        
        print(f"✅ Производственная конфигурация: {len(PRODUCTION_FEATURES)} признаков")
        print(f"   Критических формул: {len(CRITICAL_FORMULAS)}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка в производственной конфигурации: {e}")
        traceback.print_exc()
        return False

def main():
    """Основная функция проверки"""
    print("🔍 ПРОВЕРКА ИСПРАВЛЕНИЯ ML СИСТЕМЫ")
    print("=" * 40)
    
    tests = [
        ("Конфигурация признаков", test_feature_config),
        ("Точные признаки обучения", test_training_exact_features), 
        ("Производственная конфигурация", test_production_config),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\\n🧪 Тест: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ Тест провален: {test_name}")
    
    print(f"\\n📊 РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("✅ Все проверки пройдены! ML система исправлена.")
        return True
    else:
        print("❌ Некоторые проверки провалены. Требуется дополнительная настройка.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''

        with open(verification_script, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Делаем скрипт исполняемым
        os.chmod(verification_script, 0o755)

        self.logger.info(f"✅ Создан скрипт проверки: {verification_script}")
        return True

    def run_fix(self) -> bool:
        """Запускает полное исправление системы"""

        self.logger.info("🔧 ЗАПУСК ИСПРАВЛЕНИЯ ML СИСТЕМЫ")
        self.logger.info("=" * 50)

        steps = [
            ("Обновление конфигурации признаков", self.update_features_config),
            ("Обновление feature engineering", self.update_feature_engineering),
            ("Обновление ML Manager", self.update_ml_manager),
            ("Создание скрипта проверки", self.create_verification_script),
        ]

        success_count = 0

        for step_name, step_func in steps:
            self.logger.info(f"\\n🔄 {step_name}...")
            try:
                if step_func():
                    self.logger.info(f"✅ {step_name} - успешно")
                    success_count += 1
                else:
                    self.logger.error(f"❌ {step_name} - ошибка")
            except Exception as e:
                self.logger.error(f"❌ {step_name} - исключение: {e}")
                import traceback

                traceback.print_exc()

        self.logger.info(f"\\n📊 РЕЗУЛЬТАТ: {success_count}/{len(steps)} шагов выполнено")

        if success_count == len(steps):
            self.logger.info("\\n✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            self.logger.info("📝 Следующие шаги:")
            self.logger.info("   1. Запустите: python verify_ml_fix.py")
            self.logger.info("   2. Протестируйте ML систему")
            self.logger.info("   3. Если нужно откатить - используйте backup файлы")
            return True
        else:
            self.logger.error("\\n❌ ИСПРАВЛЕНИЕ ЗАВЕРШИЛОСЬ С ОШИБКАМИ!")
            return False


def main():
    """Основная функция"""
    fixer = MLFeatureMismatchFixer()
    return fixer.run_fix()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
