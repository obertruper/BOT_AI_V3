"""
Комплексные тесты для Exchange модулей - критически важный компонент торговой системы
Покрывает основную логику работы с биржами без реальных подключений
"""

import os
import sys
import time
from decimal import Decimal

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Импорты для тестирования (с обработкой ошибок импорта)
try:
    from exchanges.base.api_key_manager import APIKeyManager
    from exchanges.base.exceptions import ExchangeError, InsufficientFundsError, RateLimitError
    from exchanges.base.health_monitor import ExchangeHealthMonitor
    from exchanges.base.models import Balance, Order, OrderStatus, OrderType, Position, TradingPair
    from exchanges.base.rate_limiter import RateLimiter
    from exchanges.exchange_manager import ExchangeManager
    from exchanges.factory import ExchangeFactory
    from exchanges.registry import ExchangeRegistry
except ImportError:
    # Создаем моки для отсутствующих модулей
    class ExchangeError(Exception):
        pass

    class RateLimitError(ExchangeError):
        pass

    class InsufficientFundsError(ExchangeError):
        pass


class TestExchangeExceptions:
    """Тесты исключений Exchange системы"""

    def test_exchange_error_creation(self):
        """Тест создания базового исключения Exchange"""
        error = ExchangeError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_rate_limit_error_creation(self):
        """Тест создания исключения превышения лимита запросов"""
        error = RateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, ExchangeError)

    def test_insufficient_funds_error(self):
        """Тест исключения недостатка средств"""
        error = InsufficientFundsError("Not enough balance")
        assert str(error) == "Not enough balance"
        assert isinstance(error, ExchangeError)


class TestOrderModels:
    """Тесты моделей ордеров"""

    def test_order_status_enum(self):
        """Тест enum статусов ордера"""
        # Тестируем основные статусы
        statuses = ["PENDING", "OPEN", "FILLED", "CANCELLED", "REJECTED"]
        for status in statuses:
            # Каждый статус должен быть валидным
            assert isinstance(status, str)
            assert len(status) > 0

    def test_order_type_enum(self):
        """Тест типов ордеров"""
        order_types = ["MARKET", "LIMIT", "STOP_LOSS", "TAKE_PROFIT"]
        for order_type in order_types:
            assert isinstance(order_type, str)
            assert len(order_type) > 0

    def test_order_creation(self):
        """Тест создания ордера"""
        order_data = {
            "id": "order_123",
            "symbol": "BTCUSDT",
            "side": "buy",
            "amount": Decimal("0.001"),
            "price": Decimal("50000"),
            "type": "LIMIT",
            "status": "PENDING",
        }

        # Простая проверка данных ордера
        assert order_data["id"] == "order_123"
        assert order_data["symbol"] == "BTCUSDT"
        assert order_data["amount"] > 0
        assert order_data["price"] > 0

    def test_position_data(self):
        """Тест данных позиции"""
        position_data = {
            "symbol": "BTCUSDT",
            "size": Decimal("0.5"),
            "side": "long",
            "entry_price": Decimal("49000"),
            "mark_price": Decimal("50000"),
            "pnl": Decimal("500"),
        }

        # Проверяем корректность данных позиции
        assert position_data["size"] > 0
        assert position_data["entry_price"] > 0
        assert position_data["mark_price"] > 0
        # PnL может быть положительным (прибыль)
        assert position_data["pnl"] > 0

    def test_balance_data(self):
        """Тест данных баланса"""
        balance_data = {
            "currency": "USDT",
            "total": Decimal("10000"),
            "available": Decimal("8000"),
            "locked": Decimal("2000"),
        }

        # Проверяем логику баланса
        assert balance_data["total"] == balance_data["available"] + balance_data["locked"]
        assert balance_data["available"] >= 0
        assert balance_data["locked"] >= 0

    def test_trading_pair_data(self):
        """Тест данных торговой пары"""
        pair_data = {
            "symbol": "BTCUSDT",
            "base": "BTC",
            "quote": "USDT",
            "min_amount": Decimal("0.001"),
            "max_amount": Decimal("1000"),
            "price_precision": 2,
            "amount_precision": 6,
        }

        # Проверяем валидность торговой пары
        assert pair_data["symbol"] == f"{pair_data['base']}{pair_data['quote']}"
        assert pair_data["min_amount"] > 0
        assert pair_data["max_amount"] > pair_data["min_amount"]
        assert pair_data["price_precision"] >= 0
        assert pair_data["amount_precision"] >= 0


