#!/usr/bin/env python3
"""
🎯 Единая точка входа для всей системы тестирования BOT_AI_V3
Визуальный интерфейс и полная интеграция всех тестовых компонентов
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil

# Цвета для терминала
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


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
                "command": "pytest tests/unit/ --cov=. --cov-report=json",
                "enabled": True,
                "status": "pending"
            },
            "integration_tests": {
                "name": "Integration Tests",
                "icon": "🔗",
                "command": "pytest tests/integration/ -v",
                "enabled": True,
                "status": "pending"
            },
            "performance_tests": {
                "name": "Performance Tests",
                "icon": "⚡",
                "command": "pytest tests/performance/ -v",
                "enabled": True,
                "status": "pending"
            },
            "visual_tests": {
                "name": "Visual Web Tests",
                "icon": "👁️",
                "command": "python3 scripts/visual_web_test.py",
                "enabled": True,
                "status": "pending"
            },
            "code_analysis": {
                "name": "Code Chain Analysis",
                "icon": "🔍",
                "command": "python3 scripts/code_chain_analyzer.py",
                "enabled": True,
                "status": "pending"
            },
            "coverage_monitor": {
                "name": "Coverage Monitor",
                "icon": "📊",
                "command": "python3 scripts/coverage_monitor.py",
                "enabled": True,
                "status": "pending"
            },
            "test_generator": {
                "name": "Test Generator",
                "icon": "🤖",
                "command": "python3 scripts/mass_test_generator.py",
                "enabled": False,  # По умолчанию выключен
                "status": "pending"
            },
            "unused_code": {
                "name": "Unused Code Detector",
                "icon": "🗑️",
                "command": "python3 scripts/unused_code_remover.py --dry-run",
                "enabled": True,
                "status": "pending"
            },
            "ml_tests": {
                "name": "ML System Tests",
                "icon": "🧠",
                "command": "python3 test_ml_system_complete.py",
                "enabled": True,
                "status": "pending"
            },
            "api_tests": {
                "name": "API Tests",
                "icon": "🌐",
                "command": "pytest tests/integration/test_api_web_integration.py -v",
                "enabled": True,
                "status": "pending"
            }
        }
        
        # Статистика
        self.stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "coverage_percent": 0.0,
            "execution_time": 0,
            "errors": [],
            "warnings": []
        }
    
    def print_header(self):
        """Красивый заголовок"""
        terminal_width = shutil.get_terminal_size().columns
        print("\n" + Colors.CYAN + "=" * terminal_width + Colors.ENDC)
        print(Colors.BOLD + Colors.HEADER + 
              "🚀 UNIFIED TEST ORCHESTRATOR FOR BOT_AI_V3 🚀".center(terminal_width) + 
              Colors.ENDC)
        print(Colors.CYAN + "=" * terminal_width + Colors.ENDC)
        print(f"{Colors.BLUE}📁 Project:{Colors.ENDC} {self.project_root}")
        print(f"{Colors.BLUE}📊 Results:{Colors.ENDC} {self.results_dir}")
        print(f"{Colors.BLUE}⏰ Started:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(Colors.CYAN + "=" * terminal_width + Colors.ENDC)
    
    def print_menu(self):
        """Интерактивное меню"""
        print(f"\n{Colors.BOLD}📋 Test Components:{Colors.ENDC}")
        print("-" * 60)
        
        for key, component in self.components.items():
            status_icon = "✅" if component["enabled"] else "⭕"
            status_color = Colors.GREEN if component["enabled"] else Colors.WARNING
            print(f"{status_color}{status_icon}{Colors.ENDC} {component['icon']} "
                  f"{component['name']:<25} [{key}]")
        
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
        print("  [0] Exit")
    
    def toggle_component(self, component_key: str):
        """Переключить компонент"""
        if component_key in self.components:
            self.components[component_key]["enabled"] = not self.components[component_key]["enabled"]
            status = "enabled" if self.components[component_key]["enabled"] else "disabled"
            print(f"{Colors.GREEN}✓{Colors.ENDC} {self.components[component_key]['name']} {status}")
        else:
            print(f"{Colors.FAIL}✗{Colors.ENDC} Unknown component: {component_key}")
    
    async def run_component(self, key: str, component: Dict) -> Dict:
        """Запуск одного компонента"""
        print(f"\n{Colors.CYAN}▶{Colors.ENDC} Running {component['icon']} {component['name']}...")
        
        start_time = time.time()
        result = {
            "name": component["name"],
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "output": "",
            "error": "",
            "execution_time": 0
        }
        
        try:
            # Активация venv если нужно
            venv_activate = "source venv/bin/activate && " if (self.project_root / "venv").exists() else ""
            full_command = f"cd {self.project_root} && {venv_activate}{component['command']}"
            
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result["output"] = stdout.decode() if stdout else ""
            result["error"] = stderr.decode() if stderr else ""
            result["status"] = "success" if process.returncode == 0 else "failed"
            
            # Обновляем статус компонента
            self.components[key]["status"] = result["status"]
            
            # Парсим результаты если это pytest
            if "pytest" in component["command"] and "passed" in result["output"]:
                self._parse_pytest_output(result["output"])
            
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
        lines = output.split('\n')
        for line in lines:
            if "passed" in line and "failed" in line:
                # Пример: "5 passed, 2 failed in 1.23s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        self.stats["passed_tests"] += int(parts[i-1])
                    elif part == "failed" and i > 0:
                        self.stats["failed_tests"] += int(parts[i-1])
        
        self.stats["total_tests"] = self.stats["passed_tests"] + self.stats["failed_tests"]
    
    async def run_all_enabled(self):
        """Запуск всех включенных компонентов"""
        print(f"\n{Colors.BOLD}🚀 Starting test execution...{Colors.ENDC}\n")
        
        results = {}
        start_time = time.time()
        
        # Запускаем компоненты последовательно для лучшего контроля
        for key, component in self.components.items():
            if component["enabled"]:
                results[key] = await self.run_component(key, component)
                await asyncio.sleep(0.5)  # Небольшая пауза между компонентами
        
        self.stats["execution_time"] = time.time() - start_time
        
        # Сохраняем результаты
        self._save_results(results)
        
        # Показываем итоги
        self._print_summary()
        
        return results
    
    def _save_results(self, results: Dict):
        """Сохранение результатов"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON отчет
        report = {
            "timestamp": datetime.now().isoformat(),
            "project": str(self.project_root),
            "stats": self.stats,
            "components": results,
            "coverage": self._get_coverage_data()
        }
        
        json_file = self.results_dir / f"test_report_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{Colors.GREEN}✓{Colors.ENDC} Report saved: {json_file}")
    
    def _get_coverage_data(self) -> Dict:
        """Получение данных покрытия"""
        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file) as f:
                data = json.load(f)
                if "totals" in data:
                    self.stats["coverage_percent"] = data["totals"].get("percent_covered", 0)
                    return data["totals"]
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
            print(f"  • Coverage is below 80%. Run test generator to create more tests")
            print(f"  • Focus on critical components: trading/, ml/, exchanges/")
            print(f"  • Use 'python3 scripts/mass_test_generator.py' for automatic test generation")
        
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
                <div class="stat-value">{self.stats['total_tests']}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">✅</div>
                <div class="stat-value">{self.stats['passed_tests']}</div>
                <div class="stat-label">Passed Tests</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">❌</div>
                <div class="stat-value">{self.stats['failed_tests']}</div>
                <div class="stat-label">Failed Tests</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-value">{self.stats['coverage_percent']:.1f}%</div>
                <div class="stat-label">Code Coverage</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">⏱️</div>
                <div class="stat-value">{self.stats['execution_time']:.1f}s</div>
                <div class="stat-label">Execution Time</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">🎯</div>
                <div class="stat-value">{len([c for c in self.components.values() if c['status'] == 'success'])}/{len(self.components)}</div>
                <div class="stat-label">Components Passed</div>
            </div>
        </div>
        
        <div class="components">
            <h2 style="margin-bottom: 20px; color: #333;">Test Components Status</h2>
            {"".join([f'''
            <div class="component-item">
                <div class="component-icon">{component['icon']}</div>
                <div class="component-name">{component['name']}</div>
                <div class="component-status status-{component['status']}">{component['status'].upper()}</div>
            </div>
            ''' for component in self.components.values()])}
            
            <div class="coverage-bar">
                <div class="coverage-fill" style="width: {self.stats['coverage_percent']}%">
                    {self.stats['coverage_percent']:.1f}% Coverage
                </div>
            </div>
        </div>
        
        <div class="timestamp">
            Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
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
                        result = await self.run_component(component_key, self.components[component_key])
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
        
        results = await self.run_all_enabled()
        self.generate_html_dashboard()
        
        # Возвращаем код выхода
        failed = sum(1 for c in self.components.values() if c["status"] == "failed")
        return 0 if failed == 0 else 1


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="🚀 Unified Test Orchestrator for BOT_AI_V3"
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "full", "full-analysis", "quick", "visual", "ml"],
        default="interactive",
        help="Execution mode"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean previous results before running"
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