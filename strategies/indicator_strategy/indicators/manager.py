"""
Менеджер индикаторов для централизованного управления
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Type

import pandas as pd

from .base import IndicatorBase, IndicatorConfig

logger = logging.getLogger(__name__)


class IndicatorManager:
    """Менеджер для управления всеми индикаторами"""

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация менеджера

        Args:
            config: Конфигурация индикаторов
        """
        self.config = config
        self.indicators: Dict[str, Dict[str, IndicatorBase]] = {
            "trend": {},
            "momentum": {},
            "volume": {},
            "volatility": {},
        }

        # Пул потоков для параллельных вычислений
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Инициализация индикаторов
        self._initialize_indicators()

    def _initialize_indicators(self) -> None:
        """Инициализация всех индикаторов из конфигурации"""
        # Импорт индикаторов будет здесь после их создания
        indicator_classes = self._get_indicator_classes()

        for category, indicators_config in self.config.items():
            if category not in self.indicators:
                logger.warning(f"Unknown indicator category: {category}")
                continue

            if not isinstance(indicators_config, dict):
                continue

            for indicator_name, indicator_params in indicators_config.items():
                # Поиск класса индикатора
                indicator_class = indicator_classes.get(indicator_name)
                if not indicator_class:
                    logger.warning(f"Unknown indicator: {indicator_name}")
                    continue

                # Создание конфигурации
                config = IndicatorConfig(
                    name=indicator_name,
                    enabled=indicator_params.get("enabled", True),
                    params=indicator_params,
                )

                # Создание экземпляра индикатора
                try:
                    indicator = indicator_class(config)
                    self.indicators[category][indicator_name] = indicator
                    logger.info(f"Initialized {indicator_name} in category {category}")
                except Exception as e:
                    logger.error(f"Failed to initialize {indicator_name}: {e}")

    def _get_indicator_classes(self) -> Dict[str, Type[IndicatorBase]]:
        """Получение классов индикаторов (будет дополнено)"""
        classes = {}

        # Импорт индикаторов будет добавлен по мере их создания
        try:
            from .trend.ema import EMAIndicator
            from .trend.macd import MACDIndicator

            classes.update({"ema": EMAIndicator, "macd": MACDIndicator})
        except ImportError as e:
            logger.debug(f"Failed to import trend indicators: {e}")

        try:
            from .momentum.rsi import RSIIndicator

            classes.update({"rsi": RSIIndicator})
        except ImportError as e:
            logger.debug(f"Failed to import momentum indicators: {e}")

        try:
            from .volume.obv import OBVIndicator
            from .volume.volume_profile import VolumeProfileIndicator
            from .volume.vwap import VWAPIndicator

            classes.update(
                {
                    "obv": OBVIndicator,
                    "vwap": VWAPIndicator,
                    "volume_profile": VolumeProfileIndicator,
                }
            )
        except ImportError:
            pass

        try:
            from .volatility.atr import ATRIndicator
            from .volatility.bollinger import BollingerBandsIndicator
            from .volatility.vix_crypto import VixCryptoIndicator

            classes.update(
                {
                    "bollinger": BollingerBandsIndicator,
                    "atr": ATRIndicator,
                    "vix_crypto": VixCryptoIndicator,
                }
            )
        except ImportError:
            pass

        return classes

    async def calculate_all_indicators(
        self, data: pd.DataFrame
    ) -> Dict[str, Dict[str, Any]]:
        """
        Асинхронный расчет всех активных индикаторов

        Args:
            data: Рыночные данные

        Returns:
            Результаты по категориям
        """
        results = {}
        tasks = []

        for category, indicators in self.indicators.items():
            category_task = self._calculate_category_indicators(
                category, indicators, data
            )
            tasks.append(category_task)

        # Параллельное выполнение
        category_results = await asyncio.gather(*tasks)

        # Объединение результатов
        for category, category_result in zip(self.indicators.keys(), category_results):
            if category_result:
                results[category] = category_result

        return results

    async def _calculate_category_indicators(
        self, category: str, indicators: Dict[str, IndicatorBase], data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Расчет индикаторов категории"""
        if not indicators:
            return {}

        results = {}

        # Создание задач для каждого индикатора
        loop = asyncio.get_event_loop()
        tasks = []

        for name, indicator in indicators.items():
            if indicator.enabled:
                task = loop.run_in_executor(
                    self.executor, indicator.safe_calculate, data
                )
                tasks.append((name, task))

        # Ожидание результатов
        for name, task in tasks:
            try:
                result = await task
                if result:
                    results[name] = result.to_dict()
            except Exception as e:
                logger.error(f"Error calculating {name}: {e}")

        return results

    async def calculate_trend_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Расчет трендовых индикаторов"""
        return await self._calculate_category_indicators(
            "trend", self.indicators["trend"], data
        )

    async def calculate_momentum_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Расчет импульсных индикаторов"""
        return await self._calculate_category_indicators(
            "momentum", self.indicators["momentum"], data
        )

    async def calculate_volume_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Расчет объемных индикаторов"""
        return await self._calculate_category_indicators(
            "volume", self.indicators["volume"], data
        )

    async def calculate_volatility_indicators(
        self, data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Расчет индикаторов волатильности"""
        return await self._calculate_category_indicators(
            "volatility", self.indicators["volatility"], data
        )

    def get_indicators(self) -> List[str]:
        """Получение списка всех индикаторов"""
        all_indicators = []

        for category, indicators in self.indicators.items():
            for name in indicators.keys():
                all_indicators.append(f"{category}.{name}")

        return all_indicators

    def get_enabled_indicators(self) -> List[str]:
        """Получение списка активных индикаторов"""
        enabled = []

        for category, indicators in self.indicators.items():
            for name, indicator in indicators.items():
                if indicator.enabled:
                    enabled.append(f"{category}.{name}")

        return enabled

    def enable_indicator(self, category: str, name: str) -> bool:
        """Включение индикатора"""
        if category in self.indicators and name in self.indicators[category]:
            self.indicators[category][name].enabled = True
            return True
        return False

    def disable_indicator(self, category: str, name: str) -> bool:
        """Отключение индикатора"""
        if category in self.indicators and name in self.indicators[category]:
            self.indicators[category][name].enabled = False
            return True
        return False

    def get_min_required_periods(self) -> int:
        """Получение минимального количества периодов для всех индикаторов"""
        min_periods = 0

        for category, indicators in self.indicators.items():
            for indicator in indicators.values():
                if indicator.enabled:
                    min_periods = max(min_periods, indicator.get_min_periods())

        return min_periods

    def reset_all_caches(self) -> None:
        """Сброс кэшей всех индикаторов"""
        for category, indicators in self.indicators.items():
            for indicator in indicators.values():
                indicator.reset_cache()

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики менеджера"""
        total_indicators = sum(
            len(indicators) for indicators in self.indicators.values()
        )
        enabled_indicators = len(self.get_enabled_indicators())

        return {
            "total_indicators": total_indicators,
            "enabled_indicators": enabled_indicators,
            "categories": list(self.indicators.keys()),
            "min_required_periods": self.get_min_required_periods(),
        }

    def shutdown(self) -> None:
        """Завершение работы менеджера"""
        self.executor.shutdown(wait=True)


# Синглтон для глобального менеджера
_indicator_manager: Optional[IndicatorManager] = None


def get_indicator_manager(config: Dict[str, Any]) -> IndicatorManager:
    """Получение или создание глобального менеджера индикаторов"""
    global _indicator_manager

    if _indicator_manager is None:
        _indicator_manager = IndicatorManager(config)

    return _indicator_manager
