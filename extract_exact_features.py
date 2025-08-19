#!/usr/bin/env python3
"""
Точное извлечение всех признаков из обучающего файла BOT_AI_V2/ааа.py
Парсит код и находит ВСЕ строки df['feature_name'] = для получения точного списка.
"""

import re


def extract_features_from_code(file_path: str) -> list[str]:
    """Извлекает все признаки из Python кода, анализируя присваивания df[...]"""

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    features = []

    # Паттерны для поиска всех видов присваиваний к df
    patterns = [
        # df['feature'] = ...
        r"df\['([^']+)'\]\s*=",
        # df["feature"] = ...
        r'df\["([^"]+)"\]\s*=',
        # Базовые f-строки без переменных
        r"df\[f'([^{}']+)'\]\s*=",
        r'df\[f"([^{}"]+)"\]\s*=',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content)
        features.extend(matches)

    # Обработка f-строк с переменными (более сложный случай)
    # Найдем все циклы и проанализируем их

    # Паттерн: for variable_name in [values]:
    for_loops = re.findall(r"for\s+(\w+)\s+in\s+\[([^\]]+)\]:", content)

    for var_name, values_str in for_loops:
        try:
            # Парсим значения из цикла
            values = eval(f"[{values_str}]")

            # Найти блок кода после цикла (до следующего def или конца функции)
            loop_start = content.find(f"for {var_name} in [{values_str}]:")
            if loop_start == -1:
                continue

            # Найти конец блока цикла
            loop_lines = content[loop_start:].split("\n")
            loop_code = []

            in_loop = False
            base_indent = None

            for line in loop_lines:
                if f"for {var_name} in" in line:
                    in_loop = True
                    base_indent = len(line) - len(line.lstrip())
                    continue

                if in_loop:
                    if line.strip() == "":
                        continue

                    current_indent = len(line) - len(line.lstrip())

                    # Если отступ равен или меньше базового, цикл закончился
                    if current_indent <= base_indent:
                        break

                    loop_code.append(line)

            # Ищем паттерны присваивания в коде цикла
            loop_text = "\n".join(loop_code)

            # f-строки в цикле
            f_string_patterns = [
                rf"df\[f'([^']*\{{{var_name}}}[^']*)'\]\s*=",
                rf'df\[f"([^"]*\{{{var_name}}}[^"]*)"\]\s*=',
            ]

            for pattern in f_string_patterns:
                f_matches = re.findall(pattern, loop_text)
                for f_template in f_matches:
                    for value in values:
                        feature_name = f_template.format(**{var_name: value})
                        features.append(feature_name)

        except Exception as e:
            print(f"Ошибка обработки цикла for {var_name}: {e}")
            continue

    # Убираем дубликаты, сохраняя порядок
    unique_features = []
    seen = set()
    for feature in features:
        if feature not in seen:
            unique_features.append(feature)
            seen.add(feature)

    return unique_features


def analyze_feature_sections(file_path: str) -> dict[str, list[str]]:
    """Анализирует признаки по секциям функций"""

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Найти все функции создания признаков
    section_pattern = r"def (_create_\w+_features?)\(.*?\):.*?(?=def\s|\Z)"
    sections = re.findall(section_pattern, content, re.DOTALL)

    section_features = {}

    for section_name in sections:
        # Найти код функции
        func_start = content.find(f"def {section_name}(")
        if func_start == -1:
            continue

        # Найти следующую функцию или конец файла
        next_func = content.find("\n    def ", func_start + 1)
        if next_func == -1:
            func_content = content[func_start:]
        else:
            func_content = content[func_start:next_func]

        # Извлечь признаки из этой функции
        section_features[section_name] = extract_features_from_code_snippet(func_content)

    return section_features


def extract_features_from_code_snippet(code_snippet: str) -> list[str]:
    """Извлекает признаки из фрагмента кода"""
    features = []

    # Паттерны для поиска присваиваний
    patterns = [
        r"df\['([^']+)'\]\s*=",
        r'df\["([^"]+)"\]\s*=',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, code_snippet)
        features.extend(matches)

    # Обработка циклов в фрагменте
    for_loops = re.findall(r"for\s+(\w+)\s+in\s+\[([^\]]+)\]:", code_snippet)

    for var_name, values_str in for_loops:
        try:
            values = eval(f"[{values_str}]")

            # Найти f-строки в этом фрагменте
            f_patterns = [
                rf"df\[f'([^']*\{{{var_name}}}[^']*)'\]\s*=",
                rf'df\[f"([^"]*\{{{var_name}}}[^"]*)"\]\s*=',
            ]

            for pattern in f_patterns:
                f_matches = re.findall(pattern, code_snippet)
                for f_template in f_matches:
                    for value in values:
                        feature_name = f_template.format(**{var_name: value})
                        features.append(feature_name)

        except:
            pass

    # Убираем дубликаты
    unique_features = []
    seen = set()
    for feature in features:
        if feature not in seen:
            unique_features.append(feature)
            seen.add(feature)

    return unique_features


def main():
    """Основная функция анализа"""
    training_file = "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/BOT_AI_V2/ааа.py"

    print("🔍 ИЗВЛЕЧЕНИЕ ТОЧНЫХ ПРИЗНАКОВ ИЗ ОБУЧАЮЩЕГО ФАЙЛА")
    print("=" * 60)

    # Извлечение всех признаков
    all_features = extract_features_from_code(training_file)
    print(f"📊 Найдено {len(all_features)} уникальных признаков")

    # Анализ по секциям
    section_features = analyze_feature_sections(training_file)

    print("\n📋 ПРИЗНАКИ ПО СЕКЦИЯМ:")
    print("-" * 40)

    total_by_sections = 0
    for section_name, features in section_features.items():
        print(f"  {section_name:25}: {len(features):3d} признаков")
        total_by_sections += len(features)

    print(f"  {'ИТОГО по секциям':<25}: {total_by_sections:3d} признаков")
    print(f"  {'ВСЕГО уникальных':<25}: {len(all_features):3d} признаков")

    # Подробный список всех признаков
    print("\n📝 ПОЛНЫЙ СПИСОК ПРИЗНАКОВ:")
    print("-" * 40)
    for i, feature in enumerate(all_features, 1):
        print(f"  {i:3d}. {feature}")

    # Сохранение результатов
    with open("exact_training_features.py", "w", encoding="utf-8") as f:
        f.write('"""Точный список признаков из обучающего файла BOT_AI_V2/ааа.py"""\n\n')
        f.write("# Признаки, найденные в коде:\n")
        f.write("EXACT_TRAINING_FEATURES = [\n")
        for feature in all_features:
            f.write(f'    "{feature}",\n')
        f.write("]\n\n")
        f.write(f"# Общее количество: {len(all_features)} признаков\n\n")

        # Добавляем разбивку по секциям
        f.write("# Признаки по секциям:\n")
        for section_name, features in section_features.items():
            f.write(f"# {section_name}: {len(features)} признаков\n")
            f.write(
                f"{section_name.upper().replace('_CREATE_', '').replace('_FEATURES', '')}_FEATURES = [\n"
            )
            for feature in features:
                f.write(f'    "{feature}",\n')
            f.write("]\n\n")

    print("\n✅ Анализ завершен!")
    print("🐍 Точный список сохранен в: exact_training_features.py")
    print(f"📊 Найдено {len(all_features)} уникальных признаков")

    return all_features, section_features


if __name__ == "__main__":
    main()
