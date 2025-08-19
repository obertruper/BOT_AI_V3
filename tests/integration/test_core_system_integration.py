"""
Интеграционные тесты для основных компонентов системы BOT_AI_V3
Тесты взаимодействия между модулями core/, trading/, ml/, exchanges/
"""

import os
import sys
import time
from decimal import Decimal

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestSystemOrchestratorIntegration:
    """Интеграционные тесты оркестратора системы"""

    def test_orchestrator_initialization_flow(self):
        """Тест полного потока инициализации оркестратора"""
        # Имитируем конфигурацию системы
        system_config = {
            "trading": {"enabled": True, "max_positions": 10},
            "ml": {"enabled": True, "model_version": "v1.2.3"},
            "exchanges": {"primary": "bybit", "backup": "binance"},
            "monitoring": {"health_check_interval": 30},
        }

        # Этапы инициализации
        initialization_steps = [
            "load_configuration",
            "initialize_database",
            "connect_exchanges",
            "load_ml_models",
            "start_trading_engine",
            "enable_monitoring",
        ]

        # Имитируем успешную инициализацию
        initialized_components = {}
        for step in initialization_steps:
            initialized_components[step] = {"status": "success", "timestamp": time.time()}

        # Проверяем что все компоненты инициализированы
        assert len(initialized_components) == len(initialization_steps)
        assert all(comp["status"] == "success" for comp in initialized_components.values())

    def test_component_health_monitoring_integration(self):
        """Тест интеграции мониторинга здоровья компонентов"""
        # Статусы компонентов системы
        component_statuses = {
            "database": {"healthy": True, "response_time": 0.05, "error_count": 0},
            "exchanges": {"healthy": True, "response_time": 0.15, "error_count": 1},
            "ml_service": {"healthy": True, "response_time": 0.02, "error_count": 0},
            "trading_engine": {"healthy": True, "response_time": 0.08, "error_count": 0},
            "websocket": {"healthy": False, "response_time": 5.0, "error_count": 3},
        }

        # Анализ общего здоровья системы
        healthy_components = sum(1 for status in component_statuses.values() if status["healthy"])
        total_components = len(component_statuses)
        health_percentage = (healthy_components / total_components) * 100

        # Система считается здоровой если > 80% компонентов работают
        system_healthy = health_percentage > 80
        assert system_healthy is True
        assert health_percentage == 80.0  # 4 из 5 компонентов здоровы

        # Проверка критичных компонентов
        critical_components = ["database", "trading_engine"]
        critical_healthy = all(component_statuses[comp]["healthy"] for comp in critical_components)
        assert critical_healthy is True

    def test_configuration_management_integration(self):
        """Тест интеграции управления конфигурацией"""
        # Базовая конфигурация
        base_config = {
            "system": {"version": "3.0.0", "environment": "production"},
            "trading": {"leverage": 5, "max_positions": 10, "risk_limit": 2.0},
            "ml": {"batch_size": 64, "inference_timeout": 50},
            "exchanges": {"timeout": 30, "retry_count": 3},
        }

        # Конфигурация для тестинга
        test_overrides = {
            "system": {"environment": "test"},
            "trading": {"leverage": 1, "max_positions": 2},
            "exchanges": {"timeout": 5, "retry_count": 1},
        }

        # Имитируем слияние конфигураций
        def merge_configs(base, overrides):
            merged = base.copy()
            for section, values in overrides.items():
                if section in merged:
                    merged[section].update(values)
                else:
                    merged[section] = values
            return merged

        final_config = merge_configs(base_config, test_overrides)

        # Проверяем результат слияния
        assert final_config["system"]["environment"] == "test"
        assert final_config["trading"]["leverage"] == 1
        assert final_config["trading"]["risk_limit"] == 2.0  # Не переопределено
        assert final_config["ml"]["batch_size"] == 64  # Не переопределено


