#!/usr/bin/env python3
"""
Скрипт для генерации примеров логов с типичными проблемами
для демонстрации возможностей анализа и отладки.

Генерирует различные типы ошибок:
- WebSocket disconnections
- API errors
- Performance bottlenecks
- Trading errors
"""

import asyncio
import json
import logging
import logging.handlers
import random
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Создаем директорию для логов
log_dir = Path(__file__).parent.parent / "data" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

# Создаем различные логгеры
system_logger = logging.getLogger("system")
websocket_logger = logging.getLogger("websocket")
api_logger = logging.getLogger("api")
trading_logger = logging.getLogger("trading")
performance_logger = logging.getLogger("performance")


# Настройка хендлеров для разных файлов
def setup_file_handler(logger, filename, level=logging.INFO):
    handler = logging.handlers.RotatingFileHandler(
        log_dir / filename,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",  # 10MB
    )
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)
    logger.setLevel(level)


# Настраиваем хендлеры
setup_file_handler(system_logger, "system.log")
setup_file_handler(websocket_logger, "websocket.log")
setup_file_handler(api_logger, "api.log")
setup_file_handler(trading_logger, "trading.log")
setup_file_handler(performance_logger, "performance.log")

# JSON логгер для структурированных логов
json_handler = logging.handlers.RotatingFileHandler(
    log_dir / "structured.json",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
        return json.dumps(log_obj)


json_handler.setFormatter(JsonFormatter())
performance_logger.addHandler(json_handler)


# Генераторы различных типов событий
class LogGenerator:
    """Генератор различных типов логов для отладки"""

    def __init__(self):
        self.exchanges = ["binance", "bybit", "okx", "bitget", "gateio"]
        self.symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "MATIC/USDT"]
        self.strategies = ["grid_trading", "arbitrage", "scalping", "market_making"]

    async def generate_websocket_issues(self):
        """Генерация проблем с WebSocket соединениями"""
        for i in range(20):
            exchange = random.choice(self.exchanges)
            symbol = random.choice(self.symbols)

            # Различные типы WebSocket ошибок
            if i % 5 == 0:
                # Connection timeout
                websocket_logger.error(
                    f"WebSocket connection timeout for {exchange}:{symbol}. "
                    f"Connection attempt failed after 30s"
                )
            elif i % 5 == 1:
                # Unexpected disconnect
                websocket_logger.warning(
                    f"WebSocket disconnected unexpectedly from {exchange}. "
                    f"Code: 1006, Reason: Connection lost"
                )
            elif i % 5 == 2:
                # Reconnection
                websocket_logger.info(
                    f"Attempting to reconnect WebSocket for {exchange}:{symbol}. "
                    f"Retry attempt: {random.randint(1, 5)}"
                )
            elif i % 5 == 3:
                # Rate limit
                websocket_logger.error(
                    f"WebSocket rate limit exceeded for {exchange}. "
                    f"Max connections: 10, Current: 15"
                )
            else:
                # Ping timeout
                websocket_logger.warning(
                    f"WebSocket ping timeout for {exchange}:{symbol}. "
                    f"Last ping: {random.randint(60, 300)}s ago"
                )

            await asyncio.sleep(0.1)

    async def generate_api_errors(self):
        """Генерация API ошибок"""
        error_codes = [400, 401, 403, 429, 500, 502, 503]
        endpoints = ["/orders", "/account", "/positions", "/balance", "/trades"]

        for i in range(25):
            exchange = random.choice(self.exchanges)
            endpoint = random.choice(endpoints)
            error_code = random.choice(error_codes)

            if error_code == 429:
                # Rate limit
                api_logger.error(
                    f"API rate limit exceeded for {exchange}{endpoint}. "
                    f"Status: {error_code}, Retry-After: {random.randint(1, 60)}s, "
                    f"X-RateLimit-Remaining: 0"
                )
            elif error_code == 401:
                # Authentication error
                api_logger.error(
                    f"Authentication failed for {exchange}{endpoint}. "
                    f"Status: {error_code}, Message: Invalid API key or signature"
                )
            elif error_code >= 500:
                # Server error
                api_logger.error(
                    f"Server error from {exchange}{endpoint}. "
                    f"Status: {error_code}, Message: Internal server error, "
                    f"Request-ID: {random.randint(10000, 99999)}"
                )
            else:
                # Client error
                api_logger.warning(
                    f"Client error for {exchange}{endpoint}. "
                    f"Status: {error_code}, Message: Bad request parameters"
                )

            await asyncio.sleep(0.05)

    async def generate_performance_issues(self):
        """Генерация метрик производительности и узких мест"""
        for i in range(30):
            operation = random.choice(
                [
                    "order_execution",
                    "market_data_processing",
                    "strategy_calculation",
                    "database_query",
                    "risk_check",
                ]
            )

            # Нормальная латентность
            if i % 3 == 0:
                latency = random.uniform(10, 50)
                performance_logger.info(
                    f"Performance metric: {operation}",
                    extra={
                        "extra_data": {
                            "operation": operation,
                            "latency_ms": latency,
                            "status": "normal",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    },
                )
            # Высокая латентность
            elif i % 3 == 1:
                latency = random.uniform(500, 2000)
                performance_logger.warning(
                    f"High latency detected for {operation}: {latency:.2f}ms",
                    extra={
                        "extra_data": {
                            "operation": operation,
                            "latency_ms": latency,
                            "status": "high_latency",
                            "threshold_ms": 100,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    },
                )
            # Критическая латентность
            else:
                latency = random.uniform(2000, 5000)
                performance_logger.error(
                    f"Critical latency for {operation}: {latency:.2f}ms - potential bottleneck",
                    extra={
                        "extra_data": {
                            "operation": operation,
                            "latency_ms": latency,
                            "status": "critical",
                            "impact": "Order execution delayed",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    },
                )

            await asyncio.sleep(0.05)

    async def generate_trading_events(self):
        """Генерация торговых событий и ошибок"""
        for i in range(20):
            exchange = random.choice(self.exchanges)
            symbol = random.choice(self.symbols)
            strategy = random.choice(self.strategies)

            event_type = random.choice(
                [
                    "order_placed",
                    "order_filled",
                    "order_rejected",
                    "position_opened",
                    "position_closed",
                    "stop_loss_triggered",
                ]
            )

            if "rejected" in event_type:
                trading_logger.error(
                    f"Order rejected on {exchange} for {symbol}. "
                    f"Strategy: {strategy}, Reason: Insufficient balance, "
                    f"Required: {random.uniform(1000, 5000):.2f} USDT"
                )
            elif "stop_loss" in event_type:
                trading_logger.warning(
                    f"Stop loss triggered for {symbol} on {exchange}. "
                    f"Strategy: {strategy}, Loss: -{random.uniform(50, 200):.2f} USDT"
                )
            else:
                trading_logger.info(
                    f"Trading event: {event_type} for {symbol} on {exchange}. Strategy: {strategy}"
                )

            await asyncio.sleep(0.1)

    async def generate_system_events(self):
        """Генерация системных событий"""
        for i in range(15):
            event_type = random.choice(
                [
                    "startup",
                    "shutdown",
                    "config_reload",
                    "memory_warning",
                    "cpu_warning",
                    "disk_warning",
                ]
            )

            if "warning" in event_type:
                if "memory" in event_type:
                    system_logger.warning(
                        f"High memory usage detected: {random.uniform(80, 95):.1f}% "
                        f"(Used: {random.uniform(6, 7.5):.1f}GB / 8GB)"
                    )
                elif "cpu" in event_type:
                    system_logger.warning(
                        f"High CPU usage: {random.uniform(85, 99):.1f}% "
                        f"across {random.randint(4, 8)} cores"
                    )
                else:
                    system_logger.warning(
                        f"Low disk space: {random.uniform(5, 15):.1f}GB remaining "
                        f"({random.uniform(85, 95):.1f}% used)"
                    )
            else:
                system_logger.info(f"System event: {event_type}")

            await asyncio.sleep(0.1)


async def main():
    """Основная функция генерации логов"""
    print(f"Генерация примеров логов в {log_dir}")

    generator = LogGenerator()

    # Запускаем все генераторы параллельно
    tasks = [
        generator.generate_websocket_issues(),
        generator.generate_api_errors(),
        generator.generate_performance_issues(),
        generator.generate_trading_events(),
        generator.generate_system_events(),
    ]

    await asyncio.gather(*tasks)

    print(f"Логи успешно сгенерированы в {log_dir}")
    print("Созданные файлы:")
    for log_file in log_dir.glob("*.log"):
        size = log_file.stat().st_size / 1024  # KB
        print(f"  - {log_file.name}: {size:.2f} KB")

    if (log_dir / "structured.json").exists():
        print(f"  - structured.json: {(log_dir / 'structured.json').stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    import logging.handlers

    asyncio.run(main())
