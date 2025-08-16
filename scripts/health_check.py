#!/usr/bin/env python3
"""
Health check скрипт для BOT_AI_V3
Проверяет состояние всех компонентов и отправляет алерты
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp
import asyncpg
from redis import Redis


class HealthChecker:
    def __init__(self):
        self.checks = []
        self.alerts = []

    async def check_api(self):
        """Проверка API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8080/api/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.checks.append(
                            {"component": "API", "status": "healthy", "details": data}
                        )
                    else:
                        self.checks.append(
                            {
                                "component": "API",
                                "status": "unhealthy",
                                "error": f"Status code: {response.status}",
                            }
                        )
                        self.alerts.append(f"API unhealthy: {response.status}")
        except Exception as e:
            self.checks.append({"component": "API", "status": "down", "error": str(e)})
            self.alerts.append(f"API is down: {e!s}")

    async def check_database(self):
        """Проверка PostgreSQL"""
        try:
            conn = await asyncpg.connect(
                host="localhost",
                port=5555,
                user=os.getenv("PGUSER", "obertruper"),
                password=os.getenv("PGPASSWORD"),
                database=os.getenv("PGDATABASE", "bot_trading_v3"),
            )

            # Проверяем количество активных ордеров
            active_orders = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status = 'open'")

            # Проверяем последнюю торговлю
            last_trade = await conn.fetchrow(
                "SELECT created_at FROM trades ORDER BY created_at DESC LIMIT 1"
            )

            await conn.close()

            self.checks.append(
                {
                    "component": "PostgreSQL",
                    "status": "healthy",
                    "details": {
                        "active_orders": active_orders,
                        "last_trade": str(last_trade["created_at"]) if last_trade else None,
                    },
                }
            )
        except Exception as e:
            self.checks.append({"component": "PostgreSQL", "status": "down", "error": str(e)})
            self.alerts.append(f"PostgreSQL is down: {e!s}")

    async def check_redis(self):
        """Проверка Redis"""
        try:
            r = Redis(host="localhost", port=6379, decode_responses=True)
            r.ping()

            # Проверяем ключевые метрики
            info = r.info()

            self.checks.append(
                {
                    "component": "Redis",
                    "status": "healthy",
                    "details": {
                        "used_memory_human": info.get("used_memory_human"),
                        "connected_clients": info.get("connected_clients"),
                        "uptime_in_days": info.get("uptime_in_days"),
                    },
                }
            )
            r.close()
        except Exception as e:
            self.checks.append({"component": "Redis", "status": "down", "error": str(e)})
            self.alerts.append(f"Redis is down: {e!s}")

    async def check_disk_space(self):
        """Проверка места на диске"""
        import shutil

        try:
            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100

            status = "healthy" if free_percent > 10 else "warning"

            self.checks.append(
                {
                    "component": "Disk Space",
                    "status": status,
                    "details": {
                        "free_gb": round(free / (1024**3), 2),
                        "free_percent": round(free_percent, 2),
                    },
                }
            )

            if free_percent < 10:
                self.alerts.append(f"Low disk space: {free_percent:.1f}% free")
        except Exception as e:
            self.checks.append({"component": "Disk Space", "status": "error", "error": str(e)})

    async def check_logs_for_errors(self):
        """Проверка логов на критические ошибки"""
        try:
            log_file = (
                Path(__file__).parent.parent
                / "data"
                / "logs"
                / f"bot_trading_{datetime.now().strftime('%Y%m%d')}.log"
            )

            if log_file.exists():
                # Читаем последние 1000 строк
                with open(log_file) as f:
                    lines = f.readlines()[-1000:]

                error_count = sum(1 for line in lines if "ERROR" in line or "CRITICAL" in line)
                recent_errors = [line.strip() for line in lines[-10:] if "ERROR" in line]

                status = "healthy" if error_count < 10 else "warning"

                self.checks.append(
                    {
                        "component": "Logs",
                        "status": status,
                        "details": {
                            "error_count_last_1000": error_count,
                            "recent_errors": recent_errors[:3],  # Последние 3 ошибки
                        },
                    }
                )

                if error_count > 50:
                    self.alerts.append(
                        f"High error rate: {error_count} errors in last 1000 log lines"
                    )
        except Exception as e:
            self.checks.append({"component": "Logs", "status": "error", "error": str(e)})

    async def send_alerts(self):
        """Отправка алертов (Slack, Telegram, Email)"""
        if not self.alerts:
            return

        # Slack webhook (если настроен)
        slack_webhook = os.getenv("SLACK_WEBHOOK")
        if slack_webhook:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        slack_webhook,
                        json={
                            "text": "🚨 BOT_AI_V3 Health Alert",
                            "attachments": [
                                {
                                    "color": "danger",
                                    "fields": [
                                        {
                                            "title": "Alerts",
                                            "value": "\n".join(self.alerts),
                                        },
                                        {
                                            "title": "Time",
                                            "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        },
                                    ],
                                }
                            ],
                        },
                    )
            except Exception:  # nosec B110
                pass  # Не критично если алерт не отправится

    async def run_checks(self):
        """Запуск всех проверок"""
        await asyncio.gather(
            self.check_api(),
            self.check_database(),
            self.check_redis(),
            self.check_disk_space(),
            self.check_logs_for_errors(),
            return_exceptions=True,
        )

        # Отправляем алерты если есть
        await self.send_alerts()

        # Сохраняем результаты
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy" if not self.alerts else "unhealthy",
            "checks": self.checks,
            "alerts": self.alerts,
        }

        # Сохраняем в файл
        report_file = Path(__file__).parent.parent / "data" / "logs" / "health_check.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Выводим результат
        print(f"Health check completed: {report['overall_status']}")
        if self.alerts:
            print(f"Alerts: {', '.join(self.alerts)}")

        # Возвращаем код выхода
        return 0 if report["overall_status"] == "healthy" else 1


async def main():
    checker = HealthChecker()
    return await checker.run_checks()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
