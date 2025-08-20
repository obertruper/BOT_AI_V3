#!/usr/bin/env python3
"""
Общие фикстуры для Dynamic SL/TP тестирования
Централизованное место для создания тестовых данных и компонентов
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from trading.orders.dynamic_sltp_calculator import DynamicSLTPCalculator


@pytest.fixture
def dynamic_sltp_calculator():
    """Базовый калькулятор Dynamic SL/TP"""
    return DynamicSLTPCalculator()


@pytest.fixture
def sample_candles_low_volatility():
    """Свечи с низкой волатильностью для тестирования"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
    
    data = []
    base_price = 50000
    
    for i, date in enumerate(dates):
        # Низкая волатильность - изменения до 0.1%
        price_change = np.random.normal(0, 0.001)
        current_price = base_price * (1 + price_change)
        
        data.append({
            'timestamp': date,
            'open': current_price,
            'high': current_price * (1 + abs(np.random.normal(0, 0.0005))),
            'low': current_price * (1 - abs(np.random.normal(0, 0.0005))),
            'close': current_price * (1 + np.random.normal(0, 0.0003)),
            'volume': np.random.uniform(100, 200)
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_candles_high_volatility():
    """Свечи с высокой волатильностью для тестирования"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
    
    data = []
    base_price = 50000
    
    for i, date in enumerate(dates):
        # Высокая волатильность - изменения до 2%
        price_change = np.random.normal(0, 0.02)
        current_price = base_price * (1 + price_change)
        
        data.append({
            'timestamp': date,
            'open': current_price,
            'high': current_price * (1 + abs(np.random.normal(0, 0.01))),
            'low': current_price * (1 - abs(np.random.normal(0, 0.01))),
            'close': current_price * (1 + np.random.normal(0, 0.005)),
            'volume': np.random.uniform(500, 1000)
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_candles_medium_volatility():
    """Свечи со средней волатильностью для тестирования"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
    
    data = []
    base_price = 50000
    
    for i, date in enumerate(dates):
        # Средняя волатильность - изменения до 1%
        price_change = np.random.normal(0, 0.01)
        current_price = base_price * (1 + price_change)
        
        data.append({
            'timestamp': date,
            'open': current_price,
            'high': current_price * (1 + abs(np.random.normal(0, 0.005))),
            'low': current_price * (1 - abs(np.random.normal(0, 0.005))),
            'close': current_price * (1 + np.random.normal(0, 0.002)),
            'volume': np.random.uniform(300, 600)
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def mixed_volatility_candles():
    """Свечи со смешанной волатильностью (переходы)"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    
    data = []
    base_price = 50000
    
    for i, date in enumerate(dates):
        # Переход от низкой к высокой волатильности
        if i < 30:
            # Низкая волатильность
            price_change = np.random.normal(0, 0.001)
            vol_factor = 0.0005
        elif i < 70:
            # Переходный период
            vol_increase = (i - 30) / 40  # от 0 до 1
            vol_std = 0.001 + vol_increase * 0.019  # от 0.001 до 0.02
            price_change = np.random.normal(0, vol_std)
            vol_factor = 0.0005 + vol_increase * 0.0095
        else:
            # Высокая волатильность
            price_change = np.random.normal(0, 0.02)
            vol_factor = 0.01
            
        current_price = base_price * (1 + price_change)
        
        data.append({
            'timestamp': date,
            'open': current_price,
            'high': current_price * (1 + abs(np.random.normal(0, vol_factor))),
            'low': current_price * (1 - abs(np.random.normal(0, vol_factor))),
            'close': current_price * (1 + np.random.normal(0, vol_factor/2)),
            'volume': np.random.uniform(100 + i*5, 200 + i*8)
        })
    
    return pd.DataFrame(data)


@pytest.fixture(params=[
    (50000, 0.75, 'BUY'),
    (30000, 0.85, 'SELL'),
    (100000, 0.65, 'BUY'),
    (25000, 0.90, 'SELL')
])
def calculation_params(request):
    """Параметрические фикстуры для различных сценариев расчета"""
    current_price, confidence, signal_type = request.param
    return {
        'current_price': current_price,
        'confidence': confidence, 
        'signal_type': signal_type
    }


@pytest.fixture
def mock_ml_manager():
    """Мок для ML Manager"""
    mock = Mock()
    mock.get_prediction = Mock(return_value={
        'signal_type': 'LONG',
        'confidence': 0.75,
        'signal_strength': 0.65,
        'metadata': {
            'model_version': '1.0',
            'features_used': 240
        }
    })
    return mock


@pytest.fixture
def mock_exchange_registry():
    """Мок для Exchange Registry"""
    mock = Mock()
    mock_exchange = Mock()
    mock_exchange.place_order = Mock(return_value={'success': True, 'order_id': 'TEST123'})
    mock_exchange.get_balance = Mock(return_value={'USDT': 1000})
    mock_exchange.get_position = Mock(return_value={'size': 0})
    
    mock.get_exchange = Mock(return_value=mock_exchange)
    return mock


@pytest.fixture
def mock_order_manager():
    """Мок для Order Manager"""
    mock = Mock()
    mock.submit_order = Mock(return_value={'success': True, 'order_id': 'ORD123'})
    mock.get_active_orders = Mock(return_value=[])
    mock.cancel_order = Mock(return_value={'success': True})
    return mock


@pytest.fixture
def realistic_market_scenario():
    """Реалистичный сценарий рыночных условий"""
    return {
        'symbol': 'BTCUSDT',
        'current_price': 45000,
        'recent_high': 48000,
        'recent_low': 42000,
        'daily_volume': 1500000000,
        'market_trend': 'bullish',
        'volatility_regime': 'medium',
        'news_sentiment': 'positive'
    }


@pytest.fixture
def performance_test_data():
    """Большой датасет для performance тестирования"""
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
    
    data = []
    base_price = 50000
    current_price = base_price
    
    for i, date in enumerate(dates):
        # Случайные реалистичные изменения
        change = np.random.normal(0, 0.005)
        current_price *= (1 + change)
        
        # Обеспечиваем положительные цены
        current_price = max(current_price, base_price * 0.5)
        current_price = min(current_price, base_price * 2)
        
        data.append({
            'timestamp': date,
            'open': current_price,
            'high': current_price * (1 + abs(np.random.normal(0, 0.003))),
            'low': current_price * (1 - abs(np.random.normal(0, 0.003))),
            'close': current_price * (1 + np.random.normal(0, 0.001)),
            'volume': np.random.uniform(500, 2000)
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def expected_results_validator():
    """Валидатор ожидаемых результатов"""
    def validate_dynamic_levels(result, signal_type, confidence):
        """Валидация результатов расчета динамических уровней"""
        # Проверяем обязательные поля
        required_fields = [
            'stop_loss_pct', 'take_profit_pct',
            'stop_loss_price', 'take_profit_price',
            'partial_tp_levels', 'volatility_data',
            'expected_value', 'risk_reward_ratio'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Проверяем диапазоны
        assert 0.5 <= result['stop_loss_pct'] <= 5.0, "SL% out of range"
        assert 1.5 <= result['take_profit_pct'] <= 10.0, "TP% out of range" 
        assert result['risk_reward_ratio'] >= 2.0, "RR ratio too low"
        
        # Проверяем логику для разных типов сигналов
        if signal_type == 'BUY':
            assert result['stop_loss_price'] < result['take_profit_price'], "BUY: SL should be < TP"
        elif signal_type == 'SELL':
            assert result['stop_loss_price'] > result['take_profit_price'], "SELL: SL should be > TP"
        
        # Проверяем корреляцию с confidence
        if confidence >= 0.8:
            assert result['stop_loss_pct'] <= 2.0, "High confidence should have tighter SL"
        
        # Проверяем partial TP уровни
        assert len(result['partial_tp_levels']) >= 2, "Should have at least 2 partial TP levels"
        
        for i, level in enumerate(result['partial_tp_levels']):
            assert 'percent' in level and 'price' in level
            if i > 0:
                # Проверяем возрастающий порядок
                prev_percent = result['partial_tp_levels'][i-1]['percent']
                assert level['percent'] > prev_percent, "Partial TP percents should be increasing"
        
        return True
    
    return validate_dynamic_levels


@pytest.fixture
def stress_test_scenarios():
    """Сценарии для стресс-тестирования"""
    return {
        'extreme_volatility': {
            'volatility_std': 0.1,  # 10% стандартное отклонение
            'price_range': (10000, 100000),
            'confidence_range': (0.1, 0.99)
        },
        'market_crash': {
            'volatility_std': 0.05,
            'price_trend': -0.02,  # Падающий тренд
            'confidence_range': (0.3, 0.7)
        },
        'bull_run': {
            'volatility_std': 0.03,
            'price_trend': 0.015,  # Растущий тренд
            'confidence_range': (0.6, 0.95)
        },
        'sideways_market': {
            'volatility_std': 0.008,
            'price_trend': 0.0,
            'confidence_range': (0.4, 0.8)
        }
    }


@pytest.fixture(scope="session")
def test_database_config():
    """Конфигурация тестовой базы данных"""
    return {
        'host': 'localhost',
        'port': 5555,
        'database': 'bot_trading_v3_test',
        'user': 'test_user',
        'password': 'test_pass'
    }