#!/usr/bin/env python3
"""
Анализатор логов для BOT_Trading v3.0

Выполняет комплексный анализ логов для выявления:
- Паттернов WebSocket отключений
- API ошибок и проблем с rate limiting
- Узких мест производительности
- Системных предупреждений
"""

import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


class LogAnalyzer:
    """Комплексный анализатор логов"""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.websocket_issues = defaultdict(list)
        self.api_errors = defaultdict(list)
        self.performance_metrics = defaultdict(list)
        self.system_warnings = []

    def analyze_websocket_logs(self) -> dict:
        """Анализ WebSocket логов"""
        log_file = self.log_dir / "websocket.log"
        if not log_file.exists():
            return {}

        patterns = {
            "connection_timeout": r"connection timeout for (\w+):(\w+/\w+)",
            "unexpected_disconnect": r"disconnected unexpectedly from (\w+)\. Code: (\d+)",
            "rate_limit": r"rate limit exceeded for (\w+)\. Max connections: (\d+), Current: (\d+)",
            "ping_timeout": r"ping timeout for (\w+):(\w+/\w+)\. Last ping: (\d+)s ago",
            "reconnection": r"reconnect WebSocket for (\w+):(\w+/\w+)\. Retry attempt: (\d+)",
        }

        results = {
            "total_issues": 0,
            "by_exchange": defaultdict(int),
            "by_type": defaultdict(int),
            "critical_exchanges": set(),
            "reconnection_attempts": defaultdict(list),
        }

        with open(log_file) as f:
            for line in f:
                for issue_type, pattern in patterns.items():
                    match = re.search(pattern, line)
                    if match:
                        results["total_issues"] += 1
                        results["by_type"][issue_type] += 1

                        exchange = match.group(1)
                        results["by_exchange"][exchange] += 1

                        # Определяем критические биржи (более 3 проблем)
                        if results["by_exchange"][exchange] > 3:
                            results["critical_exchanges"].add(exchange)

                        # Отслеживаем попытки переподключения
                        if issue_type == "reconnection":
                            retry_count = int(match.group(3))
                            results["reconnection_attempts"][exchange].append(retry_count)

        return dict(results)

    def analyze_api_errors(self) -> dict:
        """Анализ API ошибок"""
        log_file = self.log_dir / "api.log"
        if not log_file.exists():
            return {}

        patterns = {
            "rate_limit": r"rate limit exceeded for (\w+)(/\w+)\. Status: (\d+), Retry-After: (\d+)s",
            "auth_error": r"Authentication failed for (\w+)(/\w+)\. Status: (\d+)",
            "server_error": r"Server error from (\w+)(/\w+)\. Status: (\d+)",
            "client_error": r"Client error for (\w+)(/\w+)\. Status: (\d+)",
        }

        results = {
            "total_errors": 0,
            "by_exchange": defaultdict(lambda: defaultdict(int)),
            "by_status_code": Counter(),
            "rate_limits": defaultdict(list),
            "auth_failures": defaultdict(int),
            "endpoints_affected": defaultdict(set),
        }

        with open(log_file) as f:
            for line in f:
                for error_type, pattern in patterns.items():
                    match = re.search(pattern, line)
                    if match:
                        results["total_errors"] += 1
                        exchange = match.group(1)
                        endpoint = match.group(2)
                        status_code = int(match.group(3))

                        results["by_exchange"][exchange][error_type] += 1
                        results["by_status_code"][status_code] += 1
                        results["endpoints_affected"][exchange].add(endpoint)

                        if error_type == "rate_limit":
                            retry_after = int(match.group(4))
                            results["rate_limits"][exchange].append(retry_after)
                        elif error_type == "auth_error":
                            results["auth_failures"][exchange] += 1

        return dict(results)

    def analyze_performance_logs(self) -> dict:
        """Анализ производительности"""
        json_file = self.log_dir / "structured.json"
        if not json_file.exists():
            return {}

        results = {
            "by_operation": defaultdict(
                lambda: {
                    "latencies": [],
                    "normal": 0,
                    "high": 0,
                    "critical": 0,
                    "avg_latency": 0,
                    "p95_latency": 0,
                    "p99_latency": 0,
                }
            ),
            "bottlenecks": [],
            "total_operations": 0,
        }

        with open(json_file) as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if "operation" in data and "latency_ms" in data:
                        operation = data["operation"]
                        latency = data["latency_ms"]
                        status = data.get("status", "unknown")

                        results["total_operations"] += 1
                        results["by_operation"][operation]["latencies"].append(latency)

                        if status == "normal":
                            results["by_operation"][operation]["normal"] += 1
                        elif status == "high_latency":
                            results["by_operation"][operation]["high"] += 1
                        elif status == "critical":
                            results["by_operation"][operation]["critical"] += 1
                            results["bottlenecks"].append(
                                {
                                    "operation": operation,
                                    "latency": latency,
                                    "impact": data.get("impact", "Unknown"),
                                }
                            )
                except json.JSONDecodeError:
                    continue

        # Вычисляем статистику
        for operation, stats in results["by_operation"].items():
            latencies = stats["latencies"]
            if latencies:
                stats["avg_latency"] = statistics.mean(latencies)
                stats["p95_latency"] = (
                    statistics.quantiles(latencies, n=20)[18]
                    if len(latencies) > 20
                    else max(latencies)
                )
                stats["p99_latency"] = (
                    statistics.quantiles(latencies, n=100)[98]
                    if len(latencies) > 100
                    else max(latencies)
                )
                # Удаляем исходный список для читаемости отчета
                del stats["latencies"]

        return dict(results)

    def analyze_system_logs(self) -> dict:
        """Анализ системных логов"""
        log_file = self.log_dir / "system.log"
        if not log_file.exists():
            return {}

        patterns = {
            "cpu_warning": r"High CPU usage: ([\d.]+)% across (\d+) cores",
            "memory_warning": r"High memory usage detected: ([\d.]+)% \(Used: ([\d.]+)GB / (\d+)GB\)",
            "disk_warning": r"Low disk space: ([\d.]+)GB remaining",
        }

        results = {
            "warnings": defaultdict(list),
            "system_events": Counter(),
            "resource_alerts": [],
        }

        with open(log_file) as f:
            for line in f:
                # Анализ предупреждений о ресурсах
                for warning_type, pattern in patterns.items():
                    match = re.search(pattern, line)
                    if match:
                        if warning_type == "cpu_warning":
                            cpu_usage = float(match.group(1))
                            cores = int(match.group(2))
                            results["warnings"]["cpu"].append({"usage": cpu_usage, "cores": cores})
                            if cpu_usage > 90:
                                results["resource_alerts"].append(
                                    f"Critical CPU usage: {cpu_usage}%"
                                )

                        elif warning_type == "memory_warning":
                            memory_percent = float(match.group(1))
                            used_gb = float(match.group(2))
                            total_gb = int(match.group(3))
                            results["warnings"]["memory"].append(
                                {
                                    "percent": memory_percent,
                                    "used_gb": used_gb,
                                    "total_gb": total_gb,
                                }
                            )
                            if memory_percent > 90:
                                results["resource_alerts"].append(
                                    f"Critical memory usage: {memory_percent}%"
                                )

                # Анализ системных событий
                if "System event:" in line:
                    event_match = re.search(r"System event: (\w+)", line)
                    if event_match:
                        event = event_match.group(1)
                        results["system_events"][event] += 1

        return dict(results)

    def generate_report(self) -> str:
        """Генерация сводного отчета"""
        websocket = self.analyze_websocket_logs()
        api = self.analyze_api_errors()
        performance = self.analyze_performance_logs()
        system = self.analyze_system_logs()

        report = []
        report.append("=" * 80)
        report.append("АНАЛИЗ ЛОГОВ BOT_Trading v3.0 - ОТЧЕТ DEBUG SPECIALIST")
        report.append("=" * 80)
        report.append(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # WebSocket анализ
        report.append("1. АНАЛИЗ WEBSOCKET СОЕДИНЕНИЙ")
        report.append("-" * 40)
        if websocket:
            report.append(f"Всего проблем: {websocket.get('total_issues', 0)}")
            report.append("\nПроблемы по типам:")
            for issue_type, count in websocket.get("by_type", {}).items():
                report.append(f"  - {issue_type}: {count}")

            report.append("\nПроблемы по биржам:")
            for exchange, count in websocket.get("by_exchange", {}).items():
                status = (
                    "⚠️ КРИТИЧНО" if exchange in websocket.get("critical_exchanges", set()) else ""
                )
                report.append(f"  - {exchange}: {count} {status}")

            if websocket.get("reconnection_attempts"):
                report.append("\nПопытки переподключения:")
                for exchange, attempts in websocket.get("reconnection_attempts", {}).items():
                    max_attempts = max(attempts) if attempts else 0
                    report.append(f"  - {exchange}: максимум {max_attempts} попыток")

        # API анализ
        report.append("\n\n2. АНАЛИЗ API ОШИБОК")
        report.append("-" * 40)
        if api:
            report.append(f"Всего ошибок: {api.get('total_errors', 0)}")
            report.append("\nОшибки по кодам состояния:")
            for status_code, count in sorted(api.get("by_status_code", {}).items()):
                report.append(f"  - HTTP {status_code}: {count}")

            report.append("\nПроблемы аутентификации:")
            for exchange, count in api.get("auth_failures", {}).items():
                if count > 0:
                    report.append(f"  - {exchange}: {count} неудачных попыток ⚠️")

            report.append("\nRate limiting:")
            for exchange, delays in api.get("rate_limits", {}).items():
                if delays:
                    avg_delay = sum(delays) / len(delays)
                    report.append(
                        f"  - {exchange}: {len(delays)} случаев, среднее время ожидания: {avg_delay:.1f}s"
                    )

        # Производительность
        report.append("\n\n3. АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ")
        report.append("-" * 40)
        if performance:
            report.append(f"Всего операций: {performance.get('total_operations', 0)}")
            report.append("\nСтатистика по операциям:")

            for operation, stats in performance.get("by_operation", {}).items():
                report.append(f"\n{operation}:")
                report.append(f"  - Нормальных: {stats.get('normal', 0)}")
                report.append(f"  - Высокая латентность: {stats.get('high', 0)}")
                report.append(f"  - Критических: {stats.get('critical', 0)}")
                report.append(f"  - Средняя латентность: {stats.get('avg_latency', 0):.2f}ms")
                report.append(f"  - P95 латентность: {stats.get('p95_latency', 0):.2f}ms")
                report.append(f"  - P99 латентность: {stats.get('p99_latency', 0):.2f}ms")

            if performance.get("bottlenecks"):
                report.append("\n⚠️ ОБНАРУЖЕНЫ УЗКИЕ МЕСТА:")
                for bottleneck in performance.get("bottlenecks", [])[:5]:  # Топ 5
                    report.append(f"  - {bottleneck['operation']}: {bottleneck['latency']:.2f}ms")

        # Системные предупреждения
        report.append("\n\n4. СИСТЕМНЫЕ ПРЕДУПРЕЖДЕНИЯ")
        report.append("-" * 40)
        if system:
            if system.get("resource_alerts"):
                report.append("⚠️ КРИТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ:")
                for alert in system.get("resource_alerts", []):
                    report.append(f"  - {alert}")

            report.append("\nСистемные события:")
            for event, count in system.get("system_events", {}).items():
                report.append(f"  - {event}: {count}")

        # Рекомендации
        report.append("\n\n5. РЕКОМЕНДАЦИИ")
        report.append("-" * 40)
        recommendations = self._generate_recommendations(websocket, api, performance, system)
        for i, rec in enumerate(recommendations, 1):
            report.append(f"{i}. {rec}")

        report.append("\n" + "=" * 80)

        return "\n".join(report)

    def _generate_recommendations(
        self, websocket: dict, api: dict, performance: dict, system: dict
    ) -> list[str]:
        """Генерация рекомендаций на основе анализа"""
        recommendations = []

        # WebSocket рекомендации
        if websocket.get("critical_exchanges"):
            exchanges = ", ".join(websocket["critical_exchanges"])
            recommendations.append(
                f"Реализовать улучшенную логику переподключения для бирж: {exchanges}. "
                f"Рекомендуется экспоненциальный backoff и connection pooling."
            )

        # API рекомендации
        if api.get("auth_failures"):
            failed_exchanges = [ex for ex, count in api["auth_failures"].items() if count > 0]
            if failed_exchanges:
                recommendations.append(
                    f"Проверить и обновить API ключи для бирж: {', '.join(failed_exchanges)}. "
                    f"Реализовать автоматическую ротацию ключей."
                )

        rate_limited = [ex for ex in api.get("rate_limits", {}) if api["rate_limits"][ex]]
        if rate_limited:
            recommendations.append(
                f"Оптимизировать частоту API запросов для: {', '.join(rate_limited)}. "
                f"Использовать batch запросы и кеширование где возможно."
            )

        # Производительность
        critical_ops = []
        for op, stats in performance.get("by_operation", {}).items():
            if stats.get("critical", 0) > 2:
                critical_ops.append(op)

        if critical_ops:
            recommendations.append(
                f"Оптимизировать критические операции: {', '.join(critical_ops)}. "
                f"Рассмотреть использование кеширования, индексов БД и асинхронной обработки."
            )

        # Системные рекомендации
        if system.get("resource_alerts"):
            if any("CPU" in alert for alert in system["resource_alerts"]):
                recommendations.append(
                    "Оптимизировать использование CPU: профилировать код, "
                    "использовать connection pooling, оптимизировать алгоритмы."
                )
            if any("memory" in alert for alert in system["resource_alerts"]):
                recommendations.append(
                    "Снизить потребление памяти: проверить утечки памяти, "
                    "оптимизировать структуры данных, использовать генераторы."
                )

        # Общие рекомендации
        recommendations.append(
            "Настроить централизованный мониторинг с Prometheus/Grafana для real-time отслеживания метрик."
        )

        recommendations.append(
            "Реализовать health checks и автоматические circuit breakers для проблемных сервисов."
        )

        return recommendations


def main():
    """Основная функция"""
    log_dir = Path(__file__).parent.parent / "data" / "logs"

    if not log_dir.exists():
        print(f"Директория логов не найдена: {log_dir}")
        return

    analyzer = LogAnalyzer(log_dir)
    report = analyzer.generate_report()

    # Выводим отчет
    print(report)

    # Сохраняем отчет
    report_file = log_dir / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nОтчет сохранен в: {report_file}")


if __name__ == "__main__":
    main()