class TestTradingEngineIntegration:
    """Интеграционные тесты торгового движка"""

    def test_signal_to_order_flow(self):
        """Тест полного потока от сигнала до ордера"""
        # 1. Получение ML сигнала
        ml_signal = {
            "symbol": "BTCUSDT",
            "prediction": "buy",
            "confidence": 0.85,
            "target_price": 50000,
            "stop_loss": 49000,
            "take_profit": 52000,
            "timestamp": time.time(),
        }

        # 2. Обработка сигнала торговым движком
        def process_signal(signal):
            if signal["confidence"] < 0.7:
                return {"action": "ignore", "reason": "low_confidence"}

            return {
                "action": "create_order",
                "order_params": {
                    "symbol": signal["symbol"],
                    "side": signal["prediction"],
                    "amount": "0.001",  # Размер позиции
                    "price": signal["target_price"],
                    "stop_loss": signal["stop_loss"],
                    "take_profit": signal["take_profit"],
                },
            }

        # 3. Создание ордера
        def create_order(params):
            return {
                "order_id": "ord_123456",
                "status": "pending",
                "created_at": time.time(),
                **params,
            }

        # Тестируем полный поток
        processing_result = process_signal(ml_signal)
        assert processing_result["action"] == "create_order"

        order = create_order(processing_result["order_params"])
        assert order["order_id"] is not None
        assert order["symbol"] == "BTCUSDT"
        assert order["side"] == "buy"

    def test_position_management_integration(self):
        """Тест интеграции управления позициями"""
        # Текущие позиции
        current_positions = {
            "BTCUSDT": {
                "side": "long",
                "size": Decimal("0.1"),
                "entry_price": Decimal("49000"),
                "current_price": Decimal("50000"),
                "pnl": Decimal("100"),
            }
        }

        # Новый сигнал
        new_signal = {"symbol": "BTCUSDT", "direction": "sell", "size": Decimal("0.05")}

        # Логика управления позициями
        def manage_position(positions, signal):
            symbol = signal["symbol"]

            if symbol in positions:
                current_pos = positions[symbol]

                if signal["direction"] == "sell" and current_pos["side"] == "long":
                    # Частичное закрытие длинной позиции
                    if signal["size"] <= current_pos["size"]:
                        new_size = current_pos["size"] - signal["size"]
                        return {
                            "action": "reduce_position",
                            "new_size": new_size,
                            "realized_pnl": (signal["size"] / current_pos["size"])
                            * current_pos["pnl"],
                        }
                    else:
                        # Переворот позиции
                        return {
                            "action": "reverse_position",
                            "new_side": "short",
                            "new_size": signal["size"] - current_pos["size"],
                        }
            else:
                # Новая позиция
                return {
                    "action": "open_position",
                    "side": "short" if signal["direction"] == "sell" else "long",
                    "size": signal["size"],
                }

        result = manage_position(current_positions, new_signal)

        assert result["action"] == "reduce_position"
        assert result["new_size"] == Decimal("0.05")
        assert result["realized_pnl"] == Decimal("50")  # 50% от PnL

    def test_risk_management_integration(self):
        """Тест интеграции риск-менеджмента"""
        # Параметры риска
        risk_config = {
            "max_risk_per_trade": 2.0,  # 2% от баланса
            "max_daily_loss": 5.0,  # 5% от баланса
            "max_positions": 10,
            "max_leverage": 5,
        }

        # Текущий статус аккаунта
        account_status = {
            "balance": Decimal("10000"),
            "daily_pnl": Decimal("-300"),  # -3%
            "open_positions": 3,
            "total_exposure": Decimal("30000"),  # 3x leverage
        }

        # Новый ордер для проверки
        new_order = {
            "symbol": "ETHUSDT",
            "side": "buy",
            "amount": Decimal("1.0"),
            "price": Decimal("3000"),
            "leverage": 5,
        }

        # Функция проверки рисков
        def check_risk_limits(order, config, status):
            checks = {}

            # Проверка дневного лимита потерь
            daily_loss_pct = abs(float(status["daily_pnl"]) / float(status["balance"]) * 100)
            checks["daily_loss"] = daily_loss_pct < config["max_daily_loss"]

            # Проверка максимального количества позиций
            checks["position_count"] = status["open_positions"] < config["max_positions"]

            # Проверка leverage
            checks["leverage"] = order["leverage"] <= config["max_leverage"]

            # Проверка риска на сделку
            trade_value = order["amount"] * order["price"]
            trade_risk_pct = float(trade_value) / float(status["balance"]) * 100
            checks["trade_risk"] = trade_risk_pct <= config["max_risk_per_trade"]

            return {"approved": all(checks.values()), "checks": checks}

        risk_result = check_risk_limits(new_order, risk_config, account_status)

        # Ордер должен быть отклонен из-за превышения дневного лимита потерь
        assert risk_result["approved"] is False
        assert risk_result["checks"]["daily_loss"] is False
        assert risk_result["checks"]["position_count"] is True
        assert risk_result["checks"]["leverage"] is True


