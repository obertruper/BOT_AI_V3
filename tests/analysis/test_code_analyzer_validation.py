#!/usr/bin/env python3
"""
Тесты валидации анализатора кода - проверка точности результатов
"""

import json
import sys
from pathlib import Path

import pytest

# Добавляем корневую директорию в path
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.code_chain_analyzer import CodeChainAnalyzer as CodeUsageAnalyzer


class TestCodeAnalyzerValidation:
    """Тесты валидации точности анализатора"""

    def test_validate_real_project_analysis(self):
        """Проверяем точность анализа реального проекта BOT_AI_V3"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)

        analyzer.scan_project()
        analyzer.analyze_imports()

        # Получаем результаты
        unused_files = analyzer.find_unused_files()
        stats = analyzer.get_file_statistics()

        # Валидация результатов
        assert len(unused_files) > 0, "Should find some unused files in a real project"
        assert stats["total_files"] > 100, "BOT_AI_V3 should have many Python files"

        # Проверяем что основные entry points НЕ в списке неиспользуемых
        entry_point_files = ["main.py", "unified_launcher.py"]
        for entry_file in entry_point_files:
            assert entry_file not in unused_files, f"Entry point {entry_file} should not be unused"

        # Проверяем что тестовые файлы НЕ в списке неиспользуемых
        test_files_in_unused = [f for f in unused_files if "test_" in f or "/test" in f]
        assert len(test_files_in_unused) == 0, "Test files should not be marked as unused"

    def test_validate_import_detection(self):
        """Проверяем правильность детекции импортов"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)
        analyzer.scan_project()

        # Проверяем что main.py найден и проанализирован
        main_file = project_root / "main.py"
        if main_file.exists():
            with open(main_file) as f:
                content = f.read()

            # Если в main.py есть импорты, они должны быть детектированы
            if "import" in content:
                analyzer.analyze_imports()
                assert "main.py" in analyzer.imports_graph, "main.py should have import graph entry"

    def test_validate_unused_file_accuracy(self):
        """Проверяем точность определения неиспользуемых файлов"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)
        analyzer.scan_project()
        analyzer.analyze_imports()

        unused_files = analyzer.find_unused_files()

        # Проверяем несколько файлов которые точно должны использоваться
        critical_files = [
            "core/system/orchestrator.py",
            "trading/engine.py",
            "database/connections/postgres.py",
        ]

        for critical_file in critical_files:
            critical_path = project_root / critical_file
            if critical_path.exists():
                assert critical_file not in unused_files, (
                    f"Critical file {critical_file} should not be unused"
                )

    def test_validate_stale_file_detection(self):
        """Проверяем правильность определения устаревших файлов"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)
        analyzer.scan_project()

        # Проверяем разные пороги
        stale_1d = analyzer.find_stale_files(1)
        stale_1w = analyzer.find_stale_files(7)
        stale_1m = analyzer.find_stale_files(30)

        # Логические проверки
        assert len(stale_1m) <= len(stale_1w), "Monthly stale should be <= weekly stale"
        assert len(stale_1w) <= len(stale_1d), "Weekly stale should be <= daily stale"

        # Проверяем что результаты содержат правильную информацию
        for file_path, days in stale_1m:
            assert days >= 30, f"File {file_path} should be at least 30 days old"
            assert isinstance(file_path, str), "File path should be string"
            assert isinstance(days, int), "Days should be integer"

    def test_validate_statistics_accuracy(self):
        """Проверяем точность статистики"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)
        analyzer.scan_project()
        analyzer.analyze_imports()

        stats = analyzer.get_file_statistics()
        unused_files = analyzer.find_unused_files()

        # Валидация статистики
        assert stats["total_files"] > 0, "Should have some files"
        assert stats["total_files"] == len(analyzer.python_files), (
            "Total files should match scan result"
        )

        # Проверяем что количества логичны
        assert stats["entry_points"] <= stats["total_files"], "Entry points <= total files"
        assert stats["test_files"] <= stats["total_files"], "Test files <= total files"

        # Проверяем что import connections разумны
        assert stats["import_connections"] >= 0, "Import connections should be non-negative"

    def test_validate_performance(self):
        """Проверяем производительность анализа"""
        import time

        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)

        # Засекаем время сканирования
        start_time = time.time()
        analyzer.scan_project()
        scan_time = time.time() - start_time

        # Засекаем время анализа импортов
        start_time = time.time()
        analyzer.analyze_imports()
        import_time = time.time() - start_time

        # Валидация производительности
        assert scan_time < 5.0, f"Scanning should take < 5s, took {scan_time:.2f}s"
        assert import_time < 10.0, f"Import analysis should take < 10s, took {import_time:.2f}s"

        # Проверяем что результаты получены
        assert len(analyzer.python_files) > 0, "Should find Python files"
        assert len(analyzer.imports_graph) > 0, "Should find imports"


class TestCodeAnalysisAccuracy:
    """Тесты точности анализа конкретных случаев"""

    def test_specific_file_analysis(self):
        """Тестируем анализ конкретных известных файлов"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)
        analyzer.scan_project()
        analyzer.analyze_imports()

        # Проверяем unified_launcher.py - должен быть entry point
        unified_launcher = "unified_launcher.py"
        if unified_launcher in {str(f) for f in analyzer.python_files}:
            unused_files = analyzer.find_unused_files()
            assert unified_launcher not in unused_files, "unified_launcher.py should not be unused"

        # Проверяем что файлы в tests/ не помечены как unused
        test_files = [str(f) for f in analyzer.python_files if "test" in str(f)]
        unused_files = analyzer.find_unused_files()
        test_files_unused = [f for f in unused_files if "test" in f]
        assert len(test_files_unused) == 0, f"Test files should not be unused: {test_files_unused}"

    def test_import_resolution_accuracy(self):
        """Тестируем точность разрешения импортов"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)

        # Тестируем разрешение известных импортов
        test_cases = [
            ("core.logger", "core/logger.py"),
            ("database.connections.postgres", "database/connections/postgres.py"),
            ("trading.engine", "trading/engine.py"),
        ]

        for import_name, expected_path in test_cases:
            expected_file = project_root / expected_path
            if expected_file.exists():
                resolved = analyzer._resolve_import_to_file(import_name)
                assert resolved == expected_path, (
                    f"Import {import_name} should resolve to {expected_path}, got {resolved}"
                )

    def test_false_positive_detection(self):
        """Проверяем на ложные срабатывания"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)
        analyzer.scan_project()
        analyzer.analyze_imports()

        unused_files = analyzer.find_unused_files()

        # Файлы которые точно НЕ должны быть в unused
        should_not_be_unused = ["main.py", "unified_launcher.py"]

        for file_name in should_not_be_unused:
            matching_files = [f for f in unused_files if f.endswith(file_name)]
            assert len(matching_files) == 0, f"File {file_name} should not be marked as unused"

    def test_edge_cases(self):
        """Тестируем граничные случаи"""
        project_root = Path(__file__).parent.parent.parent
        analyzer = CodeUsageAnalyzer(project_root)

        # Тест с пустым проектом
        analyzer.python_files = set()
        unused = analyzer.find_unused_files()
        assert len(unused) == 0, "Empty project should have no unused files"

        # Тест статистики для пустого проекта
        stats = analyzer.get_file_statistics()
        assert stats["total_files"] == 0
        assert stats["entry_points"] == 0
        assert stats["import_connections"] == 0


