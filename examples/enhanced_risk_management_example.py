#!/usr/bin/env python3
"""
Пример использования улучшенной системы управления рисками
Адаптировано из BOT_AI_V2 для BOT Trading v3
"""

import asyncio
import logging
from typing import Any

import yaml

# Импорты системы рисков
from risk_management.enhanced_calculator import EnhancedRiskCalculator, MLSignalData
from risk_management.ml_risk_adapter import MLSignalAdapter

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config() -> dict[str, Any]:
    """Загружает конфигурацию рисков"""
    try:
        with open("config/risk_management.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Ошибка загрузки конфигурации: {e}")
        return {}


async def example_ml_signal_processing():
    """Пример обработки ML-сигнала с улучшенной системой рисков"""

    # Загружаем конфигурацию
    config = load_config()
    if not config:
        logger.error("Не удалось загрузить конфигурацию")
        return

    # Инициализируем компоненты
    risk_calculator = EnhancedRiskCalculator(config)
    ml_adapter = MLSignalAdapter(config)

    # Пример ML-предсказания (как в логах)
    ml_prediction = {
        "signal_type": "LONG",
        "signal_strength": 0.75,
        "confidence": 0.6991091337054969,
        "success_probability": 0.6991091337054969,
        "stop_loss_pct": 0.01,  # 1%
        "take_profit_pct": 0.02,  # 2%
        "risk_level": "LOW",
        "predictions": {
            "returns_15m": -0.1071745902299881,
            "returns_1h": 0.1785423755645752,
            "returns_4h": 0.06026472896337509,
            "returns_12h": -0.09465909004211426,
            "direction_score": 1.4000000000000001,
            "directions_by_timeframe": [2, 1, 1, 1],
            "direction_probabilities": [
                [0.3366187810897827, 0.3242063820362091, 0.3391748070716858],
                [0.2776782214641571, 0.4530443847179413, 0.2692773938179016],
                [0.34790587425231934, 0.371046781539917, 0.28104734420776367],
                [0.341814786195755, 0.3547007739543915, 0.3034844994544983],
            ],
        },
        "timestamp": "2025-08-11T09:17:23.354447+00:00",
    }

    # Параметры торговли
    symbol = "SOLUSDT"
    entry_price = 100.0  # $100
    account_balance = 1000.0  # $1000

    logger.info("=" * 60)
    logger.info("ПРИМЕР ОБРАБОТКИ ML-СИГНАЛА С УЛУЧШЕННОЙ СИСТЕМОЙ РИСКОВ")
    logger.info("=" * 60)

    # Шаг 1: Конвертируем ML-предсказание в MLSignalData
    logger.info("\n1. Конвертация ML-предсказания...")
    ml_signal = ml_adapter.convert_ml_prediction_to_signal(ml_prediction, symbol)

    if not ml_signal:
        logger.error("Не удалось конвертировать ML-сигнал")
        return

    logger.info("✅ ML-сигнал конвертирован:")
    logger.info(f"   Тип: {ml_signal.signal_type}")
    logger.info(f"   Уверенность: {ml_signal.confidence:.3f}")
    logger.info(f"   Сила сигнала: {ml_signal.signal_strength:.3f}")
    logger.info(f"   Вероятность успеха: {ml_signal.success_probability:.3f}")
    logger.info(f"   Уровень риска: {ml_signal.risk_level}")

    # Шаг 2: Валидируем ML-сигнал
    logger.info("\n2. Валидация ML-сигнала...")
    is_valid = ml_adapter.validate_ml_signal(ml_signal, symbol)

    if not is_valid:
        logger.error("❌ ML-сигнал не прошел валидацию")
        return

    logger.info("✅ ML-сигнал прошел валидацию")

    # Шаг 3: Рассчитываем параметры риска
    logger.info("\n3. Расчет параметров риска...")
    risk_params = ml_adapter.calculate_risk_adjusted_parameters(
        symbol=symbol,
        entry_price=entry_price,
        ml_signal=ml_signal,
        account_balance=account_balance,
        risk_profile="standard",
    )

    logger.info("✅ Параметры риска рассчитаны:")
    logger.info(f"   Размер позиции: {risk_params.position_size:.6f}")
    logger.info(f"   Стоп-лосс: {risk_params.stop_loss_pct:.2%}")
    logger.info(f"   Тейк-профит: {risk_params.take_profit_pct:.2%}")
    logger.info(f"   Плечо: {risk_params.leverage}x")
    logger.info(f"   Сумма риска: ${risk_params.risk_amount:.2f}")

    # Шаг 4: Получаем адаптивную конфигурацию SL/TP
    logger.info("\n4. Адаптивная конфигурация SL/TP...")
    sltp_config = ml_adapter.get_adaptive_sltp_config(
        symbol=symbol, entry_price=entry_price, side="BUY", ml_signal=ml_signal
    )

    logger.info("✅ SL/TP конфигурация:")
    logger.info(f"   Стоп-лосс цена: ${sltp_config['stop_loss']:.4f}")
    logger.info(f"   Тейк-профит цена: ${sltp_config['take_profit']:.4f}")
    logger.info(
        f"   Трейлинг-стоп: {'Включен' if sltp_config['trailing_stop']['enabled'] else 'Отключен'}"
    )
    logger.info(
        f"   Защита прибыли: {'Включена' if sltp_config['profit_protection']['enabled'] else 'Отключена'}"
    )
    logger.info(
        f"   Частичное закрытие: {'Включено' if sltp_config['partial_tp_enabled'] else 'Отключено'}"
    )

    # Шаг 5: Пример расчета размера позиции по риску
    logger.info("\n5. Расчет размера позиции по риску...")
    stop_loss_price = entry_price * (1 - risk_params.stop_loss_pct)
    position_size = risk_calculator.calculate_position_size_by_risk(
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        risk_percentage=0.02,  # 2%
        account_balance=account_balance,
    )

    logger.info(f"✅ Размер позиции по риску: {position_size:.6f}")
    logger.info(f"   Цена входа: ${entry_price:.2f}")
    logger.info(f"   Стоп-лосс: ${stop_loss_price:.2f}")
    logger.info(f"   Риск на единицу: ${entry_price - stop_loss_price:.4f}")

    # Шаг 6: Пример адаптивных параметров SL/TP
    logger.info("\n6. Адаптивные параметры SL/TP...")
    adaptive_params = risk_calculator.get_adaptive_sltp_params(
        symbol=symbol,
        entry_price=entry_price,
        side="BUY",
        ml_signal=ml_signal,
        volatility=0.025,  # 2.5% волатильность
    )

    logger.info("✅ Адаптивные параметры:")
    logger.info(
        f"   Стоп-лосс: ${adaptive_params['stop_loss_price']:.4f} ({adaptive_params['stop_loss_pct']:.2%})"
    )
    logger.info(
        f"   Тейк-профит: ${adaptive_params['take_profit_price']:.4f} ({adaptive_params['take_profit_pct']:.2%})"
    )

    # Шаг 7: Пример корректировки на основе волатильности
    logger.info("\n7. Корректировка на основе волатильности...")
    volatility_adjusted = risk_calculator.apply_volatility_adjustment(
        base_params=risk_params,
        volatility=0.025,
        atr_period=14,  # 2.5% волатильность
    )

    logger.info("✅ Корректировка волатильности:")
    logger.info(
        f"   SL: {risk_params.stop_loss_pct:.2%} -> {volatility_adjusted.stop_loss_pct:.2%}"
    )
    logger.info(
        f"   TP: {risk_params.take_profit_pct:.2%} -> {volatility_adjusted.take_profit_pct:.2%}"
    )

    logger.info("\n" + "=" * 60)
    logger.info("ПРИМЕР ЗАВЕРШЕН УСПЕШНО!")
    logger.info("=" * 60)


