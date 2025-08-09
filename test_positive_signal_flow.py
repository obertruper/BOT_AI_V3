#!/usr/bin/env python3
"""
Тест потока обработки положительного сигнала
Временно изменяет настройки ML для генерации LONG/SHORT сигналов
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from database.models.base_models import SignalType
from database.models.signal import Signal
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger("test_signal_flow")


class TestMLManager(MLManager):
    """Тестовый ML Manager с форсированными положительными сигналами."""

    def _interpret_predictions(self, outputs):
        """Переопределяем для генерации тестовых сигналов."""

        # Вызываем оригинальный метод
        result = super()._interpret_predictions(outputs)

        # Форсируем LONG сигнал для теста
        logger.warning("🧪 ТЕСТОВЫЙ РЕЖИМ: Форсируем LONG сигнал")

        result.update(
            {
                "signal_type": "LONG",
                "signal_strength": 0.85,
                "confidence": 0.75,
                "success_probability": 0.72,
                "stop_loss_pct": 0.02,  # 2%
                "take_profit_pct": 0.05,  # 5%
                "risk_level": "LOW",
                "predictions": {
                    "returns_15m": 0.002,
                    "returns_1h": 0.005,
                    "returns_4h": 0.01,
                    "returns_12h": 0.015,
                    "direction_score": 1.8,
                    "directions_by_timeframe": [2, 2, 2, 1],  # Mostly LONG
                    "direction_probabilities": [
                        [0.1, 0.2, 0.7],  # 15m: 70% LONG
                        [0.15, 0.15, 0.7],  # 1h: 70% LONG
                        [0.1, 0.1, 0.8],  # 4h: 80% LONG
                        [0.2, 0.6, 0.2],  # 12h: 60% NEUTRAL
                    ],
                },
            }
        )

        return result


async def test_signal_flow():
    """Тестирует весь поток обработки сигнала."""

    print("🧪 ТЕСТ ПОТОКА ОБРАБОТКИ ПОЛОЖИТЕЛЬНОГО СИГНАЛА\n")
    print("=" * 60)

    # 1. Инициализация
    print("\n1️⃣ Инициализация компонентов...")

    config = {
        "ml": {
            "model": {"device": "cuda"},
            "model_directory": "models/saved",
            "signal_processor": {
                "min_confidence": 0.3,  # Снижаем для теста
                "min_signal_strength": 0.1,
            },
        }
    }

    # Используем тестовый ML Manager
    ml_manager = TestMLManager(config)
    await ml_manager.initialize()

    ml_processor = MLSignalProcessor(ml_manager, config)

    print("✅ Компоненты инициализированы")

    # 2. Загрузка данных
    print("\n2️⃣ Загрузка тестовых данных...")

    symbol = "BTCUSDT"
    query = f"""
    SELECT * FROM raw_market_data
    WHERE symbol = '{symbol}'
    ORDER BY datetime DESC
    LIMIT 100
    """

    raw_data = await AsyncPGPool.fetch(query)

    if len(raw_data) < 96:
        print("❌ Недостаточно данных")
        return

    import pandas as pd

    df_data = [dict(row) for row in raw_data]
    df = pd.DataFrame(df_data)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df.sort_values("datetime")
    current_price = df["close"].iloc[-1]

    print(f"✅ Загружено {len(df)} свечей")
    print(f"   Текущая цена: ${current_price:,.2f}")

    # 3. Генерация ML предсказания
    print("\n3️⃣ Генерация ML предсказания...")

    prediction = await ml_manager.predict(df)

    print("\n📊 Предсказание:")
    print(f"   Тип: {prediction['signal_type']}")
    print(f"   Сила: {prediction['signal_strength']:.2f}")
    print(f"   Уверенность: {prediction['confidence']:.1%}")
    print(f"   Stop Loss: {prediction.get('stop_loss_pct', 0):.1%}")
    print(f"   Take Profit: {prediction.get('take_profit_pct', 0):.1%}")

    # 4. Конвертация в сигнал
    print("\n4️⃣ Конвертация в торговый сигнал...")

    # Создаем сигнал вручную для теста
    from datetime import timedelta

    signal = Signal(
        symbol=symbol,
        exchange="bybit",
        signal_type=SignalType.LONG
        if prediction["signal_type"] == "LONG"
        else SignalType.SHORT,
        strength=prediction["signal_strength"],
        confidence=prediction["confidence"],
        suggested_price=current_price,
        suggested_quantity=0.001,  # Минимальное количество для BTC
        suggested_stop_loss=current_price * (1 - prediction["stop_loss_pct"]),
        suggested_take_profit=current_price * (1 + prediction["take_profit_pct"]),
        strategy_name="PatchTST_ML",
        timeframe="15m",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
        indicators=json.dumps(
            {
                "ml_predictions": prediction.get("predictions", {}),
                "risk_level": prediction.get("risk_level", "LOW"),
                "success_probability": prediction.get("success_probability", 0.5),
            }
        ),
        extra_data=json.dumps({"test_mode": True}),
    )

    if signal:
        print("\n✅ Сигнал создан:")
        print(f"   ID: {signal.id}")
        print(f"   Символ: {signal.symbol}")
        print(f"   Тип: {signal.signal_type.value}")
        print(f"   Цена входа: ${signal.suggested_price:,.2f}")
        print(f"   Количество: {signal.suggested_quantity}")
        print(f"   Stop Loss: ${signal.suggested_stop_loss:,.2f}")
        print(f"   Take Profit: ${signal.suggested_take_profit:,.2f}")
        print(f"   Стратегия: {signal.strategy_name}")

        # 5. Сохранение в БД
        print("\n5️⃣ Сохранение сигнала в базу данных...")

        try:
            # Проверяем, есть ли SignalManager
            from trading.signals.signal_manager import SignalManager

            signal_manager = SignalManager(config)

            # Сохраняем сигнал
            saved_signal = await signal_manager.create_signal(signal)

            if saved_signal:
                print(f"✅ Сигнал сохранен в БД с ID: {saved_signal.id}")
            else:
                print("❌ Не удалось сохранить сигнал")

        except Exception as e:
            print(f"⚠️  Ошибка при сохранении: {e}")

            # Попробуем сохранить напрямую
            print("\n   Пробуем прямое сохранение в БД...")

            insert_query = """
            INSERT INTO signals (
                symbol, exchange, signal_type, strength, confidence,
                suggested_price, suggested_quantity, suggested_stop_loss,
                suggested_take_profit, strategy_name, timeframe,
                created_at, expires_at, extra_data
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
            ) RETURNING id
            """

            try:
                result = await AsyncPGPool.fetchrow(
                    insert_query,
                    signal.symbol,
                    signal.exchange,
                    signal.signal_type.value.upper(),
                    signal.strength,
                    signal.confidence,
                    signal.suggested_price,
                    signal.suggested_quantity,
                    signal.suggested_stop_loss,
                    signal.suggested_take_profit,
                    signal.strategy_name,
                    signal.timeframe,
                    signal.created_at,
                    signal.expires_at,
                    signal.extra_data,
                )
                if result:
                    print(f"✅ Сигнал сохранен напрямую с ID: {result['id']}")
                else:
                    print("❌ Не удалось сохранить сигнал")
            except Exception as db_error:
                print(f"❌ Ошибка БД: {db_error}")

        # 6. Проверка обработки сигнала
        print("\n6️⃣ Проверка обработки сигнала торговой системой...")

        # Проверяем, был ли сигнал обработан
        await asyncio.sleep(2)  # Даем время на обработку

        # Проверяем ордера
        orders_query = """
        SELECT COUNT(*) as order_count
        FROM orders
        WHERE symbol = $1
        AND created_at > NOW() - INTERVAL '1 minute'
        """

        order_count_result = await AsyncPGPool.fetchrow(orders_query, symbol)
        order_count = order_count_result["order_count"] if order_count_result else 0

        if order_count and order_count > 0:
            print(f"✅ Создано ордеров: {order_count}")

            # Детали ордера
            order_details = await AsyncPGPool.fetchrow(
                """
                SELECT * FROM orders
                WHERE symbol = $1
                ORDER BY created_at DESC
                LIMIT 1
            """,
                symbol,
            )

            if order_details:
                print("\n   Последний ордер:")
                print(f"   ID: {order_details['id']}")
                print(f"   Биржа: {order_details['exchange']}")
                print(f"   Сторона: {order_details['side']}")
                print(f"   Статус: {order_details['status']}")
                print(f"   Цена: ${order_details.get('price', 0):,.2f}")
                print(f"   Количество: {order_details['quantity']}")
        else:
            print("❌ Ордера не созданы")
            print("\n   Возможные причины:")
            print("   - Недостаточный баланс")
            print("   - Risk Manager отклонил")
            print("   - Trading Engine не активен")

    else:
        print("❌ Сигнал не создан (возможно не прошел валидацию)")

    # 7. Итоговая проверка
    print("\n7️⃣ ИТОГОВАЯ ПРОВЕРКА ПОТОКА:")
    print("=" * 60)

    checks = {
        "ML предсказание": prediction is not None
        and prediction["signal_type"] != "NEUTRAL",
        "Создание сигнала": signal is not None,
        "Сохранение в БД": False,  # Будет обновлено выше
        "Создание ордера": False,  # Будет обновлено выше
    }

    # Проверяем сохранение
    if signal:
        saved_signal = await AsyncPGPool.fetchrow(
            """
            SELECT * FROM signals
            WHERE symbol = $1
            ORDER BY created_at DESC
            LIMIT 1
        """,
            symbol,
        )

        if saved_signal:
            time_diff = datetime.utcnow() - saved_signal["created_at"].replace(
                tzinfo=None
            )
            if time_diff.total_seconds() < 60:  # Создан в последнюю минуту
                checks["Сохранение в БД"] = True

    for check, status in checks.items():
        status_str = "✅ Успешно" if status else "❌ Не выполнено"
        print(f"{check}: {status_str}")

    print("\n" + "=" * 60)

    # Возвращаем оригинальные настройки
    print("\n⚠️  Не забудьте перезапустить систему для возврата к обычным настройкам!")


if __name__ == "__main__":
    asyncio.run(test_signal_flow())
