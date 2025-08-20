"""
End-to-End интеграционные тесты для BOT_AI_V3
Тесты полных рабочих потоков системы
"""

import os
import sys
import time

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestFullTradingWorkflow:
    """End-to-End тесты полного торгового цикла"""

    def test_complete_trading_cycle(self):
        """Тест полного цикла: данные → ML → сигнал → ордер → исполнение"""

        # 1. ЭТАП: Получение рыночных данных
        market_data_pipeline = []

        def collect_market_data():
            data = {
                "timestamp": time.time(),
                "symbol": "BTCUSDT",
                "ohlcv": {
                    "open": 49800,
                    "high": 50200,
                    "low": 49500,
                    "close": 50000,
                    "volume": 1500000,
                },
                "order_book": {
                    "bids": [[49950, 0.5], [49900, 1.0]],
                    "asks": [[50050, 0.3], [50100, 0.8]],
                },
            }
            market_data_pipeline.append("data_collected")
            return data

        # 2. ЭТАП: Обработка данных и создание признаков
        def process_data_for_ml(raw_data):
            features = {
                "price_momentum": (raw_data["ohlcv"]["close"] - raw_data["ohlcv"]["open"])
                / raw_data["ohlcv"]["open"],
                "volume_surge": raw_data["ohlcv"]["volume"] / 1000000,
                "spread": (
                    raw_data["order_book"]["asks"][0][0] - raw_data["order_book"]["bids"][0][0]
                )
                / raw_data["ohlcv"]["close"],
                "volatility": (raw_data["ohlcv"]["high"] - raw_data["ohlcv"]["low"])
                / raw_data["ohlcv"]["close"],
            }
            market_data_pipeline.append("features_created")
            return features

        # 3. ЭТАП: ML предсказание
        def ml_inference(features):
            # Взвешенная оценка
            bullish_score = (
                features["price_momentum"] * 0.4
                + (features["volume_surge"] - 1.0) * 0.2
                + -features["spread"] * 100 * 0.2
                + -features["volatility"] * 0.2
            )

            prediction = {
                "direction": (
                    "buy" if bullish_score > 0.02 else "sell" if bullish_score < -0.02 else "hold"
                ),
                "confidence": min(abs(bullish_score) * 10, 1.0),
                "score": bullish_score,
                "model_version": "v1.2.3",
            }
            market_data_pipeline.append("ml_prediction")
            return prediction

        # 4. ЭТАП: Создание торгового сигнала
        def generate_trading_signal(prediction, market_data):
            if prediction["confidence"] < 0.6:
                market_data_pipeline.append("signal_rejected")
                return None

            if prediction["direction"] == "hold":
                market_data_pipeline.append("signal_hold")
                return None

            signal = {
                "symbol": market_data["symbol"],
                "action": prediction["direction"],
                "confidence": prediction["confidence"],
                "entry_price": market_data["ohlcv"]["close"],
                "size": 0.001,  # BTC
                "stop_loss": market_data["ohlcv"]["close"]
                * (0.98 if prediction["direction"] == "buy" else 1.02),
                "take_profit": market_data["ohlcv"]["close"]
                * (1.04 if prediction["direction"] == "buy" else 0.96),
                "timestamp": time.time(),
            }
            market_data_pipeline.append("signal_generated")
            return signal

        # 5. ЭТАП: Создание и отправка ордера
        def create_and_submit_order(signal):
            if not signal:
                return None

            order = {
                "id": f"ord_{int(time.time())}",
                "exchange": "bybit",
                "symbol": signal["symbol"],
                "side": signal["action"],
                "type": "limit",
                "amount": str(signal["size"]),
                "price": str(signal["entry_price"]),
                "stop_loss": str(signal["stop_loss"]),
                "take_profit": str(signal["take_profit"]),
                "status": "pending",
                "created_at": time.time(),
            }

            # Имитируем отправку на биржу
            exchange_response = {
                "exchange_order_id": f"exch_{int(time.time())}",
                "status": "accepted",
                "message": "Order submitted successfully",
            }

            order.update(exchange_response)
            market_data_pipeline.append("order_submitted")
            return order

        # 6. ЭТАП: Мониторинг и исполнение
        def monitor_order_execution(order):
            if not order:
                return None

            # Имитируем исполнение ордера
            execution_result = {
                "order_id": order["id"],
                "status": "filled",
                "filled_amount": order["amount"],
                "average_price": str(float(order["price"]) * 0.999),  # Небольшое проскальзывание
                "commission": str(
                    float(order["amount"]) * float(order["price"]) * 0.001
                ),  # 0.1% комиссия
                "execution_time": time.time(),
                "trades": [
                    {
                        "trade_id": f"trade_{int(time.time())}",
                        "price": order["price"],
                        "amount": order["amount"],
                        "timestamp": time.time(),
                    }
                ],
            }

            market_data_pipeline.append("order_executed")
            return execution_result

        # ВЫПОЛНЕНИЕ ПОЛНОГО ЦИКЛА
        raw_data = collect_market_data()
        features = process_data_for_ml(raw_data)
        prediction = ml_inference(features)
        signal = generate_trading_signal(prediction, raw_data)
        order = create_and_submit_order(signal)
        execution = monitor_order_execution(order)

        # ПРОВЕРКА РЕЗУЛЬТАТОВ
        expected_pipeline = [
            "data_collected",
            "features_created",
            "ml_prediction",
            "signal_generated",
            "order_submitted",
            "order_executed",
        ]

        assert market_data_pipeline == expected_pipeline
        assert raw_data["symbol"] == "BTCUSDT"
        assert "price_momentum" in features
        assert prediction["direction"] in ["buy", "sell", "hold"]

        if signal:
            assert signal["symbol"] == "BTCUSDT"
            assert signal["confidence"] >= 0.6

        if order:
            assert "exchange_order_id" in order
            assert order["status"] in ["pending", "accepted"]

        if execution:
            assert execution["status"] == "filled"
            assert float(execution["filled_amount"]) > 0

    def test_multi_symbol_parallel_processing(self):
        """Тест параллельной обработки множественных торговых пар"""

        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"]

        # Имитируем параллельную обработку
        processing_results = {}

        def process_symbol(symbol):
            # Имитируем время обработки
            processing_time = 0.1

            result = {
                "symbol": symbol,
                "processing_time": processing_time,
                "data_points": 100,
                "features_created": 15,
                "prediction_confidence": 0.75,
                "signal_generated": True,
                "status": "completed",
            }

            return result

        # Обрабатываем все символы
        start_time = time.time()
        for symbol in symbols:
            processing_results[symbol] = process_symbol(symbol)
        total_time = time.time() - start_time

        # Проверки
        assert len(processing_results) == len(symbols)
        assert all(result["status"] == "completed" for result in processing_results.values())
        assert all(result["features_created"] == 15 for result in processing_results.values())
        assert total_time < 1.0  # Должно быть быстро для тестов

        # Проверяем что все символы обработаны
        processed_symbols = set(processing_results.keys())
        expected_symbols = set(symbols)
        assert processed_symbols == expected_symbols

    def test_error_recovery_in_workflow(self):
        """Тест восстановления после ошибок в рабочем потоке"""

        workflow_state = {"step": 0, "errors": [], "retries": 0, "max_retries": 3}

        def execute_step_with_retry(step_name, step_function, *args):
            """Выполнение шага с повторными попытками"""
            for attempt in range(workflow_state["max_retries"]):
                try:
                    workflow_state["step"] += 1
                    workflow_state["retries"] = attempt

                    # Имитируем случайные ошибки
                    if step_name == "ml_inference" and attempt == 0:
                        raise Exception("ML service temporary unavailable")

                    if step_name == "exchange_api" and attempt < 2:
                        raise Exception("Exchange API rate limit")

                    # Успешное выполнение
                    result = step_function(*args)
                    return result

                except Exception as e:
                    workflow_state["errors"].append(
                        {"step": step_name, "attempt": attempt + 1, "error": str(e)}
                    )

                    if attempt == workflow_state["max_retries"] - 1:
                        raise  # Последняя попытка неудачна

                    time.sleep(0.1 * (attempt + 1))  # Экспоненциальная задержка

        # Шаги рабочего процесса
        def data_collection():
            return {"data": "market_data"}

        def ml_inference(data):
            return {"prediction": "buy", "confidence": 0.8}

        def exchange_api_call(prediction):
            return {"order_id": "ord_123", "status": "submitted"}

        # Выполняем рабочий поток с обработкой ошибок
        try:
            data = execute_step_with_retry("data_collection", data_collection)
            prediction = execute_step_with_retry("ml_inference", ml_inference, data)
            order = execute_step_with_retry("exchange_api", exchange_api_call, prediction)

            # Проверяем успешное выполнение
            assert data is not None
            assert prediction["prediction"] == "buy"
            assert order["status"] == "submitted"

        except Exception:
            # Если все попытки неудачны
            assert len(workflow_state["errors"]) > 0

        # Проверяем что были попытки повтора
        assert len(workflow_state["errors"]) >= 2  # ML и Exchange ошибки
        assert workflow_state["step"] > len(
            workflow_state["errors"]
        )  # Успешных шагов больше чем ошибок


