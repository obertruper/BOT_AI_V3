#!/usr/bin/env python3
"""
🔍 BOT_AI_V3 Code Usage Analysis System
Анализирует какие файлы не используются в коде и какие файлы устарели
"""

import argparse
import ast
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
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


class CodeUsageAnalyzer:
    """Анализатор использования кода в проекте"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.python_files: set[Path] = set()
        self.imports_graph: dict[str, set[str]] = defaultdict(set)
        self.imported_by: dict[str, set[str]] = defaultdict(set)
        self.entry_points: set[str] = {
            "main.py",
            "unified_launcher.py",
            "app.py",
            "wsgi.py",
            "manage.py",
            "run.py",
            "server.py",
        }
        self.exclude_dirs = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".mypy_cache",
            ".pytest_cache",
            "htmlcov",
            ".coverage",
            "web/frontend",
            "BOT_AI_V2",
        }
        self.exclude_files = {"__init__.py", "conftest.py", "alembic.ini"}

    def scan_project(self) -> None:
        """Сканирует проект и находит все Python файлы"""
        print(f"{Colors.CYAN}🔍 Scanning project...{Colors.ENDC}")

        for root, dirs, files in os.walk(self.project_root):
            # Исключаем определенные директории
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for file in files:
                if file.endswith(".py") and file not in self.exclude_files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.project_root)
                    self.python_files.add(rel_path)

        print(f"{Colors.GREEN}✓ Found {len(self.python_files)} Python files{Colors.ENDC}")

    def analyze_imports(self) -> None:
        """Анализирует импорты в каждом файле"""
        print(f"{Colors.CYAN}📊 Analyzing imports...{Colors.ENDC}")

        for py_file in self.python_files:
            full_path = self.project_root / py_file
            try:
                with open(full_path, encoding="utf-8") as f:
                    content = f.read()

                # Парсим AST для извлечения импортов
                tree = ast.parse(content, filename=str(py_file))
                imports = self._extract_imports(tree)

                file_key = str(py_file)
                for imp in imports:
                    # Проверяем является ли импорт локальным модулем
                    local_file = self._resolve_import_to_file(imp)
                    if local_file:
                        self.imports_graph[file_key].add(local_file)
                        self.imported_by[local_file].add(file_key)

            except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
                print(f"{Colors.WARNING}⚠ Error parsing {py_file}: {e}{Colors.ENDC}")
                continue

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        """Извлекает все импорты из AST дерева"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Относительные импорты
                    if node.level > 0:
                        # Относительный импорт типа "from .module import something"
                        module_name = node.module or ""
                        imports.append(module_name)
                    else:
                        imports.append(node.module)

                    # Импортируемые имена
                    for alias in node.names:
                        if alias.name != "*":
                            full_name = f"{node.module}.{alias.name}" if node.module else alias.name
                            imports.append(full_name)

        return imports

    def _resolve_import_to_file(self, import_name: str) -> str | None:
        """Преобразует имя импорта в путь к файлу"""
        # Удаляем точки в начале (относительные импорты)
        clean_name = import_name.lstrip(".")

        # Пробуем разные варианты пути
        possible_paths = [
            f"{clean_name.replace('.', '/')}.py",
            f"{clean_name.replace('.', '/')}/__init__.py",
            f"{clean_name}.py",
        ]

        for path in possible_paths:
            full_path = self.project_root / path
            if full_path.exists():
                try:
                    rel_path = full_path.relative_to(self.project_root)
                    return str(rel_path)
                except ValueError:
                    continue

        return None

    def find_unused_files(self) -> list[str]:
        """Находит файлы которые не импортируются другими файлами"""
        unused = []

        for py_file in self.python_files:
            file_key = str(py_file)
            file_name = py_file.name

            # Пропускаем entry points
            if file_name in self.entry_points:
                continue

            # Пропускаем все тестовые файлы и скрипты
            if (
                file_name.startswith("test_")
                or "/test" in file_key
                or file_key.startswith("tests/")
                or "test" in file_name.lower()
                or file_key.startswith("scripts/")
                or file_key.startswith("testing/")
                or file_key.startswith("run_")
                or "conftest" in file_name
            ):
                continue

            # Пропускаем миграции и утилиты
            if (
                "migration" in file_key
                or "alembic" in file_key
                or file_key.startswith("utils/")
                or file_key.startswith("ai_agents/")
            ):
                continue

            # Если файл ни разу не импортировался
            if file_key not in self.imported_by:
                unused.append(file_key)

        return unused

    def find_stale_files(self, days_threshold: int) -> list[tuple[str, int]]:
        """Находит файлы которые не изменялись N дней"""
        stale_files = []
        threshold_date = datetime.now() - timedelta(days=days_threshold)

        for py_file in self.python_files:
            full_path = self.project_root / py_file
            try:
                mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
                if mtime < threshold_date:
                    days_old = (datetime.now() - mtime).days
                    stale_files.append((str(py_file), days_old))
            except OSError:
                continue

        return sorted(stale_files, key=lambda x: x[1], reverse=True)

    def get_file_statistics(self) -> dict:
        """Собирает статистику по файлам"""
        stats = {
            "total_files": len(self.python_files),
            "entry_points": len([f for f in self.python_files if f.name in self.entry_points]),
            "test_files": len([f for f in self.python_files if "test" in str(f)]),
            "import_connections": sum(len(imports) for imports in self.imports_graph.values()),
            "isolated_files": len(
                [
                    f
                    for f in self.python_files
                    if str(f) not in self.imported_by and str(f) not in self.imports_graph
                ]
            ),
        }
        return stats


