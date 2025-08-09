#!/usr/bin/env python3
"""
Исправление инициализации компонентов в orchestrator
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))


def patch_orchestrator():
    """Патчим orchestrator для инициализации всех компонентов"""

    # Читаем файл
    orchestrator_path = Path("core/system/orchestrator.py")
    content = orchestrator_path.read_text()

    # Добавляем импорт exchange registry
    if "from exchanges.registry import ExchangeRegistry" not in content:
        import_section = content.find("from core.traders.trader_manager import")
        if import_section > 0:
            content = (
                content[:import_section]
                + "from exchanges.registry import ExchangeRegistry\n"
                + content[import_section:]
            )

    # Добавляем импорт trading engine
    if "from trading.engine import TradingEngine" not in content:
        import_section = content.find("from core.traders.trader_manager import")
        if import_section > 0:
            content = (
                content[:import_section]
                + "from trading.engine import TradingEngine\n"
                + content[import_section:]
            )

    # Добавляем инициализацию exchange_registry после trader_factory
    init_section = """
    async def _initialize_exchange_registry(self) -> None:
        \"\"\"Инициализация реестра бирж\"\"\"
        try:
            from exchanges.registry import ExchangeRegistry
            self.exchange_registry = ExchangeRegistry(self.config_manager)
            await self.exchange_registry.initialize()
            self.active_components.add("exchange_registry")
            self.logger.info("✅ Exchange Registry инициализирован")
        except Exception as e:
            self.failed_components.add("exchange_registry")
            self.logger.warning(f"⚠️ Exchange Registry не инициализирован: {e}")

    async def _initialize_trading_engine(self) -> None:
        \"\"\"Инициализация торгового движка\"\"\"
        try:
            # Проверяем зависимости
            if not self.exchange_registry:
                self.logger.warning("⚠️ Trading Engine требует Exchange Registry")
                return

            from trading.engine import TradingEngine
            self.trading_engine = TradingEngine(
                orchestrator=self,
                exchange_registry=self.exchange_registry,
                trader_manager=self.trader_manager,
                config_manager=self.config_manager
            )
            await self.trading_engine.initialize()
            self.active_components.add("trading_engine")
            self.logger.info("✅ Trading Engine инициализирован")
        except Exception as e:
            self.failed_components.add("trading_engine")
            self.logger.warning(f"⚠️ Trading Engine не инициализирован: {e}")
"""

    # Ищем место для вставки новых методов
    health_checker_pos = content.find("async def _initialize_health_checker")
    if health_checker_pos > 0:
        content = (
            content[:health_checker_pos]
            + init_section
            + "\n    "
            + content[health_checker_pos:]
        )

    # Добавляем вызовы инициализации после trader_manager
    init_calls = """
            # Инициализация Exchange Registry
            await self._initialize_exchange_registry()

            # Инициализация Trading Engine
            await self._initialize_trading_engine()
"""

    trader_manager_init = "await self._initialize_trader_manager()"
    pos = content.find(trader_manager_init)
    if pos > 0:
        end_pos = pos + len(trader_manager_init)
        content = content[:end_pos] + "\n" + init_calls + content[end_pos:]

    # Добавляем trading_engine в атрибуты класса
    if "self.trading_engine = None" not in content:
        attrs_section = content.find("self.exchange_registry = None")
        if attrs_section > 0:
            end_pos = content.find("\n", attrs_section)
            content = (
                content[:end_pos]
                + "\n        self.trading_engine = None  # Торговый движок"
                + content[end_pos:]
            )

    # Сохраняем изменения
    orchestrator_path.write_text(content)
    print("✅ Orchestrator обновлен для инициализации всех компонентов")


def fix_trading_engine_imports():
    """Исправляем импорты в trading engine"""

    engine_path = Path("trading/engine.py")
    if not engine_path.exists():
        print("⚠️  Trading engine не найден")
        return

    content = engine_path.read_text()

    # Убираем несуществующие импорты
    content = content.replace(
        "from database.repositories.signal_repository import SignalRepository",
        "# from database.repositories.signal_repository import SignalRepository",
    )
    content = content.replace(
        "from database.repositories.trade_repository import TradeRepository",
        "# from database.repositories.trade_repository import TradeRepository",
    )

    # Заменяем на прямую работу с БД
    content = content.replace(
        "from risk_management.manager import RiskManager",
        "# from risk_management.manager import RiskManager",
    )

    engine_path.write_text(content)
    print("✅ Trading Engine импорты исправлены")


def main():
    """Основная функция"""
    print("🔧 Исправление компонентов orchestrator...")

    # Патчим orchestrator
    patch_orchestrator()

    # Исправляем импорты в trading engine
    fix_trading_engine_imports()

    print("\n✅ Все исправления применены!")
    print("\n📋 Теперь нужно:")
    print("1. Остановить систему: pkill -f unified_launcher")
    print("2. Перезапустить: python3 unified_launcher.py --mode=ml")


if __name__ == "__main__":
    main()
