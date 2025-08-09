#!/usr/bin/env python3
"""
Unified Signal Processor - единая точка обработки всех ML сигналов

Объединяет функционал из:
- ml/ml_signal_processor.py
- trading/signals/ai_signal_generator.py
- strategies/ml_strategy/ml_signal_strategy.py
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from core.exceptions import SignalProcessingError
from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from database.models.base_models import Order, OrderSide, OrderType, SignalType

logger = setup_logger("unified_signal_processor")


class UnifiedSignalProcessor:
    """
    Единый обработчик ML сигналов

    Обеспечивает полную цепочку:
    ML предсказание → Валидация → Сигнал → Ордер → Исполнение
    """

    def __init__(
        self, ml_manager=None, trading_engine=None, config: Dict[str, Any] = None
    ):
        self.ml_manager = ml_manager
        self.trading_engine = trading_engine
        self.config = config or {}

        # Статистика
        self.signals_processed = 0
        self.orders_created = 0
        self.errors_count = 0

        # Конфигурация
        self.min_confidence = self.config.get("min_confidence_threshold", 0.3)
        self.max_daily_trades = self.config.get("max_daily_trades", 100)
        self.position_size = Decimal(str(self.config.get("position_size", 0.01)))

        logger.info(
            f"UnifiedSignalProcessor инициализирован (min_confidence: {self.min_confidence})"
        )

    async def process_ml_prediction(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> Optional[Order]:
        """
        Полная обработка ML предсказания до создания ордера

        Args:
            symbol: Торговая пара
            market_data: Рыночные данные

        Returns:
            Order если создан, иначе None
        """
        try:
            # 1. Получаем ML предсказание
            prediction = await self._get_ml_prediction(symbol, market_data)
            if not prediction:
                logger.warning(f"Нет ML предсказания для {symbol}")
                return None

            logger.info(f"ML предсказание получено: {prediction}")

            # 2. Генерируем торговый сигнал
            signal = await self._generate_signal(symbol, prediction, market_data)
            if not signal:
                logger.debug(f"Сигнал не сгенерирован для {symbol}")
                return None

            # 3. Валидируем сигнал
            if not await self._validate_signal(signal):
                logger.debug(f"Сигнал не прошел валидацию: {symbol}")
                return None

            # 4. Сохраняем сигнал в БД
            await self._save_signal(signal)
            self.signals_processed += 1

            # 5. Создаем и исполняем ордер
            if signal["signal_type"] != SignalType.HOLD.value:
                order = await self._create_order_from_signal(signal)
                if order:
                    self.orders_created += 1
                    logger.info(
                        f"Ордер создан: {symbol} {order.side} {order.quantity} @ {order.price}"
                    )

                    # 6. Передаем ордер в TradingEngine
                    if self.trading_engine:
                        await self.trading_engine.execute_order(order)

                    return order

            return None

        except Exception as e:
            logger.error(f"Ошибка обработки ML предсказания для {symbol}: {e}")
            self.errors_count += 1
            raise SignalProcessingError(f"Ошибка обработки: {e}")

    async def _get_ml_prediction(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Получает предсказание от ML модели"""
        if not self.ml_manager:
            logger.warning("ML Manager не установлен")
            return None

        try:
            # Преобразуем данные для ML Manager
            import pandas as pd

            # Если есть candles, используем их
            if "candles" in market_data:
                candles = market_data["candles"]

                # Преобразуем в DataFrame
                df_data = []
                for candle in candles[:96]:  # Берем последние 96 свечей
                    df_data.append(
                        {
                            "datetime": candle["datetime"],
                            "open": float(candle["open"]),
                            "high": float(candle["high"]),
                            "low": float(candle["low"]),
                            "close": float(candle["close"]),
                            "volume": float(candle["volume"]),
                        }
                    )

                df = pd.DataFrame(df_data).sort_values("datetime")

                # Вызываем predict с DataFrame
                if hasattr(self.ml_manager, "predict"):
                    prediction = await self.ml_manager.predict(df)
                    return prediction

            # Альтернативные методы
            if hasattr(self.ml_manager, "predict_signal"):
                return await self.ml_manager.predict_signal(symbol, market_data)
            elif hasattr(self.ml_manager, "generate_prediction"):
                return await self.ml_manager.generate_prediction(symbol, market_data)
            else:
                logger.error("ML Manager не имеет методов предсказания")
                return None

        except Exception as e:
            logger.error(f"Ошибка получения ML предсказания: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def _generate_signal(
        self, symbol: str, prediction: Dict[str, Any], market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Генерирует торговый сигнал на основе ML предсказания"""
        try:
            # Извлекаем данные из предсказания
            confidence = float(prediction.get("confidence", 0.0))

            # Поддержка новой структуры от ML Manager
            signal_type_str = prediction.get("signal_type", "NEUTRAL")

            # Преобразуем строковый тип сигнала в числовое направление
            if signal_type_str == "LONG":
                direction = 0.8  # Высокое значение для LONG
            elif signal_type_str == "SHORT":
                direction = 0.2  # Низкое значение для SHORT
            else:
                direction = 0.5  # Нейтральное значение

            # Определяем тип сигнала
            if direction > 0.6 and confidence >= self.min_confidence:
                signal_type = SignalType.LONG
                strength = min((direction - 0.5) * 2, 1.0)  # Нормализуем силу
            elif direction < 0.4 and confidence >= self.min_confidence:
                signal_type = SignalType.SHORT
                strength = min((0.5 - direction) * 2, 1.0)
            else:
                signal_type = SignalType.NEUTRAL
                strength = 0.0

            # Используем signal_strength из ML если есть
            if "signal_strength" in prediction:
                strength = float(prediction["signal_strength"])

            # Формируем сигнал
            signal = {
                "symbol": symbol,
                "signal_type": signal_type.value,
                "confidence": confidence,
                "strength": strength,
                "suggested_price": float(market_data.get("current_price", 0)),
                "strategy_name": "UnifiedMLStrategy",
                "exchange": self.config.get("exchange", "bybit"),
                "created_at": datetime.now(timezone.utc),
                "extra_data": {
                    "ml_prediction": prediction,
                    "direction": direction,
                    "processor": "unified_signal_processor",
                    "stop_loss_pct": prediction.get("stop_loss_pct"),
                    "take_profit_pct": prediction.get("take_profit_pct"),
                },
            }

            logger.info(
                f"Сигнал сгенерирован: {symbol} {signal_type.value} "
                f"(направление: {direction:.3f}, уверенность: {confidence:.3f})"
            )

            return signal

        except Exception as e:
            logger.error(f"Ошибка генерации сигнала: {e}")
            return None

    async def _validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Валидация торгового сигнала"""
        try:
            # Проверка минимальной уверенности
            if signal["confidence"] < self.min_confidence:
                logger.debug(
                    f"Низкая уверенность: {signal['confidence']} < {self.min_confidence}"
                )
                return False

            # Проверка лимита дневных сделок
            today_trades = await self._get_today_trades_count()
            if today_trades >= self.max_daily_trades:
                logger.warning(f"Достигнут лимит дневных сделок: {today_trades}")
                return False

            # Проверка открытых позиций по символу
            open_positions = await self._get_open_positions(signal["symbol"])
            if open_positions > 0:
                logger.debug(f"Уже есть открытая позиция по {signal['symbol']}")
                return False

            return True

        except Exception as e:
            logger.error(f"Ошибка валидации сигнала: {e}")
            return False

    async def _save_signal(self, signal: Dict[str, Any]) -> None:
        """Сохраняет сигнал в базу данных"""
        try:
            query = """
            INSERT INTO signals
            (symbol, exchange, signal_type, strength, confidence,
             suggested_price, strategy_name, created_at, extra_data)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """

            pool = await AsyncPGPool.get_pool()
            signal_id = await pool.fetchval(
                query,
                signal["symbol"],
                signal["exchange"],
                signal["signal_type"],
                signal["strength"],
                signal["confidence"],
                signal["suggested_price"],
                signal["strategy_name"],
                signal["created_at"],
                json.dumps(signal.get("extra_data", {})),
            )

            signal["id"] = signal_id
            logger.debug(f"Сигнал сохранен в БД с ID: {signal_id}")

        except Exception as e:
            logger.error(f"Ошибка сохранения сигнала: {e}")
            raise

    async def _create_order_from_signal(
        self, signal: Dict[str, Any]
    ) -> Optional[Order]:
        """Создает ордер на основе сигнала"""
        try:
            # Определяем параметры ордера
            side = (
                OrderSide.BUY
                if signal["signal_type"] == SignalType.LONG.value
                else OrderSide.SELL
            )

            # Расчет размера позиции
            quantity = await self._calculate_position_size(
                signal["symbol"], signal["suggested_price"], signal["strength"]
            )

            if quantity <= 0:
                logger.warning(f"Недостаточный размер позиции для {signal['symbol']}")
                return None

            # Создаем ордер
            order = Order(
                exchange=signal["exchange"],
                symbol=signal["symbol"],
                order_type=OrderType.LIMIT,
                side=side,
                quantity=float(quantity),
                price=signal["suggested_price"],
                status="PENDING",
                strategy="UnifiedMLStrategy",
                metadata={
                    "signal_id": signal.get("id"),
                    "confidence": signal["confidence"],
                    "strength": signal["strength"],
                },
            )

            # Сохраняем ордер в БД
            await self._save_order(order)

            return order

        except Exception as e:
            logger.error(f"Ошибка создания ордера: {e}")
            return None

    async def _calculate_position_size(
        self, symbol: str, price: float, strength: float
    ) -> Decimal:
        """Расчет размера позиции с учетом риск-менеджмента"""
        try:
            # Базовый размер позиции
            base_size = self.position_size

            # Корректировка на основе силы сигнала
            adjusted_size = base_size * Decimal(str(strength))

            # Минимальный размер для Bybit
            min_sizes = {
                "BTCUSDT": Decimal("0.0001"),
                "ETHUSDT": Decimal("0.001"),
                "default": Decimal("0.01"),
            }

            min_size = min_sizes.get(symbol, min_sizes["default"])

            # Проверка минимального размера
            if adjusted_size < min_size:
                adjusted_size = min_size

            # Округление до допустимой точности
            return adjusted_size.quantize(Decimal("0.0001"))

        except Exception as e:
            logger.error(f"Ошибка расчета размера позиции: {e}")
            return Decimal("0")

    async def _save_order(self, order: Order) -> None:
        """Сохраняет ордер в базу данных"""
        try:
            query = """
            INSERT INTO orders
            (exchange, symbol, order_type, side, quantity, price,
             status, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            RETURNING id
            """

            pool = await AsyncPGPool.get_pool()
            order_id = await pool.fetchval(
                query,
                order.exchange,
                order.symbol,
                order.order_type.value,
                order.side.value,
                order.quantity,
                order.price,
                order.status,
                json.dumps(order.metadata) if order.metadata else None,
            )

            order.id = order_id
            logger.debug(f"Ордер сохранен в БД с ID: {order_id}")

        except Exception as e:
            logger.error(f"Ошибка сохранения ордера: {e}")
            raise

    async def _get_today_trades_count(self) -> int:
        """Получает количество сделок за сегодня"""
        try:
            pool = await AsyncPGPool.get_pool()
            count = await pool.fetchval(
                """
                SELECT COUNT(*) FROM orders
                WHERE created_at > CURRENT_DATE
            """
            )
            return count or 0
        except Exception as e:
            logger.error(f"Ошибка подсчета сделок: {e}")
            return 0

    async def _get_open_positions(self, symbol: str) -> int:
        """Получает количество открытых позиций по символу"""
        try:
            pool = await AsyncPGPool.get_pool()
            count = await pool.fetchval(
                """
                SELECT COUNT(*) FROM orders
                WHERE symbol = $1
                AND status IN ('PENDING', 'OPEN', 'PARTIALLY_FILLED')
            """,
                symbol,
            )
            return count or 0
        except Exception as e:
            logger.error(f"Ошибка проверки позиций: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику процессора"""
        return {
            "signals_processed": self.signals_processed,
            "orders_created": self.orders_created,
            "errors_count": self.errors_count,
            "success_rate": (
                (self.orders_created / self.signals_processed * 100)
                if self.signals_processed > 0
                else 0
            ),
        }