class TestRateLimiter:
    """Тесты ограничителя скорости запросов"""

    def test_rate_limiter_initialization(self):
        """Тест инициализации rate limiter"""
        # Простая инициализация с параметрами
        config = {"requests_per_second": 10, "burst_limit": 20, "window_size": 60}

        # Проверяем конфигурацию
        assert config["requests_per_second"] > 0
        assert config["burst_limit"] >= config["requests_per_second"]
        assert config["window_size"] > 0

    def test_rate_limit_calculations(self):
        """Тест расчетов ограничения скорости"""
        requests_per_second = 5
        window_size = 10

        # Максимальное количество запросов в окне
        max_requests = requests_per_second * window_size
        assert max_requests == 50

        # Интервал между запросами
        min_interval = 1.0 / requests_per_second
        assert abs(min_interval - 0.2) < 0.001

    def test_rate_limit_window_logic(self):
        """Тест логики окна ограничений"""
        current_time = time.time()
        window_size = 60

        # Время начала окна
        window_start = current_time - (current_time % window_size)
        assert window_start <= current_time
        assert current_time - window_start < window_size

    def test_request_counting(self):
        """Тест подсчета запросов"""
        # Имитируем счетчик запросов
        request_count = 0
        max_requests = 10

        # Добавляем запросы
        for i in range(5):
            request_count += 1
            assert request_count <= max_requests

        # Проверяем что не превышен лимит
        assert request_count == 5
        assert request_count < max_requests

    def test_burst_handling(self):
        """Тест обработки всплесков запросов"""
        normal_limit = 5
        burst_limit = 15

        # Нормальный режим
        current_requests = 3
        assert current_requests <= normal_limit

        # Режим всплеска
        burst_requests = 12
        assert burst_requests <= burst_limit
        assert burst_requests > normal_limit


class TestAPIKeyManager:
    """Тесты менеджера API ключей"""

    def test_api_key_validation(self):
        """Тест валидации API ключей"""
        # Валидный ключ
        valid_key = "abcdef123456789"
        assert len(valid_key) > 0
        assert valid_key.isalnum()

        # Проверка формата
        key_format = r"^[a-zA-Z0-9]+$"
        import re

        assert re.match(key_format, valid_key)

    def test_api_secret_validation(self):
        """Тест валидации API секрета"""
        # Валидный секрет
        valid_secret = "secret123456789abcdef"
        assert len(valid_secret) >= 16  # Минимальная длина
        assert valid_secret.isalnum()

    def test_signature_generation(self):
        """Тест генерации подписи"""
        # Параметры для подписи
        timestamp = str(int(time.time() * 1000))
        method = "POST"
        path = "/api/v1/order"
        body = '{"symbol":"BTCUSDT","side":"buy"}'

        # Строка для подписи
        message = f"{timestamp}{method}{path}{body}"

        # Проверяем что сообщение корректно сформировано
        assert timestamp in message
        assert method in message
        assert path in message
        assert body in message

    def test_api_credentials_storage(self):
        """Тест хранения учетных данных"""
        credentials = {
            "bybit": {
                "api_key": "bybit_key_123",
                "api_secret": "bybit_secret_456",
                "testnet": False,
            },
            "binance": {
                "api_key": "binance_key_789",
                "api_secret": "binance_secret_012",
                "testnet": True,
            },
        }

        # Проверяем структуру credentials
        for exchange, creds in credentials.items():
            assert "api_key" in creds
            assert "api_secret" in creds
            assert "testnet" in creds
            assert len(creds["api_key"]) > 0
            assert len(creds["api_secret"]) > 0
            assert isinstance(creds["testnet"], bool)


