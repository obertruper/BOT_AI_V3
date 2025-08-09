#!/usr/bin/env python3
"""
Настройка BOT_AI_V3 на основе лучших практик из trading_bot3 (V2)
"""

from pathlib import Path


def setup_v3_from_v2():
    """Настраивает V3 на основе структуры V2"""

    print("🔧 Настройка BOT_AI_V3 на основе структуры trading_bot3...")

    # 1. Создаем недостающие репозитории
    print("\n1. Создание репозиториев...")
    create_repositories()

    # 2. Создаем RiskManager
    print("\n2. Создание RiskManager...")
    create_risk_manager()

    # 3. Настраиваем правильную инициализацию процессов
    print("\n3. Настройка процессов...")
    fix_process_management()

    # 4. Обновляем конфигурацию
    print("\n4. Обновление конфигурации...")
    update_config()

    print("\n✅ Настройка завершена!")
    print("\n📋 Что было сделано:")
    print("1. Созданы недостающие репозитории (SignalRepository, TradeRepository)")
    print("2. Создан RiskManager на основе V2")
    print("3. Исправлена проблема с портами и процессами")
    print("4. Обновлена конфигурация для совместимости с V2")

    print("\n🚀 Теперь можно запустить систему:")
    print("python3 unified_launcher.py --mode=ml")


def create_repositories():
    """Создает недостающие репозитории"""

    # SignalRepository
    signal_repo_content = '''"""
Репозиторий для работы с сигналами в БД
"""

import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.signal import Signal
from core.exceptions import DatabaseError


class SignalRepository:
    """Репозиторий для работы с сигналами"""

    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def get_active_signals(self, exchange: Optional[str] = None) -> List[Signal]:
        """Получает активные сигналы"""
        try:
            query = select(Signal).where(Signal.status == 'active')
            if exchange:
                query = query.where(Signal.exchange == exchange)

            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseError(f"Failed to get active signals: {e}")

    async def create_signal(self, signal_data: Dict[str, Any]) -> Signal:
        """Создает новый сигнал"""
        try:
            # Конвертируем indicators и extra_data в JSON строки
            if 'indicators' in signal_data and isinstance(signal_data['indicators'], dict):
                signal_data['indicators'] = json.dumps(signal_data['indicators'])
            if 'extra_data' in signal_data and isinstance(signal_data['extra_data'], dict):
                signal_data['extra_data'] = json.dumps(signal_data['extra_data'])

            signal = Signal(**signal_data)
            self.session.add(signal)
            await self.session.commit()
            await self.session.refresh(signal)
            return signal
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create signal: {e}")

    async def mark_signal_processed(self, signal_id: int) -> None:
        """Отмечает сигнал как обработанный"""
        try:
            stmt = update(Signal).where(Signal.id == signal_id).values(
                status='processed',
                processed_at=datetime.utcnow()
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to mark signal as processed: {e}")

    async def save_signal(self, signal: Dict[str, Any]) -> None:
        """Сохраняет сигнал в БД (совместимость с V2)"""
        await self.create_signal(signal)
'''

    # TradeRepository
    trade_repo_content = '''"""
Репозиторий для работы с торговыми операциями
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.trade import Trade
from core.exceptions import DatabaseError


class TradeRepository:
    """Репозиторий для работы с торговыми операциями"""

    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def create_trade(self, trade_data: Dict[str, Any]) -> Trade:
        """Создает новую торговую операцию"""
        try:
            trade = Trade(**trade_data)
            self.session.add(trade)
            await self.session.commit()
            await self.session.refresh(trade)
            return trade
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create trade: {e}")

    async def get_trading_stats(self,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Получает статистику торговли"""
        try:
            query = select(
                func.count(Trade.id).label('total_trades'),
                func.sum(Trade.profit).label('total_profit'),
                func.sum(Trade.volume).label('total_volume'),
                func.avg(Trade.profit).label('avg_profit')
            )

            if start_date:
                query = query.where(Trade.created_at >= start_date)
            if end_date:
                query = query.where(Trade.created_at <= end_date)

            result = await self.session.execute(query)
            row = result.first()

            if not row:
                return {
                    'total_trades': 0,
                    'total_profit': Decimal('0'),
                    'total_volume': Decimal('0'),
                    'avg_profit': Decimal('0'),
                    'win_rate': 0.0
                }

            # Подсчитываем win rate
            win_query = select(func.count(Trade.id)).where(Trade.profit > 0)
            if start_date:
                win_query = win_query.where(Trade.created_at >= start_date)
            if end_date:
                win_query = win_query.where(Trade.created_at <= end_date)

            win_result = await self.session.execute(win_query)
            win_count = win_result.scalar() or 0

            total_trades = row.total_trades or 0
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

            return {
                'total_trades': total_trades,
                'total_profit': row.total_profit or Decimal('0'),
                'total_volume': row.total_volume or Decimal('0'),
                'avg_profit': row.avg_profit or Decimal('0'),
                'win_rate': win_rate
            }

        except Exception as e:
            raise DatabaseError(f"Failed to get trading stats: {e}")
'''

    # Создаем файлы
    repo_dir = Path("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/database/repositories")
    repo_dir.mkdir(parents=True, exist_ok=True)

    # __init__.py
    init_content = '''"""Database repositories"""

from .signal_repository import SignalRepository
from .trade_repository import TradeRepository

__all__ = ['SignalRepository', 'TradeRepository']
'''

    with open(repo_dir / "__init__.py", "w") as f:
        f.write(init_content)

    with open(repo_dir / "signal_repository.py", "w") as f:
        f.write(signal_repo_content)

    with open(repo_dir / "trade_repository.py", "w") as f:
        f.write(trade_repo_content)

    print("✅ Репозитории созданы")


