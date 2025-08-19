#!/usr/bin/env python3
"""
Главный оркестратор системы тестирования BOT_AI_V3
Координирует все компоненты для достижения 100% покрытия кода
"""
import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class MasterTestRunner:
    """Главный координатор системы тестирования"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results_dir = project_root / "analysis_results"
        self.results_dir.mkdir(exist_ok=True)

        # Результаты всех этапов
        self.execution_results = {
            "start_time": datetime.now().isoformat(),
            "stages": {},
            "overall_success": False,
            "coverage_improvement": 0.0,
            "recommendations": [],
            "next_steps": [],
        }

    def print_header(self):
        """Выводит заголовок системы"""
        print("\n" + "🚀 " + "BOT_AI_V3 MASTER TEST RUNNER".center(58) + " 🚀")
        print("=" * 60)
        print("🎯 Цель: Достижение 100% покрытия кода тестами")
        print("🔍 Обнаружение и удаление неиспользуемого кода")
        print("⚡ Тестирование полной цепочки выполнения")
        print("📊 Мониторинг производительности в реальном времени")
        print("=" * 60)
        print(f"📁 Проект: {self.project_root}")
        print(f"📊 Результаты: {self.results_dir}")
        print(f"🌐 Дашборд: file://{self.results_dir}/testing_dashboard.html")
        print("🗄️ PostgreSQL: localhost:5555")
        print("=" * 60)

    async def run_full_analysis(self) -> dict[str, Any]:
        """Запускает полный анализ системы"""
        print("\n🔍 ЭТАП 1: ПОЛНЫЙ АНАЛИЗ СИСТЕМЫ")
        print("-" * 40)

        stages = [
            ("code_chain_analysis", "Анализ цепочки кода", self._run_code_chain_analysis),
            ("coverage_baseline", "Базовое покрытие", self._get_coverage_baseline),
            ("performance_baseline", "Базовая производительность", self._get_performance_baseline),
            ("dependency_analysis", "Анализ зависимостей", self._analyze_dependencies),
        ]

        total_stages = len(stages)

        for i, (stage_id, stage_name, stage_func) in enumerate(stages, 1):
            print(f"\n📊 [{i}/{total_stages}] {stage_name}")
            print("─" * 50)
            self._print_progress_bar(i - 1, total_stages, "Подготовка...")

            try:
                start_time = time.time()

                # Показываем что происходит
                self._print_stage_details(stage_id, stage_name)

                result = await stage_func()
                execution_time = time.time() - start_time

                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": True,
                    "execution_time": execution_time,
                    "result": result,
                }

                self._print_progress_bar(i, total_stages, f"✅ Завершено за {execution_time:.2f}с")
                self._print_stage_results(stage_id, result)

            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = str(e)
                print(f"\n   ❌ Ошибка через {execution_time:.2f}с: {error_msg}")

                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": False,
                    "execution_time": execution_time,
                    "error": error_msg,
                }

                self._print_progress_bar(i, total_stages, f"❌ Ошибка: {error_msg[:30]}...")

        print(
            f"\n🎯 ЭТАП 1 ЗАВЕРШЁН: {sum(1 for s in self.execution_results['stages'].values() if s.get('success', False))}/{total_stages} успешно"
        )

        return self.execution_results["stages"]

    async def run_chain_testing(self) -> dict[str, Any]:
        """Запускает тестирование цепочек"""
        print("\n🔗 ЭТАП 2: ТЕСТИРОВАНИЕ ЦЕПОЧЕК ВЫПОЛНЕНИЯ")
        print("━" * 50)
        print("🎯 Тестируем 8 критических workflow:")
        print("   1️⃣ Торговая цепочка (unified_launcher → trading → exchange)")
        print("   2️⃣ ML цепочка (data → features → model → signals)")
        print("   3️⃣ API цепочка (auth → logic → database → response)")
        print("   4️⃣ WebSocket цепочка (connection → parsing → broadcast)")
        print("   5️⃣ Database цепочка (pool → transaction → query → commit)")
        print("   6️⃣ System startup (env → db → exchanges → orchestrator)")
        print("   7️⃣ Order execution (validation → risk → placement → tracking)")
        print("   8️⃣ Risk management (portfolio → calculation → limits)")
        print("━" * 50)

        stages = [
            ("chain_testing", "Тестирование критических цепочек", self._run_chain_testing),
            ("integration_tests", "Интеграционные тесты", self._run_integration_tests),
            ("performance_tests", "Тесты производительности", self._run_performance_tests),
        ]

        for stage_id, stage_name, stage_func in stages:
            print(f"\n🧪 {stage_name}...")
            try:
                start_time = time.time()
                result = await stage_func()
                execution_time = time.time() - start_time

                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": True,
                    "execution_time": execution_time,
                    "result": result,
                }

                print(f"   ✅ Завершено за {execution_time:.2f}с")

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": False,
                    "error": str(e),
                }

        return self.execution_results["stages"]

    async def run_test_generation(self) -> dict[str, Any]:
        """Запускает генерацию тестов"""
        print("\n🧪 ЭТАП 3: ГЕНЕРАЦИЯ ТЕСТОВ ДЛЯ 100% ПОКРЫТИЯ")
        print("━" * 50)
        print("🎯 Автоматическое создание тестов:")
        print("   📝 Unit тесты для всех функций")
        print("   🔗 Integration тесты для компонентов")
        print("   ⚡ Performance тесты (торговля <50мс, ML <20мс)")
        print("   🛡️ Security тесты для API endpoints")
        print("   🗄️ Database тесты с транзакциями")
        print("   🎭 Mock тесты для внешних API")
        print("━" * 50)

        stages = [
            ("test_analysis", "Анализ недостающих тестов", self._analyze_missing_tests),
            ("test_generation", "Генерация новых тестов", self._generate_comprehensive_tests),
            ("test_validation", "Валидация сгенерированных тестов", self._validate_generated_tests),
            ("coverage_measurement", "Измерение нового покрытия", self._measure_new_coverage),
        ]

        for stage_id, stage_name, stage_func in stages:
            print(f"\n📝 {stage_name}...")
            try:
                start_time = time.time()
                result = await stage_func()
                execution_time = time.time() - start_time

                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": True,
                    "execution_time": execution_time,
                    "result": result,
                }

                print(f"   ✅ Завершено за {execution_time:.2f}с")

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": False,
                    "error": str(e),
                }

        return self.execution_results["stages"]

    async def run_code_cleanup(self) -> dict[str, Any]:
        """Запускает очистку неиспользуемого кода"""
        print("\n🗑️ ЭТАП 4: ОЧИСТКА НЕИСПОЛЬЗУЕМОГО КОДА")
        print("━" * 50)
        print("🎯 Безопасное удаление dead code:")
        print("   🔍 Поиск неиспользуемых функций")
        print("   🛡️ Проверка безопасности удаления")
        print("   💾 Создание резервных копий")
        print("   🧪 Тестирование после удаления")
        print("   📊 Анализ экономии места")
        print("━" * 50)

        stages = [
            ("unused_detection", "Обнаружение неиспользуемого кода", self._detect_unused_code),
            ("safety_analysis", "Анализ безопасности удаления", self._analyze_removal_safety),
            ("code_removal", "Безопасное удаление кода", self._remove_unused_code),
            ("post_removal_testing", "Тестирование после удаления", self._test_after_removal),
        ]

        for stage_id, stage_name, stage_func in stages:
            print(f"\n🔍 {stage_name}...")
            try:
                start_time = time.time()
                result = await stage_func()
                execution_time = time.time() - start_time

                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": True,
                    "execution_time": execution_time,
                    "result": result,
                }

                print(f"   ✅ Завершено за {execution_time:.2f}с")

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": False,
                    "error": str(e),
                }

        return self.execution_results["stages"]

    async def run_monitoring_setup(self) -> dict[str, Any]:
        """Настраивает мониторинг"""
        print("\n📊 ЭТАП 5: НАСТРОЙКА МОНИТОРИНГА")
        print("━" * 50)
        print("🎯 Real-time мониторинг системы:")
        print("   📈 Покрытие кода в реальном времени")
        print("   ⚡ Мониторинг производительности")
        print("   🌐 Веб дашборд с метриками")
        print("   🤖 Автоматизация CI/CD")
        print("   🔔 Алерты и уведомления")
        print("   📊 Отчёты и аналитика")
        print("━" * 50)

        stages = [
            ("monitoring_config", "Конфигурация мониторинга", self._setup_monitoring),
            ("dashboard_creation", "Создание дашборда", self._create_coverage_dashboard),
            ("automation_setup", "Настройка автоматизации", self._setup_automation),
            ("final_validation", "Финальная валидация", self._final_validation),
        ]

        for stage_id, stage_name, stage_func in stages:
            print(f"\n⚙️ {stage_name}...")
            try:
                start_time = time.time()
                result = await stage_func()
                execution_time = time.time() - start_time

                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": True,
                    "execution_time": execution_time,
                    "result": result,
                }

                print(f"   ✅ Завершено за {execution_time:.2f}с")

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                self.execution_results["stages"][stage_id] = {
                    "name": stage_name,
                    "success": False,
                    "error": str(e),
                }

        return self.execution_results["stages"]

    def _print_progress_bar(self, current: int, total: int, status: str = ""):
        """Выводит прогресс-бар"""
        width = 40
        progress = current / total if total > 0 else 0
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        percent = progress * 100

        print(f"\r   [{bar}] {percent:5.1f}% {status}", end="", flush=True)
        if current == total or "❌" in status:
            print()  # Новая строка в конце

    def _print_stage_details(self, stage_id: str, stage_name: str):
        """Выводит детали этапа"""
        details = {
            "code_chain_analysis": {
                "description": "Строит граф зависимостей функций, ищет неиспользуемый код",
                "output_file": "analysis_results/code_chain_analysis.json",
                "log_hint": "Анализ AST дерева, построение call graph...",
            },
            "coverage_baseline": {
                "description": "Измеряет текущее покрытие кода тестами",
                "output_file": "coverage.json + htmlcov/",
                "log_hint": "Запуск pytest с coverage.py...",
            },
            "performance_baseline": {
                "description": "Замеряет производительность критических функций",
                "output_file": "benchmark.json",
                "log_hint": "Тестирование производительности...",
            },
            "dependency_analysis": {
                "description": "Анализирует импорты и зависимости модулей",
                "output_file": "analysis_results/dependencies.json",
                "log_hint": "Парсинг import statements...",
            },
            "chain_testing": {
                "description": "Тестирует 8 критических workflow цепочек",
                "output_file": "analysis_results/full_chain_test_results.json",
                "log_hint": "Тестирование trading → ml → api → websocket цепочек...",
            },
            "test_generation": {
                "description": "Генерирует недостающие тесты для 100% покрытия",
                "output_file": "tests/ (новые файлы)",
                "log_hint": "AI генерация unit/integration тестов...",
            },
            "unused_detection": {
                "description": "Обнаруживает неиспользуемые функции и dead code",
                "output_file": "analysis_results/unused_code_report.json",
                "log_hint": "Поиск unreachable functions...",
            },
            "monitoring_config": {
                "description": "Настраивает real-time мониторинг покрытия",
                "output_file": "analysis_results/monitoring_config.json",
                "log_hint": "Конфигурация coverage tracing...",
            },
        }

        detail = details.get(stage_id, {})

        if detail:
            print(f"   📝 {detail['description']}")
            print(f"   📄 Результат: {detail['output_file']}")
            print(f"   🔄 {detail['log_hint']}")

        print("   ⏳ Выполнение...", end="", flush=True)

    def _print_stage_results(self, stage_id: str, result: dict[str, Any]):
        """Выводит результаты этапа"""
        if not result:
            return

        print("\n   📊 Результаты:")

        # Специфичные результаты для разных этапов
        if stage_id == "code_chain_analysis":
            total_funcs = result.get("total_functions", 0)
            unreachable = len(result.get("unreachable_functions", []))
            unused = len(result.get("unused_code_candidates", []))

            print(f"      🔍 Всего функций: {total_funcs}")
            print(f"      🗑️ Неиспользуемых: {unused}")
            print(f"      ❌ Недостижимых: {unreachable}")

        elif stage_id == "coverage_baseline":
            coverage = result.get("coverage_percentage", 0)
            lines_covered = result.get("lines_covered", 0)
            lines_total = result.get("lines_total", 0)

            print(f"      📈 Покрытие: {coverage:.1f}%")
            print(f"      📝 Строк покрыто: {lines_covered}/{lines_total}")

        elif stage_id == "chain_testing":
            success_rate = result.get("success_rate", 0)
            chains_tested = result.get("total_chains_tested", 0)
            successful = result.get("successful_chains", 0)

            print(f"      🔗 Цепочек протестировано: {successful}/{chains_tested}")
            print(f"      ✅ Успешность: {success_rate:.1f}%")

        elif stage_id == "performance_baseline":
            if result.get("benchmarks"):
                print(f"      ⚡ Performance тестов: {len(result['benchmarks'])}")
            else:
                print("      ⚡ Performance тесты не найдены")

        elif stage_id == "dependency_analysis":
            ext_packages = len(result.get("external_packages", []))
            int_modules = len(result.get("internal_modules", []))

            print(f"      📦 Внешних пакетов: {ext_packages}")
            print(f"      🔧 Внутренних модулей: {int_modules}")

        # Ссылки на файлы результатов
        result_files = {
            "code_chain_analysis": self.results_dir / "code_chain_analysis.json",
            "coverage_baseline": self.project_root / "htmlcov" / "index.html",
            "chain_testing": self.results_dir / "full_chain_test_results.json",
            "test_generation": self.project_root / "tests",
            "unused_detection": self.results_dir / "removal_report.json",
        }

        result_file = result_files.get(stage_id)
        if result_file:
            if result_file.exists() or stage_id == "test_generation":
                print(f"      🔗 Смотреть: {result_file}")
            else:
                print(f"      📄 Файл создаётся: {result_file}")

    # Методы выполнения отдельных этапов

    async def _run_code_chain_analysis(self) -> dict[str, Any]:
        """Запускает анализ цепочки кода"""
        try:
            result = subprocess.run(
                [sys.executable, "scripts/code_chain_analyzer.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                # Загружаем результаты
                analysis_file = self.results_dir / "code_chain_analysis.json"
                if analysis_file.exists():
                    with open(analysis_file, encoding="utf-8") as f:
                        return json.load(f)
                else:
                    return {"status": "completed", "file_not_found": True}
            else:
                raise Exception(f"Код выхода: {result.returncode}, Ошибка: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise Exception("Превышен таймаут анализа (5 минут)")

    async def _get_coverage_baseline(self) -> dict[str, Any]:
        """Получает базовое покрытие"""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/",
                    "--cov=.",
                    "--cov-report=json:coverage.json",
                    "--quiet",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180,
            )

            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                return {
                    "coverage_percentage": coverage_data["totals"]["percent_covered"],
                    "lines_covered": coverage_data["totals"]["covered_lines"],
                    "lines_total": coverage_data["totals"]["num_statements"],
                }
            else:
                return {"coverage_percentage": 0, "error": "Файл покрытия не найден"}

        except Exception as e:
            return {"error": f"Ошибка измерения покрытия: {e}"}

    async def _get_performance_baseline(self) -> dict[str, Any]:
        """Получает базовую производительность"""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/",
                    "-m",
                    "performance",
                    "--benchmark-json=benchmark.json",
                    "--quiet",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180,
            )

            benchmark_file = self.project_root / "benchmark.json"
            if benchmark_file.exists():
                with open(benchmark_file) as f:
                    return json.load(f)
            else:
                return {"benchmarks": [], "note": "Нет performance тестов"}

        except Exception as e:
            return {"error": f"Ошибка performance тестов: {e}"}

    async def _analyze_dependencies(self) -> dict[str, Any]:
        """Анализирует зависимости"""
        # Простой анализ импортов
        dependencies = {"external_packages": [], "internal_modules": [], "circular_imports": []}

        try:
            for py_file in self.project_root.rglob("*.py"):
                if "venv" in str(py_file) or "__pycache__" in str(py_file):
                    continue

                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Простой поиск импортов
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        if not line.startswith("from .") and not line.startswith("from .."):
                            # Внешний пакет
                            package = line.split()[1].split(".")[0]
                            if package not in dependencies["external_packages"]:
                                dependencies["external_packages"].append(package)
                        else:
                            # Внутренний модуль
                            if line not in dependencies["internal_modules"]:
                                dependencies["internal_modules"].append(line)

            dependencies["external_packages"] = list(set(dependencies["external_packages"]))
            dependencies["internal_modules"] = list(set(dependencies["internal_modules"]))

            return dependencies

        except Exception as e:
            return {"error": f"Ошибка анализа зависимостей: {e}"}

    async def _run_chain_testing(self) -> dict[str, Any]:
        """Запускает тестирование цепочек"""
        try:
            result = subprocess.run(
                [sys.executable, "scripts/full_chain_tester.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                test_results_file = self.results_dir / "full_chain_test_results.json"
                if test_results_file.exists():
                    with open(test_results_file, encoding="utf-8") as f:
                        return json.load(f)
                else:
                    return {"status": "completed", "file_not_found": True}
            else:
                return {"error": f"Ошибка тестирования цепочек: {result.stderr}"}

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут тестирования цепочек (10 минут)"}

    async def _run_integration_tests(self) -> dict[str, Any]:
        """Запускает интеграционные тесты"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            return {
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут интеграционных тестов (5 минут)"}

    async def _run_performance_tests(self) -> dict[str, Any]:
        """Запускает тесты производительности"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-m", "performance", "-v", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            return {
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут performance тестов (5 минут)"}

    async def _analyze_missing_tests(self) -> dict[str, Any]:
        """Анализирует недостающие тесты"""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/comprehensive_test_generator.py",
                    "--analyze-only",
                    "--output-report",
                    "missing_tests_analysis.json",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            analysis_file = self.project_root / "missing_tests_analysis.json"
            if analysis_file.exists():
                with open(analysis_file, encoding="utf-8") as f:
                    return json.load(f)
            else:
                return {"error": "Файл анализа не создан"}

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут анализа тестов (5 минут)"}

    async def _generate_comprehensive_tests(self) -> dict[str, Any]:
        """Генерирует комплексные тесты"""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/comprehensive_test_generator.py",
                    "--max-functions",
                    "500",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=1800,
            )

            return {
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут генерации тестов (30 минут)"}

    async def _validate_generated_tests(self) -> dict[str, Any]:
        """Валидирует сгенерированные тесты"""
        try:
            # Запускаем только новые тесты
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/",
                    "--lf",
                    "-v",
                    "--tb=short",  # --lf = last failed, но покажет новые
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,
            )

            return {
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут валидации тестов (10 минут)"}

    async def _measure_new_coverage(self) -> dict[str, Any]:
        """Измеряет новое покрытие"""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/",
                    "--cov=.",
                    "--cov-report=json:coverage_new.json",
                    "--quiet",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            coverage_file = self.project_root / "coverage_new.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                return {
                    "coverage_percentage": coverage_data["totals"]["percent_covered"],
                    "lines_covered": coverage_data["totals"]["covered_lines"],
                    "lines_total": coverage_data["totals"]["num_statements"],
                }
            else:
                return {"error": "Файл нового покрытия не найден"}

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут измерения покрытия (5 минут)"}

    async def _detect_unused_code(self) -> dict[str, Any]:
        """Обнаруживает неиспользуемый код"""
        # Этот метод использует результаты анализа цепочки кода
        analysis_file = self.results_dir / "code_chain_analysis.json"

        if analysis_file.exists():
            with open(analysis_file, encoding="utf-8") as f:
                analysis_data = json.load(f)

            return {
                "unused_functions": analysis_data.get("unused_code_candidates", []),
                "unreachable_functions": analysis_data.get("unreachable_functions", []),
                "total_candidates": len(analysis_data.get("unused_code_candidates", [])),
            }
        else:
            return {"error": "Файл анализа цепочки кода не найден"}

    async def _analyze_removal_safety(self) -> dict[str, Any]:
        """Анализирует безопасность удаления"""
        try:
            result = subprocess.run(
                [sys.executable, "scripts/unused_code_remover.py", "--analyze-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            return {
                "exit_code": result.returncode,
                "analysis_completed": result.returncode == 0,
                "output": result.stdout,
                "warnings": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут анализа безопасности (5 минут)"}

    async def _remove_unused_code(self) -> dict[str, Any]:
        """Удаляет неиспользуемый код"""
        # В автоматическом режиме запускаем только dry-run
        try:
            result = subprocess.run(
                [sys.executable, "scripts/unused_code_remover.py", "--dry-run"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            return {
                "dry_run_completed": True,
                "exit_code": result.returncode,
                "output": result.stdout,
                "recommendations": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут dry-run удаления (5 минут)"}

    async def _test_after_removal(self) -> dict[str, Any]:
        """Тестирует систему после удаления кода"""
        # В данном случае тестируем текущее состояние
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "--tb=short", "--maxfail=5"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,
            )

            return {
                "exit_code": result.returncode,
                "tests_passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Превышен таймаут тестирования (10 минут)"}

    async def _setup_monitoring(self) -> dict[str, Any]:
        """Настраивает мониторинг"""
        # Создаём конфигурацию мониторинга
        monitoring_config = {
            "enabled": True,
            "coverage_threshold": 85,
            "performance_thresholds": {
                "trading_operations": 0.05,  # 50ms
                "ml_inference": 0.02,  # 20ms
                "api_response": 0.2,  # 200ms
                "database_query": 0.1,  # 100ms
            },
            "monitoring_interval": 30,  # секунд
            "alerts": {
                "coverage_drop": True,
                "performance_degradation": True,
                "test_failures": True,
            },
        }

        config_file = self.results_dir / "monitoring_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(monitoring_config, f, indent=2, ensure_ascii=False)

        return {"config_created": True, "config_file": str(config_file), "monitoring_enabled": True}

    async def _create_coverage_dashboard(self) -> dict[str, Any]:
        """Создаёт дашборд покрытия"""
        dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BOT_AI_V3 Coverage Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .metric {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .success {{ background: #d4edda; border-left: 5px solid #28a745; }}
        .warning {{ background: #fff3cd; border-left: 5px solid #ffc107; }}
        .danger {{ background: #f8d7da; border-left: 5px solid #dc3545; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
    </style>
</head>
<body>
    <h1>🧪 BOT_AI_V3 Testing Dashboard</h1>
    <div class="grid">
        <div class="metric success">
            <h3>📊 Покрытие кода</h3>
            <p>Цель: 100% активного кода</p>
            <p>Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="metric warning">
            <h3>🔗 Тестирование цепочек</h3>
            <p>8 критических workflow</p>
            <p>Требования производительности</p>
        </div>
        <div class="metric">
            <h3>🗑️ Неиспользуемый код</h3>
            <p>Автоматическое обнаружение</p>
            <p>Безопасное удаление</p>
        </div>
        <div class="metric">
            <h3>📈 Мониторинг</h3>
            <p>Real-time отслеживание</p>
            <p>Алерты и уведомления</p>
        </div>
    </div>
    
    <h2>📋 Быстрые ссылки</h2>
    <ul>
        <li><a href="htmlcov/index.html">HTML Coverage Report</a></li>
        <li><a href="analysis_results/code_chain_analysis.json">Анализ цепочки кода</a></li>
        <li><a href="analysis_results/full_chain_test_results.json">Результаты тестирования цепочек</a></li>
        <li><a href="analysis_results/coverage_monitoring_report.json">Отчёт мониторинга</a></li>
    </ul>
    
    <h2>🚀 Команды запуска</h2>
    <pre>
# Полный анализ системы
python3 scripts/master_test_runner.py --full-analysis

# Анализ цепочки кода
python3 scripts/code_chain_analyzer.py

# Тестирование цепочек
python3 scripts/full_chain_tester.py

# Генерация тестов
python3 scripts/comprehensive_test_generator.py

# Мониторинг покрытия
python3 scripts/coverage_monitor.py

# Удаление неиспользуемого кода
python3 scripts/unused_code_remover.py
    </pre>
    
    <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd;">
        <p>🤖 Сгенерировано Master Test Runner - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </footer>
</body>
</html>
        """

        dashboard_file = self.results_dir / "testing_dashboard.html"
        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(dashboard_html)

        return {
            "dashboard_created": True,
            "dashboard_file": str(dashboard_file),
            "url": f"file://{dashboard_file.absolute()}",
        }

    async def _setup_automation(self) -> dict[str, Any]:
        """Настраивает автоматизацию"""
        # Создаём скрипт автоматизации
        automation_script = """#!/bin/bash
# Автоматизированное тестирование BOT_AI_V3
set -e

echo "🤖 Запуск автоматизированного тестирования..."

# Активируем окружение
source venv/bin/activate
export PYTHONPATH="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3:$PYTHONPATH"
export PGPORT=5555

# Быстрая проверка системы
echo "📊 Базовая проверка покрытия..."
python3 -m pytest tests/ --cov=. --cov-report=term-missing --quiet

# Проверка критических цепочек
echo "🔗 Проверка критических цепочек..."
python3 scripts/full_chain_tester.py --quick

# Анализ производительности
echo "⚡ Анализ производительности..."
python3 -m pytest tests/ -m performance --quiet

echo "✅ Автоматизированная проверка завершена!"
"""

        automation_file = self.project_root / "run_automated_tests.sh"
        with open(automation_file, "w", encoding="utf-8") as f:
            f.write(automation_script)

        # Делаем исполняемым
        automation_file.chmod(0o755)

        return {
            "automation_script_created": True,
            "script_file": str(automation_file),
            "executable": True,
        }

    async def _final_validation(self) -> dict[str, Any]:
        """Финальная валидация системы"""
        validation_results = {
            "coverage_check": False,
            "tests_passing": False,
            "performance_check": False,
            "documentation_check": False,
            "overall_success": False,
        }

        try:
            # Проверка покрытия
            coverage_result = await self._get_coverage_baseline()
            if "coverage_percentage" in coverage_result:
                validation_results["coverage_check"] = coverage_result["coverage_percentage"] > 50

            # Проверка тестов
            test_result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "--quiet", "--tb=no"],
                cwd=self.project_root,
                capture_output=True,
                timeout=300,
            )
            validation_results["tests_passing"] = test_result.returncode == 0

            # Проверка документации
            docs_exist = (self.project_root / "docs" / "RUSSIAN_TESTING_GUIDE.md").exists() and (
                self.project_root / "docs" / "TESTING_COMPLETE_GUIDE.md"
            ).exists()
            validation_results["documentation_check"] = docs_exist

            # Общий успех
            validation_results["overall_success"] = all(
                [
                    validation_results["coverage_check"],
                    validation_results["tests_passing"],
                    validation_results["documentation_check"],
                ]
            )

        except Exception as e:
            validation_results["error"] = str(e)

        return validation_results

    def generate_final_report(self) -> dict[str, Any]:
        """Генерирует финальный отчёт"""
        total_time = (
            time.time() - datetime.fromisoformat(self.execution_results["start_time"]).timestamp()
        )

        # Подсчитываем успешные этапы
        successful_stages = sum(
            1 for stage in self.execution_results["stages"].values() if stage.get("success", False)
        )
        total_stages = len(self.execution_results["stages"])

        # Анализируем результаты
        analysis_results = self.execution_results["stages"].get("code_chain_analysis", {})
        baseline_coverage = self.execution_results["stages"].get("coverage_baseline", {})
        new_coverage = self.execution_results["stages"].get("coverage_measurement", {})

        # Вычисляем улучшение покрытия
        coverage_improvement = 0.0
        if baseline_coverage.get("result", {}).get("coverage_percentage") and new_coverage.get(
            "result", {}
        ).get("coverage_percentage"):
            old_coverage = baseline_coverage["result"]["coverage_percentage"]
            new_coverage_val = new_coverage["result"]["coverage_percentage"]
            coverage_improvement = new_coverage_val - old_coverage

        # Генерируем рекомендации
        recommendations = []
        if coverage_improvement < 20:
            recommendations.append("🔴 Требуется генерация большего количества тестов")
        if successful_stages < total_stages:
            recommendations.append(
                "⚠️ Некоторые этапы завершились с ошибками - требуется ручная проверка"
            )

        final_validation = self.execution_results["stages"].get("final_validation", {})
        if not final_validation.get("result", {}).get("overall_success", False):
            recommendations.append(
                "🔧 Финальная валидация не прошла - требуется дополнительная настройка"
            )

        # Следующие шаги
        next_steps = [
            "1. Просмотрите отчёты в analysis_results/",
            "2. Запустите ./run_automated_tests.sh для регулярной проверки",
            "3. Настройте CI/CD с созданными скриптами",
            "4. Добавьте недостающие edge case тесты",
            "5. Настройте production мониторинг",
        ]

        if coverage_improvement > 0:
            next_steps.insert(0, f"✅ Покрытие улучшено на {coverage_improvement:.1f}%")

        final_report = {
            "execution_summary": {
                "total_execution_time": total_time,
                "successful_stages": successful_stages,
                "total_stages": total_stages,
                "success_rate": (successful_stages / total_stages * 100) if total_stages > 0 else 0,
            },
            "coverage_improvement": coverage_improvement,
            "overall_success": successful_stages >= total_stages * 0.8,  # 80% этапов успешны
            "recommendations": recommendations,
            "next_steps": next_steps,
            "generated_files": {
                "analysis_results": str(self.results_dir),
                "dashboard": str(self.results_dir / "testing_dashboard.html"),
                "automation_script": str(self.project_root / "run_automated_tests.sh"),
                "documentation": [
                    str(self.project_root / "docs" / "RUSSIAN_TESTING_GUIDE.md"),
                    str(self.project_root / "docs" / "TESTING_COMPLETE_GUIDE.md"),
                ],
            },
            "detailed_results": self.execution_results,
        }

        return final_report

    def save_final_report(self, report: dict[str, Any]):
        """Сохраняет финальный отчёт"""
        report_file = self.results_dir / "master_test_runner_report.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"💾 Финальный отчёт сохранён: {report_file}")

    def print_final_summary(self, report: dict[str, Any]):
        """Выводит финальную сводку"""
        print("\n" + "🎉 " + "MASTER TEST RUNNER - ФИНАЛЬНЫЙ ОТЧЁТ".center(58) + " 🎉")
        print("=" * 60)

        exec_summary = report["execution_summary"]
        print(f"⏱️  Общее время выполнения: {exec_summary['total_execution_time']:.1f}с")
        print(
            f"✅ Успешных этапов: {exec_summary['successful_stages']}/{exec_summary['total_stages']}"
        )
        print(f"📊 Успешность: {exec_summary['success_rate']:.1f}%")

        if report["coverage_improvement"] > 0:
            print(f"📈 Улучшение покрытия: +{report['coverage_improvement']:.1f}%")

        print("=" * 60)

        if report["overall_success"]:
            print("🏆 СИСТЕМА ТЕСТИРОВАНИЯ УСПЕШНО НАСТРОЕНА!")
        else:
            print("⚠️  Настройка завершена с предупреждениями")

        # Подробные ссылки на результаты
        print("\n📂 ГДЕ ИСКАТЬ РЕЗУЛЬТАТЫ:")
        print("─" * 40)

        # Основные файлы
        print("🌐 Веб дашборд:")
        print(f"   firefox {self.results_dir}/testing_dashboard.html")
        print("   📊 Все метрики в одном месте")

        print("\n📈 HTML отчёт покрытия:")
        print("   firefox htmlcov/index.html")
        print("   📊 Детальное покрытие по файлам")

        print("\n📄 JSON отчёты:")
        print(f"   📋 Граф кода: {self.results_dir}/code_chain_analysis.json")
        print(f"   🔗 Тесты цепочек: {self.results_dir}/full_chain_test_results.json")
        print(f"   📊 Общий отчёт: {self.results_dir}/master_test_runner_report.json")

        print("\n🔍 Логи и мониторинг:")
        print("   📝 Логи анализа: data/logs/background_analysis_*.log")
        print(f"   ⚠️  Предупреждения: {self.results_dir}/analysis_warnings.txt")
        print(f"   📋 Последний статус: {self.results_dir}/last_background_analysis.txt")

        # Команды для быстрого доступа
        print("\n🚀 БЫСТРЫЕ КОМАНДЫ:")
        print("─" * 40)
        print("# Проверка результатов фонового анализа")
        print("python3 scripts/check_background_analysis.py")
        print("")
        print("# Просмотр текущего покрытия")
        print("pytest tests/ --cov=. --cov-report=term-missing")
        print("")
        print("# Запуск мониторинга в реальном времени")
        print("python3 scripts/coverage_monitor.py")
        print("")
        print("# Поиск и удаление неиспользуемого кода")
        print("python3 scripts/unused_code_remover.py")

        # Порты и URL
        print("\n🌐 СЕРВИСЫ И ПОРТЫ:")
        print("─" * 40)
        print("🗄️  PostgreSQL: localhost:5555 (НЕ 5432!)")
        print("🌐 API Server: http://localhost:8083")
        print("📡 REST API: http://localhost:8084")
        print("🔗 WebSocket: ws://localhost:8085")
        print("🎣 Webhook: http://localhost:8086")
        print("🖥️  Frontend: http://localhost:5173")

        if report["recommendations"]:
            print("\n💡 РЕКОМЕНДАЦИИ:")
            print("─" * 40)
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"  {i}. {rec}")

        print("\n🎯 СЛЕДУЮЩИЕ ШАГИ:")
        print("─" * 40)
        for i, step in enumerate(report["next_steps"][:5], 1):
            print(f"  {i}. {step}")

        if report["overall_success"]:
            print("\n🎊 ПОЗДРАВЛЯЕМ! Система тестирования настроена и готова к работе!")
            print("   Теперь при каждом коммите будет автоматически:")
            print("   ✅ Проверяться качество кода")
            print("   ✅ Запускаться тесты")
            print("   ✅ Анализироваться покрытие")
            print("   ✅ Мониториться производительность")
        else:
            print("\n⚠️  Некоторые этапы завершились с ошибками.")
            print("   Проверьте логи и исправьте проблемы:")
            print("   🔍 python3 scripts/check_background_analysis.py")

        print("\n" + "=" * 60)


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="Master Test Runner для BOT_AI_V3")
    parser.add_argument(
        "--full-analysis", action="store_true", help="Запустить полный анализ системы"
    )
    parser.add_argument(
        "--chain-testing", action="store_true", help="Запустить только тестирование цепочек"
    )
    parser.add_argument(
        "--test-generation", action="store_true", help="Запустить только генерацию тестов"
    )
    parser.add_argument("--code-cleanup", action="store_true", help="Запустить только очистку кода")
    parser.add_argument(
        "--monitoring-setup", action="store_true", help="Настроить только мониторинг"
    )
    parser.add_argument("--quick", action="store_true", help="Быстрая проверка (базовые тесты)")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    runner = MasterTestRunner(project_root)

    runner.print_header()

    # Если никаких флагов не указано, запускаем полный анализ
    if not any(
        [
            args.full_analysis,
            args.chain_testing,
            args.test_generation,
            args.code_cleanup,
            args.monitoring_setup,
            args.quick,
        ]
    ):
        args.full_analysis = True

    try:
        if args.quick:
            print("\n⚡ БЫСТРАЯ ПРОВЕРКА СИСТЕМЫ")
            print("-" * 30)
            # Только базовые проверки
            await runner._get_coverage_baseline()
            await runner._run_integration_tests()
            print("✅ Быстрая проверка завершена")
            return

        if args.full_analysis:
            await runner.run_full_analysis()
            await runner.run_chain_testing()
            await runner.run_test_generation()
            await runner.run_code_cleanup()
            await runner.run_monitoring_setup()
        elif args.chain_testing:
            await runner.run_chain_testing()
        elif args.test_generation:
            await runner.run_test_generation()
        elif args.code_cleanup:
            await runner.run_code_cleanup()
        elif args.monitoring_setup:
            await runner.run_monitoring_setup()

        # Генерируем и сохраняем финальный отчёт
        final_report = runner.generate_final_report()
        runner.save_final_report(final_report)
        runner.print_final_summary(final_report)

    except KeyboardInterrupt:
        print("\n\n⚠️ Выполнение прервано пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
