#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML торговая стратегия на основе UnifiedPatchTST модели
Использует предсказания нейронной сети для генерации торговых сигналов
"""

import logging
import pickle
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler

from database.models import Signal, SignalType
from ml.logic.feature_engineering import FeatureConfig, FeatureEngineer
from ml.logic.patchtst_model import UnifiedPatchTSTForTrading
from strategies.base.base_strategy import BaseStrategy


class PatchTSTStrategy(BaseStrategy):
    """
    ML стратегия на основе PatchTST модели

    Использует нейронную сеть для предсказания:
    - Направления движения цены (LONG/SHORT/FLAT)
    - Вероятности достижения уровней прибыли
    - Метрик риска для управления позициями
    """

    def __init__(
        self,
        name: str = "PatchTST_ML",
        symbol: str = "BTC/USDT",
        exchange: str = "binance",
        timeframe: str = "15m",
        parameters: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Инициализация ML стратегии

        Args:
            name: Имя стратегии
            symbol: Торговый символ
            exchange: Биржа
            timeframe: Таймфрейм (должен быть 15m для модели)
            parameters: Параметры стратегии
            logger: Логгер
        """
        # Инициализация базового класса
        super().__init__(name, symbol, exchange, timeframe, parameters, logger)

        # Проверка таймфрейма
        if timeframe != "15m":
            self.logger.warning(
                f"PatchTST модель обучена на 15m данных, но указан {timeframe}. "
                "Рекомендуется использовать 15m таймфрейм"
            )

        # Пути к моделям
        self.model_path = self.parameters.get("model_path", "models/patchtst/model.pth")
        self.scaler_path = self.parameters.get(
            "scaler_path", "models/patchtst/scaler.pkl"
        )
        self.config_path = self.parameters.get(
            "config_path", "models/patchtst/config.pkl"
        )

        # Параметры торговли
        self.min_confidence = self.parameters.get("min_confidence", 0.6)
        self.min_profit_probability = self.parameters.get(
            "min_profit_probability", 0.65
        )
        self.max_risk_threshold = self.parameters.get("max_risk_threshold", 0.03)  # 3%
        self.position_sizing_mode = self.parameters.get("position_sizing_mode", "kelly")

        # Параметры для разных таймфреймов предсказаний
        self.timeframe_weights = self.parameters.get(
            "timeframe_weights", {"15m": 0.3, "1h": 0.3, "4h": 0.3, "12h": 0.1}
        )

        # ML компоненты
        self.model: Optional[UnifiedPatchTSTForTrading] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_engineer: Optional[FeatureEngineer] = None
        self.model_config: Optional[Dict] = None

        # Буфер для накопления данных
        self.price_buffer = []
        self.min_buffer_size = 96  # Минимум свечей для предсказания

        # Статистика предсказаний
        self.prediction_stats = {
            "total_predictions": 0,
            "correct_directions": 0,
            "profitable_longs": 0,
            "profitable_shorts": 0,
            "avg_confidence": 0.0,
        }

        # Устройство для вычислений
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    async def on_start(self):
        """Инициализация при запуске стратегии"""
        await self._load_models()
        self.logger.info(
            f"PatchTST стратегия инициализирована на устройстве: {self.device}"
        )

    async def on_stop(self):
        """Очистка при остановке стратегии"""
        # Освобождаем память GPU если используется
        if self.model is not None and self.device.type == "cuda":
            del self.model
            torch.cuda.empty_cache()

        self.logger.info("PatchTST стратегия остановлена")

    async def _load_models(self):
        """Загрузка модели и компонентов"""
        try:
            # Загрузка конфигурации
            with open(self.config_path, "rb") as f:
                self.model_config = pickle.load(f)

            # Загрузка scaler
            with open(self.scaler_path, "rb") as f:
                self.scaler = pickle.load(f)

            # Создание и загрузка модели
            self.model = UnifiedPatchTSTForTrading(self.model_config)

            # Загрузка весов модели
            checkpoint = torch.load(self.model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                self.model.load_state_dict(checkpoint["model_state_dict"])
            else:
                self.model.load_state_dict(checkpoint)

            self.model.to(self.device)
            self.model.eval()  # Переводим в режим инференса

            # Создание feature engineer
            feature_config = FeatureConfig()  # Можно загрузить из конфига
            self.feature_engineer = FeatureEngineer(feature_config)

            self.logger.info("Модели успешно загружены")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки моделей: {e}")
            raise

    def get_required_indicators(self) -> List[str]:
        """Список необходимых индикаторов"""
        # PatchTST использует свой feature engineering
        return []

    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Анализ рыночных данных с помощью ML модели

        Args:
            market_data: Рыночные данные

        Returns:
            Торговый сигнал или None
        """
        if not self._is_active or self.model is None:
            return None

        try:
            # Обновляем буфер данных
            self._update_price_buffer(market_data)

            # Проверяем достаточно ли данных
            if len(self.price_buffer) < self.min_buffer_size:
                return None

            # Подготовка данных для модели
            features_df = self._prepare_features()
            if features_df is None or len(features_df) < self.min_buffer_size:
                return None

            # Получаем предсказания модели
            predictions = await self._get_model_predictions(features_df)
            if predictions is None:
                return None

            # Анализируем предсказания и генерируем сигнал
            signal = self._analyze_predictions(predictions, market_data)

            # Обновляем статистику
            if signal:
                self.prediction_stats["total_predictions"] += 1

            return signal

        except Exception as e:
            self.logger.error(f"Ошибка в analyze: {e}", exc_info=True)
            return None

    def _update_price_buffer(self, market_data: Dict[str, Any]):
        """Обновление буфера ценовых данных"""
        if "candles" not in market_data:
            return

        candles = market_data["candles"]
        if not candles:
            return

        # Добавляем новые свечи в буфер
        for candle in candles[-1:]:  # Берем только последнюю свечу
            self.price_buffer.append(
                {
                    "datetime": candle.get("timestamp", datetime.utcnow()),
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": float(candle["close"]),
                    "volume": float(candle["volume"]),
                    "symbol": self.symbol,
                }
            )

        # Ограничиваем размер буфера
        max_buffer_size = self.min_buffer_size + 100  # Запас для индикаторов
        if len(self.price_buffer) > max_buffer_size:
            self.price_buffer = self.price_buffer[-max_buffer_size:]

    def _prepare_features(self) -> Optional[pd.DataFrame]:
        """Подготовка признаков для модели"""
        try:
            # Создаем DataFrame из буфера
            df = pd.DataFrame(self.price_buffer)

            # Проверяем достаточность данных
            if len(df) < self.min_buffer_size:
                return None

            # Создаем признаки
            df = self.feature_engineer.create_features(df)

            # Получаем только нужные признаки
            feature_names = self.feature_engineer.get_feature_names()

            # Проверяем наличие всех признаков
            missing_features = set(feature_names) - set(df.columns)
            if missing_features:
                self.logger.warning(f"Отсутствуют признаки: {missing_features}")
                return None

            # Берем последние min_buffer_size строк
            features_df = df[feature_names].iloc[-self.min_buffer_size :]

            # Проверяем на NaN
            if features_df.isna().any().any():
                # Заполняем пропуски
                features_df = features_df.fillna(method="ffill").fillna(0)

            return features_df

        except Exception as e:
            self.logger.error(f"Ошибка подготовки признаков: {e}")
            return None

    async def _get_model_predictions(
        self, features_df: pd.DataFrame
    ) -> Optional[np.ndarray]:
        """Получение предсказаний от модели"""
        try:
            # Преобразуем в numpy массив
            features = features_df.values

            # Нормализация данных
            features_scaled = self.scaler.transform(features)

            # Преобразуем в тензор
            features_tensor = torch.FloatTensor(features_scaled).unsqueeze(
                0
            )  # (1, seq_len, features)
            features_tensor = features_tensor.to(self.device)

            # Предсказание
            with torch.no_grad():
                outputs = self.model(features_tensor)
                predictions = outputs.cpu().numpy()[0]  # (20,)

            return predictions

        except Exception as e:
            self.logger.error(f"Ошибка получения предсказаний: {e}")
            return None

    def _analyze_predictions(
        self, predictions: np.ndarray, market_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """
        Анализ предсказаний модели и генерация торгового сигнала

        Структура predictions (20 выходов):
        - 0-3: future returns для 15m, 1h, 4h, 12h
        - 4-7: directions (0=LONG, 1=SHORT, 2=FLAT) для 15m, 1h, 4h, 12h
        - 8-11: long level probabilities
        - 12-15: short level probabilities
        - 16-19: risk metrics (drawdown/rally)
        """
        try:
            # Извлекаем компоненты предсказаний
            future_returns = predictions[0:4]
            directions = predictions[4:8]
            long_probs = 1 / (
                1 + np.exp(-predictions[8:12])
            )  # Sigmoid для вероятностей
            short_probs = 1 / (
                1 + np.exp(-predictions[12:16])
            )  # Sigmoid для вероятностей
            risk_metrics = predictions[16:20]

            # Взвешенное голосование по направлениям
            weights = np.array(
                [
                    self.timeframe_weights.get("15m", 0.25),
                    self.timeframe_weights.get("1h", 0.25),
                    self.timeframe_weights.get("4h", 0.25),
                    self.timeframe_weights.get("12h", 0.25),
                ]
            )

            # Подсчет голосов для каждого направления
            long_votes = np.sum(weights[directions == 0])
            short_votes = np.sum(weights[directions == 1])
            flat_votes = np.sum(weights[directions == 2])

            # Определяем основное направление
            if long_votes > short_votes and long_votes > flat_votes:
                primary_direction = "LONG"
                direction_confidence = long_votes
                profit_probs = long_probs
                risk_values = risk_metrics[[0, 2]]  # max_drawdown для long позиций
            elif short_votes > long_votes and short_votes > flat_votes:
                primary_direction = "SHORT"
                direction_confidence = short_votes
                profit_probs = short_probs
                risk_values = risk_metrics[[1, 3]]  # max_rally для short позиций
            else:
                # Нет четкого направления
                return None

            # Проверяем минимальную уверенность
            if direction_confidence < self.min_confidence:
                self.logger.debug(
                    f"Низкая уверенность в направлении: {direction_confidence:.2f} < {self.min_confidence}"
                )
                return None

            # Анализ вероятностей прибыли
            avg_profit_prob = np.mean(profit_probs)
            max_profit_prob = np.max(profit_probs)

            if avg_profit_prob < self.min_profit_probability:
                self.logger.debug(
                    f"Низкая вероятность прибыли: {avg_profit_prob:.2f} < {self.min_profit_probability}"
                )
                return None

            # Анализ рисков
            max_risk = np.max(np.abs(risk_values))
            if max_risk > self.max_risk_threshold:
                self.logger.debug(
                    f"Высокий риск: {max_risk:.2%} > {self.max_risk_threshold:.2%}"
                )
                return None

            # Расчет силы сигнала
            signal_strength = self._calculate_signal_strength(
                direction_confidence, avg_profit_prob, max_risk, future_returns
            )

            # Расчет целевых уровней
            current_price = float(market_data["candles"][-1]["close"])
            stop_loss, take_profit = self._calculate_levels(
                primary_direction, current_price, risk_values, profit_probs
            )

            # Создание сигнала
            signal = Signal(
                symbol=self.symbol,
                exchange=self.exchange,
                signal_type=SignalType.LONG
                if primary_direction == "LONG"
                else SignalType.SHORT,
                strength=float(signal_strength),
                confidence=float(direction_confidence),
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "model": "PatchTST",
                    "future_returns": future_returns.tolist(),
                    "directions": directions.tolist(),
                    "profit_probabilities": {
                        "1pct_4h": float(profit_probs[0]),
                        "2pct_4h": float(profit_probs[1]),
                        "3pct_12h": float(profit_probs[2]),
                        "5pct_12h": float(profit_probs[3]),
                    },
                    "risk_metrics": {
                        "max_drawdown_1h": float(risk_metrics[0]),
                        "max_rally_1h": float(risk_metrics[1]),
                        "max_drawdown_4h": float(risk_metrics[2]),
                        "max_rally_4h": float(risk_metrics[3]),
                    },
                    "votes": {
                        "long": float(long_votes),
                        "short": float(short_votes),
                        "flat": float(flat_votes),
                    },
                },
                created_at=datetime.utcnow(),
            )

            self.logger.info(
                f"Сгенерирован ML сигнал: {primary_direction} с уверенностью {direction_confidence:.2f}, "
                f"вероятность прибыли: {avg_profit_prob:.2f}, сила: {signal_strength:.2f}"
            )

            return signal

        except Exception as e:
            self.logger.error(f"Ошибка анализа предсказаний: {e}")
            return None

    def _calculate_signal_strength(
        self,
        direction_confidence: float,
        profit_probability: float,
        risk_level: float,
        future_returns: np.ndarray,
    ) -> float:
        """Расчет силы сигнала на основе всех факторов"""
        # Нормализуем компоненты
        confidence_score = direction_confidence  # Уже от 0 до 1
        profit_score = profit_probability  # Уже от 0 до 1
        risk_score = 1.0 - min(risk_level / self.max_risk_threshold, 1.0)

        # Средний ожидаемый возврат
        avg_return = np.mean(np.abs(future_returns))
        return_score = min(avg_return / 0.05, 1.0)  # Нормализуем к 5%

        # Взвешенная комбинация
        weights = {"confidence": 0.3, "profit": 0.3, "risk": 0.2, "return": 0.2}

        signal_strength = (
            weights["confidence"] * confidence_score
            + weights["profit"] * profit_score
            + weights["risk"] * risk_score
            + weights["return"] * return_score
        )

        return float(np.clip(signal_strength, 0.0, 1.0))

    def _calculate_levels(
        self,
        direction: str,
        current_price: float,
        risk_values: np.ndarray,
        profit_probs: np.ndarray,
    ) -> Tuple[float, float]:
        """Расчет уровней stop-loss и take-profit"""
        # Базовый риск на основе предсказаний модели
        base_risk = np.mean(np.abs(risk_values))

        # Адаптивный stop-loss
        risk_multiplier = self.parameters.get("risk_multiplier", 1.5)
        if direction == "LONG":
            stop_loss = current_price * (1 - base_risk * risk_multiplier)
        else:
            stop_loss = current_price * (1 + base_risk * risk_multiplier)

        # Take-profit на основе вероятностей достижения уровней
        # Выбираем уровень с наибольшей вероятностью
        profit_levels = [0.01, 0.02, 0.03, 0.05]  # 1%, 2%, 3%, 5%
        best_level_idx = np.argmax(profit_probs)
        target_profit = profit_levels[best_level_idx]

        # Корректируем на основе risk-reward ratio
        min_rr_ratio = self.parameters.get("min_risk_reward_ratio", 2.0)
        risk_distance = abs(current_price - stop_loss) / current_price

        if target_profit < risk_distance * min_rr_ratio:
            target_profit = risk_distance * min_rr_ratio

        if direction == "LONG":
            take_profit = current_price * (1 + target_profit)
        else:
            take_profit = current_price * (1 - target_profit)

        return float(stop_loss), float(take_profit)

    async def calculate_position_size(
        self, signal: Signal, account_balance: Decimal
    ) -> Decimal:
        """
        Расчет размера позиции на основе Kelly Criterion или фиксированного риска

        Args:
            signal: Торговый сигнал
            account_balance: Доступный баланс

        Returns:
            Размер позиции
        """
        if self.position_sizing_mode == "kelly":
            # Kelly Criterion с учетом вероятности успеха
            metadata = signal.metadata or {}
            profit_probs = metadata.get("profit_probabilities", {})

            # Средняя вероятность прибыли
            avg_win_prob = np.mean(list(profit_probs.values())) if profit_probs else 0.5

            # Ожидаемый выигрыш/проигрыш
            current_price = (
                float(self._price_history[-1]["close"]) if self._price_history else 1.0
            )

            if signal.take_profit and signal.stop_loss:
                win_amount = abs(signal.take_profit - current_price) / current_price
                loss_amount = abs(current_price - signal.stop_loss) / current_price

                # Kelly %
                if loss_amount > 0:
                    kelly_pct = (
                        avg_win_prob * win_amount - (1 - avg_win_prob) * loss_amount
                    ) / win_amount
                    kelly_pct = max(0, min(kelly_pct, 0.25))  # Ограничиваем 25%
                else:
                    kelly_pct = 0.02  # 2% по умолчанию
            else:
                kelly_pct = 0.02

            # Применяем коэффициент безопасности
            safety_factor = self.parameters.get("kelly_safety_factor", 0.25)
            position_pct = kelly_pct * safety_factor

        else:
            # Фиксированный процент риска
            risk_pct = self.parameters.get("fixed_risk_pct", 0.02)  # 2% по умолчанию
            position_pct = risk_pct

        # Корректировка на основе силы сигнала
        position_pct *= float(signal.strength)

        # Минимальный и максимальный размер позиции
        min_position_pct = self.parameters.get("min_position_pct", 0.01)  # 1%
        max_position_pct = self.parameters.get("max_position_pct", 0.1)  # 10%

        position_pct = max(min_position_pct, min(position_pct, max_position_pct))

        # Расчет размера позиции
        position_size = account_balance * Decimal(str(position_pct))

        self.logger.info(
            f"Размер позиции: {position_size:.2f} ({position_pct:.1%} от баланса), "
            f"режим: {self.position_sizing_mode}"
        )

        return position_size

    def get_metrics(self) -> Dict[str, Any]:
        """Получить метрики производительности стратегии"""
        base_metrics = super().get_metrics()

        # Добавляем ML-специфичные метрики
        ml_metrics = {
            "prediction_accuracy": (
                self.prediction_stats["correct_directions"]
                / max(self.prediction_stats["total_predictions"], 1)
            ),
            "avg_prediction_confidence": self.prediction_stats["avg_confidence"],
            "total_ml_predictions": self.prediction_stats["total_predictions"],
            "model_device": str(self.device),
            "buffer_size": len(self.price_buffer),
        }

        return {**base_metrics, **ml_metrics}
