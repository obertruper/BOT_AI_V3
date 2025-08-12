#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Risk Calculator с ML-интеграцией
Адаптировано из BOT_AI_V2 для BOT Trading v3
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RiskParameters:
    """Параметры риска для позиции"""

    position_size: float
    stop_loss_pct: float
    take_profit_pct: float
    leverage: int
    risk_amount: float
    confidence_adjusted: bool = False
    ml_score: Optional[float] = None


@dataclass
class MLSignalData:
    """Данные ML-сигнала"""

    signal_type: str  # LONG, SHORT, NEUTRAL
    signal_strength: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    success_probability: float  # 0.0 - 1.0
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH


class EnhancedRiskCalculator:
    """Улучшенный калькулятор рисков с ML-интеграцией"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_config = config.get("risk_management", {})
        self.ml_config = config.get("ml_integration", {})

        # Основные параметры риска
        self.risk_per_trade = Decimal(str(self.risk_config.get("risk_per_trade", 0.02)))
        self.fixed_risk_balance = Decimal(
            str(self.risk_config.get("fixed_risk_balance", 500))
        )
        self.max_leverage = self.risk_config.get("max_leverage", 20)
        self.min_notional = self.risk_config.get("min_notional", 5.0)

        # Профили риска
        self.risk_profiles = self.risk_config.get("risk_profiles", {})

        # Категории активов
        self.asset_categories = self.risk_config.get("asset_categories", {})

        logger.info(
            f"EnhancedRiskCalculator инициализирован с риском {self.risk_per_trade}% на сделку"
        )

    def calculate_ml_adjusted_risk_params(
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
            ml_signal: Данные ML-сигнала
            account_balance: Баланс счета (опционально)
            risk_profile: Профиль риска (standard, conservative, very_conservative)

        Returns:
            RiskParameters с рассчитанными параметрами
        """
        try:
            # Базовые параметры
            base_risk_multiplier = self._get_risk_multiplier(risk_profile)
            asset_risk_multiplier = self._get_asset_risk_multiplier(symbol)

            # Корректировка на основе ML-скоринга
            ml_adjustment = self._calculate_ml_adjustment(ml_signal)

            # Итоговый множитель риска
            total_risk_multiplier = (
                base_risk_multiplier * asset_risk_multiplier * ml_adjustment
            )

            # Расчет размера позиции
            position_size = self._calculate_position_size(
                entry_price, total_risk_multiplier, account_balance
            )

            # Расчет стоп-лосса и тейк-профита
            stop_loss_pct, take_profit_pct = self._calculate_sltp_levels(
                ml_signal, symbol, entry_price
            )

            # Расчет плеча
            leverage = self._calculate_leverage(symbol, ml_signal)

            # Расчет суммы риска
            risk_amount = float(
                self.fixed_risk_balance
                * self.risk_per_trade
                * Decimal(str(total_risk_multiplier))
            )

            logger.info(
                f"ML-adjusted risk params для {symbol}: "
                f"size={position_size:.6f}, sl={stop_loss_pct:.2f}%, "
                f"tp={take_profit_pct:.2f}%, leverage={leverage}, "
                f"ml_adjustment={ml_adjustment:.3f}"
            )

            return RiskParameters(
                position_size=position_size,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                leverage=leverage,
                risk_amount=risk_amount,
                confidence_adjusted=True,
                ml_score=ml_signal.confidence,
            )

        except Exception as e:
            logger.error(f"Ошибка расчета ML-adjusted risk params для {symbol}: {e}")
            # Возвращаем базовые параметры при ошибке
            return self._get_fallback_parameters(symbol, entry_price)

    def calculate_position_size_by_risk(
        self,
        entry_price: float,
        stop_loss_price: float,
        risk_percentage: Optional[float] = None,
        account_balance: Optional[float] = None,
    ) -> float:
        """
        Рассчитывает размер позиции на основе риска (формула из V2)

        Args:
            entry_price: Цена входа
            stop_loss_price: Цена стоп-лосса
            risk_percentage: Процент риска (опционально)
            account_balance: Баланс счета (опционально)

        Returns:
            Размер позиции
        """
        try:
            if risk_percentage is None:
                risk_percentage = float(self.risk_per_trade)

            # Используем фиксированный баланс или реальный
            balance = (
                account_balance if account_balance else float(self.fixed_risk_balance)
            )

            # Риск в долларах
            risk_amount = balance * risk_percentage

            # Риск на единицу
            risk_per_unit = abs(entry_price - stop_loss_price)

            if risk_per_unit == 0:
                logger.warning("Риск на единицу равен 0, используем минимальный размер")
                return self.min_notional / entry_price

            # Размер позиции (формула из V2)
            position_size = risk_amount / risk_per_unit

            # Проверяем минимальный размер
            min_size = self.min_notional / entry_price
            if position_size < min_size:
                logger.warning(
                    f"Размер позиции {position_size} меньше минимального {min_size}"
                )
                position_size = min_size

            logger.info(
                f"Position size для цены {entry_price}: {position_size:.6f} "
                f"(риск: {risk_percentage:.1%}, сумма: ${risk_amount:.2f})"
            )

            return position_size

        except Exception as e:
            logger.error(f"Ошибка расчета position size: {e}")
            return 0.0

    def get_adaptive_sltp_params(
        self,
        symbol: str,
        entry_price: float,
        side: str,
        ml_signal: Optional[MLSignalData] = None,
        volatility: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Получает адаптивные параметры SL/TP на основе ML и волатильности

        Args:
            symbol: Торговый символ
            entry_price: Цена входа
            side: Сторона позиции (BUY/SELL)
            ml_signal: ML-сигнал (опционально)
            volatility: Волатильность (опционально)

        Returns:
            Словарь с параметрами SL/TP
        """
        try:
            # Базовые параметры из конфигурации
            base_sl_pct = 0.02  # 2% по умолчанию
            base_tp_pct = 0.04  # 4% по умолчанию

            # Корректировка на основе ML
            if ml_signal:
                if ml_signal.stop_loss_pct is not None:
                    base_sl_pct = ml_signal.stop_loss_pct
                if ml_signal.take_profit_pct is not None:
                    base_tp_pct = ml_signal.take_profit_pct

                # Дополнительная корректировка на основе уверенности
                confidence_factor = ml_signal.confidence
                if confidence_factor > 0.8:
                    base_sl_pct *= 0.8  # Уменьшаем SL при высокой уверенности
                    base_tp_pct *= 1.2  # Увеличиваем TP
                elif confidence_factor < 0.6:
                    base_sl_pct *= 1.2  # Увеличиваем SL при низкой уверенности
                    base_tp_pct *= 0.8  # Уменьшаем TP

            # Корректировка на основе волатильности
            if volatility:
                volatility_factor = min(
                    max(volatility / 0.02, 0.5), 2.0
                )  # Ограничиваем 0.5-2.0
                base_sl_pct *= volatility_factor
                base_tp_pct *= volatility_factor

            # Корректировка на основе типа актива
            asset_category = self._get_asset_category(symbol)
            if asset_category == "meme_coins":
                base_sl_pct *= 1.2  # Увеличиваем SL для мемкоинов
                base_tp_pct *= 1.1  # Увеличиваем TP

            # Корректировка на основе стороны позиции
            if side == "SELL":
                # Для шортов инвертируем логику
                sl_price = entry_price * (1 + base_sl_pct)
                tp_price = entry_price * (1 - base_tp_pct)
            else:
                sl_price = entry_price * (1 - base_sl_pct)
                tp_price = entry_price * (1 + base_tp_pct)

            logger.info(
                f"Adaptive SL/TP для {symbol} {side}: "
                f"SL={sl_price:.4f} ({base_sl_pct:.2%}), "
                f"TP={tp_price:.4f} ({base_tp_pct:.2%})"
            )

            return {
                "stop_loss_price": sl_price,
                "take_profit_price": tp_price,
                "stop_loss_pct": base_sl_pct,
                "take_profit_pct": base_tp_pct,
            }

        except Exception as e:
            logger.error(f"Ошибка расчета adaptive SL/TP для {symbol}: {e}")
            return {
                "stop_loss_price": entry_price * 0.98,
                "take_profit_price": entry_price * 1.04,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.04,
            }

    def apply_volatility_adjustment(
        self, base_params: RiskParameters, volatility: float, atr_period: int = 14
    ) -> RiskParameters:
        """
        Применяет корректировку на основе волатильности

        Args:
            base_params: Базовые параметры риска
            volatility: Волатильность (ATR или стандартное отклонение)
            atr_period: Период ATR

        Returns:
            Скорректированные параметры риска
        """
        try:
            # Получаем настройки волатильности
            vol_config = self.config.get("enhanced_sltp", {}).get(
                "volatility_adjustment", {}
            )

            if not vol_config.get("enabled", False):
                return base_params

            sl_multiplier = vol_config.get("sl_multiplier", 1.5)
            tp_multiplier = vol_config.get("tp_multiplier", 2.5)

            # Нормализуем волатильность
            normalized_vol = min(max(volatility / 0.02, 0.5), 2.0)

            # Корректируем параметры
            adjusted_sl_pct = base_params.stop_loss_pct * normalized_vol * sl_multiplier
            adjusted_tp_pct = (
                base_params.take_profit_pct * normalized_vol * tp_multiplier
            )

            # Ограничиваем значения
            adjusted_sl_pct = min(max(adjusted_sl_pct, 0.005), 0.10)  # 0.5% - 10%
            adjusted_tp_pct = min(max(adjusted_tp_pct, 0.01), 0.20)  # 1% - 20%

            logger.info(
                f"Volatility adjustment: vol={volatility:.4f}, "
                f"SL: {base_params.stop_loss_pct:.2%} -> {adjusted_sl_pct:.2%}, "
                f"TP: {base_params.take_profit_pct:.2%} -> {adjusted_tp_pct:.2%}"
            )

            return RiskParameters(
                position_size=base_params.position_size,
                stop_loss_pct=adjusted_sl_pct,
                take_profit_pct=adjusted_tp_pct,
                leverage=base_params.leverage,
                risk_amount=base_params.risk_amount,
                confidence_adjusted=base_params.confidence_adjusted,
                ml_score=base_params.ml_score,
            )

        except Exception as e:
            logger.error(f"Ошибка volatility adjustment: {e}")
            return base_params

    def _get_risk_multiplier(self, risk_profile: str) -> float:
        """Получает множитель риска для профиля"""
        profile_config = self.risk_profiles.get(risk_profile, {})
        return profile_config.get("risk_multiplier", 1.0)

    def _get_asset_risk_multiplier(self, symbol: str) -> float:
        """Получает множитель риска для типа актива"""
        for category, config in self.asset_categories.items():
            symbols = config.get("symbols", [])
            if any(s in symbol.upper() for s in symbols):
                return config.get("risk_multiplier", 1.0)
        return 1.0

    def _get_asset_category(self, symbol: str) -> str:
        """Определяет категорию актива"""
        for category, config in self.asset_categories.items():
            symbols = config.get("symbols", [])
            if any(s in symbol.upper() for s in symbols):
                return category
        return "stable_coins"  # По умолчанию

    def _calculate_ml_adjustment(self, ml_signal: MLSignalData) -> float:
        """Рассчитывает корректировку на основе ML-сигнала"""
        try:
            # Базовая корректировка на основе уверенности
            confidence_factor = ml_signal.confidence

            # Дополнительная корректировка на основе силы сигнала
            strength_factor = ml_signal.signal_strength

            # Корректировка на основе вероятности успеха
            success_factor = ml_signal.success_probability

            # Итоговая корректировка
            total_adjustment = confidence_factor * strength_factor * success_factor

            # Ограничиваем значения
            total_adjustment = min(max(total_adjustment, 0.3), 2.0)

            logger.debug(
                f"ML adjustment: confidence={confidence_factor:.3f}, "
                f"strength={strength_factor:.3f}, success={success_factor:.3f}, "
                f"total={total_adjustment:.3f}"
            )

            return total_adjustment

        except Exception as e:
            logger.error(f"Ошибка расчета ML adjustment: {e}")
            return 1.0

    def _calculate_position_size(
        self,
        entry_price: float,
        risk_multiplier: float,
        account_balance: Optional[float] = None,
    ) -> float:
        """Рассчитывает размер позиции"""
        try:
            balance = (
                account_balance if account_balance else float(self.fixed_risk_balance)
            )
            risk_amount = balance * float(self.risk_per_trade) * risk_multiplier

            # Используем 2% стоп-лосс для расчета
            stop_loss_pct = 0.02
            risk_per_unit = entry_price * stop_loss_pct

            if risk_per_unit == 0:
                return 0.0

            position_size = risk_amount / risk_per_unit

            # Проверяем минимальный размер
            min_size = self.min_notional / entry_price
            return max(position_size, min_size)

        except Exception as e:
            logger.error(f"Ошибка расчета position size: {e}")
            return 0.0

    def _calculate_sltp_levels(
        self, ml_signal: MLSignalData, symbol: str, entry_price: float
    ) -> Tuple[float, float]:
        """Рассчитывает уровни SL/TP"""
        try:
            # Используем значения из ML-сигнала или дефолтные
            sl_pct = ml_signal.stop_loss_pct if ml_signal.stop_loss_pct else 0.02
            tp_pct = ml_signal.take_profit_pct if ml_signal.take_profit_pct else 0.04

            # Корректировка на основе типа актива
            asset_category = self._get_asset_category(symbol)
            if asset_category == "meme_coins":
                sl_pct *= 1.2
                tp_pct *= 1.1

            return sl_pct, tp_pct

        except Exception as e:
            logger.error(f"Ошибка расчета SL/TP levels: {e}")
            return 0.02, 0.04

    def _calculate_leverage(self, symbol: str, ml_signal: MLSignalData) -> int:
        """Рассчитывает плечо на основе ML-сигнала"""
        try:
            # Базовое плечо
            base_leverage = self.risk_config.get("default_leverage", 5)

            # Корректировка на основе уверенности
            if ml_signal.confidence > 0.8:
                leverage_multiplier = 1.2
            elif ml_signal.confidence > 0.6:
                leverage_multiplier = 1.0
            else:
                leverage_multiplier = 0.8

            # Корректировка на основе типа актива
            asset_category = self._get_asset_category(symbol)
            if asset_category == "meme_coins":
                leverage_multiplier *= 0.8  # Снижаем плечо для мемкоинов

            leverage = int(base_leverage * leverage_multiplier)

            # Ограничиваем максимальным значением
            return min(leverage, self.max_leverage)

        except Exception as e:
            logger.error(f"Ошибка расчета leverage: {e}")
            return self.risk_config.get("default_leverage", 5)

    def _get_fallback_parameters(
        self, symbol: str, entry_price: float
    ) -> RiskParameters:
        """Возвращает базовые параметры при ошибке"""
        return RiskParameters(
            position_size=self.min_notional / entry_price,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            leverage=self.risk_config.get("default_leverage", 5),
            risk_amount=float(self.fixed_risk_balance * self.risk_per_trade),
            confidence_adjusted=False,
            ml_score=None,
        )
