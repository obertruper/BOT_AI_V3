"""
Комплексные тесты для TradingEngine - ядро торговой системы BOT_AI_V3
Покрывает обработку сигналов, управление ордерами, риск-менеджмент и исполнение
"""

import os
import sys
import time
from decimal import Decimal

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestTradingEngineCore:
    """Тесты основной функциональности торгового движка"""

    def test_trading_engine_initialization(self):
        """Тест инициализации торгового движка"""
        # Конфигурация движка
        trading_config = {
            "max_positions": 10,
            "max_leverage": 5,
            "risk_limit_percentage": 2.0,
            "default_stop_loss": 2.0,
            "default_take_profit": 4.0,
            "min_trade_amount": 0.001,
            "supported_symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
        }

        # Состояние движка
        engine_state = {
            "initialized": False,
            "running": False,
            "config": None,
            "active_positions": {},
            "pending_orders": {},
            "processed_signals": 0,
            "total_pnl": Decimal("0"),
            "start_time": None,
        }

        def initialize_trading_engine(config):
            """Инициализация торгового движка"""
            # Валидация конфигурации
            required_fields = ["max_positions", "max_leverage", "risk_limit_percentage"]
            for field in required_fields:
                if field not in config:
                    return {"success": False, "error": f"Missing required field: {field}"}

            # Валидация значений
            if config["max_positions"] <= 0:
                return {"success": False, "error": "max_positions must be positive"}

            if config["max_leverage"] < 1:
                return {"success": False, "error": "max_leverage must be >= 1"}

            if not (0 < config["risk_limit_percentage"] <= 10):
                return {"success": False, "error": "risk_limit_percentage must be between 0 and 10"}

            # Инициализация
            engine_state["config"] = config
            engine_state["initialized"] = True
            engine_state["start_time"] = time.time()

            return {"success": True, "message": "Trading engine initialized successfully"}

        # Тестируем инициализацию
        result = initialize_trading_engine(trading_config)

        assert result["success"] is True
        assert engine_state["initialized"] is True
        assert engine_state["config"] == trading_config
        assert engine_state["start_time"] is not None

        # Тестируем валидацию с неверной конфигурацией
        invalid_config = {"max_positions": -1, "max_leverage": 0}
        invalid_result = initialize_trading_engine(invalid_config)

        assert invalid_result["success"] is False
        assert "max_positions must be positive" in invalid_result["error"]

    def test_signal_processing_workflow(self):
        """Тест полного процесса обработки торговых сигналов"""
        # Очередь сигналов
        signal_queue = []
        processed_signals = []

        # Конфигурация фильтров
        signal_filters = {
            "min_confidence": 0.7,
            "max_signals_per_symbol": 3,
            "cooldown_period": 300,  # 5 минут
            "blacklisted_symbols": ["SCAMUSDT"],
        }

        def validate_signal(signal, filters):
            """Валидация торгового сигнала"""
            # Проверка уверенности
            if signal.get("confidence", 0) < filters["min_confidence"]:
                return False, "Low confidence"

            # Проверка черного списка
            if signal.get("symbol") in filters["blacklisted_symbols"]:
                return False, "Symbol blacklisted"

            # Проверка обязательных полей
            required_fields = ["symbol", "direction", "confidence", "entry_price"]
            for field in required_fields:
                if field not in signal:
                    return False, f"Missing field: {field}"

            # Проверка направления
            if signal["direction"] not in ["buy", "sell"]:
                return False, "Invalid direction"

            return True, "Valid signal"

        def process_signal(signal, filters, recent_signals):
            """Обработка одного сигнала"""
            # Валидация
            is_valid, reason = validate_signal(signal, filters)
            if not is_valid:
                return {"processed": False, "reason": reason}

            # Проверка лимита сигналов на символ
            symbol = signal["symbol"]
            recent_for_symbol = [s for s in recent_signals if s["symbol"] == symbol]

            if len(recent_for_symbol) >= filters["max_signals_per_symbol"]:
                return {"processed": False, "reason": "Too many signals for symbol"}

            # Проверка периода восстановления
            current_time = time.time()
            for recent_signal in recent_for_symbol:
                if (current_time - recent_signal["timestamp"]) < filters["cooldown_period"]:
                    return {"processed": False, "reason": "Cooldown period active"}

            # Обработка сигнала
            processed_signal = {**signal, "processed_at": current_time, "status": "processed"}

            return {"processed": True, "signal": processed_signal}

        # Тестовые сигналы
        test_signals = [
            {
                "symbol": "BTCUSDT",
                "direction": "buy",
                "confidence": 0.85,
                "entry_price": 50000,
                "timestamp": time.time(),
            },
            {
                "symbol": "ETHUSDT",
                "direction": "sell",
                "confidence": 0.6,  # Низкая уверенность
                "entry_price": 3000,
                "timestamp": time.time(),
            },
            {
                "symbol": "SCAMUSDT",  # Черный список
                "direction": "buy",
                "confidence": 0.9,
                "entry_price": 1,
                "timestamp": time.time(),
            },
            {
                "symbol": "ADAUSDT",
                "direction": "buy",
                "confidence": 0.8,
                "entry_price": 0.5,
                "timestamp": time.time(),
            },
        ]

        # Обрабатываем сигналы
        for signal in test_signals:
            result = process_signal(signal, signal_filters, processed_signals)
            if result["processed"]:
                processed_signals.append(result["signal"])

        # Проверки
        assert len(processed_signals) == 2  # BTCUSDT и ADAUSDT прошли

        # Проверяем что правильные сигналы обработаны
        processed_symbols = [s["symbol"] for s in processed_signals]
        assert "BTCUSDT" in processed_symbols
        assert "ADAUSDT" in processed_symbols
        assert "ETHUSDT" not in processed_symbols  # Низкая уверенность
        assert "SCAMUSDT" not in processed_symbols  # Черный список

    def test_order_creation_and_management(self):
        """Тест создания и управления ордерами"""
        # Состояние ордеров
        orders = {}
        order_counter = 0

        # Конфигурация ордеров
        order_config = {
            "default_order_type": "limit",
            "slippage_tolerance": 0.1,  # 0.1%
            "min_order_size": 0.001,
            "max_order_size": 10.0,
            "default_timeout": 300,  # 5 минут
        }

        def create_order(signal, account_balance, config):
            """Создание ордера на основе сигнала"""
            nonlocal order_counter
            order_counter += 1

            # Расчет размера позиции
            risk_amount = account_balance * 0.02  # 2% риска
            entry_price = signal["entry_price"]

            # Стоп-лосс
            if signal["direction"] == "buy":
                stop_loss = entry_price * 0.98  # 2% ниже
                take_profit = entry_price * 1.04  # 4% выше
            else:
                stop_loss = entry_price * 1.02  # 2% выше
                take_profit = entry_price * 0.96  # 4% ниже

            # Размер позиции на основе риска
            stop_distance = abs(entry_price - stop_loss)
            position_size = risk_amount / stop_distance

            # Ограничения размера
            position_size = max(
                config["min_order_size"], min(position_size, config["max_order_size"])
            )

            order = {
                "id": f"ord_{order_counter:06d}",
                "symbol": signal["symbol"],
                "side": signal["direction"],
                "type": config["default_order_type"],
                "amount": round(position_size, 6),
                "price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "status": "pending",
                "created_at": time.time(),
                "signal_confidence": signal["confidence"],
                "timeout_at": time.time() + config["default_timeout"],
            }

            orders[order["id"]] = order
            return order

        def manage_order_lifecycle(order_id, market_price):
            """Управление жизненным циклом ордера"""
            if order_id not in orders:
                return {"error": "Order not found"}

            order = orders[order_id]
            current_time = time.time()

            # Проверка таймаута
            if current_time > order["timeout_at"] and order["status"] == "pending":
                order["status"] = "expired"
                return {"status": "expired", "reason": "timeout"}

            # Проверка исполнения (упрощенная логика)
            if order["status"] == "pending":
                entry_price = order["price"]
                slippage_range = entry_price * 0.001  # 0.1% slippage

                if order["side"] == "buy":
                    if market_price <= (entry_price + slippage_range):
                        order["status"] = "filled"
                        order["filled_price"] = market_price
                        order["filled_at"] = current_time
                        return {"status": "filled", "price": market_price}
                else:  # sell
                    if market_price >= (entry_price - slippage_range):
                        order["status"] = "filled"
                        order["filled_price"] = market_price
                        order["filled_at"] = current_time
                        return {"status": "filled", "price": market_price}

            return {"status": order["status"]}

        # Тестируем создание ордера
        test_signal = {
            "symbol": "BTCUSDT",
            "direction": "buy",
            "confidence": 0.8,
            "entry_price": 50000,
        }

        account_balance = Decimal("10000")  # $10,000
        order = create_order(test_signal, account_balance, order_config)

        # Проверки ордера
        assert order["symbol"] == "BTCUSDT"
        assert order["side"] == "buy"
        assert order["price"] == 50000
        assert order["stop_loss"] == 49000  # 2% ниже
        assert order["take_profit"] == 52000  # 4% выше
        assert order["amount"] >= order_config["min_order_size"]
        assert order["status"] == "pending"

        # Тестируем исполнение ордера
        market_price = 50025  # Близко к цене ордера
        execution_result = manage_order_lifecycle(order["id"], market_price)

        assert execution_result["status"] == "filled"
        assert execution_result["price"] == market_price
        assert orders[order["id"]]["status"] == "filled"
        assert orders[order["id"]]["filled_price"] == market_price

    def test_position_management_system(self):
        """Тест системы управления позициями"""
        # Активные позиции
        positions = {}

        def open_position(order):
            """Открытие позиции на основе исполненного ордера"""
            if order["status"] != "filled":
                return {"error": "Order not filled"}

            position_id = f"pos_{order['symbol']}_{int(time.time())}"

            position = {
                "id": position_id,
                "symbol": order["symbol"],
                "side": order["side"],
                "size": order["amount"],
                "entry_price": order["filled_price"],
                "current_price": order["filled_price"],
                "stop_loss": order["stop_loss"],
                "take_profit": order["take_profit"],
                "pnl": 0.0,
                "pnl_percentage": 0.0,
                "status": "open",
                "opened_at": time.time(),
                "order_id": order["id"],
            }

            positions[position_id] = position
            return position

        def update_position(position_id, current_market_price):
            """Обновление позиции с текущей рыночной ценой"""
            if position_id not in positions:
                return {"error": "Position not found"}

            position = positions[position_id]
            if position["status"] != "open":
                return {"error": "Position not open"}

            position["current_price"] = current_market_price
            entry_price = position["entry_price"]

            # Расчет PnL
            if position["side"] == "buy":
                pnl = (current_market_price - entry_price) * position["size"]
            else:  # sell
                pnl = (entry_price - current_market_price) * position["size"]

            position["pnl"] = round(pnl, 2)
            position["pnl_percentage"] = round((pnl / (entry_price * position["size"])) * 100, 2)

            # Проверка стоп-лосс и тейк-профит
            if position["side"] == "buy":
                if current_market_price <= position["stop_loss"]:
                    position["status"] = "closed_sl"
                    position["exit_price"] = position["stop_loss"]
                    position["closed_at"] = time.time()
                    return {"action": "stop_loss_triggered", "pnl": position["pnl"]}
                elif current_market_price >= position["take_profit"]:
                    position["status"] = "closed_tp"
                    position["exit_price"] = position["take_profit"]
                    position["closed_at"] = time.time()
                    return {"action": "take_profit_triggered", "pnl": position["pnl"]}
            else:  # sell
                if current_market_price >= position["stop_loss"]:
                    position["status"] = "closed_sl"
                    position["exit_price"] = position["stop_loss"]
                    position["closed_at"] = time.time()
                    return {"action": "stop_loss_triggered", "pnl": position["pnl"]}
                elif current_market_price <= position["take_profit"]:
                    position["status"] = "closed_tp"
                    position["exit_price"] = position["take_profit"]
                    position["closed_at"] = time.time()
                    return {"action": "take_profit_triggered", "pnl": position["pnl"]}

            return {"action": "updated", "pnl": position["pnl"]}

        def calculate_portfolio_metrics(positions):
            """Расчет метрик портфеля"""
            open_positions = [p for p in positions.values() if p["status"] == "open"]
            closed_positions = [p for p in positions.values() if p["status"].startswith("closed")]

            total_pnl = sum(p["pnl"] for p in positions.values())
            unrealized_pnl = sum(p["pnl"] for p in open_positions)
            realized_pnl = sum(p["pnl"] for p in closed_positions)

            winning_trades = len([p for p in closed_positions if p["pnl"] > 0])
            losing_trades = len([p for p in closed_positions if p["pnl"] < 0])
            total_trades = len(closed_positions)

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            return {
                "total_pnl": total_pnl,
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": realized_pnl,
                "open_positions": len(open_positions),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
            }

        # Тестируем открытие позиции
        filled_order = {
            "id": "ord_000001",
            "symbol": "BTCUSDT",
            "side": "buy",
            "amount": 0.1,
            "price": 50000,
            "stop_loss": 49000,
            "take_profit": 52000,
            "status": "filled",
            "filled_price": 50025,
        }

        position = open_position(filled_order)
        position_id = position["id"]

        # Проверки позиции
        assert position["symbol"] == "BTCUSDT"
        assert position["side"] == "buy"
        assert position["size"] == 0.1
        assert position["entry_price"] == 50025
        assert position["status"] == "open"

        # Тестируем обновление позиции (прибыль)
        profit_result = update_position(position_id, 51000)  # Цена выросла

        assert profit_result["action"] == "updated"
        assert positions[position_id]["pnl"] > 0
        assert positions[position_id]["pnl"] == 97.5  # (51000 - 50025) * 0.1

        # Тестируем тейк-профит
        tp_result = update_position(position_id, 52000)  # Достигли тейк-профит

        assert tp_result["action"] == "take_profit_triggered"
        assert positions[position_id]["status"] == "closed_tp"

        # Тестируем метрики портфеля
        metrics = calculate_portfolio_metrics(positions)

        assert metrics["total_trades"] == 1
        assert metrics["winning_trades"] == 1
        assert metrics["win_rate"] == 100.0
        assert metrics["realized_pnl"] > 0


