#!/usr/bin/env python3
"""
Unit тесты для DynamicSLTPCalculator
Тестирование расчета динамических уровней Stop Loss и Take Profit
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from trading.orders.dynamic_sltp_calculator import DynamicSLTPCalculator


class TestDynamicSLTPCalculator:
    """Тесты для класса DynamicSLTPCalculator"""
    
    @pytest.fixture
    def calculator(self):
        """Создание экземпляра калькулятора"""
        return DynamicSLTPCalculator()
    
    @pytest.fixture
    def sample_candles_low_volatility(self):
        """Свечи с низкой волатильностью (ATR ~0.5%)"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        base_price = 50000
        candles = []
        
        for i in range(100):
            # Низкая волатильность - маленькие изменения
            change = np.random.normal(0, 0.001)  # 0.1% стандартное отклонение
            price = base_price * (1 + change)
            
            candles.append({
                'timestamp': dates[i],
                'open': price,
                'high': price * 1.002,  # +0.2%
                'low': price * 0.998,   # -0.2%
                'close': price * (1 + np.random.normal(0, 0.0005)),
                'volume': np.random.uniform(100, 200)
            })
        
        return pd.DataFrame(candles)
    
    @pytest.fixture
    def sample_candles_high_volatility(self):
        """Свечи с высокой волатильностью (ATR ~3%)"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        base_price = 50000
        candles = []
        
        for i in range(100):
            # Высокая волатильность - большие изменения
            change = np.random.normal(0, 0.015)  # 1.5% стандартное отклонение
            price = base_price * (1 + change)
            
            candles.append({
                'timestamp': dates[i],
                'open': price,
                'high': price * 1.03,  # +3%
                'low': price * 0.97,   # -3%
                'close': price * (1 + np.random.normal(0, 0.01)),
                'volume': np.random.uniform(500, 1000)
            })
        
        return pd.DataFrame(candles)
    
    @pytest.mark.asyncio
    async def test_calculate_atr_low_volatility(self, calculator, sample_candles_low_volatility):
        """Тест расчета ATR для низкой волатильности"""
        candles = sample_candles_low_volatility
        atr = calculator._calculate_atr(candles)
        
        # При низкой волатильности ATR должен быть маленьким
        assert atr > 0, "ATR должен быть положительным"
        assert atr < 300, "ATR должен быть меньше 300 для низкой волатильности"
        
    @pytest.mark.asyncio
    async def test_calculate_atr_high_volatility(self, calculator, sample_candles_high_volatility):
        """Тест расчета ATR для высокой волатильности"""
        candles = sample_candles_high_volatility
        atr = calculator._calculate_atr(candles)
        
        # При высокой волатильности ATR должен быть большим
        assert atr > 1000, "ATR должен быть больше 1000 для высокой волатильности"
        assert atr < 3000, "ATR не должен быть слишком большим"
    
    @pytest.mark.asyncio
    async def test_determine_volatility_regime_low(self, calculator, sample_candles_low_volatility):
        """Тест определения режима низкой волатильности"""
        candles = sample_candles_low_volatility
        current_price = 50000
        
        atr = calculator._calculate_atr(candles)
        normalized_vol = calculator._normalize_volatility(atr, current_price)
        regime = calculator._determine_volatility_regime(normalized_vol)
        
        assert regime == "low", f"Должен быть режим 'low', получен {regime}"
    
    @pytest.mark.asyncio
    async def test_determine_volatility_regime_high(self, calculator, sample_candles_high_volatility):
        """Тест определения режима высокой волатильности"""
        candles = sample_candles_high_volatility
        current_price = 50000
        
        atr = calculator._calculate_atr(candles)
        normalized_vol = calculator._normalize_volatility(atr, current_price)
        regime = calculator._determine_volatility_regime(normalized_vol)
        
        assert regime == "high", f"Должен быть режим 'high', получен {regime}"
    
    @pytest.mark.asyncio
    async def test_calculate_dynamic_levels_buy_low_volatility(self, calculator, sample_candles_low_volatility):
        """Тест расчета динамических уровней для BUY при низкой волатильности"""
        candles = sample_candles_low_volatility
        current_price = 50000
        confidence = 0.85
        signal_type = "BUY"
        
        result = calculator.calculate_dynamic_levels(
            current_price=current_price,
            candles=candles,
            confidence=confidence,
            signal_type=signal_type
        )
        
        # Проверяем структуру результата
        assert "stop_loss_pct" in result
        assert "take_profit_pct" in result
        assert "stop_loss_price" in result
        assert "take_profit_price" in result
        assert "partial_tp_levels" in result
        assert "volatility_data" in result
        assert "expected_value" in result
        
        # При низкой волатильности SL должен быть 1-1.3%
        assert 0.8 <= result["stop_loss_pct"] <= 1.5
        # TP должен быть 3.6-4.2%
        assert 3.0 <= result["take_profit_pct"] <= 5.0
        
        # Проверяем цены для BUY
        assert result["stop_loss_price"] < current_price
        assert result["take_profit_price"] > current_price
    
    @pytest.mark.asyncio
    async def test_calculate_dynamic_levels_sell_high_volatility(self, calculator, sample_candles_high_volatility):
        """Тест расчета динамических уровней для SELL при высокой волатильности"""
        candles = sample_candles_high_volatility
        current_price = 50000
        confidence = 0.65
        signal_type = "SELL"
        
        result = calculator.calculate_dynamic_levels(
            current_price=current_price,
            candles=candles,
            confidence=confidence,
            signal_type=signal_type
        )
        
        # При высокой волатильности SL должен быть 1.7-2%
        assert 1.5 <= result["stop_loss_pct"] <= 2.5
        # TP должен быть 5.4-6%
        assert 4.5 <= result["take_profit_pct"] <= 7.0
        
        # Проверяем цены для SELL
        assert result["stop_loss_price"] > current_price
        assert result["take_profit_price"] < current_price
    
    @pytest.mark.asyncio
    async def test_partial_tp_levels(self, calculator, sample_candles_low_volatility):
        """Тест расчета уровней частичного закрытия"""
        candles = sample_candles_low_volatility
        current_price = 50000
        
        result = calculator.calculate_dynamic_levels(
            current_price=current_price,
            candles=candles,
            confidence=0.8,
            signal_type="BUY"
        )
        
        partial_levels = result["partial_tp_levels"]
        
        # Должно быть 3 уровня
        assert len(partial_levels) == 3
        
        # Проверяем процентные соотношения
        assert partial_levels[0]["percent"] == 40  # 40% от TP
        assert partial_levels[1]["percent"] == 70  # 70% от TP
        assert partial_levels[2]["percent"] == 100  # 100% от TP
        
        # Проверяем, что цены возрастают для BUY
        assert partial_levels[0]["price"] < partial_levels[1]["price"]
        assert partial_levels[1]["price"] < partial_levels[2]["price"]
        assert partial_levels[2]["price"] == result["take_profit_price"]
    
    @pytest.mark.asyncio
    async def test_confidence_adjustments_low(self, calculator, sample_candles_low_volatility):
        """Тест корректировок при низкой уверенности"""
        candles = sample_candles_low_volatility
        current_price = 50000
        
        # Низкая уверенность
        low_conf_result = calculator.calculate_dynamic_levels(
            current_price=current_price,
            candles=candles,
            confidence=0.45,
            signal_type="BUY"
        )
        
        # Высокая уверенность
        high_conf_result = calculator.calculate_dynamic_levels(
            current_price=current_price,
            candles=candles,
            confidence=0.95,
            signal_type="BUY"
        )
        
        # При низкой уверенности TP должен быть больше (увеличен на 15%)
        assert low_conf_result["take_profit_pct"] > high_conf_result["take_profit_pct"]
        # При высокой уверенности SL может быть меньше (уменьшен на 15%)
        assert high_conf_result["stop_loss_pct"] <= low_conf_result["stop_loss_pct"]
    
    @pytest.mark.asyncio
    async def test_expected_value_calculation(self, calculator, sample_candles_low_volatility):
        """Тест расчета математического ожидания"""
        candles = sample_candles_low_volatility
        current_price = 50000
        
        result = calculator.calculate_dynamic_levels(
            current_price=current_price,
            candles=candles,
            confidence=0.75,
            signal_type="BUY"
        )
        
        ev_data = result["expected_value"]
        
        # Проверяем структуру EV
        assert "win_rate_required" in ev_data
        assert "expected_value_45wr" in ev_data
        assert "risk_reward_ratio" in ev_data
        
        # Risk/Reward должен быть больше 1:3
        assert ev_data["risk_reward_ratio"] >= 3.0
        
        # Точка безубыточности должна быть 22-25%
        assert 0.20 <= ev_data["win_rate_required"] <= 0.30
        
        # При 45% win rate EV должно быть положительным
        assert ev_data["expected_value_45wr"] > 0
    
    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, calculator):
        """Тест обработки недостаточных данных"""
        # Создаем только 10 свечей (меньше 14 для ATR)
        dates = pd.date_range(start='2024-01-01', periods=10, freq='1min')
        candles = pd.DataFrame({
            'timestamp': dates,
            'open': [50000] * 10,
            'high': [50100] * 10,
            'low': [49900] * 10,
            'close': [50050] * 10,
            'volume': [100] * 10
        })
        
        result = calculator.calculate_dynamic_levels(
            current_price=50000,
            candles=candles,
            confidence=0.7,
            signal_type="BUY"
        )
        
        # Должны использоваться значения по умолчанию
        assert result["volatility_data"]["volatility_regime"] == "medium"
        assert result["volatility_data"]["reason"] == "insufficient_data"
        # SL и TP должны быть в средних диапазонах
        assert 1.3 <= result["stop_loss_pct"] <= 1.7
        assert 4.2 <= result["take_profit_pct"] <= 5.4
    
    @pytest.mark.asyncio
    async def test_rsi_adjustments(self, calculator, sample_candles_low_volatility):
        """Тест корректировок на основе RSI"""
        candles = sample_candles_low_volatility.copy()
        current_price = 50000
        
        # Добавляем RSI данные в candles
        candles['rsi'] = 75  # Перекупленность
        
        with patch.object(calculator, '_calculate_rsi_adjustment') as mock_rsi:
            mock_rsi.return_value = 1.1  # Увеличение на 10%
            
            result = calculator.calculate_dynamic_levels(
                current_price=current_price,
                candles=candles,
                confidence=0.7,
                signal_type="BUY",
                rsi=75
            )
            
            # RSI adjustment должен быть вызван
            mock_rsi.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_volume_adjustments(self, calculator, sample_candles_low_volatility):
        """Тест корректировок на основе объема"""
        candles = sample_candles_low_volatility.copy()
        current_price = 50000
        
        # Добавляем данные объема
        candles['volume_sma'] = candles['volume'].rolling(20).mean()
        
        with patch.object(calculator, '_calculate_volume_adjustment') as mock_volume:
            mock_volume.return_value = 0.95  # Уменьшение на 5%
            
            result = calculator.calculate_dynamic_levels(
                current_price=current_price,
                candles=candles,
                confidence=0.7,
                signal_type="BUY",
                volume_ratio=1.5
            )
            
            # Volume adjustment должен быть вызван
            mock_volume.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_multiplier(self, calculator, sample_candles_low_volatility):
        """Тест мультипликатора для торговых сессий"""
        candles = sample_candles_low_volatility
        current_price = 50000
        
        # Тестируем азиатскую сессию (UTC 0-8)
        with patch('trading.orders.dynamic_sltp_calculator.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 4  # Азиатская сессия
            
            result = calculator.calculate_dynamic_levels(
                current_price=current_price,
                candles=candles,
                confidence=0.7,
                signal_type="BUY"
            )
            
            # В азиатскую сессию уровни должны быть меньше
            assert result["volatility_data"].get("session_multiplier", 1.0) == 0.8


@pytest.mark.integration
class TestDynamicSLTPIntegration:
    """Интеграционные тесты для Dynamic SL/TP"""
    
    @pytest.mark.asyncio
    async def test_integration_with_ml_signal(self):
        """Тест интеграции с ML сигналом"""
        calculator = DynamicSLTPCalculator()
        
        # Создаем реалистичные данные
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        candles = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(49000, 51000, 50),
            'high': np.random.uniform(49500, 51500, 50),
            'low': np.random.uniform(48500, 50500, 50),
            'close': np.random.uniform(49000, 51000, 50),
            'volume': np.random.uniform(100, 1000, 50)
        })
        
        # ML сигнал с высокой уверенностью
        ml_signal = {
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'confidence': 0.92,
            'current_price': 50000
        }
        
        # Расчет динамических уровней
        result = calculator.calculate_dynamic_levels(
            current_price=ml_signal['current_price'],
            candles=candles,
            confidence=ml_signal['confidence'],
            signal_type=ml_signal['signal_type']
        )
        
        # Проверяем интеграцию
        assert result is not None
        assert result["stop_loss_pct"] > 0
        assert result["take_profit_pct"] > 0
        assert len(result["partial_tp_levels"]) == 3
        assert result["expected_value"]["risk_reward_ratio"] >= 3.0