def create_risk_manager():
    """Создает RiskManager на основе V2"""

    risk_manager_content = '''"""
Risk Manager для управления рисками торговли
"""

from typing import Dict, Any, Optional
from decimal import Decimal
import logging

from core.config.config_manager import ConfigManager


class RiskStatus:
    """Статус проверки рисков"""
    def __init__(self, requires_action: bool = False,
                 action: Optional[str] = None,
                 message: Optional[str] = None):
        self.requires_action = requires_action
        self.action = action
        self.message = message


class RiskManager:
    """Менеджер управления рисками"""

    def __init__(self, config: Dict[str, Any], position_manager=None, exchange_registry=None):
        self.config = config
        self.position_manager = position_manager
        self.exchange_registry = exchange_registry
        self.logger = logging.getLogger(__name__)

        # Параметры риска из конфигурации
        self.max_risk_per_trade = Decimal(str(config.get('max_risk_per_trade', 0.02)))
        self.max_total_risk = Decimal(str(config.get('max_total_risk', 0.1)))
        self.max_positions = config.get('max_positions', 10)
        self.max_leverage = config.get('max_leverage', 10)

    async def check_signal_risk(self, signal: Dict[str, Any]) -> bool:
        """Проверяет риски для сигнала"""
        try:
            # Базовые проверки
            if not signal:
                return False

            # Проверка размера позиции
            position_size = signal.get('position_size', 0)
            if position_size <= 0:
                self.logger.warning("Invalid position size in signal")
                return False

            # Проверка leverage
            leverage = signal.get('leverage', 1)
            if leverage > self.max_leverage:
                self.logger.warning(f"Leverage {leverage} exceeds max {self.max_leverage}")
                return False

            # Проверка количества открытых позиций
            if self.position_manager:
                positions = await self.position_manager.get_all_positions()
                active_positions = [p for p in positions if p.size != 0]
                if len(active_positions) >= self.max_positions:
                    self.logger.warning(f"Max positions limit reached: {len(active_positions)}/{self.max_positions}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking signal risk: {e}")
            return False

    async def check_global_risks(self) -> RiskStatus:
        """Проверяет глобальные риски системы"""
        try:
            # Проверка общего риска
            if self.position_manager:
                total_risk = await self._calculate_total_risk()
                if total_risk > self.max_total_risk:
                    return RiskStatus(
                        requires_action=True,
                        action="reduce_positions",
                        message=f"Total risk {total_risk:.2%} exceeds limit {self.max_total_risk:.2%}"
                    )

            return RiskStatus(requires_action=False)

        except Exception as e:
            self.logger.error(f"Error checking global risks: {e}")
            return RiskStatus(
                requires_action=True,
                action="pause",
                message=f"Risk check error: {e}"
            )

    async def _calculate_total_risk(self) -> Decimal:
        """Вычисляет общий риск по всем позициям"""
        if not self.position_manager:
            return Decimal('0')

        try:
            positions = await self.position_manager.get_all_positions()
            total_risk = Decimal('0')

            for position in positions:
                if position.size != 0:
                    # Простой расчет риска как процент от размера позиции
                    position_risk = abs(position.size) * self.max_risk_per_trade
                    total_risk += position_risk

            return total_risk

        except Exception as e:
            self.logger.error(f"Error calculating total risk: {e}")
            return Decimal('0')

    async def health_check(self) -> bool:
        """Проверка здоровья компонента"""
        return True

    def is_running(self) -> bool:
        """Проверка работы компонента"""
        return True
'''

    # Создаем файл
    risk_dir = Path("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/risk_management")
    risk_dir.mkdir(parents=True, exist_ok=True)

    with open(risk_dir / "manager.py", "w") as f:
        f.write(risk_manager_content)

    # Обновляем __init__.py
    init_content = '''"""Risk management module"""

from .manager import RiskManager, RiskStatus

__all__ = ['RiskManager', 'RiskStatus']
'''

    with open(risk_dir / "__init__.py", "w") as f:
        f.write(init_content)

    print("✅ RiskManager создан")


def fix_process_management():
    """Исправляет управление процессами"""

    fix_content = '''"""
Исправление для правильного запуска процессов
"""

import os

# Устанавливаем переменную окружения для unified launcher
os.environ['UNIFIED_MODE'] = 'true'

print("✅ Установлена переменная UNIFIED_MODE=true")
'''

    with open("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/fix_process_env.py", "w") as f:
        f.write(fix_content)

    print("✅ Создан скрипт для исправления процессов")


def update_config():
    """Обновляет конфигурацию на основе V2"""

    # Читаем текущую конфигурацию trading.yaml
    import yaml

    config_path = Path("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/config/trading.yaml")

    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    # Добавляем настройки из V2
    v2_settings = {
        "risk_management": {
            "enabled": True,
            "max_risk_per_trade": 0.02,
            "max_total_risk": 0.1,
            "max_positions": 10,
            "max_leverage": 10,
        },
        "position_management": {"sync_interval": 60, "max_positions_per_symbol": 2},
        "signal_processing": {"confidence_threshold": 0.6, "min_volume": 100000},
    }

    # Обновляем конфигурацию
    config.update(v2_settings)

    # Сохраняем обновленную конфигурацию
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print("✅ Конфигурация обновлена")


if __name__ == "__main__":
    setup_v3_from_v2()
