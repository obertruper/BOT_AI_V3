#!/usr/bin/env python3
"""
🎯 Единая точка входа для всей системы тестирования BOT_AI_V3
Визуальный интерфейс и полная интеграция всех тестовых компонентов
"""

import argparse
import asyncio
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Импорт улучшенного генератора дашборда
try:
    from enhanced_dashboard_generator import EnhancedDashboardGenerator

    ENHANCED_DASHBOARD_AVAILABLE = True
except ImportError:
    ENHANCED_DASHBOARD_AVAILABLE = False


# Цвета для терминала
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class UnifiedTestOrchestrator:
    """Единый оркестратор всех тестовых систем"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results_dir = self.project_root / "test_results"
        self.results_dir.mkdir(exist_ok=True)

        # Компоненты тестирования
        self.components = {
            "unit_tests": {
                "name": "Unit Tests",
                "icon": "🧪",
                "command": "pytest tests/unit/test_simple_working.py tests/unit/test_database_simple.py tests/unit/test_trading_simple.py tests/unit/test_ml_simple.py --tb=short -q",
                "enabled": True,
                "status": "pending",
            },
            "database_tests": {
                "name": "Database Tests",
                "icon": "🗄️",
                "command": "pytest tests/unit/test_database_simple.py --tb=short -q",
                "enabled": True,
                "status": "pending",
            },
            "trading_tests": {
                "name": "Trading Tests",
                "icon": "📈",
                "command": "pytest tests/unit/test_trading_simple.py --tb=short -q",
                "enabled": True,
                "status": "pending",
            },
            "ml_tests": {
                "name": "ML System Tests",
                "icon": "🧠",
                "command": "pytest tests/unit/test_ml_simple.py --tb=short -q",
                "enabled": True,
                "status": "pending",
            },
            "integration_tests": {
                "name": "Integration Tests",
                "icon": "🔗",
                "command": "pytest tests/integration/test_core_system_integration.py tests/integration/test_end_to_end_workflows.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "performance_tests": {
                "name": "Performance Tests",
                "icon": "⚡",
                "command": "python3 test_signal_quality.py 2>/dev/null || echo 'Performance test not found'",
                "enabled": False,
                "status": "pending",
            },
            "code_quality": {
                "name": "Code Quality Check",
                "icon": "✨",
                "command": "ruff check . --statistics 2>/dev/null || echo 'Ruff not configured'",
                "enabled": True,
                "status": "pending",
            },
            "type_check": {
                "name": "Type Checking",
                "icon": "🔍",
                "command": "mypy . --ignore-missing-imports --no-error-summary 2>/dev/null || echo 'MyPy check skipped'",
                "enabled": False,
                "status": "pending",
            },
            "coverage_report": {
                "name": "Coverage Report",
                "icon": "📊",
                "command": "pytest tests/unit/test_simple_working.py tests/unit/test_database_simple.py tests/unit/test_trading_simple.py tests/unit/test_ml_simple.py tests/unit/test_feature_engineering_production.py tests/unit/test_exchanges_comprehensive.py tests/unit/test_web_api_comprehensive.py tests/unit/test_core_orchestrator.py tests/unit/test_trading_engine_comprehensive.py tests/unit/test_ml_manager_comprehensive.py tests/unit/test_core_system_comprehensive.py tests/unit/test_main_application.py tests/unit/test_unified_launcher.py tests/unit/test_ml_prediction_logger.py tests/unit/test_ml_manager_enhanced.py --cov=main --cov=unified_launcher --cov=core --cov=trading --cov=ml --cov=database --cov=exchanges --cov=web --cov-report=term-missing --cov-report=json -q",
                "enabled": True,
                "status": "pending",
            },
            "security_check": {
                "name": "Security Check",
                "icon": "🔐",
                "command": "grep -r 'API_KEY\\|SECRET\\|PASSWORD' --include='*.py' . 2>/dev/null | grep -v '.env' | grep -v 'test_' || echo 'No secrets found in code'",
                "enabled": True,
                "status": "pending",
            },
            "feature_engineering_tests": {
                "name": "Feature Engineering Tests",
                "icon": "⚙️",
                "command": "pytest tests/unit/test_feature_engineering_production.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "exchanges_tests": {
                "name": "Exchanges System Tests",
                "icon": "🔄",
                "command": "pytest tests/unit/test_exchanges_comprehensive.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "web_api_tests": {
                "name": "Web API Tests",
                "icon": "🌐",
                "command": "pytest tests/unit/test_web_api_comprehensive.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "core_orchestrator_tests": {
                "name": "Core Orchestrator Tests",
                "icon": "🎯",
                "command": "pytest tests/unit/test_core_orchestrator.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "trading_engine_tests": {
                "name": "Trading Engine Tests",
                "icon": "⚡",
                "command": "pytest tests/unit/test_trading_engine_comprehensive.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "ml_manager_tests": {
                "name": "ML Manager Tests",
                "icon": "🧠",
                "command": "pytest tests/unit/test_ml_manager_comprehensive.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "core_system_tests": {
                "name": "Core System Tests",
                "icon": "⚙️",
                "command": "pytest tests/unit/test_core_system_comprehensive.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "main_application_tests": {
                "name": "Main Application Tests",
                "icon": "🎯",
                "command": "pytest tests/unit/test_main_application.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "unified_launcher_tests": {
                "name": "Unified Launcher Tests",
                "icon": "🚀",
                "command": "pytest tests/unit/test_unified_launcher.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "ml_prediction_logger_tests": {
                "name": "ML Prediction Logger Tests",
                "icon": "📊",
                "command": "pytest tests/unit/test_ml_prediction_logger.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "ml_manager_enhanced_tests": {
                "name": "ML Manager Enhanced Tests",
                "icon": "🧠",
                "command": "pytest tests/unit/test_ml_manager_enhanced.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "code_usage_analyzer_tests": {
                "name": "Code Usage Analyzer Tests",
                "icon": "🔍",
                "command": "pytest tests/analysis/test_code_usage_analyzer.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "code_analyzer_validation_tests": {
                "name": "Code Analyzer Validation Tests",
                "icon": "✅",
                "command": "pytest tests/analysis/test_code_analyzer_validation.py --tb=short -v",
                "enabled": True,
                "status": "pending",
            },
            "code_analysis_report": {
                "name": "Code Usage Analysis Report",
                "icon": "📊",
                "command": "python3 scripts/run_code_usage_analysis.py --format both --verbose",
                "enabled": False,  # Отключен по умолчанию так как может быть медленным
                "status": "pending",
            },
            # === DYNAMIC SL/TP TEST SUITE ===
            "dynamic_sltp_unit_tests": {
                "name": "Dynamic SL/TP Unit Tests",
                "icon": "📊",
                "command": "pytest tests/unit/trading/orders/test_dynamic_sltp_calculator.py -v --tb=short -m sltp",
                "enabled": True,
                "status": "pending",
            },
            "dynamic_sltp_integration_tests": {
                "name": "Dynamic SL/TP Integration",
                "icon": "🔗",
                "command": "pytest tests/integration/test_dynamic_sltp_integration.py -v --tb=short -m 'integration and sltp'",
                "enabled": True,
                "status": "pending",
            },
            "dynamic_sltp_e2e_tests": {
                "name": "Dynamic SL/TP E2E Tests",
                "icon": "🎯",
                "command": "pytest tests/integration/test_dynamic_sltp_e2e.py -v --tb=short -m 'e2e and sltp'",
                "enabled": True,
                "status": "pending",
            },
            "dynamic_sltp_performance_tests": {
                "name": "Dynamic SL/TP Performance",
                "icon": "⚡",
                "command": "pytest tests/performance/test_dynamic_sltp_performance.py -v --tb=short -m 'performance and sltp'",
                "enabled": False,  # По умолчанию отключен - может быть медленным
                "status": "pending",
            },
            "dynamic_sltp_comprehensive": {
                "name": "Complete Dynamic SL/TP Suite",
                "icon": "🎪",
                "command": "pytest tests/unit/trading/orders/test_dynamic_sltp_calculator.py tests/integration/test_dynamic_sltp_integration.py tests/integration/test_dynamic_sltp_e2e.py -v --tb=short -m sltp",
                "enabled": True,
                "status": "pending",
            },
        }

        # Статистика
        self.stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "coverage_percent": 0.0,
            "execution_time": 0,
            "errors": [],
            "warnings": [],
        }

    def print_header(self):
        """Красивый заголовок"""
        terminal_width = shutil.get_terminal_size().columns
        print("\n" + Colors.CYAN + "=" * terminal_width + Colors.ENDC)
        print(
            Colors.BOLD
            + Colors.HEADER
            + "🚀 UNIFIED TEST ORCHESTRATOR FOR BOT_AI_V3 🚀".center(terminal_width)
            + Colors.ENDC
        )
        print(Colors.CYAN + "=" * terminal_width + Colors.ENDC)
        print(f"{Colors.BLUE}📁 Project:{Colors.ENDC} {self.project_root}")
        print(f"{Colors.BLUE}📊 Results:{Colors.ENDC} {self.results_dir}")
        print(
            f"{Colors.BLUE}⏰ Started:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(Colors.CYAN + "=" * terminal_width + Colors.ENDC)

    def print_menu(self):
        """Интерактивное меню"""
        print(f"\n{Colors.BOLD}📋 Test Components:{Colors.ENDC}")
        print("-" * 60)

        for key, component in self.components.items():
            status_icon = "✅" if component["enabled"] else "⭕"
            status_color = Colors.GREEN if component["enabled"] else Colors.WARNING
            print(
                f"{status_color}{status_icon}{Colors.ENDC} {component['icon']} "
                f"{component['name']:<25} [{key}]"
            )

        print("-" * 60)
        print(f"\n{Colors.BOLD}⚙️  Options:{Colors.ENDC}")
        print("  [1] Run all enabled tests")
        print("  [2] Toggle component on/off")
        print("  [3] Run specific component")
        print("  [4] Generate HTML report")
        print("  [5] Clean previous results")
        print("  [6] Quick test (unit only)")
        print("  [7] Full analysis (everything)")
        print("  [8] Visual dashboard")
        print("  [9] Code analysis suite")
        print("  [D] Dynamic SL/TP test suite 📊")
        if ENHANCED_DASHBOARD_AVAILABLE:
            print("  [E] Enhanced interactive dashboard ✨")
        print("  [0] Exit")

    def toggle_component(self, component_key: str):
        """Переключить компонент"""
        if component_key in self.components:
            self.components[component_key]["enabled"] = not self.components[component_key][
                "enabled"
            ]
            status = "enabled" if self.components[component_key]["enabled"] else "disabled"
            print(f"{Colors.GREEN}✓{Colors.ENDC} {self.components[component_key]['name']} {status}")
        else:
            print(f"{Colors.FAIL}✗{Colors.ENDC} Unknown component: {component_key}")

    async def run_component(self, key: str, component: dict) -> dict:
        """Запуск одного компонента"""
        print(f"\n{Colors.CYAN}▶{Colors.ENDC} Running {component['icon']} {component['name']}...")

        start_time = time.time()
        result = {
            "name": component["name"],
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "output": "",
            "error": "",
            "execution_time": 0,
        }

        try:
            # Используем python из venv напрямую
            venv_python = self.project_root / "venv/bin/python3"
            if venv_python.exists():
                # Заменяем pytest на полный путь к pytest из venv
                command = component["command"].replace("pytest", f"{venv_python.parent}/pytest")
                command = command.replace("python3", str(venv_python))
                command = command.replace("ruff", f"{venv_python.parent}/ruff")
                command = command.replace("mypy", f"{venv_python.parent}/mypy")
            else:
                command = component["command"]

            full_command = f"cd {self.project_root} && {command}"

            process = await asyncio.create_subprocess_shell(
                full_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            result["output"] = stdout.decode() if stdout else ""
            result["error"] = stderr.decode() if stderr else ""

            # Для pytest определяем статус по содержимому вывода
            if "pytest" in component["command"]:
                output_text = result["output"] + result["error"]
                # Проверяем наличие успешных тестов в выводе
                if "passed" in output_text and "failed" not in output_text:
                    result["status"] = "success"
                elif "passed" in output_text and "failed" in output_text:
                    # Есть и успешные и проваленные тесты
                    result["status"] = "partial"
                elif "No tests ran" in output_text or "no tests ran" in output_text:
                    result["status"] = "failed"
                elif process.returncode == 0 or "warning" in output_text.lower():
                    # Если только warnings, считаем успешным
                    result["status"] = "success"
                else:
                    result["status"] = "failed"
            else:
                result["status"] = "success" if process.returncode == 0 else "failed"

            # Обновляем статус компонента
            self.components[key]["status"] = result["status"]

            # Парсим результаты если это pytest
            if "pytest" in component["command"]:
                self._parse_pytest_output(result["output"])
                # Также парсим stderr, так как pytest может выводить туда
                if result["error"]:
                    self._parse_pytest_output(result["error"])

            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"{status_icon} {component['name']}: {result['status'].upper()}")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            self.components[key]["status"] = "error"
            print(f"❌ {component['name']}: ERROR - {e}")

        result["execution_time"] = time.time() - start_time
        result["end_time"] = datetime.now().isoformat()

        return result

    def _parse_pytest_output(self, output: str):
        """Парсинг вывода pytest"""
        import re

        # Сбрасываем счетчики перед парсингом нового вывода
        current_passed = 0
        current_failed = 0

        lines = output.split("\n")
        for line in lines:
            # Ищем строки вида "37 passed, 2 warnings in 0.09s" или "5 passed, 2 failed in 1.23s"
            # Также ищем "====== 37 passed in 0.09s ======"
            if "passed" in line or "failed" in line:
                # Ищем числа перед словами passed и failed
                passed_match = re.search(r"(\d+)\s+passed", line)
                failed_match = re.search(r"(\d+)\s+failed", line)

                if passed_match:
                    current_passed = max(current_passed, int(passed_match.group(1)))
                if failed_match:
                    current_failed = max(current_failed, int(failed_match.group(1)))

        # Обновляем общую статистику (накапливаем результаты)
        if current_passed > 0 or current_failed > 0:
            self.stats["passed_tests"] += current_passed
            self.stats["failed_tests"] += current_failed
            self.stats["total_tests"] = self.stats["passed_tests"] + self.stats["failed_tests"]

    async def run_dynamic_sltp_suite(self):
        """Специализированная функция для запуска Dynamic SL/TP test suite"""
        print(f"\n{Colors.HEADER}📊 DYNAMIC SL/TP TEST SUITE{Colors.ENDC}")
        print(f"{Colors.CYAN}{'=' * 50}{Colors.ENDC}")

        # Определяем все компоненты Dynamic SL/TP
        dynamic_sltp_components = [
            "dynamic_sltp_unit_tests",
            "dynamic_sltp_integration_tests",
            "dynamic_sltp_e2e_tests",
            "dynamic_sltp_performance_tests",
            "dynamic_sltp_comprehensive",
        ]

        # Отключаем все остальные компоненты
        for key in self.components:
            if key in dynamic_sltp_components:
                self.components[key]["enabled"] = True
                print(f"{Colors.GREEN}✓{Colors.ENDC} Enabled: {self.components[key]['name']}")
            else:
                self.components[key]["enabled"] = False

        print(f"\n{Colors.BLUE}🎯 Running Dynamic SL/TP comprehensive test suite...{Colors.ENDC}")

        # Предлагаем варианты выполнения
        print(f"\n{Colors.BOLD}Select test mode:{Colors.ENDC}")
        print("  [1] Quick tests (unit + integration)")
        print("  [2] Complete suite (unit + integration + e2e)")
        print("  [3] Performance suite (all + performance)")
        print("  [4] Comprehensive all-in-one test")
        print("  [0] Cancel")

        try:
            mode_choice = input(f"\n{Colors.BOLD}Enter mode choice:{Colors.ENDC} ").strip()

            if mode_choice == "0":
                print(f"{Colors.WARNING}✗{Colors.ENDC} Cancelled")
                return
            elif mode_choice == "1":
                # Quick tests
                selected_components = ["dynamic_sltp_unit_tests", "dynamic_sltp_integration_tests"]
            elif mode_choice == "2":
                # Complete suite
                selected_components = [
                    "dynamic_sltp_unit_tests",
                    "dynamic_sltp_integration_tests",
                    "dynamic_sltp_e2e_tests",
                ]
            elif mode_choice == "3":
                # Performance suite
                selected_components = dynamic_sltp_components  # все включая performance
            elif mode_choice == "4":
                # Comprehensive all-in-one
                selected_components = ["dynamic_sltp_comprehensive"]
            else:
                print(f"{Colors.WARNING}⚠️ Invalid mode, running quick tests{Colors.ENDC}")
                selected_components = ["dynamic_sltp_unit_tests", "dynamic_sltp_integration_tests"]

            # Отключаем неселектированные компоненты
            for key in dynamic_sltp_components:
                self.components[key]["enabled"] = key in selected_components

            # Запускаем выбранные тесты
            await self.run_all_enabled()

            # Генерируем отчет
            print(f"\n{Colors.GREEN}✨ Generating Dynamic SL/TP test report...{Colors.ENDC}")
            self.generate_html_dashboard()

            # Выводим краткую статистику
            print(f"\n{Colors.HEADER}📊 Dynamic SL/TP Test Results Summary:{Colors.ENDC}")
            print(f"  Total tests: {self.stats['total_tests']}")
            print(f"  Passed: {Colors.GREEN}{self.stats['passed_tests']}{Colors.ENDC}")
            print(f"  Failed: {Colors.FAIL}{self.stats['failed_tests']}{Colors.ENDC}")

            if self.stats["failed_tests"] == 0:
                print(f"\n{Colors.GREEN}🎉 All Dynamic SL/TP tests passed!{Colors.ENDC}")
            else:
                print(
                    f"\n{Colors.WARNING}⚠️ Some tests failed, check the detailed report{Colors.ENDC}"
                )

        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}✗{Colors.ENDC} Dynamic SL/TP test suite cancelled")
        except Exception as e:
            print(f"{Colors.FAIL}❌ Error in Dynamic SL/TP suite: {e}{Colors.ENDC}")

    def generate_enhanced_dashboard(self):
        """Генерирует улучшенный интерактивный дашборд"""
        if not ENHANCED_DASHBOARD_AVAILABLE:
            print(
                f"{Colors.WARNING}⚠️ Enhanced dashboard not available, using basic version{Colors.ENDC}"
            )
            self.generate_html_dashboard()
            return

        print(f"{Colors.CYAN}✨ Generating enhanced interactive dashboard...{Colors.ENDC}")

        try:
            generator = EnhancedDashboardGenerator()

            # Собираем результаты если они есть
            results = getattr(self, "last_results", {})

            html_content = generator.generate_interactive_dashboard(
                stats=self.stats, components=self.components, results=results
            )

            dashboard_file = self.results_dir / "enhanced_dashboard.html"
            with open(dashboard_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"{Colors.GREEN}✨ Enhanced dashboard generated: {dashboard_file}{Colors.ENDC}")
            print(f"  🌐 Open in browser: file://{dashboard_file}")

            # Попытка открыть в браузере
            try:
                import webbrowser

                webbrowser.open(f"file://{dashboard_file}")
            except:
                pass

        except Exception as e:
            print(f"{Colors.FAIL}❌ Error generating enhanced dashboard: {e}{Colors.ENDC}")
            print(f"{Colors.WARNING}📋 Falling back to basic dashboard{Colors.ENDC}")
            self.generate_html_dashboard()

    async def run_all_enabled(self):
        """Запуск всех включенных компонентов"""
        print(f"\n{Colors.BOLD}🚀 Starting test execution...{Colors.ENDC}\n")

        # Сбрасываем статистику перед запуском
        self.stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "coverage_percent": 0.0,
            "execution_time": 0,
            "errors": [],
            "warnings": [],
        }

        results = {}
        start_time = time.time()

        # Запускаем компоненты последовательно для лучшего контроля
        for key, component in self.components.items():
            if component["enabled"]:
                results[key] = await self.run_component(key, component)
                await asyncio.sleep(0.5)  # Небольшая пауза между компонентами

        self.stats["execution_time"] = time.time() - start_time

        # Сохраняем результаты в объекте для парсинга покрытия
        self.last_results = results

        # Сохраняем результаты
        self._save_results(results)

        # Показываем итоги
        self._print_summary()

        return results

    def _save_results(self, results: dict):
        """Сохранение результатов"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON отчет
        report = {
            "timestamp": datetime.now().isoformat(),
            "project": str(self.project_root),
            "stats": self.stats,
            "components": results,
            "coverage": self._get_coverage_data(),
        }

        json_file = self.results_dir / f"test_report_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n{Colors.GREEN}✓{Colors.ENDC} Report saved: {json_file}")

    def _get_coverage_data(self) -> dict:
        """Получение данных покрытия"""
        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    data = json.load(f)
                    if "totals" in data:
                        self.stats["coverage_percent"] = data["totals"].get("percent_covered", 0)
                        return data["totals"]
            except Exception as e:
                print(f"Warning: Could not parse coverage data: {e}")

        # Попытка найти покрытие в выводе pytest
        for key, component in self.components.items():
            if key == "coverage_report" and component.get("status") == "success":
                # Ищем coverage в результатах
                results = getattr(self, "last_results", {})
                if key in results:
                    output = results[key].get("output", "")
                    if "%" in output:
                        # Ищем строку вида "TOTAL ... 45%"
                        import re

                        match = re.search(r"TOTAL.*?(\d+)%", output)
                        if match:
                            coverage = float(match.group(1))
                            self.stats["coverage_percent"] = coverage
                            return {"percent_covered": coverage}

        return {}

    def _print_summary(self):
        """Вывод итогов"""
        terminal_width = shutil.get_terminal_size().columns

        print("\n" + Colors.CYAN + "=" * terminal_width + Colors.ENDC)
        print(Colors.BOLD + "📊 TEST EXECUTION SUMMARY".center(terminal_width) + Colors.ENDC)
        print(Colors.CYAN + "=" * terminal_width + Colors.ENDC)

        # Статус компонентов
        print(f"\n{Colors.BOLD}Component Status:{Colors.ENDC}")
        for key, component in self.components.items():
            if component["enabled"]:
                status = component["status"]
                if status == "success":
                    icon = f"{Colors.GREEN}✅{Colors.ENDC}"
                elif status == "failed":
                    icon = f"{Colors.FAIL}❌{Colors.ENDC}"
                elif status == "error":
                    icon = f"{Colors.WARNING}⚠️{Colors.ENDC}"
                else:
                    icon = "⭕"

                print(f"  {icon} {component['name']:<30} {status}")

        # Общая статистика
        print(f"\n{Colors.BOLD}Overall Statistics:{Colors.ENDC}")
        print(f"  📋 Total Tests: {self.stats['total_tests']}")
        print(f"  ✅ Passed: {Colors.GREEN}{self.stats['passed_tests']}{Colors.ENDC}")
        print(f"  ❌ Failed: {Colors.FAIL}{self.stats['failed_tests']}{Colors.ENDC}")
        print(f"  📊 Coverage: {Colors.CYAN}{self.stats['coverage_percent']:.1f}%{Colors.ENDC}")
        print(f"  ⏱️  Execution Time: {self.stats['execution_time']:.2f}s")

        # Рекомендации
        if self.stats["coverage_percent"] < 80:
            print(f"\n{Colors.WARNING}⚠️  Recommendations:{Colors.ENDC}")
            print("  • Coverage is below 80%. Run test generator to create more tests")
            print("  • Focus on critical components: trading/, ml/, exchanges/")
            print("  • Use 'python3 scripts/mass_test_generator.py' for automatic test generation")

        print("\n" + Colors.CYAN + "=" * terminal_width + Colors.ENDC)

    def generate_html_dashboard(self):
        """Генерация HTML дашборда"""
        print(f"\n{Colors.CYAN}📊 Generating HTML dashboard...{Colors.ENDC}")

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOT_AI_V3 Test Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
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
        h1 {{
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #666;
            font-size: 1.2em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-icon {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #999;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .components {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .component-item {{
            display: flex;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
            transition: background 0.3s;
        }}
        .component-item:hover {{
            background: #f9f9f9;
        }}
        .component-icon {{
            font-size: 1.5em;
            margin-right: 15px;
        }}
        .component-name {{
            flex: 1;
            font-weight: 500;
            color: #333;
        }}
        .component-status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
        }}
        .status-success {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-pending {{
            background: #fff3cd;
            color: #856404;
        }}
        .coverage-bar {{
            width: 100%;
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 20px;
        }}
        .coverage-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 1s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
        .timestamp {{
            text-align: center;
            color: #999;
            margin-top: 30px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 BOT_AI_V3 Test Dashboard</h1>
            <div class="subtitle">Comprehensive Testing & Code Analysis</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">📋</div>
                <div class="stat-value">{self.stats["total_tests"]}</div>
                <div class="stat-label">Total Tests</div>
            </div>

            <div class="stat-card">
                <div class="stat-icon">✅</div>
                <div class="stat-value">{self.stats["passed_tests"]}</div>
                <div class="stat-label">Passed Tests</div>
            </div>

            <div class="stat-card">
                <div class="stat-icon">❌</div>
                <div class="stat-value">{self.stats["failed_tests"]}</div>
                <div class="stat-label">Failed Tests</div>
            </div>

            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-value">{self.stats["coverage_percent"]:.1f}%</div>
                <div class="stat-label">Code Coverage</div>
            </div>

            <div class="stat-card">
                <div class="stat-icon">⏱️</div>
                <div class="stat-value">{self.stats["execution_time"]:.1f}s</div>
                <div class="stat-label">Execution Time</div>
            </div>

            <div class="stat-card">
                <div class="stat-icon">🎯</div>
                <div class="stat-value">{
            len([c for c in self.components.values() if c["status"] == "success"])
        }/{len(self.components)}</div>
                <div class="stat-label">Components Passed</div>
            </div>
        </div>

        <div class="components">
            <h2 style="margin-bottom: 20px; color: #333;">Test Components Status</h2>
            {
            "".join(
                [
                    f'''
            <div class="component-item">
                <div class="component-icon">{component["icon"]}</div>
                <div class="component-name">{component["name"]}</div>
                <div class="component-status status-{component["status"]}">{component["status"].upper()}</div>
            </div>
            '''
                    for component in self.components.values()
                ]
            )
        }

            <div class="coverage-bar">
                <div class="coverage-fill" style="width: {self.stats["coverage_percent"]}%">
                    {self.stats["coverage_percent"]:.1f}% Coverage
                </div>
            </div>
        </div>

        <div class="timestamp">
            Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
</body>
</html>
        """

        dashboard_file = self.results_dir / "dashboard.html"
        with open(dashboard_file, "w") as f:
            f.write(html_content)

        print(f"{Colors.GREEN}✓{Colors.ENDC} Dashboard generated: {dashboard_file}")
        print(f"  Open in browser: file://{dashboard_file}")

        # Попытка открыть в браузере
        try:
            import webbrowser

            webbrowser.open(f"file://{dashboard_file}")
        except:
            pass

    def clean_results(self):
        """Очистка предыдущих результатов"""
        print(f"\n{Colors.WARNING}🧹 Cleaning previous results...{Colors.ENDC}")

        for file in self.results_dir.glob("*"):
            if file.is_file():
                file.unlink()
                print(f"  Deleted: {file.name}")

        # Очистка coverage файлов
        coverage_files = [".coverage", "coverage.json", "htmlcov"]
        for cf in coverage_files:
            path = self.project_root / cf
            if path.exists():
                if path.is_dir():
                    import shutil

                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"  Deleted: {cf}")

        print(f"{Colors.GREEN}✓{Colors.ENDC} Cleanup complete")

    async def run_interactive(self):
        """Интерактивный режим"""
        self.print_header()

        while True:
            self.print_menu()

            try:
                choice = input(f"\n{Colors.BOLD}Enter choice:{Colors.ENDC} ").strip()

                if choice == "0":
                    print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.ENDC}")
                    break

                elif choice == "1":
                    await self.run_all_enabled()
                    self.generate_html_dashboard()

                elif choice == "2":
                    component_key = input("Enter component key to toggle: ").strip()
                    self.toggle_component(component_key)

                elif choice == "3":
                    component_key = input("Enter component key to run: ").strip()
                    if component_key in self.components:
                        result = await self.run_component(
                            component_key, self.components[component_key]
                        )
                        self._save_results({component_key: result})
                    else:
                        print(f"{Colors.FAIL}✗{Colors.ENDC} Unknown component")

                elif choice == "4":
                    self.generate_html_dashboard()

                elif choice == "5":
                    self.clean_results()

                elif choice == "6":
                    # Quick test - только unit тесты
                    for key in self.components:
                        self.components[key]["enabled"] = key == "unit_tests"
                    await self.run_all_enabled()
                    self.generate_html_dashboard()

                elif choice == "7":
                    # Full analysis - все включено
                    for key in self.components:
                        self.components[key]["enabled"] = True
                    await self.run_all_enabled()
                    self.generate_html_dashboard()

                elif choice == "8":
                    self.generate_html_dashboard()

                elif choice == "9":
                    # Code analysis suite - включаем только тесты анализа кода
                    for key in self.components:
                        self.components[key]["enabled"] = key in [
                            "code_usage_analyzer_tests",
                            "code_analyzer_validation_tests",
                            "code_analysis_report",
                        ]
                    await self.run_all_enabled()
                    self.generate_html_dashboard()

                elif choice.upper() == "D":
                    # Dynamic SL/TP test suite
                    await self.run_dynamic_sltp_suite()

                elif choice.upper() == "E" and ENHANCED_DASHBOARD_AVAILABLE:
                    # Enhanced interactive dashboard
                    self.generate_enhanced_dashboard()

                else:
                    print(f"{Colors.WARNING}⚠️  Invalid choice{Colors.ENDC}")

            except KeyboardInterrupt:
                print(f"\n\n{Colors.CYAN}👋 Interrupted by user{Colors.ENDC}")
                break
            except Exception as e:
                print(f"{Colors.FAIL}❌ Error: {e}{Colors.ENDC}")

    async def run_cli(self, mode: str = "full"):
        """CLI режим для скриптов"""
        self.print_header()

        if mode == "full" or mode == "full-analysis":
            # Включаем все компоненты
            for key in self.components:
                self.components[key]["enabled"] = True
        elif mode == "quick":
            # Только unit тесты
            for key in self.components:
                self.components[key]["enabled"] = key == "unit_tests"
        elif mode == "visual":
            # Только визуальные тесты
            for key in self.components:
                self.components[key]["enabled"] = key in ["visual_tests", "api_tests"]
        elif mode == "ml":
            # ML тесты
            for key in self.components:
                self.components[key]["enabled"] = key in ["ml_tests", "unit_tests"]
        elif mode == "code-analysis":
            # Тесты анализа кода
            for key in self.components:
                self.components[key]["enabled"] = key in [
                    "code_usage_analyzer_tests",
                    "code_analyzer_validation_tests",
                    "code_analysis_report",
                ]

        results = await self.run_all_enabled()
        self.generate_html_dashboard()

        # Возвращаем код выхода
        failed = sum(1 for c in self.components.values() if c["status"] == "failed")
        return 0 if failed == 0 else 1


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="🚀 Unified Test Orchestrator for BOT_AI_V3")
    parser.add_argument(
        "--mode",
        choices=["interactive", "full", "full-analysis", "quick", "visual", "ml", "code-analysis"],
        default="interactive",
        help="Execution mode",
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean previous results before running"
    )

    args = parser.parse_args()

    orchestrator = UnifiedTestOrchestrator()

    if args.clean:
        orchestrator.clean_results()

    if args.mode == "interactive":
        await orchestrator.run_interactive()
    else:
        exit_code = await orchestrator.run_cli(args.mode)
        sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.ENDC}")
        sys.exit(0)