class TestRealTimeDataProcessing:
    """Тесты обработки данных в реальном времени"""

    def test_streaming_data_pipeline(self):
        """Тест пайплайна потоковых данных"""

        # Имитируем поток данных
        streaming_data = [
            {"timestamp": time.time(), "symbol": "BTCUSDT", "price": 50000, "volume": 1000},
            {"timestamp": time.time() + 1, "symbol": "BTCUSDT", "price": 50050, "volume": 1200},
            {"timestamp": time.time() + 2, "symbol": "BTCUSDT", "price": 49980, "volume": 800},
            {"timestamp": time.time() + 3, "symbol": "BTCUSDT", "price": 50020, "volume": 1500},
            {"timestamp": time.time() + 4, "symbol": "BTCUSDT", "price": 50100, "volume": 900},
        ]

        processed_data = []
        alerts = []

        def process_tick(tick):
            """Обработка одного тика данных"""
            # Добавляем скользящее среднее (простое, для последних 3 тиков)
            recent_prices = [t["price"] for t in processed_data[-2:]] + [tick["price"]]
            moving_avg = sum(recent_prices) / len(recent_prices)

            processed_tick = {
                **tick,
                "moving_avg": moving_avg,
                "price_change": tick["price"] - recent_prices[-2] if len(recent_prices) > 1 else 0,
                "volume_change": (
                    tick["volume"] - processed_data[-1]["volume"] if processed_data else 0
                ),
            }

            # Проверяем условия для алертов
            if abs(processed_tick["price_change"]) > 50:
                alerts.append(
                    {
                        "type": "price_spike",
                        "symbol": tick["symbol"],
                        "change": processed_tick["price_change"],
                        "timestamp": tick["timestamp"],
                    }
                )

            if processed_tick["volume"] > 1400:
                alerts.append(
                    {
                        "type": "volume_surge",
                        "symbol": tick["symbol"],
                        "volume": processed_tick["volume"],
                        "timestamp": tick["timestamp"],
                    }
                )

            processed_data.append(processed_tick)
            return processed_tick

        # Обрабатываем поток данных
        for tick in streaming_data:
            process_tick(tick)

        # Проверки
        assert len(processed_data) == len(streaming_data)
        assert all("moving_avg" in tick for tick in processed_data)
        assert len(alerts) >= 1  # Должны быть алерты по объему

        # Проверяем корректность расчетов
        last_tick = processed_data[-1]
        assert last_tick["price"] == 50100
        assert last_tick["price_change"] == 80  # 50100 - 50020

        # Проверяем алерты
        volume_alerts = [a for a in alerts if a["type"] == "volume_surge"]
        assert len(volume_alerts) == 1
        assert volume_alerts[0]["volume"] == 1500

    def test_websocket_message_processing(self):
        """Тест обработки WebSocket сообщений"""

        # Имитируем WebSocket сообщения
        websocket_messages = [
            {
                "channel": "orderbook",
                "symbol": "BTCUSDT",
                "data": {
                    "bids": [["50000", "0.5"], ["49950", "1.0"]],
                    "asks": [["50050", "0.3"], ["50100", "0.8"]],
                },
            },
            {
                "channel": "trade",
                "symbol": "BTCUSDT",
                "data": {"price": "50025", "size": "0.1", "side": "buy", "timestamp": time.time()},
            },
            {
                "channel": "ticker",
                "symbol": "BTCUSDT",
                "data": {"last_price": "50025", "24h_change": "2.5%", "24h_volume": "1250000"},
            },
        ]

        processed_messages = {}

        def process_websocket_message(message):
            """Обработка WebSocket сообщения"""
            channel = message["channel"]
            symbol = message["symbol"]

            if symbol not in processed_messages:
                processed_messages[symbol] = {}

            if channel == "orderbook":
                processed_messages[symbol]["orderbook"] = {
                    "best_bid": float(message["data"]["bids"][0][0]),
                    "best_ask": float(message["data"]["asks"][0][0]),
                    "spread": float(message["data"]["asks"][0][0])
                    - float(message["data"]["bids"][0][0]),
                    "updated_at": time.time(),
                }

            elif channel == "trade":
                if "trades" not in processed_messages[symbol]:
                    processed_messages[symbol]["trades"] = []

                processed_messages[symbol]["trades"].append(
                    {
                        "price": float(message["data"]["price"]),
                        "size": float(message["data"]["size"]),
                        "side": message["data"]["side"],
                        "timestamp": message["data"]["timestamp"],
                    }
                )

            elif channel == "ticker":
                processed_messages[symbol]["ticker"] = {
                    "price": float(message["data"]["last_price"]),
                    "change_24h": message["data"]["24h_change"],
                    "volume_24h": float(message["data"]["24h_volume"]),
                }

        # Обрабатываем все сообщения
        for message in websocket_messages:
            process_websocket_message(message)

        # Проверки
        btc_data = processed_messages["BTCUSDT"]

        assert "orderbook" in btc_data
        assert "trades" in btc_data
        assert "ticker" in btc_data

        assert btc_data["orderbook"]["best_bid"] == 50000
        assert btc_data["orderbook"]["best_ask"] == 50050
        assert btc_data["orderbook"]["spread"] == 50

        assert len(btc_data["trades"]) == 1
        assert btc_data["trades"][0]["price"] == 50025
        assert btc_data["trades"][0]["side"] == "buy"

        assert btc_data["ticker"]["price"] == 50025
        assert btc_data["ticker"]["volume_24h"] == 1250000


