#!/usr/bin/env python3
"""
Планировщик для генерации ML сигналов каждую минуту
Координирует работу всех ML компонентов для real-time торговли
"""

import asyncio
import signal
import sys
from datetime import UTC, datetime
from typing import Any

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger(__name__)


class SignalScheduler:
    """
    Планировщик для периодической генерации торговых сигналов
    с использованием ML модели
    """

    def __init__(self, config_or_manager: ConfigManager | dict | None = None):
        """
        Args:
            config_or_manager: Менеджер конфигурации или dict конфигурации
        """
        if isinstance(config_or_manager, dict):
            # Если передан dict конфигурации напрямую
            self.config = config_or_manager
            self.config_manager = None
        else:
            # Если передан ConfigManager или None
            self.config_manager = config_or_manager or ConfigManager()
            self.config = self.config_manager.get_config()

        # ML компоненты
        self.ml_manager = None
        self.signal_processor = None
        self.trading_engine = None  # Ссылка на Trading Engine

        # Настройки планировщика
        ml_config = self.config.get("ml", {})
        self.symbols = ml_config.get("symbols", ["BTCUSDT"])
        # Читаем интервал из конфигурации (по умолчанию 180 секунд = 3 минуты)
        self.interval_seconds = ml_config.get("signal_generation", {}).get("interval_seconds", 180)
        self.exchange = ml_config.get("default_exchange", "bybit")
        self.enabled = ml_config.get("enabled", True)

        # Состояние
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}
        self._last_signals: dict[str, Any] = {}
        self._error_counts: dict[str, int] = {}
        self._max_errors = 5  # Максимум ошибок подряд перед отключением символа

        logger.info(
            f"SignalScheduler инициализирован: "
            f"{len(self.symbols)} символов, интервал {self.interval_seconds}с"
        )

    async def initialize(self):
        """Инициализация всех компонентов"""
        try:
            logger.info("🚀 Инициализация Signal Scheduler...")

            # Инициализируем ML Manager
            self.ml_manager = MLManager(self.config)
            await self.ml_manager.initialize()

            # Инициализируем Signal Processor
            # Если у нас нет config_manager, создаем временный для signal_processor
            if self.config_manager:
                self.signal_processor = MLSignalProcessor(
                    ml_manager=self.ml_manager,
                    config=self.config,
                    config_manager=self.config_manager,
                )
            else:
                # Создаем временный ConfigManager для signal_processor
                from core.config.config_manager import ConfigManager

                temp_manager = ConfigManager()
                self.signal_processor = MLSignalProcessor(
                    ml_manager=self.ml_manager,
                    config=self.config,
                    config_manager=temp_manager,
                )
            await self.signal_processor.initialize()

            logger.info("✅ Signal Scheduler готов к работе")

        except Exception as e:
            logger.error(f"Ошибка инициализации Signal Scheduler: {e}")
            raise

    async def start(self):
        """Запуск планировщика"""
        if not self.enabled:
            logger.warning("ML сигналы отключены в конфигурации")
            return

        if self._running:
            logger.warning("Планировщик уже запущен")
            return

        self._running = True
        logger.info("📡 Запуск генерации ML сигналов...")

        # Запускаем задачи для каждого символа
        for symbol in self.symbols:
            task = asyncio.create_task(self._signal_loop(symbol))
            self._tasks[symbol] = task
            self._error_counts[symbol] = 0

        # Запускаем мониторинг
        monitor_task = asyncio.create_task(self._monitoring_loop())
        self._tasks["monitor"] = monitor_task

        logger.info(f"✅ Запущено {len(self.symbols)} задач генерации сигналов")

    async def stop(self):
        """Остановка планировщика"""
        self._running = False
        logger.info("Остановка Signal Scheduler...")

        # Отменяем все задачи
        for task in self._tasks.values():
            if not task.done():
                task.cancel()

        # Ждем завершения
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        self._tasks.clear()

        # Завершаем работу компонентов
        if self.signal_processor:
            await self.signal_processor.shutdown()

        logger.info("✅ Signal Scheduler остановлен")

    def set_trading_engine(self, trading_engine):
        """
        Устанавливает ссылку на Trading Engine для отправки сигналов

        Args:
            trading_engine: Экземпляр TradingEngine
        """
        self.trading_engine = trading_engine
        logger.info("✅ Trading Engine подключен к Signal Scheduler")

        # Если у нас есть signal_processor, передаем ему тоже
        if self.signal_processor:
            self.signal_processor.trading_engine = trading_engine

    async def _signal_loop(self, symbol: str):
        """
        Основной цикл генерации сигналов для символа

        Args:
            symbol: Торговый символ
        """
        logger.info(f"Запуск цикла генерации для {symbol}")

        while self._running:
            try:
                start_time = datetime.now(UTC)

                # Генерируем сигнал
                signal = await self._generate_signal(symbol)

                if signal:
                    self._last_signals[symbol] = {
                        "signal": signal,
                        "timestamp": start_time,
                        "success": True,
                    }
                    self._error_counts[symbol] = 0  # Сбрасываем счетчик ошибок

                    logger.info(
                        f"✅ {symbol}: {signal.signal_type.value} сигнал, "
                        f"уверенность {signal.confidence:.1f}%"
                    )

                    # Отправляем сигнал в Trading Engine
                    await self._emit_signal_to_trading_engine(signal)
                else:
                    logger.debug(f"Нет сигнала для {symbol}")

                # Вычисляем время до следующего запуска
                elapsed = (datetime.now(UTC) - start_time).total_seconds()
                sleep_time = max(0, self.interval_seconds - elapsed)

                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info(f"Цикл генерации для {symbol} отменен")
                break

            except Exception as e:
                logger.error(f"Ошибка генерации сигнала для {symbol}: {e}")
                self._error_counts[symbol] += 1

                # Если слишком много ошибок - останавливаем для этого символа
                if self._error_counts[symbol] >= self._max_errors:
                    logger.error(
                        f"Слишком много ошибок для {symbol} "
                        f"({self._error_counts[symbol]}), остановка генерации"
                    )
                    break

                # Ждем перед повтором
                await asyncio.sleep(self.interval_seconds)

    async def _generate_signal(self, symbol: str) -> Any | None:
        """
        Генерация сигнала для символа

        Args:
            symbol: Торговый символ

        Returns:
            Signal объект или None
        """
        try:
            # Проверяем что signal_processor инициализирован
            if not self.signal_processor:
                raise ValueError("Signal Processor не инициализирован")

            # Используем real-time метод
            signal = await self.signal_processor.process_realtime_signal(
                symbol=symbol, exchange=self.exchange
            )

            return signal

        except Exception as e:
            logger.error(f"Ошибка при генерации сигнала для {symbol}: {e}")
            # Просто перебрасываем исключение без кастомного класса
            raise Exception(f"Failed to generate signal for {symbol}: {e}") from e

    async def _monitoring_loop(self):
        """Цикл мониторинга состояния"""
        log_interval = 300  # Логируем статистику каждые 5 минут

        while self._running:
            try:
                await asyncio.sleep(log_interval)

                # Собираем статистику
                active_symbols = len(
                    [s for s in self.symbols if s in self._tasks and not self._tasks[s].done()]
                )

                total_signals = len(self._last_signals)
                recent_signals = len(
                    [
                        s
                        for s in self._last_signals.values()
                        if (datetime.now(UTC) - s["timestamp"]).total_seconds() < 300
                    ]
                )

                error_symbols = [s for s, count in self._error_counts.items() if count > 0]

                # Получаем статистику от процессора
                processor_stats = {}
                if self.signal_processor and hasattr(self.signal_processor, "get_metrics"):
                    processor_stats = await self.signal_processor.get_metrics()

                logger.info(
                    f"📊 Статистика Signal Scheduler:\n"
                    f"   Активных символов: {active_symbols}/{len(self.symbols)}\n"
                    f"   Сигналов за последние 5 мин: {recent_signals}\n"
                    f"   Всего обработано: {processor_stats.get('total_processed', 0)}\n"
                    f"   Успешность: {processor_stats.get('success_rate', 0):.1%}\n"
                    f"   Символы с ошибками: {error_symbols if error_symbols else 'нет'}"
                )

            except Exception as e:
                logger.error(f"Ошибка в мониторинге: {e}")

    async def get_status(self) -> dict[str, Any]:
        """Получение текущего статуса планировщика"""
        status = {
            "running": self._running,
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "symbols": {
                symbol: {
                    "active": symbol in self._tasks and not self._tasks[symbol].done(),
                    "errors": self._error_counts.get(symbol, 0),
                    "last_signal": self._last_signals.get(symbol, {}),
                }
                for symbol in self.symbols
            },
            "processor_stats": (
                await self.signal_processor.get_metrics()
                if self.signal_processor and hasattr(self.signal_processor, "get_metrics")
                else {}
            ),
        }

        return status

    async def add_symbol(self, symbol: str):
        """Добавление нового символа для отслеживания"""
        if symbol in self.symbols:
            logger.warning(f"Символ {symbol} уже отслеживается")
            return

        self.symbols.append(symbol)
        self._error_counts[symbol] = 0

        if self._running:
            # Запускаем задачу для нового символа
            task = asyncio.create_task(self._signal_loop(symbol))
            self._tasks[symbol] = task

        logger.info(f"Добавлен символ {symbol} для отслеживания")

    def set_trading_engine(self, trading_engine):
        """Установка ссылки на Trading Engine"""
        self.trading_engine = trading_engine
        logger.info("🔗 Trading Engine подключен к Signal Scheduler")

    async def remove_symbol(self, symbol: str):
        """Удаление символа из отслеживания"""
        if symbol not in self.symbols:
            logger.warning(f"Символ {symbol} не отслеживается")
            return

        self.symbols.remove(symbol)

        # Останавливаем задачу
        if symbol in self._tasks:
            self._tasks[symbol].cancel()
            await asyncio.gather(self._tasks[symbol], return_exceptions=True)
            del self._tasks[symbol]

        # Очищаем данные
        self._error_counts.pop(symbol, None)
        self._last_signals.pop(symbol, None)

        logger.info(f"Удален символ {symbol} из отслеживания")

    async def _emit_signal_to_trading_engine(self, signal):
        """Отправка сигнала в Trading Engine"""
        if self.trading_engine:
            try:
                logger.info("📤 Отправляем сигнал в Trading Engine:")
                logger.info(f"   Тип сигнала: {type(signal)}")
                logger.info(
                    f"   Symbol: {signal.symbol if hasattr(signal, 'symbol') else 'нет атрибута'}"
                )
                logger.info(
                    f"   Signal type: {signal.signal_type if hasattr(signal, 'signal_type') else 'нет атрибута'}"
                )
                logger.info(
                    f"   Confidence: {signal.confidence if hasattr(signal, 'confidence') else 'нет атрибута'}"
                )

                await self.trading_engine.receive_trading_signal(signal)
                logger.info(f"✅ Сигнал {signal.symbol} отправлен в Trading Engine")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки сигнала в Trading Engine: {e}")
                import traceback

                logger.error(traceback.format_exc())
        else:
            logger.warning(
                "⚠️ Trading Engine не подключен к Signal Scheduler - сигналы не будут обработаны!"
            )


async def main():
    """Основная функция для запуска планировщика"""
    scheduler = SignalScheduler()

    # Обработчик сигналов для graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Получен сигнал остановки...")
        asyncio.create_task(scheduler.stop())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Инициализация
        await scheduler.initialize()

        # Запуск
        await scheduler.start()

        # Бесконечный цикл
        while True:
            await asyncio.sleep(180)  # Проверка каждые 3 минуты

    except KeyboardInterrupt:
        logger.info("Остановка по запросу пользователя...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
