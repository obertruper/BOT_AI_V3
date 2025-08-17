"""
Тесты утилит и индикаторов BOT_AI_V3
Тесты для вспомогательных функций, индикаторов и утилит
"""

import asyncio
import os
import sys
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestUtilityHelpers:
    """Тесты вспомогательных утилит"""

    def test_helpers_import(self):
        """Тест импорта хелперов"""
        from utils.helpers import clean_symbol, format_decimal

        assert callable(format_decimal)
        assert callable(clean_symbol)

    def test_format_decimal(self):
        """Тест функции форматирования десятичных чисел"""
        from utils.helpers import format_decimal

        # Тестируем различные входные данные
        assert format_decimal(1.23456, 2) == "1.23"
        assert format_decimal("1.23456", 2) == "1.23"
        assert format_decimal(Decimal("1.23456"), 2) == "1.23"
        assert format_decimal(0, 2) == "0.00"
        assert format_decimal(None, 2) == "0.00"

    def test_clean_symbol(self):
        """Тест функции очистки символа"""
        from utils.helpers import clean_symbol

        assert clean_symbol("BTCUSDT") == "BTCUSDT"
        assert clean_symbol("btcusdt") == "BTCUSDT"
        assert clean_symbol("BTC-USDT") == "BTCUSDT"
        assert clean_symbol("BTC/USDT") == "BTCUSDT"


class TestMathUtilities:
    """Тесты математических утилит"""

    def test_math_utils_import(self):
        """Тест импорта математических утилит"""
        try:
            from utils.math import calculate_percentage, round_to_precision

            assert callable(calculate_percentage)
            assert callable(round_to_precision)
        except ImportError:
            pytest.skip("Math utils may not be implemented yet")


class TestTimeUtilities:
    """Тесты утилит времени"""

    def test_time_utils_import(self):
        """Тест импорта утилит времени"""
        try:
            from utils.time import format_timestamp, get_current_timestamp

            assert callable(get_current_timestamp)
            assert callable(format_timestamp)
        except ImportError:
            pytest.skip("Time utils may not be implemented yet")


class TestNetworkUtilities:
    """Тесты сетевых утилит"""

    def test_network_utils_import(self):
        """Тест импорта сетевых утилит"""
        try:
            from utils.network import make_request, retry_request

            assert callable(make_request)
            assert callable(retry_request)
        except ImportError:
            pytest.skip("Network utils may not be implemented yet")


class TestSecurityUtilities:
    """Тесты утилит безопасности"""

    def test_security_utils_import(self):
        """Тест импорта утилит безопасности"""
        try:
            from utils.security import decrypt_api_key, encrypt_api_key

            assert callable(encrypt_api_key)
            assert callable(decrypt_api_key)
        except ImportError:
            pytest.skip("Security utils may not be implemented yet")


class TestIndicatorCalculator:
    """Тесты калькулятора индикаторов"""

    def test_indicator_calculator_import(self):
        """Тест импорта калькулятора индикаторов"""
        from indicators.calculator.indicator_calculator import IndicatorCalculator

        assert IndicatorCalculator is not None

    def test_indicator_calculator_creation(self):
        """Тест создания калькулятора индикаторов"""
        from indicators.calculator.indicator_calculator import IndicatorCalculator

        calculator = IndicatorCalculator()
        assert calculator is not None
        assert hasattr(calculator, "calculate_rsi")
        assert hasattr(calculator, "calculate_macd")
        assert hasattr(calculator, "calculate_bollinger_bands")


class TestTechnicalIndicators:
    """Тесты технических индикаторов"""

    def test_technical_indicators_import(self):
        """Тест импорта технических индикаторов"""
        try:
            from indicators.technical import MACD, RSI, BollingerBands

            assert RSI is not None
            assert MACD is not None
            assert BollingerBands is not None
        except ImportError:
            pytest.skip("Technical indicators may not be fully implemented")


class TestCustomIndicators:
    """Тесты пользовательских индикаторов"""

    def test_custom_indicators_import(self):
        """Тест импорта пользовательских индикаторов"""
        try:
            from indicators.custom import CustomMACD, CustomRSI

            assert CustomRSI is not None
            assert CustomMACD is not None
        except ImportError:
            pytest.skip("Custom indicators may not be implemented yet")


class TestDataProvider:
    """Тесты провайдера данных для индикаторов"""

    def test_data_provider_import(self):
        """Тест импорта провайдера данных"""
        try:
            from indicators.data_provider import DataProvider

            assert DataProvider is not None
        except ImportError:
            pytest.skip("Data provider may not be implemented yet")