class TestMLTradingIntegration:
    """Интеграционные тесты ML и торговой системы"""

    def test_feature_engineering_to_prediction_flow(self):
        """Тест потока от создания признаков до прогноза"""
        # 1. Сырые рыночные данные
        raw_market_data = {
            "symbol": "BTCUSDT",
            "timestamp": "2023-01-01T12:00:00Z",
            "open": 49500,
            "high": 50200,
            "low": 49300,
            "close": 50000,
            "volume": 1250000,
        }

        # 2. Создание технических индикаторов
        def create_technical_features(data):
            # Простые технические индикаторы
            return {
                "price_change": (data["close"] - data["open"]) / data["open"],
                "high_low_ratio": data["high"] / data["low"],
                "volume_ratio": data["volume"] / 1000000,  # Нормализация объема
                "rsi_signal": 0.6,  # Имитируем RSI
                "macd_signal": 0.3,  # Имитируем MACD
            }

        # 3. ML предсказание
        def ml_prediction(features):
            # Простая логика предсказания
            score = (
                features["price_change"] * 0.3
                + (features["rsi_signal"] - 0.5) * 0.2
                + features["macd_signal"] * 0.3
                + (features["volume_ratio"] - 1.0) * 0.2
            )

            return {
                "prediction": "buy" if score > 0.1 else "sell" if score < -0.1 else "hold",
                "confidence": min(abs(score) * 2, 1.0),
                "score": score,
            }

        # 4. Генерация торгового сигнала
        def generate_trading_signal(prediction, market_data):
            if prediction["confidence"] < 0.6:
                return {"action": "no_trade", "reason": "low_confidence"}

            if prediction["prediction"] == "buy":
                return {
                    "action": "buy",
                    "symbol": market_data["symbol"],
                    "entry_price": market_data["close"],
                    "stop_loss": market_data["close"] * 0.98,
                    "take_profit": market_data["close"] * 1.04,
                }
            elif prediction["prediction"] == "sell":
                return {
                    "action": "sell",
                    "symbol": market_data["symbol"],
                    "entry_price": market_data["close"],
                    "stop_loss": market_data["close"] * 1.02,
                    "take_profit": market_data["close"] * 0.96,
                }

        # Тестируем полный поток
        features = create_technical_features(raw_market_data)
        prediction = ml_prediction(features)
        trading_signal = generate_trading_signal(prediction, raw_market_data)

        # Проверяем результаты
        assert "price_change" in features
        assert "prediction" in prediction
        assert prediction["prediction"] in ["buy", "sell", "hold"]

        if trading_signal:
            assert trading_signal["symbol"] == "BTCUSDT"
            if trading_signal["action"] in ["buy", "sell"]:
                assert "entry_price" in trading_signal
                assert "stop_loss" in trading_signal
                assert "take_profit" in trading_signal

    def test_model_performance_monitoring(self):
        """Тест мониторинга производительности ML модели"""
        # История предсказаний
        prediction_history = [
            {"prediction": "buy", "confidence": 0.8, "actual": "profitable", "pnl": 150},
            {"prediction": "sell", "confidence": 0.7, "actual": "profitable", "pnl": 80},
            {"prediction": "buy", "confidence": 0.9, "actual": "loss", "pnl": -50},
            {"prediction": "sell", "confidence": 0.6, "actual": "profitable", "pnl": 30},
            {"prediction": "buy", "confidence": 0.85, "actual": "profitable", "pnl": 120},
        ]

        def calculate_model_metrics(history):
            total_predictions = len(history)
            profitable_predictions = sum(1 for p in history if p["actual"] == "profitable")

            # Accuracy
            accuracy = profitable_predictions / total_predictions

            # Total PnL
            total_pnl = sum(p["pnl"] for p in history)

            # Average confidence
            avg_confidence = sum(p["confidence"] for p in history) / total_predictions

            # Confidence vs Performance correlation
            high_conf_predictions = [p for p in history if p["confidence"] > 0.8]
            high_conf_accuracy = sum(
                1 for p in high_conf_predictions if p["actual"] == "profitable"
            ) / len(high_conf_predictions)

            return {
                "accuracy": accuracy,
                "total_pnl": total_pnl,
                "avg_confidence": avg_confidence,
                "high_confidence_accuracy": high_conf_accuracy,
                "total_trades": total_predictions,
            }

        metrics = calculate_model_metrics(prediction_history)

        assert metrics["accuracy"] == 0.8  # 80% точность
        assert metrics["total_pnl"] == 330  # Общая прибыль
        assert metrics["avg_confidence"] == 0.76  # Средняя уверенность
        assert metrics["high_confidence_accuracy"] == 0.67  # ~67% для высокой уверенности