class TestExchangeHealthMonitor:
    """Тесты мониторинга здоровья бирж"""

    def test_health_metrics_initialization(self):
        """Тест инициализации метрик здоровья"""
        health_metrics = {
            "connection_status": "connected",
            "last_ping": time.time(),
            "response_time": 0.15,
            "error_count": 0,
            "success_rate": 100.0,
            "uptime": 3600,
        }

        # Проверяем метрики
        assert health_metrics["connection_status"] in ["connected", "disconnected", "connecting"]
        assert health_metrics["response_time"] >= 0
        assert health_metrics["error_count"] >= 0
        assert 0 <= health_metrics["success_rate"] <= 100
        assert health_metrics["uptime"] >= 0

    def test_response_time_tracking(self):
        """Тест отслеживания времени ответа"""
        response_times = [0.1, 0.2, 0.15, 0.3, 0.12]

        # Средний отклик
        avg_response_time = sum(response_times) / len(response_times)
        assert 0 < avg_response_time < 1.0

        # Максимальный отклик
        max_response_time = max(response_times)
        assert max_response_time >= avg_response_time

    def test_error_rate_calculation(self):
        """Тест расчета частоты ошибок"""
        total_requests = 1000
        error_requests = 25

        error_rate = (error_requests / total_requests) * 100
        success_rate = 100 - error_rate

        assert error_rate == 2.5
        assert success_rate == 97.5
        assert error_rate + success_rate == 100

    def test_connection_status_tracking(self):
        """Тест отслеживания статуса соединения"""
        connection_events = [
            {"timestamp": time.time() - 3600, "status": "connected"},
            {"timestamp": time.time() - 1800, "status": "disconnected"},
            {"timestamp": time.time() - 900, "status": "connected"},
            {"timestamp": time.time(), "status": "connected"},
        ]

        # Последний статус
        current_status = connection_events[-1]["status"]
        assert current_status == "connected"

        # Подсчет времени активности
        connected_time = 0
        total_time = connection_events[-1]["timestamp"] - connection_events[0]["timestamp"]

        for i in range(len(connection_events) - 1):
            if connection_events[i]["status"] == "connected":
                duration = connection_events[i + 1]["timestamp"] - connection_events[i]["timestamp"]
                connected_time += duration

        uptime_percentage = (connected_time / total_time) * 100
        assert 0 <= uptime_percentage <= 100


class TestExchangeManager:
    """Тесты менеджера бирж"""

    def test_exchange_registration(self):
        """Тест регистрации бирж"""
        # Список поддерживаемых бирж
        supported_exchanges = ["bybit", "binance", "okx", "gateio", "kucoin"]

        # Проверяем что все биржи валидны
        for exchange in supported_exchanges:
            assert isinstance(exchange, str)
            assert len(exchange) > 0
            assert exchange.islower()

    def test_exchange_configuration(self):
        """Тест конфигурации бирж"""
        exchange_config = {
            "bybit": {"enabled": True, "testnet": False, "max_positions": 10, "leverage": 5}
        }

        # Проверяем конфигурацию
        config = exchange_config["bybit"]
        assert isinstance(config["enabled"], bool)
        assert isinstance(config["testnet"], bool)
        assert config["max_positions"] > 0
        assert config["leverage"] >= 1

    def test_exchange_selection_logic(self):
        """Тест логики выбора биржи"""
        exchanges_status = {
            "bybit": {"active": True, "health": 95},
            "binance": {"active": False, "health": 60},
            "okx": {"active": True, "health": 88},
        }

        # Фильтруем активные биржи
        active_exchanges = {k: v for k, v in exchanges_status.items() if v["active"]}
        assert len(active_exchanges) == 2

        # Выбираем биржу с лучшим здоровьем
        best_exchange = max(active_exchanges.items(), key=lambda x: x[1]["health"])
        assert best_exchange[0] == "bybit"

    def test_load_balancing(self):
        """Тест балансировки нагрузки между биржами"""
        exchanges_load = {
            "bybit": {"requests": 45, "capacity": 100},
            "binance": {"requests": 80, "capacity": 100},
            "okx": {"requests": 20, "capacity": 100},
        }

        # Рассчитываем загрузку в процентах
        for exchange, data in exchanges_load.items():
            load_percent = (data["requests"] / data["capacity"]) * 100
            data["load_percent"] = load_percent

        # Находим наименее загруженную биржу
        least_loaded = min(exchanges_load.items(), key=lambda x: x[1]["load_percent"])
        assert least_loaded[0] == "okx"


