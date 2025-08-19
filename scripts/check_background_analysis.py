#!/usr/bin/env python3
"""
Проверка результатов фонового анализа BOT_AI_V3
"""
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def check_background_analysis():
    """Проверяет результаты последнего фонового анализа"""

    print("🔍 Проверка результатов фонового анализа BOT_AI_V3")
    print("=" * 50)

    # Проверяем уведомление о последнем анализе
    notification_file = PROJECT_ROOT / "analysis_results" / "last_background_analysis.txt"

    if notification_file.exists():
        print("📋 Последний фоновый анализ:")
        print("-" * 30)
        with open(notification_file, encoding="utf-8") as f:
            print(f.read())
    else:
        print("❌ Файл уведомления о фоновом анализе не найден")
        print(f"   Ожидаемый путь: {notification_file}")

    # Проверяем предупреждения
    warnings_file = PROJECT_ROOT / "analysis_results" / "analysis_warnings.txt"

    if warnings_file.exists():
        print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ:")
        print("-" * 30)
        with open(warnings_file, encoding="utf-8") as f:
            print(f.read())

    # Проверяем логи
    logs_dir = PROJECT_ROOT / "data" / "logs"

    if logs_dir.exists():
        background_logs = list(logs_dir.glob("background_analysis_*.log"))

        if background_logs:
            latest_log = max(background_logs, key=lambda p: p.stat().st_mtime)
            print("\n📄 Последний лог анализа:")
            print(f"   {latest_log}")
            print(f"   Размер: {latest_log.stat().st_size} байт")
            print(f"   Изменён: {datetime.fromtimestamp(latest_log.stat().st_mtime)}")

            # Показываем последние 10 строк
            with open(latest_log, encoding="utf-8") as f:
                lines = f.readlines()
                print("\n📝 Последние 10 строк лога:")
                print("-" * 30)
                for line in lines[-10:]:
                    print(f"   {line.rstrip()}")
        else:
            print("\n📄 Логи фонового анализа не найдены")

    # Проверяем результаты анализа
    results_dir = PROJECT_ROOT / "analysis_results"

    if results_dir.exists():
        print("\n📊 Файлы результатов анализа:")
        print("-" * 30)

        for result_file in results_dir.glob("*.json"):
            file_stats = result_file.stat()
            print(f"   📄 {result_file.name}")
            print(f"      Размер: {file_stats.st_size} байт")
            print(f"      Изменён: {datetime.fromtimestamp(file_stats.st_mtime)}")

        # Проверяем coverage данные
        coverage_file = PROJECT_ROOT / "coverage_post_commit.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                coverage_percent = coverage_data["totals"]["percent_covered"]
                lines_covered = coverage_data["totals"]["covered_lines"]
                lines_total = coverage_data["totals"]["num_statements"]

                print("\n📈 Покрытие кода (последний анализ):")
                print(f"   Покрытие: {coverage_percent:.1f}%")
                print(f"   Строк покрыто: {lines_covered}/{lines_total}")

            except Exception as e:
                print(f"\n❌ Ошибка чтения данных покрытия: {e}")

    # Проверяем активные процессы анализа
    try:
        import psutil

        analysis_processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""
                if any(
                    script in cmdline
                    for script in [
                        "master_test_runner.py",
                        "code_chain_analyzer.py",
                        "full_chain_tester.py",
                        "coverage_monitor.py",
                    ]
                ):
                    analysis_processes.append(
                        {"pid": proc.info["pid"], "name": proc.info["name"], "cmdline": cmdline}
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if analysis_processes:
            print("\n🔄 Активные процессы анализа:")
            print("-" * 30)
            for proc in analysis_processes:
                print(f"   PID {proc['pid']}: {proc['cmdline'][:80]}...")
        else:
            print("\n💤 Нет активных процессов анализа")

    except ImportError:
        print("\n❓ psutil не установлен - проверка активных процессов недоступна")

    # Рекомендации
    print("\n💡 Рекомендации:")
    print("-" * 30)

    if warnings_file.exists():
        print("   🔴 Есть предупреждения - проверьте analysis_warnings.txt")

    if not (PROJECT_ROOT / "analysis_results").exists():
        print(
            "   🟡 Запустите полный анализ: python3 scripts/master_test_runner.py --full-analysis"
        )

    print("   📊 Просмотр дашборда: firefox analysis_results/testing_dashboard.html")
    print("   📈 HTML покрытие: firefox htmlcov/index.html")
    print("   🔄 Запуск мониторинга: python3 scripts/coverage_monitor.py")


def main():
    """Главная функция"""
    try:
        check_background_analysis()
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