class TestCodeAnalysisResults:
    """Тесты анализа результатов последнего запуска"""

    def test_analyze_latest_results(self):
        """Анализируем результаты последнего запуска"""
        results_dir = Path(__file__).parent.parent.parent / "analysis_results"

        # Находим последний JSON файл
        json_files = list(results_dir.glob("code_usage_analysis_*.json"))
        if not json_files:
            pytest.skip("No analysis results found")

        latest_json = max(json_files, key=lambda f: f.stat().st_mtime)

        with open(latest_json) as f:
            results = json.load(f)

        # Валидация структуры результатов
        assert "statistics" in results
        assert "unused_files" in results
        assert "stale_files" in results

        stats = results["statistics"]
        unused_files = results["unused_files"]

        # Анализ качества результатов
        print("\n📊 Analysis Quality Report:")
        print(f"Total files analyzed: {stats['total_files']}")
        print(f"Unused files found: {len(unused_files)}")
        print(f"Import connections: {stats['import_connections']}")
        print(f"Isolated files: {stats['isolated_files']}")

        # Проверки качества
        unused_ratio = len(unused_files) / stats["total_files"] * 100
        print(f"Unused file ratio: {unused_ratio:.1f}%")

        # Если более 80% файлов помечены как unused - возможно проблема в анализе
        if unused_ratio > 80:
            print(
                f"⚠️ Warning: High unused file ratio ({unused_ratio:.1f}%) - check analysis accuracy"
            )

        # Проверяем что есть импорты
        assert stats["import_connections"] > 0, "Should find some import connections"

        # Проверяем разумность результатов
        assert len(unused_files) < stats["total_files"], "Not all files can be unused"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
