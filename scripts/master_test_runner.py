#!/usr/bin/env python3
"""
🎯 Master Test Runner - Единая точка входа для системы тестирования BOT_AI_V3
Перенаправляет все вызовы на унифицированный оркестратор
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Импортируем унифицированный оркестратор
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

async def main():
    """Главная функция - перенаправляет на unified_test_orchestrator"""
    from scripts.unified_test_orchestrator import UnifiedTestOrchestrator, Colors
    
    parser = argparse.ArgumentParser(
        description="🚀 Master Test Runner for BOT_AI_V3 (redirects to Unified Test Orchestrator)"
    )
    
    # Поддерживаем старый интерфейс
    parser.add_argument(
        "--full-analysis",
        action="store_true",
        help="Run complete analysis (all tests + code analysis)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (unit tests)"
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Run visual web tests"
    )
    parser.add_argument(
        "--ml",
        action="store_true",
        help="Run ML system tests"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean previous results"
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "full", "quick", "visual", "ml"],
        help="Execution mode (overrides other flags)"
    )
    
    args = parser.parse_args()
    
    # Определяем режим
    mode = "interactive"  # По умолчанию интерактивный
    
    if args.mode:
        mode = args.mode
    elif args.full_analysis:
        mode = "full-analysis"
    elif args.quick:
        mode = "quick"
    elif args.visual:
        mode = "visual"
    elif args.ml:
        mode = "ml"
    
    # Создаем и запускаем оркестратор
    orchestrator = UnifiedTestOrchestrator()
    
    if args.clean:
        orchestrator.clean_results()
    
    # Выводим информацию о перенаправлении
    print(f"{Colors.CYAN}╔══════════════════════════════════════════════════════════╗{Colors.ENDC}")
    print(f"{Colors.CYAN}║{Colors.ENDC} {Colors.BOLD}Master Test Runner → Unified Test Orchestrator{Colors.ENDC}          {Colors.CYAN}║{Colors.ENDC}")
    print(f"{Colors.CYAN}╚══════════════════════════════════════════════════════════╝{Colors.ENDC}")
    print(f"{Colors.WARNING}ℹ️  Using new unified system for all testing needs{Colors.ENDC}\n")
    
    if mode == "interactive":
        await orchestrator.run_interactive()
    else:
        exit_code = await orchestrator.run_cli(mode)
        sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.ENDC}")
        sys.exit(0)