#!/usr/bin/env python3
"""
Скрипт для запуска ML стратегии на основе PatchTST модели
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from database.connections import get_async_db
from database.models import HistoricalData
from strategies.ml_strategy.patchtst_strategy import PatchTSTStrategy

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def load_historical_data(symbol: str, limit: int = 1000):
    """Загрузка исторических данных для тестирования"""
    async with get_async_db() as db:
        query = (
            select(HistoricalData)
            .where(HistoricalData.symbol == symbol)
            .order_by(HistoricalData.timestamp.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        data = result.scalars().all()

        if not data:
            raise ValueError(f"Нет данных для символа {symbol}")

        # Конвертируем в формат для стратегии
        market_data = []
        for row in reversed(data):  # Восстанавливаем хронологический порядок
            market_data.append(
                {
                    "symbol": row.symbol,
                    "timestamp": row.timestamp,
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                }
            )

        return market_data


async def run_strategy(config_path: str, symbol: str, dry_run: bool = True):
    """Запуск ML стратегии"""

    # Загружаем конфигурацию
    with open(config_path) as f:
        config = yaml.safe_load(f)

    logger.info(f"Загружена конфигурация из {config_path}")

    # Создаем стратегию
    try:
        strategy = PatchTSTStrategy(config)
        logger.info("ML стратегия инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации стратегии: {e}")
        return

    # Загружаем исторические данные
    try:
        market_data = await load_historical_data(symbol)
        logger.info(f"Загружено {len(market_data)} записей для {symbol}")
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return

    # Запускаем стратегию на исторических данных
    total_signals = 0
    long_signals = 0
    short_signals = 0

    for data_point in market_data[-100:]:  # Обрабатываем последние 100 точек
        try:
            # Генерируем сигнал
            signal = await strategy.generate_signal(data_point)

            if signal:
                total_signals += 1

                if signal.direction == "LONG":
                    long_signals += 1
                    action = "📈 LONG"
                elif signal.direction == "SHORT":
                    short_signals += 1
                    action = "📉 SHORT"
                else:
                    action = "⏸️ FLAT"

                logger.info(
                    f"{action} сигнал для {signal.symbol} @ {signal.price:.2f} | "
                    f"Уверенность: {signal.confidence:.2%} | "
                    f"SL: {signal.stop_loss:.2f} | TP: {signal.take_profit:.2f}"
                )

                # В режиме dry run не выполняем реальные сделки
                if not dry_run:
                    # Здесь можно добавить код для отправки ордеров на биржу
                    pass

        except Exception as e:
            logger.error(f"Ошибка генерации сигнала: {e}")

    # Статистика
    logger.info("\n" + "=" * 50)
    logger.info("📊 СТАТИСТИКА СИГНАЛОВ:")
    logger.info(f"Всего сигналов: {total_signals}")
    logger.info(
        f"LONG сигналов: {long_signals} ({long_signals / max(total_signals, 1) * 100:.1f}%)"
    )
    logger.info(
        f"SHORT сигналов: {short_signals} ({short_signals / max(total_signals, 1) * 100:.1f}%)"
    )
    logger.info("=" * 50)


async def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Запуск ML стратегии")
    parser.add_argument(
        "--config",
        type=str,
        default="strategies/ml_strategy/patchtst_config.yaml",
        help="Путь к конфигурации стратегии",
    )
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Торговый символ")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Запуск в режиме реальной торговли (по умолчанию dry run)",
    )

    args = parser.parse_args()

    # Проверяем наличие файлов модели
    model_path = Path("models/saved/best_model_20250728_215703.pth")
    scaler_path = Path("models/saved/data_scaler.pkl")

    if not model_path.exists():
        logger.error(f"Файл модели не найден: {model_path}")
        logger.info("Скопируйте файл модели из LLM TRANSFORM проекта")
        return

    if not scaler_path.exists():
        logger.error(f"Файл scaler не найден: {scaler_path}")
        logger.info("Скопируйте файл scaler из LLM TRANSFORM проекта")
        return

    # Запускаем стратегию
    await run_strategy(args.config, args.symbol, dry_run=not args.live)


if __name__ == "__main__":
    asyncio.run(main())