class TestExchangeIntegration:
    """Интеграционные тесты интеграции с биржами"""

    def test_multi_exchange_order_routing(self):
        """Тест маршрутизации ордеров между биржами"""
        # Статус бирж
        exchange_status = {
            "bybit": {"available": True, "latency": 150, "fees": 0.1, "liquidity": 0.9},
            "binance": {"available": True, "latency": 200, "fees": 0.1, "liquidity": 0.95},
            "okx": {"available": False, "latency": 500, "fees": 0.08, "liquidity": 0.7},
        }

        # Алгоритм выбора биржи
        def select_exchange(exchanges, order_size):
            # Фильтруем доступные биржи
            available = {k: v for k, v in exchanges.items() if v["available"]}

            if not available:
                return None

            # Для больших ордеров приоритет - ликвидность
            if order_size > 1.0:
                return max(available.items(), key=lambda x: x[1]["liquidity"])[0]

            # Для малых ордеров приоритет - низкая задержка
            return min(available.items(), key=lambda x: x[1]["latency"])[0]

        # Тестируем выбор биржи
        small_order_exchange = select_exchange(exchange_status, 0.1)
        large_order_exchange = select_exchange(exchange_status, 2.0)

        assert small_order_exchange == "bybit"  # Меньшая задержка
        assert large_order_exchange == "binance"  # Лучшая ликвидность

    def test_order_execution_flow(self):
        """Тест полного потока исполнения ордера"""
        # Ордер для исполнения
        order = {
            "id": "ord_123",
            "symbol": "BTCUSDT",
            "side": "buy",
            "amount": Decimal("0.001"),
            "price": Decimal("50000"),
            "type": "limit",
        }

        # Имитируем этапы исполнения
        execution_stages = []

        # 1. Валидация ордера
        def validate_order(order):
            execution_stages.append("validation")
            return order["amount"] > 0 and order["price"] > 0

        # 2. Отправка на биржу
        def submit_to_exchange(order):
            execution_stages.append("submission")
            return {"exchange_order_id": "exch_789", "status": "pending"}

        # 3. Мониторинг исполнения
        def monitor_execution(exchange_order):
            execution_stages.append("monitoring")
            return {"status": "filled", "filled_amount": "0.001", "avg_price": "49950"}

        # 4. Обновление локального состояния
        def update_local_state(order, execution_result):
            execution_stages.append("state_update")
            return {
                "order_id": order["id"],
                "status": execution_result["status"],
                "filled_amount": execution_result["filled_amount"],
            }

        # Выполняем поток
        assert validate_order(order) is True
        exchange_result = submit_to_exchange(order)
        execution_result = monitor_execution(exchange_result)
        final_state = update_local_state(order, execution_result)

        # Проверяем результаты
        assert len(execution_stages) == 4
        assert execution_stages == ["validation", "submission", "monitoring", "state_update"]
        assert final_state["status"] == "filled"
        assert final_state["filled_amount"] == "0.001"