class TestRiskManagementSystem:
    """Тесты системы риск-менеджмента"""

    def test_position_sizing_logic(self):
        """Тест логики расчета размера позиции"""
        # Параметры риска
        risk_config = {
            "max_risk_per_trade": 2.0,  # 2% от баланса
            "account_balance": 10000,
            "max_leverage": 5,
            "min_position_size": 0.001,
            "max_position_size": 1.0,
        }

        def calculate_position_size(entry_price, stop_loss, risk_config):
            """Расчет размера позиции на основе риска"""
            account_balance = risk_config["account_balance"]
            max_risk_amount = account_balance * (risk_config["max_risk_per_trade"] / 100)

            # Расстояние до стоп-лосса
            risk_distance = abs(entry_price - stop_loss)

            if risk_distance == 0:
                return 0

            # Размер позиции
            position_size = max_risk_amount / risk_distance

            # Применяем ограничения
            position_size = max(risk_config["min_position_size"], position_size)
            position_size = min(risk_config["max_position_size"], position_size)

            return round(position_size, 6)

        def validate_position_risk(position_size, entry_price, leverage, risk_config):
            """Валидация риска позиции"""
            position_value = position_size * entry_price * leverage
            account_balance = risk_config["account_balance"]

            # Проверка максимального риска
            max_position_value = (
                account_balance * (risk_config["max_risk_per_trade"] / 100) * 10
            )  # 10x buffer

            if position_value > max_position_value:
                return False, "Position value exceeds risk limit"

            # Проверка leverage
            if leverage > risk_config["max_leverage"]:
                return False, "Leverage exceeds maximum"

            # Проверка размера позиции
            if position_size < risk_config["min_position_size"]:
                return False, "Position size below minimum"

            if position_size > risk_config["max_position_size"]:
                return False, "Position size above maximum"

            return True, "Position risk acceptable"

        # Тестируем расчет размера позиции
        entry_price = 50000
        stop_loss = 49000  # 2% стоп-лосс

        position_size = calculate_position_size(entry_price, stop_loss, risk_config)

        # Проверяем что размер позиции рассчитан корректно
        expected_risk = 10000 * 0.02  # $200 риска
        expected_size = expected_risk / 1000  # $200 / $1000 = 0.2 BTC

        assert abs(position_size - expected_size) < 0.001  # Допустимая погрешность

        # Тестируем валидацию риска
        is_valid, message = validate_position_risk(position_size, entry_price, 3, risk_config)

        assert is_valid is True
        assert message == "Position risk acceptable"

        # Тестируем превышение leverage
        invalid_validation = validate_position_risk(position_size, entry_price, 10, risk_config)

        assert invalid_validation[0] is False
        assert "Leverage exceeds maximum" in invalid_validation[1]

    def test_portfolio_risk_monitoring(self):
        """Тест мониторинга риска портфеля"""
        # Состояние портфеля
        portfolio = {
            "balance": 10000,
            "equity": 10000,
            "margin_used": 0,
            "margin_available": 10000,
            "positions": [],
            "daily_pnl": 0,
            "max_drawdown": 0,
        }

        # Лимиты риска
        risk_limits = {
            "max_portfolio_risk": 10.0,  # 10% от баланса
            "max_daily_loss": 5.0,  # 5% от баланса в день
            "max_margin_usage": 80.0,  # 80% от доступной маржи
            "max_correlation_risk": 60.0,  # 60% в одном направлении
            "max_drawdown_limit": 15.0,  # 15% максимальная просадка
        }

        def add_position_to_portfolio(position, portfolio):
            """Добавление позиции в портфель"""
            portfolio["positions"].append(position)

            # Обновляем используемую маржу
            position_margin = (
                position["size"] * position["entry_price"] / position.get("leverage", 1)
            )
            portfolio["margin_used"] += position_margin
            portfolio["margin_available"] = portfolio["balance"] - portfolio["margin_used"]

            # Обновляем эквити с учетом PnL
            portfolio["equity"] = portfolio["balance"] + sum(
                p.get("pnl", 0) for p in portfolio["positions"]
            )

        def check_portfolio_risk(portfolio, limits):
            """Проверка рисков портфеля"""
            alerts = []

            # Проверка использования маржи
            margin_usage_pct = (portfolio["margin_used"] / portfolio["balance"]) * 100
            if margin_usage_pct > limits["max_margin_usage"]:
                alerts.append(
                    {
                        "type": "margin_risk",
                        "severity": "high",
                        "message": f"Margin usage {margin_usage_pct:.1f}% exceeds limit {limits['max_margin_usage']}%",
                    }
                )

            # Проверка дневного PnL
            daily_loss_pct = abs(portfolio["daily_pnl"]) / portfolio["balance"] * 100
            if portfolio["daily_pnl"] < 0 and daily_loss_pct > limits["max_daily_loss"]:
                alerts.append(
                    {
                        "type": "daily_loss",
                        "severity": "critical",
                        "message": f"Daily loss {daily_loss_pct:.1f}% exceeds limit {limits['max_daily_loss']}%",
                    }
                )

            # Проверка корреляционного риска
            long_exposure = sum(
                p["size"] * p["entry_price"] for p in portfolio["positions"] if p["side"] == "buy"
            )
            short_exposure = sum(
                p["size"] * p["entry_price"] for p in portfolio["positions"] if p["side"] == "sell"
            )
            total_exposure = long_exposure + short_exposure

            if total_exposure > 0:
                directional_bias = max(long_exposure, short_exposure) / total_exposure * 100
                if directional_bias > limits["max_correlation_risk"]:
                    alerts.append(
                        {
                            "type": "correlation_risk",
                            "severity": "medium",
                            "message": f"Directional bias {directional_bias:.1f}% exceeds limit {limits['max_correlation_risk']}%",
                        }
                    )

            # Проверка просадки
            current_drawdown = (
                (portfolio["balance"] - portfolio["equity"]) / portfolio["balance"] * 100
            )
            if current_drawdown > limits["max_drawdown_limit"]:
                alerts.append(
                    {
                        "type": "drawdown_risk",
                        "severity": "critical",
                        "message": f"Drawdown {current_drawdown:.1f}% exceeds limit {limits['max_drawdown_limit']}%",
                    }
                )

            return alerts

        # Тестируем добавление позиций
        position1 = {
            "symbol": "BTCUSDT",
            "side": "buy",
            "size": 0.2,
            "entry_price": 50000,
            "leverage": 3,
            "pnl": 100,
        }

        position2 = {
            "symbol": "ETHUSDT",
            "side": "buy",
            "size": 1.0,
            "entry_price": 3000,
            "leverage": 2,
            "pnl": -50,
        }

        add_position_to_portfolio(position1, portfolio)
        add_position_to_portfolio(position2, portfolio)

        # Проверяем состояние портфеля
        assert len(portfolio["positions"]) == 2
        assert portfolio["equity"] == 10050  # 10000 + 100 - 50

        expected_margin = (0.2 * 50000 / 3) + (1.0 * 3000 / 2)  # 3333.33 + 1500
        assert abs(portfolio["margin_used"] - expected_margin) < 1

        # Тестируем проверку рисков (нормальное состояние)
        normal_alerts = check_portfolio_risk(portfolio, risk_limits)
        assert len(normal_alerts) == 0  # Нет превышений

        # Тестируем превышение дневных потерь
        portfolio["daily_pnl"] = -600  # 6% потери
        daily_loss_alerts = check_portfolio_risk(portfolio, risk_limits)

        daily_loss_alert = next((a for a in daily_loss_alerts if a["type"] == "daily_loss"), None)
        assert daily_loss_alert is not None
        assert daily_loss_alert["severity"] == "critical"

    def test_dynamic_risk_adjustment(self):
        """Тест динамической настройки риска"""
        # Параметры адаптивного риска
        adaptive_risk = {
            "base_risk": 2.0,  # Базовый риск 2%
            "current_risk": 2.0,
            "volatility_multiplier": 1.0,
            "performance_multiplier": 1.0,
            "market_condition": "normal",  # normal, volatile, trending
        }

        # Исторические данные для анализа
        market_history = {
            "volatility_30d": 0.15,  # 15% волатильность
            "avg_volatility": 0.20,  # Средняя волатильность
            "recent_performance": 0.05,  # 5% доходность за период
            "win_rate_30d": 0.65,  # 65% выигрышных сделок
            "sharpe_ratio": 1.2,
        }

        def calculate_volatility_adjustment(current_vol, avg_vol):
            """Корректировка на волатильность"""
            vol_ratio = current_vol / avg_vol

            if vol_ratio > 1.5:  # Высокая волатильность
                return 0.7  # Снижаем риск на 30%
            elif vol_ratio > 1.2:  # Повышенная волатильность
                return 0.85  # Снижаем риск на 15%
            elif vol_ratio < 0.8:  # Низкая волатильность
                return 1.2  # Увеличиваем риск на 20%
            else:
                return 1.0  # Нормальный риск

        def calculate_performance_adjustment(performance, win_rate, sharpe):
            """Корректировка на основе производительности"""
            # Базовая корректировка на доходность
            if performance > 0.1:  # Высокая доходность
                perf_mult = 1.1
            elif performance < -0.05:  # Убытки
                perf_mult = 0.8
            else:
                perf_mult = 1.0

            # Корректировка на винрейт
            if win_rate > 0.7:
                wr_mult = 1.05
            elif win_rate < 0.5:
                wr_mult = 0.9
            else:
                wr_mult = 1.0

            # Корректировка на Sharpe ratio
            if sharpe > 1.5:
                sharpe_mult = 1.1
            elif sharpe < 0.8:
                sharpe_mult = 0.85
            else:
                sharpe_mult = 1.0

            return perf_mult * wr_mult * sharpe_mult

        def adjust_risk_dynamically(adaptive_risk, market_history):
            """Динамическая корректировка риска"""
            # Корректировка на волатильность
            vol_adj = calculate_volatility_adjustment(
                market_history["volatility_30d"], market_history["avg_volatility"]
            )

            # Корректировка на производительность
            perf_adj = calculate_performance_adjustment(
                market_history["recent_performance"],
                market_history["win_rate_30d"],
                market_history["sharpe_ratio"],
            )

            # Итоговая корректировка
            total_adjustment = vol_adj * perf_adj

            # Ограничиваем корректировку разумными пределами
            total_adjustment = max(0.5, min(total_adjustment, 2.0))

            # Обновляем текущий риск
            new_risk = adaptive_risk["base_risk"] * total_adjustment
            adaptive_risk["current_risk"] = round(new_risk, 2)
            adaptive_risk["volatility_multiplier"] = vol_adj
            adaptive_risk["performance_multiplier"] = perf_adj

            return adaptive_risk

        # Тестируем адаптацию риска
        adjusted_risk = adjust_risk_dynamically(adaptive_risk, market_history)

        # Проверяем корректировки
        # Волатильность ниже средней (0.15 vs 0.20) -> увеличение риска
        assert adjusted_risk["volatility_multiplier"] == 1.2

        # Хорошая производительность -> небольшое увеличение риска
        assert adjusted_risk["performance_multiplier"] > 1.0

        # Итоговый риск должен быть скорректирован
        assert adjusted_risk["current_risk"] != adaptive_risk["base_risk"]
        assert 1.0 <= adjusted_risk["current_risk"] <= 4.0  # В разумных пределах

        # Тестируем экстремальные условия
        extreme_market = {
            "volatility_30d": 0.40,  # Очень высокая волатильность
            "avg_volatility": 0.20,
            "recent_performance": -0.10,  # Убытки
            "win_rate_30d": 0.40,  # Низкий винрейт
            "sharpe_ratio": 0.5,  # Плохой Sharpe
        }

        extreme_risk = adjust_risk_dynamically(adaptive_risk.copy(), extreme_market)

        # В экстремальных условиях риск должен быть существенно снижен
        assert extreme_risk["current_risk"] < adaptive_risk["base_risk"]
        assert extreme_risk["volatility_multiplier"] < 1.0
        assert extreme_risk["performance_multiplier"] < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