def generate_html_report(
    analyzer: CodeUsageAnalyzer,
    unused_files: list[str],
    stale_1d: list[tuple[str, int]],
    stale_1w: list[tuple[str, int]],
    stale_1m: list[tuple[str, int]],
    stats: dict,
) -> str:
    """Генерирует HTML отчет"""

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOT_AI_V3 Code Usage Analysis</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .section {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .file-list {{
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 15px;
        }}
        .file-item {{
            padding: 8px;
            border-bottom: 1px solid #f0f0f0;
            font-family: monospace;
            font-size: 0.9em;
        }}
        .warning {{ color: #e67e22; }}
        .danger {{ color: #e74c3c; }}
        .info {{ color: #3498db; }}
        h1 {{ color: #333; font-size: 2.5em; margin-bottom: 10px; }}
        h2 {{ color: #333; margin-bottom: 15px; }}
        .timestamp {{ text-align: center; color: #999; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 BOT_AI_V3 Code Usage Analysis</h1>
            <div style="color: #666; font-size: 1.2em;">Dead Code & Stale File Detection</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats['total_files']}</div>
                <div>Total Python Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(unused_files)}</div>
                <div>Unused Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(stale_1d)}</div>
                <div>Stale 1+ Day</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(stale_1w)}</div>
                <div>Stale 1+ Week</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(stale_1m)}</div>
                <div>Stale 1+ Month</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['import_connections']}</div>
                <div>Import Connections</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🚫 Unused Files (Not Imported by Any Other File)</h2>
            <div class="file-list">
                {"".join(f'<div class="file-item danger">❌ {file}</div>' for file in unused_files[:50])}
                {f'<div class="file-item info">... and {len(unused_files) - 50} more files</div>' if len(unused_files) > 50 else ''}
            </div>
        </div>
        
        <div class="section">
            <h2>📅 Stale Files - Not Modified 1+ Week</h2>
            <div class="file-list">
                {"".join(f'<div class="file-item warning">⚠️ {file} ({days} days old)</div>' for file, days in stale_1w[:30])}
                {f'<div class="file-item info">... and {len(stale_1w) - 30} more files</div>' if len(stale_1w) > 30 else ''}
            </div>
        </div>
        
        <div class="section">
            <h2>🗓️ Stale Files - Not Modified 1+ Month</h2>
            <div class="file-list">
                {"".join(f'<div class="file-item danger">🔴 {file} ({days} days old)</div>' for file, days in stale_1m[:30])}
                {f'<div class="file-item info">... and {len(stale_1m) - 30} more files</div>' if len(stale_1m) > 30 else ''}
            </div>
        </div>
        
        <div class="timestamp">
            Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
    return html_content


def generate_cleanup_script(
    unused_files: list[str], stale_files: list[tuple[str, int]], output_path: Path
) -> None:
    """Генерирует bash скрипт для очистки неиспользуемых файлов"""
    script_content = f"""#!/bin/bash
# BOT_AI_V3 Code Cleanup Script
# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

set -e  # Exit on any error

echo "🧹 BOT_AI_V3 Code Cleanup"
echo "========================="

# Create backup directory
BACKUP_DIR="code_cleanup_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "📦 Created backup directory: $BACKUP_DIR"

# Function to backup and remove file
backup_and_remove() {{
    local file="$1"
    if [ -f "$file" ]; then
        echo "🔄 Processing: $file"
        # Create directory structure in backup
        mkdir -p "$BACKUP_DIR/$(dirname "$file")"
        cp "$file" "$BACKUP_DIR/$file"
        read -p "Remove $file? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$file"
            echo "❌ Removed: $file"
        else
            echo "⏭️  Skipped: $file"
        fi
    fi
}}

echo ""
echo "🚫 Processing unused files..."
echo "============================="
"""

    for unused_file in unused_files[:20]:  # Ограничиваем количество
        script_content += f'backup_and_remove "{unused_file}"\n'

    script_content += """
echo ""
echo "📅 Processing very old stale files (30+ days)..."
echo "============================================="
"""

    very_old_files = [f for f, days in stale_files if days > 30]
    for stale_file in very_old_files[:10]:  # Только очень старые
        script_content += f'backup_and_remove "{stale_file}"\n'

    script_content += """
echo ""
echo "✅ Cleanup complete!"
echo "📦 Backup saved in: $BACKUP_DIR"
echo "🔄 To restore files: cp -r $BACKUP_DIR/* ."
"""

    with open(output_path, "w") as f:
        f.write(script_content)

    # Делаем скрипт исполняемым
    output_path.chmod(0o755)


def main():
    parser = argparse.ArgumentParser(description="BOT_AI_V3 Code Usage Analysis")
    parser.add_argument(
        "--format", choices=["json", "html", "both"], default="both", help="Output format"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--cleanup-script", action="store_true", help="Generate cleanup script")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    results_dir = project_root / "analysis_results"
    results_dir.mkdir(exist_ok=True)

    print(f"{Colors.BOLD}{Colors.HEADER}🔍 BOT_AI_V3 Code Usage Analysis{Colors.ENDC}")
    print(f"{Colors.BLUE}📁 Project: {project_root}{Colors.ENDC}")
    print(f"{Colors.BLUE}📊 Results: {results_dir}{Colors.ENDC}")

    # Инициализация анализатора
    analyzer = CodeUsageAnalyzer(project_root)

    # Сканирование проекта
    start_time = time.time()
    analyzer.scan_project()
    analyzer.analyze_imports()

    # Анализ
    unused_files = analyzer.find_unused_files()
    stale_1d = analyzer.find_stale_files(1)
    stale_1w = analyzer.find_stale_files(7)
    stale_1m = analyzer.find_stale_files(30)
    stats = analyzer.get_file_statistics()

    execution_time = time.time() - start_time

    # Вывод результатов
    print(f"\n{Colors.BOLD}📊 Analysis Results:{Colors.ENDC}")
    print(f"{Colors.GREEN}✓ Total Python files: {stats['total_files']}{Colors.ENDC}")
    print(f"{Colors.FAIL}❌ Unused files: {len(unused_files)}{Colors.ENDC}")
    print(f"{Colors.WARNING}⚠️  Files stale 1+ day: {len(stale_1d)}{Colors.ENDC}")
    print(f"{Colors.WARNING}⚠️  Files stale 1+ week: {len(stale_1w)}{Colors.ENDC}")
    print(f"{Colors.FAIL}🔴 Files stale 1+ month: {len(stale_1m)}{Colors.ENDC}")
    print(f"{Colors.CYAN}⏱️  Analysis time: {execution_time:.2f}s{Colors.ENDC}")

    if args.verbose and unused_files:
        print(f"\n{Colors.BOLD}🚫 Unused Files (first 20):{Colors.ENDC}")
        for file in unused_files[:20]:
            print(f"  ❌ {file}")
        if len(unused_files) > 20:
            print(f"  ... and {len(unused_files) - 20} more files")

    # Сохранение результатов
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON отчет
    if args.format in ["json", "both"]:
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(project_root),
            "statistics": stats,
            "execution_time": execution_time,
            "unused_files": unused_files,
            "stale_files": {"1_day": stale_1d, "1_week": stale_1w, "1_month": stale_1m},
        }

        json_file = results_dir / f"code_usage_analysis_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"{Colors.GREEN}✓ JSON report: {json_file}{Colors.ENDC}")

    # HTML отчет
    if args.format in ["html", "both"]:
        html_content = generate_html_report(
            analyzer, unused_files, stale_1d, stale_1w, stale_1m, stats
        )
        html_file = results_dir / f"code_usage_report_{timestamp}.html"
        with open(html_file, "w") as f:
            f.write(html_content)
        print(f"{Colors.GREEN}✓ HTML report: {html_file}{Colors.ENDC}")
        print(f"  🌐 Open in browser: file://{html_file}")

    # Скрипт очистки
    if args.cleanup_script:
        script_file = results_dir / f"cleanup_script_{timestamp}.sh"
        generate_cleanup_script(unused_files, stale_1m, script_file)
        print(f"{Colors.GREEN}✓ Cleanup script: {script_file}{Colors.ENDC}")
        print(f"  🔧 Run with: bash {script_file}")

    # Рекомендации
    if unused_files or len(stale_1m) > 10:
        print(f"\n{Colors.BOLD}💡 Recommendations:{Colors.ENDC}")
        if unused_files:
            print(f"  • Found {len(unused_files)} unused files - consider removing")
        if len(stale_1m) > 10:
            print(f"  • Found {len(stale_1m)} files older than 1 month")
        print("  • Use --cleanup-script to generate removal script")
        print("  • Review files before deletion!")

    return 0


if __name__ == "__main__":
    exit(main())
