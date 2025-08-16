"""
Risk Manager для управления рисками торговли
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.logger import setup_risk_management_logger


@dataclass
class RiskStatus:
    """Статус проверки рисков"""

    def __init__(
        self,
        requires_action: bool = False,
        action: str | None = None,
        message: str | None = None,
    ):
        self.requires_action = requires_action
        self.action = action
        self.message = message


class RiskManager:
    """Менеджер управления рисками с поддержкой профилей и ML-интеграции"""

    def __init__(self, config: dict[str, Any], position_manager=None, exchange_registry=None):
        self.config = config
        self.position_manager = position_manager
        self.exchange_registry = exchange_registry
        self.logger = setup_risk_management_logger()

        # Основные параметры риска
        self.enabled = config.get("enabled", True)
        self.risk_per_trade = Decimal(str(config.get("risk_per_trade", 0.02)))
        self.fixed_risk_balance = Decimal(str(config.get("fixed_risk_balance", 500)))
        self.max_total_risk = Decimal(str(config.get("max_total_risk", 0.10)))
        self.max_positions = config.get("max_positions", 10)

        # Параметры плеча
        self.default_leverage = config.get("default_leverage", 5)
        self.max_leverage = config.get("max_leverage", 20)
        self.min_notional = Decimal(str(config.get("min_notional", 5.0)))

        # Профили риска
        self.risk_profiles = config.get("risk_profiles", {})
        self.current_profile = "standard"

        # Категории активов
        self.asset_categories = config.get("asset_categories", {})

        # ML-интеграция
        self.ml_integration = config.get("ml_integration", {})
        self.ml_enabled = self.ml_integration.get("enabled", False)

        # Мониторинг
        self.monitoring = config.get("monitoring", {})

        # Логирование инициализации
        self.logger.info("🛡️ RiskManager инициализирован")
        self.logger.info(f"   📊 Профиль риска: {self.current_profile}")
        self.logger.info(f"   💰 Риск на сделку: {self.risk_per_trade:.2%}")
        self.logger.info(f"   🎯 Максимум позиций: {self.max_positions}")
        self.logger.info(
            f"   🔧 ML-интеграция: {'✅ Включена' if self.ml_enabled else '❌ Отключена'}"
        )
        self.logger.info(f"   📈 Доступные профили: {list(self.risk_profiles.keys())}")
        self.logger.info(f"   🏷️ Категории активов: {list(self.asset_categories.keys())}")

    def get_risk_profile(self, profile_name: str | None = None) -> dict[str, Any]:
        """Получение профиля риска"""
        if profile_name is None:
            profile_name = self.current_profile

        result = self.risk_profiles.get(profile_name, self.risk_profiles.get("standard", {}))
        return result if isinstance(result, dict) else {}

    def get_asset_category(self, symbol: str) -> dict[str, Any]:
        """Получение категории актива по символу"""
        for category_name, category_config in self.asset_categories.items():
            symbols = category_config.get("symbols", [])
            if symbol in symbols:
                return category_config

        # Возвращаем стандартную категорию если не найдена
        result = self.asset_categories.get("stable_coins", {})
        return result if isinstance(result, dict) else {}

    def calculate_position_size(
        self,
        signal: dict[str, Any],
        balance: Decimal | None = None,
        profile_name: str | None = None,
    ) -> Decimal:
        """Расчет размера позиции с учетом профиля риска и категории актива"""
        if not self.enabled:
            self.logger.debug("🛑 RiskManager отключен, возвращаем 0")
            return Decimal("0")

        symbol = signal.get("symbol", "UNKNOWN")
        side = signal.get("side", "UNKNOWN")

        self.logger.info(f"📊 Расчет размера позиции для {symbol} ({side})")
        self.logger.debug(f"   📋 Профиль: {profile_name or self.current_profile}")
        self.logger.debug(f"   💰 Баланс: {balance or 'не указан'}")

        # Получаем профиль риска
        profile = self.get_risk_profile(profile_name)
        risk_multiplier = Decimal(str(profile.get("risk_multiplier", 1.0)))

        # Получаем категорию актива
        asset_category = self.get_asset_category(symbol)
        asset_risk_multiplier = Decimal(str(asset_category.get("risk_multiplier", 1.0)))

        # Базовый расчет
        base_risk_amount = self.fixed_risk_balance * self.risk_per_trade

        # Применяем множители
        adjusted_risk = base_risk_amount * risk_multiplier * asset_risk_multiplier

        self.logger.debug(f"   🧮 Базовый риск: ${base_risk_amount}")
        self.logger.debug(f"   📈 Множитель профиля: {risk_multiplier}")
        self.logger.debug(f"   🏷️ Множитель категории: {asset_risk_multiplier}")
        self.logger.debug(f"   📊 Скорректированный риск: ${adjusted_risk}")

        # ML-корректировка если включена
        if self.ml_enabled:
            ml_adjustment = self._calculate_ml_adjustment(signal)
            adjusted_risk *= ml_adjustment
            self.logger.debug(f"   🤖 ML-корректировка: {ml_adjustment}")
            self.logger.debug(f"   📊 Финальный риск с ML: ${adjusted_risk}")

        # Ограничиваем максимальным размером позиции
        max_position_size = Decimal(str(profile.get("max_position_size", 1000)))
        if adjusted_risk > max_position_size:
            self.logger.warning(
                f"   ⚠️ Размер позиции ограничен: ${adjusted_risk} → ${max_position_size}"
            )
            adjusted_risk = max_position_size

        self.logger.info(f"   ✅ Финальный размер позиции: ${adjusted_risk}")
        return adjusted_risk

    def _calculate_ml_adjustment(self, signal: dict[str, Any]) -> Decimal:
        """Расчет ML-корректировки для риска"""
        if not self.ml_enabled:
            return Decimal("1.0")

        try:
            # Получаем ML-предсказания из сигнала
            ml_predictions = signal.get("ml_predictions", {})
            if not ml_predictions:
                return Decimal("1.0")

            # Получаем пороги из конфигурации
            thresholds = self.ml_integration.get("thresholds", {})
            buy_profit_threshold = Decimal(str(thresholds.get("buy_profit", 0.65)))
            buy_loss_threshold = Decimal(str(thresholds.get("buy_loss", 0.35)))

            # Получаем вероятности
            profit_probability = Decimal(str(ml_predictions.get("profit_probability", 0.5)))
            loss_probability = Decimal(str(ml_predictions.get("loss_probability", 0.5)))

            # Рассчитываем корректировку
            if signal.get("side") == "buy":
                if profit_probability > buy_profit_threshold:
                    return Decimal("1.2")  # Увеличиваем риск на 20%
                elif loss_probability > buy_loss_threshold:
                    return Decimal("0.8")  # Уменьшаем риск на 20%

            return Decimal("1.0")

        except Exception as e:
            self.logger.warning(f"Ошибка расчета ML-корректировки: {e}")
            return Decimal("1.0")

    async def check_signal_risk(self, signal: dict[str, Any]) -> bool:
        """Проверяет риски для сигнала с учетом профилей и категорий"""
        if not self.enabled:
            self.logger.debug("🛑 RiskManager отключен, пропускаем проверку")
            return True

        symbol = signal.get("symbol", "UNKNOWN")
        side = signal.get("side", "UNKNOWN")

        self.logger.info(f"🔍 Проверка рисков для {symbol} ({side})")

        try:
            # Базовые проверки
            if not signal:
                self.logger.warning("❌ Сигнал пустой")
                return False

            # Получаем профиль и категорию
            profile = self.get_risk_profile()
            asset_category = self.get_asset_category(symbol)

            self.logger.debug(f"   📊 Профиль: {self.current_profile}")
            self.logger.debug(f"   🏷️ Категория: {list(self.asset_categories.keys())}")

            # Проверка leverage
            leverage = signal.get("leverage", self.default_leverage)
            max_leverage = min(
                self.max_leverage, asset_category.get("max_leverage", self.max_leverage)
            )

            if leverage > max_leverage:
                self.logger.warning(
                    f"❌ Плечо {leverage}x превышает максимум {max_leverage}x для {symbol}"
                )
                return False
            else:
                self.logger.debug(f"   ✅ Плечо {leverage}x в пределах лимита {max_leverage}x")

            # Проверка размера позиции
            position_size = signal.get("position_size", 0)
            if position_size <= 0:
                self.logger.warning("❌ Некорректный размер позиции")
                return False
            else:
                self.logger.debug(f"   ✅ Размер позиции: {position_size}")

            # Проверка количества открытых позиций
            if self.position_manager:
                try:
                    positions = await self.position_manager.get_all_positions()
                    active_positions = [p for p in positions if p.size != 0]
                    if len(active_positions) >= self.max_positions:
                        self.logger.warning(
                            f"❌ Достигнут лимит позиций: {len(active_positions)}/{self.max_positions}"
                        )
                        return False
                    else:
                        self.logger.debug(
                            f"   ✅ Активных позиций: {len(active_positions)}/{self.max_positions}"
                        )
                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось проверить позиции: {e}")

            # ML-проверки если включены
            if self.ml_enabled:
                if not self._check_ml_requirements(signal, side):
                    self.logger.warning("❌ Сигнал не прошел ML-проверку")
                    return False
                else:
                    self.logger.debug("   ✅ ML-требования выполнены")

            self.logger.info(f"✅ Сигнал {symbol} прошел все проверки рисков")
            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки рисков для {symbol}: {e}")
            return False

    def _check_ml_requirements(self, signal: dict[str, Any], side: str) -> bool:
        """Проверка ML-требований для сигнала"""
        try:
            ml_predictions = signal.get("ml_predictions", {})
            if not ml_predictions:
                self.logger.warning("ML predictions not found in signal")
                return False

            # Получаем модель для стороны
            model_config = self.ml_integration.get(f"{side}_model", {})
            profile_model = model_config.get(self.current_profile, {})

            if not profile_model:
                return True  # Если нет конфигурации, пропускаем

            # Проверяем пороги
            profit_probability = ml_predictions.get("profit_probability", 0)
            loss_probability = ml_predictions.get("loss_probability", 0)

            profit_min = profile_model.get("profit_probability_min", 0)
            profit_max = profile_model.get("profit_probability_max", 1)
            loss_min = profile_model.get("loss_probability_min", 0)
            loss_max = profile_model.get("loss_probability_max", 1)

            # Проверяем соответствие порогам
            if not (profit_min <= profit_probability <= profit_max):
                self.logger.warning(
                    f"Profit probability {profit_probability} outside range [{profit_min}, {profit_max}]"
                )
                return False

            if not (loss_min <= loss_probability <= loss_max):
                self.logger.warning(
                    f"Loss probability {loss_probability} outside range [{loss_min}, {loss_max}]"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking ML requirements: {e}")
            return False

    async def check_global_risks(self) -> RiskStatus:
        """Проверяет глобальные риски системы"""
        if not self.enabled:
            return RiskStatus(requires_action=False)

        try:
            # Проверка общего риска
            if self.position_manager:
                total_risk = await self._calculate_total_risk()
                if total_risk > self.max_total_risk:
                    return RiskStatus(
                        requires_action=True,
                        action="reduce_positions",
                        message=f"Total risk {total_risk:.2%} exceeds limit {self.max_total_risk:.2%}",
                    )

            # ML-мониторинг если включен
            if self.ml_enabled:
                ml_status = await self._check_ml_performance()
                if ml_status.requires_action:
                    return ml_status

            return RiskStatus(requires_action=False)

        except Exception as e:
            self.logger.error(f"Error checking global risks: {e}")
            return RiskStatus(
                requires_action=True, action="pause", message=f"Risk check error: {e}"
            )

    async def _check_ml_performance(self) -> RiskStatus:
        """Проверка производительности ML-модели"""
        try:
            # Получаем пороги из конфигурации мониторинга
            accuracy_threshold = self.monitoring.get("accuracy_alert_threshold", 5.0)
            expected_buy_accuracy = self.monitoring.get("expected_buy_accuracy", 63.04)
            expected_sell_accuracy = self.monitoring.get("expected_sell_accuracy", 60.0)

            # Здесь должна быть логика получения реальной точности
            # Пока возвращаем статус без действий
            return RiskStatus(requires_action=False)

        except Exception as e:
            self.logger.error(f"Error checking ML performance: {e}")
            return RiskStatus(requires_action=False)

    async def _calculate_total_risk(self) -> Decimal:
        """Вычисляет общий риск по всем позициям"""
        if not self.position_manager:
            return Decimal("0")

        try:
            positions = await self.position_manager.get_all_positions()
            total_risk = Decimal("0")

            for position in positions:
                if position.size != 0:
                    # Получаем категорию актива для позиции
                    asset_category = self.get_asset_category(position.symbol)
                    asset_risk_multiplier = Decimal(str(asset_category.get("risk_multiplier", 1.0)))

                    # Рассчитываем риск с учетом категории
                    position_risk = abs(position.size) * self.risk_per_trade * asset_risk_multiplier
                    total_risk += position_risk

            return total_risk

        except Exception as e:
            self.logger.error(f"Error calculating total risk: {e}")
            return Decimal("0")

    def set_risk_profile(self, profile_name: str) -> None:
        """Установка профиля риска"""
        if profile_name in self.risk_profiles:
            self.current_profile = profile_name
            self.logger.info(f"Risk profile changed to: {profile_name}")
        else:
            self.logger.warning(f"Unknown risk profile: {profile_name}")

    async def health_check(self) -> bool:
        """Проверка здоровья компонента"""
        return bool(self.enabled)

    def is_running(self) -> bool:
        """Проверка работы компонента"""
        return bool(self.enabled)