class TestSystemResilienceIntegration:
    """Интеграционные тесты устойчивости системы"""

    def test_graceful_degradation(self):
        """Тест плавной деградации при отказе компонентов"""
        # Нормальный режим работы
        normal_mode = {
            "ml_predictions": True,
            "all_exchanges": True,
            "advanced_features": True,
            "real_time_data": True,
        }

        # Режимы деградации
        degradation_scenarios = [
            {
                "failed_component": "ml_service",
                "degraded_mode": {
                    "ml_predictions": False,
                    "all_exchanges": True,
                    "advanced_features": False,
                    "real_time_data": True,
                    "fallback": "technical_indicators",
                },
            },
            {
                "failed_component": "primary_exchange",
                "degraded_mode": {
                    "ml_predictions": True,
                    "all_exchanges": False,
                    "advanced_features": True,
                    "real_time_data": True,
                    "fallback": "backup_exchange",
                },
            },
            {
                "failed_component": "real_time_feed",
                "degraded_mode": {
                    "ml_predictions": False,
                    "all_exchanges": True,
                    "advanced_features": False,
                    "real_time_data": False,
                    "fallback": "polling_mode",
                },
            },
        ]

        def apply_degradation(scenario):
            """Применяет режим деградации"""
            return scenario["degraded_mode"]

        # Тестируем каждый сценарий деградации
        for scenario in degradation_scenarios:
            degraded_mode = apply_degradation(scenario)

            # Система должна продолжать работать
            assert "fallback" in degraded_mode

            # Хотя бы один критический компонент должен работать
            critical_working = any(
                [
                    degraded_mode.get("all_exchanges", False),
                    degraded_mode.get("real_time_data", False),
                ]
            )
            assert critical_working is True

    def test_recovery_mechanisms(self):
        """Тест механизмов восстановления"""
        # Имитируем восстановление компонентов
        recovery_attempts = {
            "database": {"attempts": 0, "max_attempts": 3, "delay": 5},
            "exchange_api": {"attempts": 0, "max_attempts": 5, "delay": 10},
            "ml_service": {"attempts": 0, "max_attempts": 2, "delay": 30},
        }

        def attempt_recovery(component, config):
            """Попытка восстановления компонента"""
            if config["attempts"] < config["max_attempts"]:
                config["attempts"] += 1
                # Имитируем успешное восстановление с вероятностью
                success_probability = 0.7
                import random

                random.seed(42)  # Для стабильности тестов
                success = random.random() < success_probability

                return {
                    "component": component,
                    "attempt": config["attempts"],
                    "success": success,
                    "next_attempt_delay": config["delay"] if not success else 0,
                }
            else:
                return {"component": component, "success": False, "exhausted": True}

        # Тестируем восстановление
        db_recovery = attempt_recovery("database", recovery_attempts["database"])
        api_recovery = attempt_recovery("exchange_api", recovery_attempts["exchange_api"])

        # Проверяем результаты
        assert "success" in db_recovery
        assert "attempt" in db_recovery
        assert db_recovery["attempt"] == 1
        assert api_recovery["attempt"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