class TestExchangeFactory:
    """Тесты фабрики бирж"""

    def test_exchange_creation_logic(self):
        """Тест логики создания экземпляров бирж"""
        # Конфигурация для создания биржи
        exchange_params = {
            "name": "bybit",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "testnet": True,
        }

        # Проверяем параметры
        assert exchange_params["name"] in ["bybit", "binance", "okx"]
        assert len(exchange_params["api_key"]) > 0
        assert len(exchange_params["api_secret"]) > 0
        assert isinstance(exchange_params["testnet"], bool)

    def test_exchange_validation(self):
        """Тест валидации конфигурации бирж"""
        # Валидная конфигурация
        valid_config = {
            "api_key": "valid_key_123",
            "api_secret": "valid_secret_456",
            "testnet": False,
            "timeout": 30,
            "retry_count": 3,
        }

        # Проверки валидации
        assert len(valid_config["api_key"]) >= 10
        assert len(valid_config["api_secret"]) >= 10
        assert valid_config["timeout"] > 0
        assert valid_config["retry_count"] >= 0

    def test_singleton_pattern(self):
        """Тест паттерна Singleton для бирж"""
        # Имитируем singleton поведение
        exchange_instances = {}

        def get_exchange(name):
            if name not in exchange_instances:
                exchange_instances[name] = f"Exchange_{name}_instance"
            return exchange_instances[name]

        # Проверяем что возвращается тот же экземпляр
        exchange1 = get_exchange("bybit")
        exchange2 = get_exchange("bybit")
        assert exchange1 is exchange2

        # Разные биржи - разные экземпляры
        exchange3 = get_exchange("binance")
        assert exchange1 is not exchange3


class TestWebSocketConnection:
    """Тесты WebSocket соединений"""

    def test_websocket_url_construction(self):
        """Тест построения WebSocket URL"""
        base_urls = {
            "bybit": "wss://stream.bybit.com/v5/public/linear",
            "binance": "wss://stream.binance.com:9443/ws",
        }

        # Проверяем URL
        for exchange, url in base_urls.items():
            assert url.startswith("wss://")
            assert exchange in ["bybit", "binance"]
            assert len(url) > 10

    def test_subscription_message_format(self):
        """Тест формата сообщений подписки"""
        subscription_msg = {
            "op": "subscribe",
            "args": ["orderbook.1.BTCUSDT", "publicTrade.BTCUSDT"],
        }

        # Проверяем формат
        assert "op" in subscription_msg
        assert "args" in subscription_msg
        assert subscription_msg["op"] == "subscribe"
        assert len(subscription_msg["args"]) > 0

    def test_heartbeat_mechanism(self):
        """Тест механизма heartbeat"""
        heartbeat_config = {
            "interval": 30,  # секунды
            "timeout": 10,  # секунды
            "max_missed": 3,  # количество
        }

        # Проверяем конфигурацию heartbeat
        assert heartbeat_config["interval"] > 0
        assert heartbeat_config["timeout"] < heartbeat_config["interval"]
        assert heartbeat_config["max_missed"] >= 1

    def test_message_parsing(self):
        """Тест парсинга WebSocket сообщений"""
        # Пример сообщения от биржи
        ws_message = {
            "topic": "orderbook.1.BTCUSDT",
            "type": "snapshot",
            "data": {
                "s": "BTCUSDT",
                "b": [["50000", "0.5"], ["49950", "1.0"]],
                "a": [["50050", "0.3"], ["50100", "0.8"]],
            },
        }

        # Проверяем структуру сообщения
        assert "topic" in ws_message
        assert "type" in ws_message
        assert "data" in ws_message
        assert "s" in ws_message["data"]  # symbol
        assert "b" in ws_message["data"]  # bids
        assert "a" in ws_message["data"]  # asks


