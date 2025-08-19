#!/usr/bin/env python3
"""
Исправляет все type annotations с | None на Optional[]
"""

import re
from pathlib import Path


def fix_type_annotations(file_path):
    """Исправляет type annotations в файле"""

    with open(file_path) as f:
        content = f.read()

    original = content

    # Паттерны для замены
    patterns = [
        # Простые типы: int | None -> Optional[int]
        (r"\b(int|float|str|bool|dict|list|tuple|set|Any)\s*\|\s*None\b", r"Optional[\1]"),
        # Сложные типы с квадратными скобками: dict[str, Any] | None -> Optional[dict[str, Any]]
        (r"\b(dict|list|tuple|set)\[([^\]]+)\]\s*\|\s*None\b", r"Optional[\1[\2]]"),
        # Классы: ClassName | None -> Optional[ClassName]
        (r"\b([A-Z][a-zA-Z0-9_]*)\s*\|\s*None\b", r"Optional[\1]"),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    # Добавляем импорт Optional если его нет и были изменения
    if content != original and "Optional" in content:
        if (
            "from typing import" in content
            and "Optional" not in content[: content.find("from typing import") + 200]
        ):
            # Добавляем Optional к существующему импорту
            content = re.sub(
                r"(from typing import[^\\n]+)",
                lambda m: m.group(1) + (", Optional" if "Optional" not in m.group(1) else ""),
                content,
                count=1,
            )
        elif "from typing import" not in content and "import" in content:
            # Добавляем новый импорт после первого импорта
            first_import = content.find("import")
            end_of_line = content.find("\n", first_import)
            content = (
                content[: end_of_line + 1]
                + "from typing import Optional\n"
                + content[end_of_line + 1 :]
            )

    if content != original:
        with open(file_path, "w") as f:
            f.write(content)
        return True
    return False


def main():
    """Исправляет все файлы в web/"""

    web_dir = Path("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/web")

    fixed_files = []

    for py_file in web_dir.rglob("*.py"):
        if "backup" in str(py_file) or "__pycache__" in str(py_file):
            continue

        if fix_type_annotations(py_file):
            fixed_files.append(py_file)
            print(f"✅ Fixed: {py_file.relative_to(web_dir.parent)}")

    print(f"\n📊 Исправлено файлов: {len(fixed_files)}")

    return len(fixed_files)


if __name__ == "__main__":
    main()