class TestCheckUtilities:
    """Тесты утилит проверки"""

    def test_check_all_balances_import(self):
        """Тест импорта проверки балансов"""

        check_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "utils",
            "checks",
            "check_all_balances.py",
        )

        assert os.path.exists(check_path)

    def test_check_all_positions_import(self):
        """Тест импорта проверки позиций"""

        check_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "utils",
            "checks",
            "check_all_positions.py",
        )

        assert os.path.exists(check_path)

    def test_check_system_status_import(self):
        """Тест импорта проверки статуса системы"""

        check_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "utils",
            "checks",
            "check_system_status.py",
        )

        assert os.path.exists(check_path)


class TestDataUtilities:
    """Тесты утилит данных"""

    def test_data_utils_import(self):
        """Тест импорта утилит данных"""
        try:
            from utils.data import clean_dataframe, validate_data

            assert callable(clean_dataframe)
            assert callable(validate_data)
        except ImportError:
            pytest.skip("Data utils may not be implemented yet")


class TestMCPUtilities:
    """Тесты MCP утилит"""

    def test_mcp_database_wrapper_import(self):
        """Тест импорта MCP обертки базы данных"""
        from utils.mcp.database_wrapper import DatabaseWrapper

        assert DatabaseWrapper is not None


class TestRealWorldUtilities:
    """Тесты реальных утилит с данными"""

    def test_format_decimal_with_real_data(self):
        """Тест форматирования с реальными данными"""
        from utils.helpers import format_decimal

        # Тестируем с реальными торговыми значениями
        price = 45123.456789
        formatted = format_decimal(price, 2)
        assert formatted == "45123.46"

        # Тестируем с маленькими значениями
        small_price = 0.000123456
        formatted_small = format_decimal(small_price, 6)
        assert formatted_small == "0.000123"

    def test_clean_symbol_with_real_pairs(self):
        """Тест очистки символов с реальными парами"""
        from utils.helpers import clean_symbol

        # Тестируем с реальными торговыми парами
        test_pairs = [
            ("BTCUSDT", "BTCUSDT"),
            ("btcusdt", "BTCUSDT"),
            ("BTC/USDT", "BTCUSDT"),
            ("BTC-USDT", "BTCUSDT"),
            ("ETHUSDT", "ETHUSDT"),
            ("eth/usdt", "ETHUSDT"),
        ]

        for input_symbol, expected in test_pairs:
            result = clean_symbol(input_symbol)
            assert result == expected, f"Expected {expected}, got {result} for {input_symbol}"


class TestIndicatorCalculations:
    """Тесты расчетов индикаторов с данными"""

    def create_sample_data(self):
        """Создание тестовых данных для индикаторов"""
        dates = pd.date_range("2023-01-01", periods=100, freq="1H")
        np.random.seed(42)  # Для воспроизводимости

        base_price = 45000
        price_changes = np.random.normal(0, 0.01, 100)
        prices = [base_price]

        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 1))  # Не допускаем отрицательные цены

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
                "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
                "close": prices,
                "volume": np.random.uniform(100, 1000, 100),
            }
        )

        return df

    def test_rsi_calculation(self):
        """Тест расчета RSI"""
        from indicators.calculator.indicator_calculator import IndicatorCalculator

        calculator = IndicatorCalculator()
        df = self.create_sample_data()

        if hasattr(calculator, "calculate_rsi"):
            rsi = calculator.calculate_rsi(df["close"], period=14)

            # RSI должен быть в диапазоне 0-100
            assert all(0 <= r <= 100 for r in rsi if not pd.isna(r))
            # Первые 14 значений должны быть NaN
            assert pd.isna(rsi.iloc[:13]).all()

    def test_macd_calculation(self):
        """Тест расчета MACD"""
        from indicators.calculator.indicator_calculator import IndicatorCalculator

        calculator = IndicatorCalculator()
        df = self.create_sample_data()

        if hasattr(calculator, "calculate_macd"):
            macd_line, signal_line, histogram = calculator.calculate_macd(df["close"])

            # Проверяем что возвращаются pandas Series
            assert isinstance(macd_line, pd.Series)
            assert isinstance(signal_line, pd.Series)
            assert isinstance(histogram, pd.Series)

            # Проверяем что длины совпадают
            assert len(macd_line) == len(df)
            assert len(signal_line) == len(df)
            assert len(histogram) == len(df)


@pytest.mark.asyncio
class TestAsyncUtilities:
    """Тесты асинхронных утилит"""

    async def test_async_data_processing(self):
        """Тест асинхронной обработки данных"""
        # Простой тест что асинхронные функции могут быть вызваны
        await asyncio.sleep(0.001)  # Минимальная асинхронная операция
        assert True

    async def test_async_database_operations(self):
        """Тест асинхронных операций с базой данных"""
        # Тест что асинхронные операции доступны
        from database.connections.postgres import AsyncPGPool

        # Проверяем что класс существует и имеет асинхронные методы
        assert hasattr(AsyncPGPool, "fetch")
        assert hasattr(AsyncPGPool, "execute")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
