#!/usr/bin/env python3
"""
🧹 Interactive Code Cleanup Tool
Безопасная интерактивная очистка неиспользуемых файлов с предварительным просмотром
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class InteractiveCodeCleanup:
    """Интерактивная очистка кода с предварительным просмотром"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results_dir = project_root / "analysis_results"
        self.backup_dir = None
        self.removed_files = []
        self.skipped_files = []

    def load_latest_analysis(self) -> dict | None:
        """Загружает последний анализ кода"""
        json_files = list(self.results_dir.glob("code_usage_analysis_*.json"))
        if not json_files:
            return None

        latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
        with open(latest_file) as f:
            return json.load(f)

    def create_backup_directory(self) -> Path:
        """Создает директорию бэкапа"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / f"code_cleanup_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        self.backup_dir = backup_dir
        return backup_dir

    def preview_file(self, file_path: str, max_lines: int = 20) -> None:
        """Показывает превью файла"""
        full_path = self.project_root / file_path

        if not full_path.exists():
            print(f"{Colors.FAIL}❌ File not found: {file_path}{Colors.ENDC}")
            return

        try:
            with open(full_path, encoding="utf-8") as f:
                lines = f.readlines()

            print(f"\n{Colors.CYAN}📄 Preview of {file_path}:{Colors.ENDC}")
            print("-" * 60)

            for i, line in enumerate(lines[:max_lines], 1):
                print(f"{i:3}: {line.rstrip()}")

            if len(lines) > max_lines:
                print(f"... and {len(lines) - max_lines} more lines")

            print("-" * 60)
            print(f"File size: {full_path.stat().st_size} bytes")
            print(f"Last modified: {datetime.fromtimestamp(full_path.stat().st_mtime)}")

        except (UnicodeDecodeError, PermissionError) as e:
            print(f"{Colors.WARNING}⚠️ Could not read file: {e}{Colors.ENDC}")

    def backup_and_remove_file(self, file_path: str) -> bool:
        """Создает бэкап и удаляет файл"""
        full_path = self.project_root / file_path

        if not full_path.exists():
            print(f"{Colors.WARNING}⚠️ File not found: {file_path}{Colors.ENDC}")
            return False

        try:
            # Создаем структуру директорий в бэкапе
            backup_file = self.backup_dir / file_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)

            # Копируем в бэкап
            shutil.copy2(full_path, backup_file)

            # Удаляем оригинал
            full_path.unlink()

            self.removed_files.append(file_path)
            return True

        except Exception as e:
            print(f"{Colors.FAIL}❌ Error removing {file_path}: {e}{Colors.ENDC}")
            return False

    def interactive_cleanup(self, unused_files: list[str]) -> None:
        """Интерактивная очистка файлов"""
        if not unused_files:
            print(f"{Colors.GREEN}✅ No unused files to clean up!{Colors.ENDC}")
            return

        backup_dir = self.create_backup_directory()
        print(f"{Colors.GREEN}📦 Created backup directory: {backup_dir}{Colors.ENDC}")

        print(f"\n{Colors.BOLD}🧹 Interactive File Cleanup{Colors.ENDC}")
        print(f"Found {len(unused_files)} unused files")
        print("Commands: [y]es, [n]o, [v]iew, [s]kip all, [q]uit")
        print("-" * 60)

        for i, file_path in enumerate(unused_files, 1):
            print(f"\n{Colors.CYAN}[{i}/{len(unused_files)}]{Colors.ENDC} {file_path}")

            while True:
                choice = input("Remove this file? [y/n/v/s/q]: ").lower().strip()

                if choice == "y":
                    if self.backup_and_remove_file(file_path):
                        print(f"{Colors.GREEN}✅ Removed: {file_path}{Colors.ENDC}")
                    break

                elif choice == "n":
                    self.skipped_files.append(file_path)
                    print(f"{Colors.WARNING}⏭️ Skipped: {file_path}{Colors.ENDC}")
                    break

                elif choice == "v":
                    self.preview_file(file_path)
                    continue

                elif choice == "s":
                    remaining_files = unused_files[i - 1 :]
                    self.skipped_files.extend(remaining_files)
                    print(
                        f"{Colors.WARNING}⏭️ Skipped remaining {len(remaining_files)} files{Colors.ENDC}"
                    )
                    return

                elif choice == "q":
                    print(f"{Colors.CYAN}👋 Cleanup cancelled{Colors.ENDC}")
                    return

                else:
                    print(f"{Colors.WARNING}Invalid choice. Use y/n/v/s/q{Colors.ENDC}")

    def cleanup_by_category(self, unused_files: list[str]) -> None:
        """Очистка по категориям файлов"""
        # Группируем файлы по категориям
        categories = {
            "debug_files": [f for f in unused_files if "debug" in f.lower()],
            "temp_analysis": [
                f
                for f in unused_files
                if any(x in f.lower() for x in ["analyze", "check", "final", "temp"])
            ],
            "old_strategies": [f for f in unused_files if "strategies/" in f],
            "unused_ml": [
                f
                for f in unused_files
                if "ml/" in f and f not in categories.get("temp_analysis", [])
            ],
            "other": [],
        }

        # Добавляем файлы которые не попали ни в одну категорию
        categorized = set()
        for cat_files in categories.values():
            categorized.update(cat_files)
        categories["other"] = [f for f in unused_files if f not in categorized]

        # Убираем пустые категории
        categories = {k: v for k, v in categories.items() if v}

        print(f"\n{Colors.BOLD}📂 Cleanup by Categories:{Colors.ENDC}")

        for category, files in categories.items():
            if not files:
                continue

            print(
                f"\n{Colors.CYAN}📁 {category.replace('_', ' ').title()} ({len(files)} files):{Colors.ENDC}"
            )
            for file_path in files[:5]:  # Показываем первые 5
                print(f"  • {file_path}")
            if len(files) > 5:
                print(f"  • ... and {len(files) - 5} more files")

            choice = (
                input(f"Remove all {len(files)} files in this category? [y/n/v]: ").lower().strip()
            )

            if choice == "y":
                removed_count = 0
                for file_path in files:
                    if self.backup_and_remove_file(file_path):
                        removed_count += 1
                print(
                    f"{Colors.GREEN}✅ Removed {removed_count}/{len(files)} files from {category}{Colors.ENDC}"
                )

            elif choice == "v":
                print(f"\n{Colors.CYAN}Files in {category}:{Colors.ENDC}")
                for file_path in files:
                    print(f"  • {file_path}")
                # Повторяем вопрос после просмотра
                choice2 = input(f"Remove all {len(files)} files? [y/n]: ").lower().strip()
                if choice2 == "y":
                    removed_count = 0
                    for file_path in files:
                        if self.backup_and_remove_file(file_path):
                            removed_count += 1
                    print(
                        f"{Colors.GREEN}✅ Removed {removed_count}/{len(files)} files from {category}{Colors.ENDC}"
                    )
                else:
                    self.skipped_files.extend(files)
            else:
                self.skipped_files.extend(files)
                print(f"{Colors.WARNING}⏭️ Skipped {category}{Colors.ENDC}")

    def show_summary(self) -> None:
        """Показывает итоговый отчет"""
        print(f"\n{Colors.BOLD}📊 Cleanup Summary:{Colors.ENDC}")
        print(f"{Colors.GREEN}✅ Removed files: {len(self.removed_files)}{Colors.ENDC}")
        print(f"{Colors.WARNING}⏭️ Skipped files: {len(self.skipped_files)}{Colors.ENDC}")

        if self.backup_dir:
            print(f"{Colors.BLUE}📦 Backup location: {self.backup_dir}{Colors.ENDC}")

        if self.removed_files:
            print(f"\n{Colors.BOLD}Removed files:{Colors.ENDC}")
            for file_path in self.removed_files[:10]:
                print(f"  ❌ {file_path}")
            if len(self.removed_files) > 10:
                print(f"  ... and {len(self.removed_files) - 10} more files")

        # Подсчитываем освобожденное место
        if self.backup_dir:
            total_size = 0
            for file_path in self.removed_files:
                backup_file = self.backup_dir / file_path
                if backup_file.exists():
                    total_size += backup_file.stat().st_size

            if total_size > 0:
                size_mb = total_size / (1024 * 1024)
                print(f"{Colors.CYAN}💾 Freed disk space: {size_mb:.2f} MB{Colors.ENDC}")

        # Инструкции по восстановлению
        if self.backup_dir and self.removed_files:
            print(f"\n{Colors.BOLD}🔄 To restore files:{Colors.ENDC}")
            print(f"  cp -r {self.backup_dir}/* {self.project_root}/")

            restore_script = self.backup_dir / "restore.sh"
            with open(restore_script, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("# Restore removed files\n")
                f.write(f"cp -r {self.backup_dir}/* {self.project_root}/\n")
                f.write("echo 'Files restored successfully'\n")
            restore_script.chmod(0o755)
            print(f"  Or run: bash {restore_script}")


def main():
    project_root = Path(__file__).parent.parent
    cleanup = InteractiveCodeCleanup(project_root)

    print(f"{Colors.BOLD}{Colors.HEADER}🧹 Interactive Code Cleanup for BOT_AI_V3{Colors.ENDC}")
    print(f"{Colors.BLUE}📁 Project: {project_root}{Colors.ENDC}")

    # Загружаем последний анализ
    analysis_data = cleanup.load_latest_analysis()
    if not analysis_data:
        print(
            f"{Colors.FAIL}❌ No code analysis found. Run code usage analysis first:{Colors.ENDC}"
        )
        print("  python3 scripts/run_code_usage_analysis.py")
        return 1

    unused_files = analysis_data.get("unused_files", [])
    if not unused_files:
        print(f"{Colors.GREEN}✅ No unused files found to clean up!{Colors.ENDC}")
        return 0

    print(f"\n{Colors.WARNING}⚠️ Found {len(unused_files)} unused files{Colors.ENDC}")
    print(f"Analysis from: {analysis_data.get('timestamp', 'unknown')}")

    # Выбираем режим очистки
    print(f"\n{Colors.BOLD}Choose cleanup mode:{Colors.ENDC}")
    print("  1. Interactive (review each file)")
    print("  2. By categories (group similar files)")
    print("  3. Show file list and exit")
    print("  4. Cancel")

    choice = input("Enter choice [1-4]: ").strip()

    if choice == "1":
        cleanup.interactive_cleanup(unused_files)
    elif choice == "2":
        cleanup.cleanup_by_category(unused_files)
    elif choice == "3":
        print(f"\n{Colors.BOLD}📋 Unused Files:{Colors.ENDC}")
        for file_path in unused_files:
            print(f"  • {file_path}")
    else:
        print(f"{Colors.CYAN}👋 Cleanup cancelled{Colors.ENDC}")
        return 0

    cleanup.show_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
