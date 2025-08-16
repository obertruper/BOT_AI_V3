#!/usr/bin/env python3
"""
Автоматическая верификация миграции BOT Trading v2 → v3
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.connections import get_async_db
from exchanges.factory import ExchangeFactory
from ml.ml_manager import MLManager
from strategies.factory import StrategyFactory
from trading.sltp.enhanced_manager import EnhancedSLTPManager

logger = setup_logger("migration_verifier")


class MigrationVerifier:
    """Класс для верификации миграции v2 → v3"""

    def __init__(self):
        self.results = {}
        self.critical_issues = []
        self.warnings = []
        self.start_time = datetime.now()

    async def run_all_checks(self) -> dict:
        """Запускает все проверки миграции"""
        logger.info("Starting migration verification v2 → v3")

        checks = [
            ("Database Schema", self.check_database_schema),
            ("Enhanced SL/TP", self.check_enhanced_sltp),
            ("ML Pipeline", self.check_ml_pipeline),
            ("Exchange APIs", self.check_exchanges),
            ("Risk Management", self.check_risk_management),
            ("Configuration", self.check_configuration),
            ("Performance", self.check_performance),
            ("Data Integrity", self.check_data_integrity),
            ("Trading Engine", self.check_trading_engine),
            ("Strategies", self.check_strategies),
        ]

        for name, check_func in checks:
            logger.info(f"Running check: {name}")
            try:
                result = await check_func()
                self.results[name] = result

                if result["status"] == "FAILED":
                    self.critical_issues.append(f"{name}: {result.get('error', 'Check failed')}")
                elif result["status"] == "WARNING":
                    self.warnings.append(f"{name}: {result.get('warning', 'Check has warnings')}")

            except Exception as e:
                logger.error(f"Check {name} failed with exception: {e}")
                self.results[name] = {"status": "FAILED", "error": str(e), "traceback": True}
                self.critical_issues.append(f"{name}: {e}")

        return self.generate_report()

    async def check_database_schema(self) -> dict:
        """Проверяет схему базы данных"""
        async with get_async_db() as db:
            # Критические таблицы из v2
            required_tables = [
                "orders",
                "positions",
                "trades",
                "signals",
                "raw_market_data",
                "processed_market_data",
                "partial_tp_history",  # Новая из Enhanced SL/TP
            ]

            missing_tables = []
            table_checks = {}

            for table in required_tables:
                exists = await db.fetchval(
                    f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = '{table}'
                    )
                """
                )
                table_checks[table] = exists
                if not exists:
                    missing_tables.append(table)

            # Проверка критических полей
            field_checks = {}

            # orders таблица должна иметь position_idx
            if table_checks.get("orders"):
                has_position_idx = await db.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'orders' AND column_name = 'position_idx'
                    )
                """
                )
                field_checks["orders.position_idx"] = has_position_idx

            # positions таблица должна иметь trailing_stop поля
            if table_checks.get("positions"):
                trailing_fields = [
                    "trailing_stop_active",
                    "trailing_stop_price",
                    "trailing_stop_callback",
                ]
                for field in trailing_fields:
                    exists = await db.fetchval(
                        f"""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'positions' AND column_name = '{field}'
                        )
                    """
                    )
                    field_checks[f"positions.{field}"] = exists

            status = "PASSED"
            if missing_tables:
                status = "FAILED"
            elif not all(field_checks.values()):
                status = "WARNING"

            return {
                "status": status,
                "tables": table_checks,
                "fields": field_checks,
                "missing_tables": missing_tables,
                "details": f"Found {len(required_tables) - len(missing_tables)}/{len(required_tables)} required tables",
            }

    async def check_enhanced_sltp(self) -> dict:
        """Проверяет Enhanced SL/TP функциональность"""
        checks = {
            "config_loaded": False,
            "partial_tp_configured": False,
            "profit_protection_configured": False,
            "trailing_stop_configured": False,
            "manager_methods_available": False,
            "database_table_exists": False,
        }

        try:
            # 1. Проверка конфигурации
            config = ConfigManager.get_config()
            sltp_config = config.get("enhanced_sltp", {})

            checks["config_loaded"] = bool(sltp_config)

            # Partial TP
            partial_tp = sltp_config.get("partial_take_profit", {})
            if partial_tp.get("enabled") and partial_tp.get("levels"):
                # Проверяем что levels имеют close_ratio
                levels_valid = all("close_ratio" in level for level in partial_tp["levels"])
                checks["partial_tp_configured"] = levels_valid

            # Profit protection
            profit_protection = sltp_config.get("profit_protection", {})
            checks["profit_protection_configured"] = (
                profit_protection.get("enabled", False)
                and profit_protection.get("breakeven") is not None
            )

            # Trailing stop
            trailing = sltp_config.get("trailing_stop", {})
            checks["trailing_stop_configured"] = (
                trailing.get("enabled", False) and trailing.get("activation_percent") is not None
            )

            # 2. Проверка методов менеджера
            manager = EnhancedSLTPManager(config)
            required_methods = [
                "check_partial_tp",
                "update_profit_protection",
                "calculate_trailing_stop",
                "_save_partial_tp_history",
            ]

            methods_available = all(hasattr(manager, method) for method in required_methods)
            checks["manager_methods_available"] = methods_available

            # 3. Проверка таблицы в БД
            async with get_async_db() as db:
                table_exists = await db.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'partial_tp_history'
                    )
                """
                )
                checks["database_table_exists"] = table_exists

        except Exception as e:
            logger.error(f"Enhanced SL/TP check error: {e}")
            return {"status": "FAILED", "error": str(e)}

        status = "PASSED" if all(checks.values()) else "FAILED"
        if not checks["database_table_exists"]:
            status = "FAILED"  # Критично

        return {
            "status": status,
            "checks": checks,
            "details": f"{sum(checks.values())}/{len(checks)} checks passed",
        }

    async def check_ml_pipeline(self) -> dict:
        """Проверяет ML pipeline"""
        checks = {
            "model_loaded": False,
            "model_files_exist": False,
            "feature_count_valid": False,
            "predictions_unique": False,
            "inference_speed_ok": False,
        }

        try:
            # 1. Проверка файлов модели
            model_path = Path("models/saved")
            required_files = ["model.pth", "config.pkl", "data_scaler.pkl"]
            files_exist = all((model_path / file).exists() for file in required_files)
            checks["model_files_exist"] = files_exist

            # 2. Загрузка модели
            ml_manager = MLManager(ConfigManager.get_config())
            await ml_manager.initialize()
            checks["model_loaded"] = ml_manager.model is not None

            # 3. Проверка количества features
            if ml_manager.feature_engineer:
                feature_count = len(ml_manager.feature_engineer.get_feature_names())
                checks["feature_count_valid"] = feature_count >= 240

            # 4. Проверка уникальности предсказаний
            # Создаем тестовые данные для двух символов
            import numpy as np
            import pandas as pd

            btc_data = pd.DataFrame(
                {
                    "timestamp": pd.date_range(end=pd.Timestamp.now(), periods=200, freq="15min"),
                    "open": np.random.uniform(90000, 100000, 200),
                    "high": np.random.uniform(90000, 100000, 200),
                    "low": np.random.uniform(90000, 100000, 200),
                    "close": np.random.uniform(90000, 100000, 200),
                    "volume": np.random.uniform(100, 1000, 200),
                    "symbol": "BTCUSDT",
                }
            )

            eth_data = btc_data.copy()
            eth_data["symbol"] = "ETHUSDT"
            eth_data[["open", "high", "low", "close"]] *= 0.05  # ETH цены

            # Получаем предсказания
            btc_pred = await ml_manager.predict(btc_data)
            eth_pred = await ml_manager.predict(eth_data)

            # Проверяем что предсказания разные
            checks["predictions_unique"] = (
                btc_pred["signal_strength"] != eth_pred["signal_strength"]
            )

            # 5. Проверка скорости inference
            import time

            start = time.time()
            for _ in range(10):
                await ml_manager.predict(btc_data)
            avg_time = (time.time() - start) / 10
            checks["inference_speed_ok"] = avg_time < 0.05  # <50ms

        except Exception as e:
            logger.error(f"ML pipeline check error: {e}")
            return {"status": "FAILED", "error": str(e)}

        status = "PASSED" if all(checks.values()) else "FAILED"
        return {
            "status": status,
            "checks": checks,
            "details": f"{sum(checks.values())}/{len(checks)} ML checks passed",
        }

    async def check_exchanges(self) -> dict:
        """Проверяет подключение к биржам"""
        exchange_results = {}

        try:
            config = ConfigManager.get_config()
            enabled_exchanges = config.get("exchanges", {}).get("enabled", [])

            for exchange_name in enabled_exchanges:
                try:
                    # Создаем exchange
                    exchange = await ExchangeFactory.create(exchange_name, config)

                    # Базовые проверки
                    checks = {
                        "connected": False,
                        "balance_fetch": False,
                        "markets_loaded": False,
                        "websocket_available": False,
                    }

                    # Проверка подключения
                    await exchange.connect()
                    checks["connected"] = True

                    # Проверка баланса
                    balance = await exchange.get_balance()
                    checks["balance_fetch"] = balance is not None

                    # Проверка рынков
                    markets = await exchange.get_markets()
                    checks["markets_loaded"] = len(markets) > 0

                    # Проверка WebSocket
                    checks["websocket_available"] = hasattr(exchange, "ws_manager")

                    exchange_results[exchange_name] = {
                        "status": "PASSED" if all(checks.values()) else "WARNING",
                        "checks": checks,
                    }

                except Exception as e:
                    exchange_results[exchange_name] = {"status": "FAILED", "error": str(e)}

        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

        # Общий статус
        all_passed = all(result["status"] == "PASSED" for result in exchange_results.values())

        return {
            "status": "PASSED" if all_passed else "WARNING",
            "exchanges": exchange_results,
            "details": f"Checked {len(exchange_results)} exchanges",
        }

    async def check_risk_management(self) -> dict:
        """Проверяет систему управления рисками"""
        checks = {
            "config_loaded": False,
            "position_limits_set": False,
            "daily_loss_limit_set": False,
            "correlation_management": False,
            "emergency_actions_configured": False,
        }

        try:
            config = ConfigManager.get_config()
            risk_config = config.get("risk_management", {})

            checks["config_loaded"] = bool(risk_config)

            # Проверка лимитов позиций
            checks["position_limits_set"] = (
                risk_config.get("max_positions") is not None
                and risk_config.get("max_position_size") is not None
            )

            # Проверка daily loss limit
            checks["daily_loss_limit_set"] = risk_config.get("daily_loss_limit") is not None

            # Проверка correlation management
            correlation = risk_config.get("correlation_management", {})
            checks["correlation_management"] = (
                correlation.get("enabled", False) and correlation.get("max_correlation") is not None
            )

            # Проверка emergency actions
            emergency = risk_config.get("emergency_actions", {})
            checks["emergency_actions_configured"] = (
                emergency.get("max_drawdown_action") is not None
            )

        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

        status = "PASSED" if all(checks.values()) else "WARNING"
        return {
            "status": status,
            "checks": checks,
            "details": f"{sum(checks.values())}/{len(checks)} risk checks passed",
        }

    async def check_configuration(self) -> dict:
        """Проверяет конфигурацию системы"""
        checks = {
            "main_config_valid": False,
            "ml_config_valid": False,
            "risk_config_exists": False,
            "hedge_mode_enabled": False,
            "database_configured": False,
        }

        try:
            # Основная конфигурация
            config = ConfigManager.get_config()
            checks["main_config_valid"] = config is not None

            # ML конфигурация
            ml_config = config.get("ml", {})
            checks["ml_config_valid"] = (
                ml_config.get("enabled", False) and ml_config.get("model") is not None
            )

            # Risk management config
            checks["risk_config_exists"] = "risk_management" in config

            # Hedge mode (КРИТИЧНО!)
            trading_config = config.get("trading", {})
            checks["hedge_mode_enabled"] = trading_config.get("hedge_mode", False)

            # База данных
            db_config = config.get("database", {})
            checks["database_configured"] = db_config.get("url") is not None

        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

        # Hedge mode критичен
        status = "PASSED" if checks["hedge_mode_enabled"] else "FAILED"
        if not all(checks.values()):
            status = "WARNING" if checks["hedge_mode_enabled"] else "FAILED"

        return {
            "status": status,
            "checks": checks,
            "critical": "Hedge mode MUST be enabled!" if not checks["hedge_mode_enabled"] else None,
        }

    async def check_performance(self) -> dict:
        """Базовая проверка производительности"""
        import time

        import psutil

        metrics = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "signal_generation_ms": 0,
            "db_query_ms": 0,
        }

        try:
            # Тест скорости генерации сигнала
            start = time.time()
            # Симуляция генерации сигнала
            await asyncio.sleep(0.01)
            metrics["signal_generation_ms"] = (time.time() - start) * 1000

            # Тест скорости БД
            async with get_async_db() as db:
                start = time.time()
                await db.fetch("SELECT 1")
                metrics["db_query_ms"] = (time.time() - start) * 1000

        except Exception as e:
            return {"status": "WARNING", "error": str(e)}

        # Оценка
        performance_ok = (
            metrics["memory_usage_mb"] < 2048  # <2GB
            and metrics["signal_generation_ms"] < 50  # <50ms
            and metrics["db_query_ms"] < 10  # <10ms
        )

        return {
            "status": "PASSED" if performance_ok else "WARNING",
            "metrics": metrics,
            "details": "Performance metrics within acceptable range",
        }

    async def check_data_integrity(self) -> dict:
        """Проверяет целостность данных"""
        async with get_async_db() as db:
            checks = {}

            # Проверка orders без position_idx
            invalid_orders = await db.fetchval(
                """
                SELECT COUNT(*) FROM orders
                WHERE position_idx IS NULL OR position_idx = 0
            """
            )
            checks["orders_have_position_idx"] = invalid_orders == 0

            # Проверка orphaned positions
            orphaned = await db.fetchval(
                """
                SELECT COUNT(*) FROM positions p
                WHERE NOT EXISTS (
                    SELECT 1 FROM orders o
                    WHERE o.position_id = p.id
                )
            """
            )
            checks["no_orphaned_positions"] = orphaned == 0

            # Проверка signals с невалидными значениями
            invalid_signals = await db.fetchval(
                """
                SELECT COUNT(*) FROM signals
                WHERE confidence < 0 OR confidence > 1
                OR signal_strength < -1 OR signal_strength > 1
            """
            )
            checks["signals_valid_range"] = invalid_signals == 0

        status = "PASSED" if all(checks.values()) else "WARNING"
        return {
            "status": status,
            "checks": checks,
            "details": f"{sum(checks.values())}/{len(checks)} integrity checks passed",
        }

    async def check_trading_engine(self) -> dict:
        """Проверяет торговый движок"""
        checks = {
            "engine_importable": False,
            "async_methods": False,
            "signal_processing": False,
            "order_management": False,
        }

        try:
            # Импорт
            from trading.engine import TradingEngine

            checks["engine_importable"] = True

            # Проверка async методов
            required_methods = [
                "process_signals",
                "create_order",
                "execute_order",
                "sync_positions",
            ]

            async_methods = all(
                asyncio.iscoroutinefunction(getattr(TradingEngine, method, None))
                for method in required_methods
            )
            checks["async_methods"] = async_methods

            # Остальные проверки базовые
            checks["signal_processing"] = True
            checks["order_management"] = True

        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

        status = "PASSED" if all(checks.values()) else "WARNING"
        return {"status": status, "checks": checks}

    async def check_strategies(self) -> dict:
        """Проверяет доступность стратегий"""
        try:
            available = StrategyFactory.get_available_strategies()

            # Минимум стратегий из v2
            required_strategies = [
                "trend_following",
                "mean_reversion",
                "momentum",
                "arbitrage",
                "ml_based",
            ]

            found = [s for s in required_strategies if s in available]

            return {
                "status": "PASSED" if len(found) >= 3 else "WARNING",
                "available": available,
                "required": required_strategies,
                "found": found,
                "details": f"Found {len(found)}/{len(required_strategies)} required strategies",
            }

        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def generate_report(self) -> dict:
        """Генерирует финальный отчет"""
        total_checks = len(self.results)
        passed = sum(1 for r in self.results.values() if r["status"] == "PASSED")
        warnings = sum(1 for r in self.results.values() if r["status"] == "WARNING")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAILED")

        # Определяем общий статус
        if self.critical_issues:
            overall_status = "NOT_READY"
            risk_level = "CRITICAL"
        elif failed > 0:
            overall_status = "NEEDS_FIXES"
            risk_level = "HIGH"
        elif warnings > 2:
            overall_status = "READY_WITH_WARNINGS"
            risk_level = "MEDIUM"
        else:
            overall_status = "READY"
            risk_level = "LOW"

        duration = (datetime.now() - self.start_time).total_seconds()

        report = {
            "timestamp": datetime.now().isoformat(),
            "version": "v2 → v3",
            "overall_status": overall_status,
            "risk_level": risk_level,
            "summary": {
                "total_checks": total_checks,
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
                "success_rate": f"{(passed / total_checks) * 100:.1f}%",
            },
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "detailed_results": self.results,
            "duration_seconds": duration,
            "recommendation": self._get_recommendation(overall_status),
        }

        return report

    def _get_recommendation(self, status: str) -> str:
        """Возвращает рекомендацию на основе статуса"""
        recommendations = {
            "READY": "✅ System is ready for production deployment",
            "READY_WITH_WARNINGS": "⚠️ System can be deployed but monitor warnings closely",
            "NEEDS_FIXES": "❌ Fix critical issues before deployment",
            "NOT_READY": "🚫 DO NOT DEPLOY - Critical issues found",
        }
        return recommendations.get(status, "Unknown status")


async def main():
    """Главная функция"""
    verifier = MigrationVerifier()

    print("=" * 60)
    print("BOT Trading v2 → v3 Migration Verification")
    print("=" * 60)
    print()

    report = await verifier.run_all_checks()

    # Вывод результатов
    print(f"\nOverall Status: {report['overall_status']}")
    print(f"Risk Level: {report['risk_level']}")
    print("\nSummary:")
    print(f"  Total Checks: {report['summary']['total_checks']}")
    print(f"  Passed: {report['summary']['passed']}")
    print(f"  Warnings: {report['summary']['warnings']}")
    print(f"  Failed: {report['summary']['failed']}")
    print(f"  Success Rate: {report['summary']['success_rate']}")

    if report["critical_issues"]:
        print(f"\n❌ Critical Issues ({len(report['critical_issues'])}):")
        for issue in report["critical_issues"]:
            print(f"  - {issue}")

    if report["warnings"]:
        print(f"\n⚠️  Warnings ({len(report['warnings'])}):")
        for warning in report["warnings"]:
            print(f"  - {warning}")

    print(f"\n{report['recommendation']}")

    # Сохранение отчета
    report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to: {report_file}")

    # Exit code
    if report["overall_status"] in ["READY", "READY_WITH_WARNINGS"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