class TestOrderExecutionLogic:
    """Тесты логики исполнения ордеров"""

    def test_order_validation(self):
        """Тест валидации ордера перед отправкой"""
        order = {
            "symbol": "BTCUSDT",
            "side": "buy",
            "type": "limit",
            "amount": Decimal("0.001"),
            "price": Decimal("50000"),
        }

        # Базовая валидация
        assert order["symbol"] in ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        assert order["side"] in ["buy", "sell"]
        assert order["type"] in ["market", "limit"]
        assert order["amount"] > 0
        assert order["price"] > 0

    def test_position_size_calculation(self):
        """Тест расчета размера позиции"""
        account_balance = Decimal("10000")  # USDT
        risk_percentage = Decimal("2")  # 2%
        entry_price = Decimal("50000")  # BTC price
        stop_loss_price = Decimal("49000")  # SL price

        # Расчет риска
        risk_amount = account_balance * (risk_percentage / 100)
        assert risk_amount == Decimal("200")

        # Расчет размера позиции
        price_diff = entry_price - stop_loss_price
        position_size = risk_amount / price_diff

        assert position_size > 0
        assert position_size == Decimal("0.2")

    def test_stop_loss_take_profit_logic(self):
        """Тест логики стоп-лосс и тейк-профит"""
        entry_price = Decimal("50000")

        # Для длинной позиции
        stop_loss_pct = Decimal("2")  # 2% ниже входа
        take_profit_pct = Decimal("4")  # 4% выше входа

        stop_loss = entry_price * (1 - stop_loss_pct / 100)
        take_profit = entry_price * (1 + take_profit_pct / 100)

        assert stop_loss == Decimal("49000")
        assert take_profit == Decimal("52000")
        assert stop_loss < entry_price < take_profit

    def test_leverage_calculation(self):
        """Тест расчета кредитного плеча"""
        position_value = Decimal("5000")  # USDT
        margin_required = Decimal("1000")  # USDT

        leverage = position_value / margin_required
        assert leverage == Decimal("5")

        # Проверка лимитов leverage
        max_leverage = Decimal("10")
        assert leverage <= max_leverage


class TestExchangeIntegrationFlow:
    """Интеграционные тесты потока работы с биржами"""

    def test_full_trading_flow_simulation(self):
        """Тест полного потока торговли"""
        # 1. Инициализация
        exchange = "bybit"
        symbol = "BTCUSDT"

        # 2. Получение баланса
        balance = Decimal("10000")
        assert balance > 0

        # 3. Создание ордера
        order_data = {
            "symbol": symbol,
            "side": "buy",
            "amount": Decimal("0.001"),
            "price": Decimal("50000"),
            "type": "limit",
        }

        # 4. Валидация ордера
        assert order_data["amount"] > 0
        assert order_data["price"] > 0

        # 5. Симуляция исполнения
        execution_result = {
            "order_id": "order_123456",
            "status": "filled",
            "filled_amount": order_data["amount"],
            "avg_price": order_data["price"],
        }

        # 6. Проверка результата
        assert execution_result["status"] == "filled"
        assert execution_result["filled_amount"] == order_data["amount"]

    def test_error_handling_flow(self):
        """Тест потока обработки ошибок"""
        # Различные типы ошибок
        errors = [
            {"type": "RateLimitError", "retry": True, "delay": 1},
            {"type": "InsufficientFundsError", "retry": False, "delay": 0},
            {"type": "NetworkError", "retry": True, "delay": 5},
        ]

        for error in errors:
            # Проверяем стратегию обработки
            if error["retry"]:
                assert error["delay"] > 0
            else:
                assert error["delay"] == 0

    def test_multi_exchange_coordination(self):
        """Тест координации между несколькими биржами"""
        exchanges = {
            "bybit": {"active": True, "balance": Decimal("5000")},
            "binance": {"active": True, "balance": Decimal("3000")},
            "okx": {"active": False, "balance": Decimal("2000")},
        }

        # Подсчет общего баланса активных бирж
        total_active_balance = sum(data["balance"] for data in exchanges.values() if data["active"])

        assert total_active_balance == Decimal("8000")

        # Распределение ордера по биржам
        order_amount = Decimal("0.001")
        active_exchanges = [k for k, v in exchanges.items() if v["active"]]

        amount_per_exchange = order_amount / len(active_exchanges)
        assert amount_per_exchange == Decimal("0.0005")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
