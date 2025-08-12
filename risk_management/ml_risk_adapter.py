#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Risk Adapter - адаптер для интеграции ML-сигналов с системой управления рисками
Адаптировано из BOT_AI_V2 для BOT Trading v3
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .enhanced_calculator import EnhancedRiskCalculator, MLSignalData, RiskParameters

logger = logging.getLogger(__name__)


@dataclass
class MLSignalAdapter:
    """Адаптер для конвертации ML-сигналов в формат системы рисков"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ml_config = config.get("ml_integration", {})
        self.risk_calculator = EnhancedRiskCalculator(config)

        # Пороги для ML-сигналов
        self.thresholds = self.ml_config.get("thresholds", {})
        self.buy_model = self.ml_config.get("buy_model", {})
        self.sell_model = self.ml_config.get("sell_model", {})

        logger.info("MLSignalAdapter инициализирован")

    def convert_ml_prediction_to_signal(
        self, prediction: Dict[str, Any], symbol: str
    ) -> Optional[MLSignalData]:
        """
        Конвертирует ML-предсказание в MLSignalData

        Args:
            prediction: Словарь с ML-предсказанием
            symbol: Торговый символ

        Returns:
            MLSignalData или None если сигнал не подходит
        """
        try:
            # Извлекаем основные параметры
            signal_type = prediction.get("signal_type", "NEUTRAL")
            signal_strength = prediction.get("signal_strength", 0.5)
            confidence = prediction.get("confidence", 0.5)
            success_probability = prediction.get("success_probability", 0.5)

            # Проверяем, что это торговый сигнал
            if signal_type == "NEUTRAL":
                logger.debug(f"Нейтральный сигнал для {symbol}, пропускаем")
                return None

            # Проверяем пороги уверенности
            if not self._check_confidence_thresholds(
                signal_type, confidence, success_probability
            ):
                logger.debug(f"Сигнал {symbol} не проходит пороги уверенности")
                return None

            # Извлекаем SL/TP из предсказания
            stop_loss_pct = prediction.get("stop_loss_pct")
            take_profit_pct = prediction.get("take_profit_pct")

            # Определяем уровень риска
            risk_level = self._determine_risk_level(
                confidence, signal_strength, success_probability
            )

            # Создаем MLSignalData
            ml_signal = MLSignalData(
                signal_type=signal_type,
                signal_strength=signal_strength,
                confidence=confidence,
                success_probability=success_probability,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                risk_level=risk_level,
            )

            logger.info(
                f"Конвертирован ML-сигнал для {symbol}: "
                f"тип={signal_type}, уверенность={confidence:.3f}, "
                f"сила={signal_strength:.3f}, риск={risk_level}"
            )

            return ml_signal

        except Exception as e:
            logger.error(f"Ошибка конвертации ML-предсказания для {symbol}: {e}")
            return None

    def calculate_risk_adjusted_parameters(
        self,
        symbol: str,
        entry_price: float,
        ml_signal: MLSignalData,
        account_balance: Optional[float] = None,
        risk_profile: str = "standard",
    ) -> RiskParameters:
        """
        Рассчитывает параметры риска с учетом ML-сигнала

        Args:
            symbol: Торговый символ
            entry_price: Цена входа
            ml_signal: ML-сигнал
            account_balance: Баланс счета
            risk_profile: Профиль риска

        Returns:
            RiskParameters с рассчитанными параметрами
        """
        try:
            # Используем enhanced calculator для расчета
            risk_params = self.risk_calculator.calculate_ml_adjusted_risk_params(
                symbol=symbol,
                entry_price=entry_price,
                ml_signal=ml_signal,
                account_balance=account_balance,
                risk_profile=risk_profile,
            )

            # Дополнительная корректировка на основе типа сигнала
            risk_params = self._apply_signal_type_adjustment(risk_params, ml_signal)

            # Корректировка на основе уровня риска
            risk_params = self._apply_risk_level_adjustment(risk_params, ml_signal)

            logger.info(
                f"Risk-adjusted параметры для {symbol}: "
                f"размер={risk_params.position_size:.6f}, "
                f"SL={risk_params.stop_loss_pct:.2%}, "
                f"TP={risk_params.take_profit_pct:.2%}, "
                f"плечо={risk_params.leverage}"
            )

            return risk_params

        except Exception as e:
            logger.error(f"Ошибка расчета risk-adjusted параметров для {symbol}: {e}")
            return self._get_fallback_parameters(symbol, entry_price)

    def validate_ml_signal(self, ml_signal: MLSignalData, symbol: str) -> bool:
        """
        Валидирует ML-сигнал на соответствие требованиям

        Args:
            ml_signal: ML-сигнал для валидации
            symbol: Торговый символ

        Returns:
            True если сигнал валиден
        """
        try:
            # Проверяем базовые параметры
            if not (0 <= ml_signal.confidence <= 1):
                logger.warning(
                    f"Некорректная уверенность для {symbol}: {ml_signal.confidence}"
                )
                return False

            if not (0 <= ml_signal.signal_strength <= 1):
                logger.warning(
                    f"Некорректная сила сигнала для {symbol}: {ml_signal.signal_strength}"
                )
                return False

            if not (0 <= ml_signal.success_probability <= 1):
                logger.warning(
                    f"Некорректная вероятность успеха для {symbol}: {ml_signal.success_probability}"
                )
                return False

            # Проверяем тип сигнала
            if ml_signal.signal_type not in ["LONG", "SHORT"]:
                logger.warning(
                    f"Неподдерживаемый тип сигнала для {symbol}: {ml_signal.signal_type}"
                )
                return False

            # Проверяем пороги
            if not self._check_confidence_thresholds(
                ml_signal.signal_type,
                ml_signal.confidence,
                ml_signal.success_probability,
            ):
                return False

            # Проверяем SL/TP если есть
            if ml_signal.stop_loss_pct is not None:
                if not (0.001 <= ml_signal.stop_loss_pct <= 0.1):  # 0.1% - 10%
                    logger.warning(
                        f"Некорректный SL для {symbol}: {ml_signal.stop_loss_pct}"
                    )
                    return False

            if ml_signal.take_profit_pct is not None:
                if not (0.002 <= ml_signal.take_profit_pct <= 0.2):  # 0.2% - 20%
                    logger.warning(
                        f"Некорректный TP для {symbol}: {ml_signal.take_profit_pct}"
                    )
                    return False

            logger.debug(f"ML-сигнал для {symbol} прошел валидацию")
            return True

        except Exception as e:
            logger.error(f"Ошибка валидации ML-сигнала для {symbol}: {e}")
            return False

    def get_adaptive_sltp_config(
        self, symbol: str, entry_price: float, side: str, ml_signal: MLSignalData
    ) -> Dict[str, Any]:
        """
        Получает адаптивную конфигурацию SL/TP на основе ML-сигнала

        Args:
            symbol: Торговый символ
            entry_price: Цена входа
            side: Сторона позиции (BUY/SELL)
            ml_signal: ML-сигнал

        Returns:
            Конфигурация SL/TP
        """
        try:
            # Получаем базовые параметры SL/TP
            sltp_params = self.risk_calculator.get_adaptive_sltp_params(
                symbol=symbol, entry_price=entry_price, side=side, ml_signal=ml_signal
            )

            # Создаем конфигурацию для enhanced SLTP manager
            sltp_config = {
                "stop_loss": sltp_params["stop_loss_price"],
                "take_profit": sltp_params["take_profit_price"],
                "stop_loss_pct": sltp_params["stop_loss_pct"],
                "take_profit_pct": sltp_params["take_profit_pct"],
                # Enhanced функции
                "trailing_stop": {
                    "enabled": True,
                    "activation_percent": 1.0,
                    "step_percent": 0.5,
                    "min_distance": 0.3,
                },
                "profit_protection": {
                    "enabled": True,
                    "breakeven_percent": 0.5,
                    "breakeven_offset": 0.1,
                    "levels": [
                        {"trigger": 1.0, "lock": 0.5},
                        {"trigger": 2.0, "lock": 1.0},
                        {"trigger": 3.0, "lock": 1.5},
                    ],
                },
                "partial_tp_enabled": True,
                "partial_tp_levels": [
                    {"percent": 1.0, "close_ratio": 0.3},
                    {"percent": 2.0, "close_ratio": 0.3},
                    {"percent": 3.0, "close_ratio": 0.4},
                ],
                "partial_tp_update_sl": True,
            }

            logger.info(
                f"Adaptive SLTP config для {symbol}: "
                f"SL={sltp_config['stop_loss']:.4f}, "
                f"TP={sltp_config['take_profit']:.4f}"
            )

            return sltp_config

        except Exception as e:
            logger.error(f"Ошибка создания adaptive SLTP config для {symbol}: {e}")
            return self._get_default_sltp_config(entry_price, side)

    def _check_confidence_thresholds(
        self, signal_type: str, confidence: float, success_probability: float
    ) -> bool:
        """Проверяет пороги уверенности для сигнала"""
        try:
            if signal_type == "LONG":
                thresholds = self.thresholds
                buy_model = self.buy_model.get("standard", {})

                # Проверяем пороги для покупки
                if confidence < thresholds.get("buy_profit", 0.65):
                    return False

                if success_probability < buy_model.get("profit_probability_min", 0.50):
                    return False

            elif signal_type == "SHORT":
                thresholds = self.thresholds
                sell_model = self.sell_model.get("standard", {})

                # Проверяем пороги для продажи
                if confidence < thresholds.get("sell_profit", 0.65):
                    return False

                if success_probability < sell_model.get("profit_probability_min", 0.53):
                    return False

            return True

        except Exception as e:
            logger.error(f"Ошибка проверки порогов уверенности: {e}")
            return False

    def _determine_risk_level(
        self, confidence: float, signal_strength: float, success_probability: float
    ) -> str:
        """Определяет уровень риска на основе ML-параметров"""
        try:
            # Комбинированный скор
            combined_score = (confidence + signal_strength + success_probability) / 3

            if combined_score >= 0.8:
                return "LOW"
            elif combined_score >= 0.6:
                return "MEDIUM"
            else:
                return "HIGH"

        except Exception as e:
            logger.error(f"Ошибка определения уровня риска: {e}")
            return "MEDIUM"

    def _apply_signal_type_adjustment(
        self, risk_params: RiskParameters, ml_signal: MLSignalData
    ) -> RiskParameters:
        """Применяет корректировку на основе типа сигнала"""
        try:
            # Для шортов корректируем параметры
            if ml_signal.signal_type == "SHORT":
                # Увеличиваем SL для шортов (более консервативно)
                risk_params.stop_loss_pct *= 1.1
                # Уменьшаем TP для шортов
                risk_params.take_profit_pct *= 0.9

            return risk_params

        except Exception as e:
            logger.error(f"Ошибка применения signal type adjustment: {e}")
            return risk_params

    def _apply_risk_level_adjustment(
        self, risk_params: RiskParameters, ml_signal: MLSignalData
    ) -> RiskParameters:
        """Применяет корректировку на основе уровня риска"""
        try:
            if ml_signal.risk_level == "HIGH":
                # Уменьшаем размер позиции для высокого риска
                risk_params.position_size *= 0.7
                # Увеличиваем SL
                risk_params.stop_loss_pct *= 1.2
                # Уменьшаем плечо
                risk_params.leverage = max(1, risk_params.leverage - 1)

            elif ml_signal.risk_level == "LOW":
                # Увеличиваем размер позиции для низкого риска
                risk_params.position_size *= 1.1
                # Уменьшаем SL
                risk_params.stop_loss_pct *= 0.9
                # Увеличиваем плечо
                risk_params.leverage = min(20, risk_params.leverage + 1)

            return risk_params

        except Exception as e:
            logger.error(f"Ошибка применения risk level adjustment: {e}")
            return risk_params

    def _get_fallback_parameters(
        self, symbol: str, entry_price: float
    ) -> RiskParameters:
        """Возвращает базовые параметры при ошибке"""
        return RiskParameters(
            position_size=5.0 / entry_price,  # Минимальный размер
            stop_loss_pct=0.02,  # 2%
            take_profit_pct=0.04,  # 4%
            leverage=5,
            risk_amount=10.0,  # $10 риск
            confidence_adjusted=False,
            ml_score=None,
        )

    def _get_default_sltp_config(self, entry_price: float, side: str) -> Dict[str, Any]:
        """Возвращает базовую конфигурацию SL/TP"""
        if side == "SELL":
            sl_price = entry_price * 1.02
            tp_price = entry_price * 0.96
        else:
            sl_price = entry_price * 0.98
            tp_price = entry_price * 1.04

        return {
            "stop_loss": sl_price,
            "take_profit": tp_price,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.04,
            "trailing_stop": {"enabled": False},
            "profit_protection": {"enabled": False},
            "partial_tp_enabled": False,
        }
