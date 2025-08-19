#!/usr/bin/env python3
"""
Мониторинг покрытия кода в реальном времени для BOT_AI_V3
Отслеживает какой код реально выполняется в продакшене
"""
import ast
import json
import sqlite3
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import coverage

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class ExecutionTrace:
    """Трассировка выполнения функции"""

    function_name: str
    file_path: str
    line_number: int
    timestamp: datetime
    execution_time: float
    call_count: int
    arguments: dict[str, Any]
    return_value_type: str
    caller_function: str | None = None


@dataclass
class CoverageMetrics:
    """Метрики покрытия кода"""

    total_functions: int
    executed_functions: int
    coverage_percentage: float
    uncovered_functions: list[str]
    hot_functions: list[str]  # Часто вызываемые
    cold_functions: list[str]  # Редко вызываемые
    performance_data: dict[str, float]
    last_updated: datetime


class RealTimeCoverageTracer:
    """Трассировщик покрытия в реальном времени"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.execution_traces: dict[str, ExecutionTrace] = {}
        self.function_call_counts: dict[str, int] = defaultdict(int)
        self.function_timings: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.last_execution_times: dict[str, datetime] = {}

        # База данных для хранения трассировок
        self.db_path = project_root / "analysis_results" / "coverage_trace.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()

        # Настройки мониторинга
        self.is_monitoring = False
        self.monitoring_thread = None
        self.coverage_obj = None

    def _init_database(self):
        """Инициализирует базу данных для трассировок"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    function_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INTEGER,
                    timestamp TEXT NOT NULL,
                    execution_time REAL,
                    call_count INTEGER,
                    arguments TEXT,
                    return_value_type TEXT,
                    caller_function TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS coverage_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_functions INTEGER,
                    executed_functions INTEGER,
                    coverage_percentage REAL,
                    uncovered_functions TEXT,
                    hot_functions TEXT,
                    cold_functions TEXT,
                    performance_data TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_function_name 
                ON execution_traces(function_name)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON execution_traces(timestamp)
            """
            )

    def start_monitoring(self):
        """Запускает мониторинг покрытия"""
        if self.is_monitoring:
            print("⚠️ Мониторинг уже запущен")
            return

        print("🔍 Запускаем мониторинг покрытия в реальном времени...")

        # Инициализируем coverage.py
        self.coverage_obj = coverage.Coverage(
            source=[str(self.project_root)],
            omit=["*/tests/*", "*/test_*", "*/__pycache__/*", "*/venv/*", "*/env/*"],
        )

        # Устанавливаем трассировщик
        sys.settrace(self._trace_function_calls)

        # Запускаем coverage
        self.coverage_obj.start()

        self.is_monitoring = True

        # Запускаем поток для периодического сохранения данных
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        print("✅ Мониторинг покрытия запущен")

    def stop_monitoring(self):
        """Останавливает мониторинг покрытия"""
        if not self.is_monitoring:
            print("⚠️ Мониторинг не запущен")
            return

        print("🛑 Останавливаем мониторинг покрытия...")

        self.is_monitoring = False

        # Отключаем трассировщик
        sys.settrace(None)

        # Останавливаем coverage
        if self.coverage_obj:
            self.coverage_obj.stop()

        # Сохраняем финальные данные
        self._save_coverage_snapshot()

        print("✅ Мониторинг покрытия остановлен")

    def _trace_function_calls(self, frame, event, arg):
        """Трассирует вызовы функций"""
        if event != "call":
            return self._trace_function_calls

        # Получаем информацию о функции
        code = frame.f_code
        filename = code.co_filename

        # Фильтруем только файлы проекта
        if not str(filename).startswith(str(self.project_root)):
            return self._trace_function_calls

        # Исключаем системные файлы
        if any(exclude in filename for exclude in ["__pycache__", "site-packages", "venv"]):
            return self._trace_function_calls

        function_name = code.co_name
        line_number = frame.f_lineno
        file_path = Path(filename).relative_to(self.project_root)

        # Получаем информацию о вызывающей функции
        caller_function = None
        if frame.f_back:
            caller_code = frame.f_back.f_code
            caller_function = f"{caller_code.co_filename}:{caller_code.co_name}"

        # Создаём ключ функции
        func_key = f"{file_path}:{function_name}:{line_number}"

        # Обновляем счётчики
        self.function_call_counts[func_key] += 1
        self.last_execution_times[func_key] = datetime.now()

        # Измеряем время выполнения (упрощённо)
        start_time = time.perf_counter()

        def trace_return(frame, event, arg):
            if event == "return":
                execution_time = time.perf_counter() - start_time
                self.function_timings[func_key].append(execution_time)

                # Создаём трассировку
                try:
                    # Получаем аргументы (безопасно)
                    arguments = self._extract_function_arguments(frame)

                    # Определяем тип возвращаемого значения
                    return_type = type(arg).__name__ if arg is not None else "NoneType"

                    trace = ExecutionTrace(
                        function_name=function_name,
                        file_path=str(file_path),
                        line_number=line_number,
                        timestamp=datetime.now(),
                        execution_time=execution_time,
                        call_count=self.function_call_counts[func_key],
                        arguments=arguments,
                        return_value_type=return_type,
                        caller_function=caller_function,
                    )

                    self.execution_traces[func_key] = trace

                except Exception as e:
                    # Логируем ошибку, но не прерываем выполнение
                    print(f"⚠️ Ошибка трассировки {func_key}: {e}")

            return None

        return trace_return

    def _extract_function_arguments(self, frame) -> dict[str, str]:
        """Безопасно извлекает аргументы функции"""
        try:
            arguments = {}
            local_vars = frame.f_locals

            # Получаем только простые типы для безопасности
            for name, value in local_vars.items():
                if name.startswith("_"):
                    continue

                try:
                    if isinstance(value, (str, int, float, bool, type(None))):
                        arguments[name] = str(value)
                    elif isinstance(value, (list, dict, tuple)):
                        # Ограничиваем размер для производительности
                        if len(str(value)) < 100:
                            arguments[name] = str(value)[:100]
                        else:
                            arguments[name] = f"<{type(value).__name__} size={len(value)}>"
                    else:
                        arguments[name] = f"<{type(value).__name__}>"
                except:
                    arguments[name] = "<unprintable>"

            return arguments

        except Exception:
            return {}

    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self.is_monitoring:
            try:
                time.sleep(30)  # Сохраняем данные каждые 30 секунд

                if self.is_monitoring:
                    self._save_traces_to_db()
                    self._save_coverage_snapshot()

            except Exception as e:
                print(f"⚠️ Ошибка в цикле мониторинга: {e}")

    def _save_traces_to_db(self):
        """Сохраняет трассировки в базу данных"""
        if not self.execution_traces:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                for trace in self.execution_traces.values():
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO execution_traces
                        (function_name, file_path, line_number, timestamp, 
                         execution_time, call_count, arguments, return_value_type, caller_function)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            trace.function_name,
                            trace.file_path,
                            trace.line_number,
                            trace.timestamp.isoformat(),
                            trace.execution_time,
                            trace.call_count,
                            json.dumps(trace.arguments),
                            trace.return_value_type,
                            trace.caller_function,
                        ),
                    )

                conn.commit()

        except Exception as e:
            print(f"⚠️ Ошибка сохранения трассировок: {e}")

    def _save_coverage_snapshot(self):
        """Сохраняет снимок покрытия"""
        try:
            metrics = self.get_current_metrics()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO coverage_snapshots
                    (timestamp, total_functions, executed_functions, coverage_percentage,
                     uncovered_functions, hot_functions, cold_functions, performance_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        metrics.last_updated.isoformat(),
                        metrics.total_functions,
                        metrics.executed_functions,
                        metrics.coverage_percentage,
                        json.dumps(metrics.uncovered_functions),
                        json.dumps(metrics.hot_functions),
                        json.dumps(metrics.cold_functions),
                        json.dumps(metrics.performance_data),
                    ),
                )

                conn.commit()

        except Exception as e:
            print(f"⚠️ Ошибка сохранения снимка покрытия: {e}")

    def get_current_metrics(self) -> CoverageMetrics:
        """Получает текущие метрики покрытия"""
        # Анализируем все функции в проекте
        total_functions = self._count_total_functions()
        executed_functions = len(self.execution_traces)

        coverage_percentage = (
            (executed_functions / total_functions * 100) if total_functions > 0 else 0
        )

        # Находим непокрытые функции
        all_function_keys = self._get_all_function_keys()
        executed_keys = set(self.execution_traces.keys())
        uncovered_functions = list(all_function_keys - executed_keys)

        # Анализируем горячие и холодные функции
        hot_functions = self._find_hot_functions()
        cold_functions = self._find_cold_functions()

        # Собираем данные производительности
        performance_data = self._calculate_performance_data()

        return CoverageMetrics(
            total_functions=total_functions,
            executed_functions=executed_functions,
            coverage_percentage=coverage_percentage,
            uncovered_functions=uncovered_functions,
            hot_functions=hot_functions,
            cold_functions=cold_functions,
            performance_data=performance_data,
            last_updated=datetime.now(),
        )

    def _count_total_functions(self) -> int:
        """Подсчитывает общее количество функций в проекте"""
        total = 0

        for py_file in self.project_root.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ["__pycache__", "venv", "test"]):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith("_"):  # Исключаем приватные
                            total += 1

            except Exception:
                continue

        return total

    def _get_all_function_keys(self) -> set[str]:
        """Получает ключи всех функций в проекте"""
        function_keys = set()

        for py_file in self.project_root.rglob("*.py"):
            if any(exclude in str(py_file) for exclude in ["__pycache__", "venv", "test"]):
                continue

            try:
                rel_path = py_file.relative_to(self.project_root)

                with open(py_file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith("_"):
                            func_key = f"{rel_path}:{node.name}:{node.lineno}"
                            function_keys.add(func_key)

            except Exception:
                continue

        return function_keys

    def _find_hot_functions(self, min_calls: int = 10) -> list[str]:
        """Находит часто вызываемые функции"""
        hot_functions = []

        for func_key, call_count in self.function_call_counts.items():
            if call_count >= min_calls:
                hot_functions.append(f"{func_key} ({call_count} calls)")

        # Сортируем по количеству вызовов
        hot_functions.sort(key=lambda x: int(x.split("(")[1].split(" ")[0]), reverse=True)

        return hot_functions[:20]  # Топ 20

    def _find_cold_functions(self, max_age_hours: int = 24) -> list[str]:
        """Находит редко используемые функции"""
        cold_functions = []
        threshold = datetime.now() - timedelta(hours=max_age_hours)

        for func_key, last_execution in self.last_execution_times.items():
            if last_execution < threshold:
                call_count = self.function_call_counts.get(func_key, 0)
                cold_functions.append(
                    f"{func_key} (last: {last_execution.strftime('%Y-%m-%d %H:%M')}, calls: {call_count})"
                )

        return cold_functions

    def _calculate_performance_data(self) -> dict[str, float]:
        """Вычисляет данные производительности"""
        performance_data = {}

        for func_key, timings in self.function_timings.items():
            if timings:
                performance_data[func_key] = {
                    "avg_time": sum(timings) / len(timings),
                    "max_time": max(timings),
                    "min_time": min(timings),
                    "total_time": sum(timings),
                    "call_count": len(timings),
                }

        return performance_data

    def generate_report(self) -> dict[str, Any]:
        """Генерирует подробный отчёт о покрытии"""
        metrics = self.get_current_metrics()

        # Анализируем тенденции из базы данных
        trends = self._analyze_trends()

        # Находим проблемные области
        issues = self._identify_issues()

        report = {
            "timestamp": datetime.now().isoformat(),
            "current_metrics": asdict(metrics),
            "trends": trends,
            "issues": issues,
            "recommendations": self._generate_recommendations(metrics, issues),
            "top_performers": self._find_top_performers(),
            "bottlenecks": self._find_bottlenecks(),
        }

        return report

    def _analyze_trends(self) -> dict[str, Any]:
        """Анализирует тенденции покрытия"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT timestamp, coverage_percentage 
                    FROM coverage_snapshots 
                    ORDER BY timestamp DESC 
                    LIMIT 100
                """
                )

                snapshots = cursor.fetchall()

            if len(snapshots) < 2:
                return {"trend": "insufficient_data"}

            # Вычисляем тренд
            recent_coverage = snapshots[0][1]
            older_coverage = snapshots[-1][1]
            trend = recent_coverage - older_coverage

            return {
                "trend_direction": (
                    "improving" if trend > 0 else "declining" if trend < 0 else "stable"
                ),
                "trend_value": trend,
                "recent_coverage": recent_coverage,
                "data_points": len(snapshots),
            }

        except Exception as e:
            return {"error": f"Ошибка анализа трендов: {e}"}

    def _identify_issues(self) -> list[dict[str, Any]]:
        """Выявляет проблемы в коде"""
        issues = []

        # Функции с долгим временем выполнения
        for func_key, timings in self.function_timings.items():
            if timings:
                avg_time = sum(timings) / len(timings)
                if avg_time > 1.0:  # Медленнее 1 секунды
                    issues.append(
                        {
                            "type": "performance",
                            "severity": "high" if avg_time > 5.0 else "medium",
                            "function": func_key,
                            "description": f"Медленная функция: {avg_time:.3f}с в среднем",
                            "avg_time": avg_time,
                        }
                    )

        # Неиспользуемые функции
        metrics = self.get_current_metrics()
        if metrics.uncovered_functions:
            issues.append(
                {
                    "type": "coverage",
                    "severity": "medium",
                    "description": f"Неиспользуемых функций: {len(metrics.uncovered_functions)}",
                    "count": len(metrics.uncovered_functions),
                }
            )

        # Горячие точки (слишком частые вызовы)
        for func_key, call_count in self.function_call_counts.items():
            if call_count > 1000:  # Более 1000 вызовов
                issues.append(
                    {
                        "type": "hotspot",
                        "severity": "low",
                        "function": func_key,
                        "description": f"Горячая точка: {call_count} вызовов",
                        "call_count": call_count,
                    }
                )

        return issues

    def _generate_recommendations(
        self, metrics: CoverageMetrics, issues: list[dict[str, Any]]
    ) -> list[str]:
        """Генерирует рекомендации по улучшению"""
        recommendations = []

        # Рекомендации по покрытию
        if metrics.coverage_percentage < 50:
            recommendations.append("🔴 Критически низкое покрытие кода! Необходимо добавить тесты.")
        elif metrics.coverage_percentage < 80:
            recommendations.append(
                "🟡 Покрытие кода ниже целевого (80%). Рекомендуется добавить тесты."
            )

        # Рекомендации по производительности
        perf_issues = [i for i in issues if i["type"] == "performance" and i["severity"] == "high"]
        if perf_issues:
            recommendations.append(
                f"⚡ Найдено {len(perf_issues)} медленных функций. Требуется оптимизация."
            )

        # Рекомендации по неиспользуемому коду
        if len(metrics.uncovered_functions) > 50:
            recommendations.append(
                "🗑️ Много неиспользуемых функций. Рассмотрите возможность удаления."
            )

        # Рекомендации по горячим точкам
        hotspot_issues = [i for i in issues if i["type"] == "hotspot"]
        if hotspot_issues:
            recommendations.append(
                f"🔥 Найдено {len(hotspot_issues)} горячих точек. Рассмотрите кэширование или оптимизацию."
            )

        return recommendations

    def _find_top_performers(self) -> list[dict[str, Any]]:
        """Находит самые быстрые функции"""
        performers = []

        for func_key, timings in self.function_timings.items():
            if timings and len(timings) > 10:  # Минимум 10 вызовов
                avg_time = sum(timings) / len(timings)
                call_count = self.function_call_counts.get(func_key, 0)

                performers.append(
                    {
                        "function": func_key,
                        "avg_time": avg_time,
                        "call_count": call_count,
                        "efficiency_score": call_count / (avg_time + 0.001),  # Вызовы/время
                    }
                )

        # Сортируем по эффективности
        performers.sort(key=lambda x: x["efficiency_score"], reverse=True)

        return performers[:10]  # Топ 10

    def _find_bottlenecks(self) -> list[dict[str, Any]]:
        """Находит узкие места"""
        bottlenecks = []

        for func_key, timings in self.function_timings.items():
            if timings:
                total_time = sum(timings)
                call_count = self.function_call_counts.get(func_key, 0)
                avg_time = total_time / len(timings)

                # Функции которые занимают много общего времени
                if total_time > 10.0:  # Более 10 секунд общего времени
                    bottlenecks.append(
                        {
                            "function": func_key,
                            "total_time": total_time,
                            "avg_time": avg_time,
                            "call_count": call_count,
                            "impact_score": total_time,  # Влияние на производительность
                        }
                    )

        # Сортируем по влиянию
        bottlenecks.sort(key=lambda x: x["impact_score"], reverse=True)

        return bottlenecks[:10]  # Топ 10


def main():
    """Главная функция"""
    project_root = Path(__file__).parent.parent
    tracer = RealTimeCoverageTracer(project_root)

    print("📊 Мониторинг покрытия кода в реальном времени BOT_AI_V3")
    print("=" * 60)

    try:
        # Запускаем мониторинг
        tracer.start_monitoring()

        print("🔍 Мониторинг запущен. Нажмите Ctrl+C для остановки.")
        print("📈 Данные сохраняются каждые 30 секунд...")

        # Ждём сигнала остановки
        while True:
            time.sleep(10)

            # Показываем текущие метрики
            metrics = tracer.get_current_metrics()
            print(
                f"\r📊 Покрытие: {metrics.coverage_percentage:.1f}% "
                f"({metrics.executed_functions}/{metrics.total_functions}), "
                f"Трассировок: {len(tracer.execution_traces)}",
                end="",
            )

    except KeyboardInterrupt:
        print("\n\n🛑 Остановка мониторинга...")

    finally:
        tracer.stop_monitoring()

        # Генерируем финальный отчёт
        print("📄 Генерируем финальный отчёт...")
        report = tracer.generate_report()

        # Сохраняем отчёт
        output_file = project_root / "analysis_results" / "coverage_monitoring_report.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        # Показываем краткую сводку
        print("\n📊 ФИНАЛЬНЫЙ ОТЧЁТ:")
        print(f"  Покрытие кода: {report['current_metrics']['coverage_percentage']:.1f}%")
        print(f"  Выполненных функций: {report['current_metrics']['executed_functions']}")
        print(f"  Всего функций: {report['current_metrics']['total_functions']}")
        print(f"  Неиспользуемых функций: {len(report['current_metrics']['uncovered_functions'])}")

        if report["issues"]:
            print(f"  ⚠️ Найдено проблем: {len(report['issues'])}")

        if report["recommendations"]:
            print("\n💡 Рекомендации:")
            for rec in report["recommendations"]:
                print(f"    {rec}")

        print(f"\n📄 Подробный отчёт: {output_file}")
        print(f"💾 База данных: {tracer.db_path}")


if __name__ == "__main__":
    main()