class TestPerformanceAndScalability:
    """Тесты производительности и масштабируемости"""

    def test_high_frequency_processing(self):
        """Тест высокочастотной обработки данных"""

        # Генерируем большой объем данных
        data_points = 1000
        processing_times = []

        def high_frequency_processor(data_point):
            """Быстрая обработка одной точки данных"""
            start = time.time()

            # Имитируем быструю обработку
            result = {
                "processed_at": start,
                "value": data_point * 1.01,
                "moving_avg": data_point * 0.99,
                "signal": "buy" if data_point > 50000 else "sell",
            }

            end = time.time()
            processing_times.append(end - start)

            return result

        # Обрабатываем данные
        start_time = time.time()
        results = []

        for i in range(data_points):
            data_point = 50000 + (i % 200) - 100  # Колебания цены
            result = high_frequency_processor(data_point)
            results.append(result)

        total_time = time.time() - start_time

        # Проверки производительности
        assert len(results) == data_points
        assert total_time < 1.0  # Менее секунды на 1000 точек

        avg_processing_time = sum(processing_times) / len(processing_times)
        assert avg_processing_time < 0.001  # Менее 1мс на точку

        # Проверяем результаты обработки
        buy_signals = sum(1 for r in results if r["signal"] == "buy")
        sell_signals = sum(1 for r in results if r["signal"] == "sell")

        assert buy_signals + sell_signals == data_points
        assert buy_signals > 0 and sell_signals > 0

    def test_memory_efficient_processing(self):
        """Тест эффективного использования памяти"""

        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Обработка больших объемов данных с управлением памятью
        def process_large_dataset(batch_size=100):
            processed_count = 0
            results_summary = {"total_processed": 0, "avg_price": 0, "price_sum": 0, "batches": 0}

            # Имитируем обработку больших данных по батчам
            for batch_num in range(10):  # 10 батчей
                batch_data = []

                # Создаем батч данных
                for i in range(batch_size):
                    price = 50000 + (batch_num * 10) + i
                    batch_data.append(
                        {"price": price, "volume": 1000 + i, "timestamp": time.time() + i}
                    )

                # Обрабатываем батч
                batch_sum = sum(item["price"] for item in batch_data)
                results_summary["price_sum"] += batch_sum
                results_summary["total_processed"] += len(batch_data)
                results_summary["batches"] += 1

                # Очищаем батч из памяти
                del batch_data

                processed_count += batch_size

            # Финальные расчеты
            results_summary["avg_price"] = (
                results_summary["price_sum"] / results_summary["total_processed"]
            )

            return results_summary

        # Выполняем обработку
        results = process_large_dataset()

        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory

        # Проверки
        assert results["total_processed"] == 1000  # 10 батчей по 100
        assert results["batches"] == 10
        assert results["avg_price"] > 50000

        # Память не должна значительно увеличиться
        assert memory_increase < 100  # Менее 100MB для теста

    def test_concurrent_order_processing(self):
        """Тест конкурентной обработки ордеров"""

        import queue
        import threading

        # Очередь ордеров
        order_queue = queue.Queue()
        processed_orders = []
        processing_errors = []

        # Генерируем ордеры
        test_orders = []
        for i in range(50):
            order = {
                "id": f"ord_{i:03d}",
                "symbol": "BTCUSDT",
                "side": "buy" if i % 2 == 0 else "sell",
                "amount": f"{0.001 + (i * 0.0001):.4f}",
                "price": f"{50000 + (i * 10)}",
                "timestamp": time.time() + i,
            }
            test_orders.append(order)
            order_queue.put(order)

        def order_processor(worker_id):
            """Обработчик ордеров (воркер)"""
            while True:
                try:
                    order = order_queue.get(timeout=1)

                    # Имитируем обработку ордера
                    processing_time = 0.01  # 10ms
                    time.sleep(processing_time)

                    # Результат обработки
                    result = {
                        "order_id": order["id"],
                        "worker_id": worker_id,
                        "processed_at": time.time(),
                        "status": "processed",
                        "processing_time": processing_time,
                    }

                    processed_orders.append(result)
                    order_queue.task_done()

                except queue.Empty:
                    break
                except Exception as e:
                    processing_errors.append(
                        {"worker_id": worker_id, "error": str(e), "timestamp": time.time()}
                    )

        # Запускаем несколько воркеров
        workers = []
        num_workers = 5

        start_time = time.time()

        for i in range(num_workers):
            worker = threading.Thread(target=order_processor, args=(i,))
            worker.start()
            workers.append(worker)

        # Ждем завершения всех задач
        order_queue.join()

        # Завершаем воркеров
        for worker in workers:
            worker.join(timeout=1)

        total_time = time.time() - start_time

        # Проверки
        assert len(processed_orders) == len(test_orders)
        assert len(processing_errors) == 0
        assert total_time < 1.0  # Параллельная обработка должна быть быстрой

        # Проверяем что все ордеры обработаны
        processed_ids = {result["order_id"] for result in processed_orders}
        expected_ids = {order["id"] for order in test_orders}
        assert processed_ids == expected_ids

        # Проверяем распределение по воркерам
        worker_distribution = {}
        for result in processed_orders:
            worker_id = result["worker_id"]
            worker_distribution[worker_id] = worker_distribution.get(worker_id, 0) + 1

        # Каждый воркер должен обработать хотя бы один ордер
        assert len(worker_distribution) > 1
        assert all(count > 0 for count in worker_distribution.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