async def example_different_risk_profiles():
    """Пример работы с разными профилями риска"""

    config = load_config()
    if not config:
        return

    risk_calculator = EnhancedRiskCalculator(config)
    ml_adapter = MLSignalAdapter(config)

    # Тестовый ML-сигнал
    ml_signal = MLSignalData(
        signal_type="LONG",
        signal_strength=0.8,
        confidence=0.75,
        success_probability=0.7,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        risk_level="MEDIUM",
    )

    symbol = "BTCUSDT"
    entry_price = 50000.0
    account_balance = 10000.0

    logger.info("\n" + "=" * 60)
    logger.info("ПРИМЕР РАЗНЫХ ПРОФИЛЕЙ РИСКА")
    logger.info("=" * 60)

    profiles = ["standard", "conservative", "very_conservative"]

    for profile in profiles:
        logger.info(f"\n--- Профиль риска: {profile.upper()} ---")

        risk_params = ml_adapter.calculate_risk_adjusted_parameters(
            symbol=symbol,
            entry_price=entry_price,
            ml_signal=ml_signal,
            account_balance=account_balance,
            risk_profile=profile,
        )

        logger.info(f"Размер позиции: {risk_params.position_size:.6f}")
        logger.info(f"Стоп-лосс: {risk_params.stop_loss_pct:.2%}")
        logger.info(f"Тейк-профит: {risk_params.take_profit_pct:.2%}")
        logger.info(f"Плечо: {risk_params.leverage}x")
        logger.info(f"Сумма риска: ${risk_params.risk_amount:.2f}")


async def example_asset_categories():
    """Пример работы с разными категориями активов"""

    config = load_config()
    if not config:
        return

    risk_calculator = EnhancedRiskCalculator(config)

    # Тестовый ML-сигнал
    ml_signal = MLSignalData(
        signal_type="LONG",
        signal_strength=0.7,
        confidence=0.65,
        success_probability=0.6,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        risk_level="MEDIUM",
    )

    entry_price = 100.0
    account_balance = 5000.0

    logger.info("\n" + "=" * 60)
    logger.info("ПРИМЕР РАЗНЫХ КАТЕГОРИЙ АКТИВОВ")
    logger.info("=" * 60)

    symbols = ["BTCUSDT", "DOGEUSDT", "PEPEUSDT"]

    for symbol in symbols:
        logger.info(f"\n--- Символ: {symbol} ---")

        risk_params = risk_calculator.calculate_ml_adjusted_risk_params(
            symbol=symbol,
            entry_price=entry_price,
            ml_signal=ml_signal,
            account_balance=account_balance,
        )

        logger.info(f"Размер позиции: {risk_params.position_size:.6f}")
        logger.info(f"Стоп-лосс: {risk_params.stop_loss_pct:.2%}")
        logger.info(f"Тейк-профит: {risk_params.take_profit_pct:.2%}")
        logger.info(f"Плечо: {risk_params.leverage}x")
        logger.info(f"Сумма риска: ${risk_params.risk_amount:.2f}")


async def main():
    """Главная функция с примерами"""
    try:
        # Основной пример
        await example_ml_signal_processing()

        # Пример профилей риска
        await example_different_risk_profiles()

        # Пример категорий активов
        await example_asset_categories()

    except Exception as e:
        logger.error(f"Ошибка в примере: {e}")


if __name__ == "__main__":
    asyncio.run(main())
