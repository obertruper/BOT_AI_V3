#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный мониторинг системы BOT Trading v3
С детальным анализом работы риск-менеджмента и ML-интеграции
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.config_manager import ConfigManager
from risk_management.manager import RiskManager


class EnhancedSystemMonitor:
    """Улучшенный мониторинг системы с анализом риск-менеджмента"""

    def __init__(self):
        self.config_manager = None
        self.risk_manager = None
        self.monitoring_data = {
            "start_time": datetime.now(),
            "risk_checks": 0,
            "signals_processed": 0,
            "ml_predictions": 0,
            "errors": [],
            "warnings": [],
            "api_issues": [],
            "database_issues": [],
        }

    async def initialize(self):
        """Инициализация мониторинга"""
        print("🚀 Инициализация улучшенного мониторинга системы")

        # Инициализация ConfigManager
        self.config_manager = ConfigManager("config/system.yaml")
        await self.config_manager.initialize()

        # Инициализация RiskManager
        risk_config = self.config_manager.get_risk_management_config()
        self.risk_manager = RiskManager(risk_config)

        print("✅ Система мониторинга инициализирована")

    async def monitor_system_health(self):
        """Мониторинг здоровья системы"""
        print("\n🏥 Проверка здоровья системы")
        print("=" * 50)

        # Проверка конфигурации
        await self._check_configuration()

        # Проверка API ключей и бирж
        await self._check_api_keys_and_exchanges()

        # Проверка риск-менеджмента
        await self._check_risk_management()

        # Проверка ML-интеграции
        await self._check_ml_integration()

        # Проверка базы данных
        await self._check_database()

        # Проверка логов с детальным анализом
        await self._check_logs_detailed()

    async def _check_configuration(self):
        """Проверка конфигурации"""
        print("📋 Проверка конфигурации...")

        try:
            # Проверка основных настроек
            risk_config = self.config_manager.get_risk_management_config()
            ml_config = self.config_manager.get_ml_integration_config()
            monitoring_config = self.config_manager.get_monitoring_config()

            print(
                f"   ✅ Risk Management: {'Включен' if risk_config.get('enabled') else 'Отключен'}"
            )
            print(
                f"   ✅ ML Integration: {'Включена' if ml_config.get('enabled') else 'Отключена'}"
            )
            print(
                f"   ✅ Monitoring: {'Настроен' if monitoring_config else 'Не настроен'}"
            )

            # Проверка профилей риска
            profiles = risk_config.get("risk_profiles", {})
            print(f"   📊 Профили риска: {list(profiles.keys())}")

            # Проверка категорий активов
            categories = risk_config.get("asset_categories", {})
            print(f"   🏷️ Категории активов: {list(categories.keys())}")

        except Exception as e:
            print(f"   ❌ Ошибка проверки конфигурации: {e}")
            self.monitoring_data["errors"].append(f"Configuration error: {e}")

    async def _check_api_keys_and_exchanges(self):
        """Проверка API ключей и бирж"""
        print("\n🔑 Проверка API ключей и бирж...")

        try:
            # Проверяем, что config_manager инициализирован
            if not self.config_manager:
                print("   ❌ ConfigManager не инициализирован")
                self.monitoring_data["api_issues"].append(
                    "ConfigManager not initialized"
                )
                return

            # Проверяем конфигурацию бирж
            exchanges_config = self.config_manager.get_exchange_config()

            if not exchanges_config:
                print("   ❌ Конфигурация бирж не найдена")
                self.monitoring_data["api_issues"].append("Exchanges config not found")
                return

            print("   📊 Найденные биржи:")

            for exchange_name, exchange_config in exchanges_config.items():
                print(f"      🔍 {exchange_name.upper()}:")

                # Проверяем наличие API ключей
                api_key = exchange_config.get("api_key")
                api_secret = exchange_config.get("api_secret")

                if not api_key or not api_secret:
                    print("         ❌ API ключи отсутствуют")
                    self.monitoring_data["api_issues"].append(
                        f"{exchange_name}: Missing API keys"
                    )
                else:
                    # Проверяем формат ключей
                    if len(api_key) < 10:
                        print("         ⚠️ API ключ слишком короткий")
                        self.monitoring_data["warnings"].append(
                            f"{exchange_name}: API key too short"
                        )
                    else:
                        print(
                            f"         ✅ API ключ: {'*' * (len(api_key) - 4) + api_key[-4:]}"
                        )

                    if len(api_secret) < 10:
                        print("         ⚠️ API секрет слишком короткий")
                        self.monitoring_data["warnings"].append(
                            f"{exchange_name}: API secret too short"
                        )
                    else:
                        print(
                            f"         ✅ API секрет: {'*' * (len(api_secret) - 4) + api_secret[-4:]}"
                        )

                # Проверяем дополнительные настройки
                testnet = exchange_config.get("testnet", False)
                print(f"         🧪 Testnet: {'Да' if testnet else 'Нет'}")

                # Проверяем настройки подписи
                signature_algorithm = exchange_config.get(
                    "signature_algorithm", "HMAC-SHA256"
                )
                print(f"         🔐 Алгоритм подписи: {signature_algorithm}")

        except Exception as e:
            print(f"   ❌ Ошибка проверки API ключей: {e}")
            self.monitoring_data["api_issues"].append(f"API keys check error: {e}")

    async def _check_risk_management(self):
        """Проверка системы управления рисками"""
        print("\n🛡️ Проверка системы управления рисками...")

        try:
            # Проверка инициализации
            if not self.risk_manager:
                print("   ❌ RiskManager не инициализирован")
                return

            print(
                f"   ✅ RiskManager: {'Включен' if self.risk_manager.enabled else 'Отключен'}"
            )
            print(f"   📊 Текущий профиль: {self.risk_manager.current_profile}")
            print(f"   💰 Риск на сделку: {self.risk_manager.risk_per_trade:.2%}")
            print(f"   🎯 Максимум позиций: {self.risk_manager.max_positions}")

            # Тестирование расчета позиции
            test_signal = {
                "symbol": "BTCUSDT",
                "side": "buy",
                "leverage": 5,
                "position_size": 100.0,
                "ml_predictions": {"profit_probability": 0.7, "loss_probability": 0.3},
            }

            position_size = self.risk_manager.calculate_position_size(test_signal)
            print(f"   📊 Тестовый расчет позиции: ${position_size}")

            # Проверка рисков
            risk_check = await self.risk_manager.check_signal_risk(test_signal)
            print(
                f"   🔍 Проверка рисков: {'✅ Прошла' if risk_check else '❌ Не прошла'}"
            )

            self.monitoring_data["risk_checks"] += 1

        except Exception as e:
            print(f"   ❌ Ошибка проверки риск-менеджмента: {e}")
            self.monitoring_data["errors"].append(f"Risk management error: {e}")

    async def _check_ml_integration(self):
        """Проверка ML-интеграции"""
        print("\n🤖 Проверка ML-интеграции...")

        try:
            ml_config = self.config_manager.get_ml_integration_config()

            if not ml_config.get("enabled"):
                print("   ⚠️ ML-интеграция отключена")
                return

            print("   ✅ ML-интеграция включена")

            # Проверка порогов
            thresholds = ml_config.get("thresholds", {})
            print("   📊 Пороги ML:")
            print(f"      Покупка прибыль: {thresholds.get('buy_profit', 'N/A')}")
            print(f"      Покупка убыток: {thresholds.get('buy_loss', 'N/A')}")
            print(f"      Продажа прибыль: {thresholds.get('sell_profit', 'N/A')}")
            print(f"      Продажа убыток: {thresholds.get('sell_loss', 'N/A')}")

            # Проверка моделей
            buy_model = ml_config.get("buy_model", {})
            sell_model = ml_config.get("sell_model", {})

            print("   🧠 Модели:")
            print(f"      Покупка: {list(buy_model.keys())}")
            print(f"      Продажа: {list(sell_model.keys())}")

            self.monitoring_data["ml_predictions"] += 1

        except Exception as e:
            print(f"   ❌ Ошибка проверки ML-интеграции: {e}")
            self.monitoring_data["errors"].append(f"ML integration error: {e}")

    async def _check_database(self):
        """Проверка базы данных"""
        print("\n🗄️ Проверка базы данных...")

        try:
            from database.connections.postgres import AsyncPGPool

            # Проверка подключения
            result = await AsyncPGPool.fetch("SELECT COUNT(*) as count FROM signals")
            signals_count = result[0]["count"] if result else 0

            result = await AsyncPGPool.fetch("SELECT COUNT(*) as count FROM trades")
            trades_count = result[0]["count"] if result else 0

            result = await AsyncPGPool.fetch("SELECT COUNT(*) as count FROM orders")
            orders_count = result[0]["count"] if result else 0

            print("   ✅ Подключение к БД: OK")
            print(f"   📊 Сигналов: {signals_count}")
            print(f"   📊 Сделок: {trades_count}")
            print(f"   📊 Ордеров: {orders_count}")

        except Exception as e:
            print(f"   ❌ Ошибка подключения к БД: {e}")
            self.monitoring_data["database_issues"].append(
                f"Database connection error: {e}"
            )

    async def _check_logs_detailed(self):
        """Детальная проверка логов с анализом ошибок"""
        print("\n📝 Детальная проверка логов...")

        log_files = [
            "logs/core.log",
            "logs/unified_launcher.log",
            "logs/risk_management.log",
            "logs/api.log",
        ]

        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    # Получаем размер файла
                    size = os.path.getsize(log_file)
                    size_mb = size / (1024 * 1024)

                    # Получаем время последнего изменения
                    mtime = os.path.getmtime(log_file)
                    last_modified = datetime.fromtimestamp(mtime)

                    print(f"   📄 {log_file}:")
                    print(f"      Размер: {size_mb:.2f} MB")
                    print(f"      Обновлен: {last_modified.strftime('%H:%M:%S')}")

                    # Анализируем последние 200 строк для детальных ошибок
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        recent_lines = lines[-200:] if len(lines) > 200 else lines

                        # Подсчитываем ошибки по типам
                        error_count = sum(1 for line in recent_lines if "ERROR" in line)
                        warning_count = sum(
                            1 for line in recent_lines if "WARNING" in line
                        )

                        print(f"      Ошибки (последние 200 строк): {error_count}")
                        print(
                            f"      Предупреждения (последние 200 строк): {warning_count}"
                        )

                        # Анализируем специфические ошибки
                        api_errors = [
                            line
                            for line in recent_lines
                            if "API" in line and "ERROR" in line
                        ]
                        signature_errors = [
                            line
                            for line in recent_lines
                            if "signature" in line.lower() and "ERROR" in line
                        ]
                        database_errors = [
                            line
                            for line in recent_lines
                            if "database" in line.lower() and "ERROR" in line
                        ]
                        signal_errors = [
                            line
                            for line in recent_lines
                            if "signal" in line.lower() and "ERROR" in line
                        ]

                        if api_errors:
                            print(f"      🔑 API ошибки: {len(api_errors)}")
                            for error in api_errors[-3:]:  # Показываем последние 3
                                print(f"         • {error.strip()}")
                            self.monitoring_data["api_issues"].extend(api_errors[-3:])

                        if signature_errors:
                            print(f"      🔐 Ошибки подписи: {len(signature_errors)}")
                            for error in signature_errors[-3:]:
                                print(f"         • {error.strip()}")
                            self.monitoring_data["api_issues"].extend(
                                signature_errors[-3:]
                            )

                        if database_errors:
                            print(f"      🗄️ Ошибки БД: {len(database_errors)}")
                            for error in database_errors[-3:]:
                                print(f"         • {error.strip()}")
                            self.monitoring_data["database_issues"].extend(
                                database_errors[-3:]
                            )

                        if signal_errors:
                            print(f"      📡 Ошибки сигналов: {len(signal_errors)}")
                            for error in signal_errors[-3:]:
                                print(f"         • {error.strip()}")
                            self.monitoring_data["errors"].extend(signal_errors[-3:])

                        if error_count > 0:
                            self.monitoring_data["warnings"].append(
                                f"Errors in {log_file}: {error_count}"
                            )

                except Exception as e:
                    print(f"   ⚠️ Не удалось прочитать {log_file}: {e}")
            else:
                print(f"   ⚠️ Файл {log_file} не найден")

    async def generate_report(self):
        """Генерация отчета"""
        print("\n📊 Генерация отчета мониторинга")
        print("=" * 50)

        report = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_duration": (
                datetime.now() - self.monitoring_data["start_time"]
            ).total_seconds(),
            "risk_checks_performed": self.monitoring_data["risk_checks"],
            "ml_predictions_processed": self.monitoring_data["ml_predictions"],
            "errors_count": len(self.monitoring_data["errors"]),
            "warnings_count": len(self.monitoring_data["warnings"]),
            "api_issues_count": len(self.monitoring_data["api_issues"]),
            "database_issues_count": len(self.monitoring_data["database_issues"]),
            "errors": self.monitoring_data["errors"],
            "warnings": self.monitoring_data["warnings"],
            "api_issues": self.monitoring_data["api_issues"],
            "database_issues": self.monitoring_data["database_issues"],
        }

        # Сохраняем отчет
        report_file = (
            f"logs/monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"📄 Отчет сохранен: {report_file}")

        # Выводим краткую статистику
        print("\n📈 Статистика мониторинга:")
        print(f"   ⏱️ Длительность: {report['monitoring_duration']:.1f} сек")
        print(f"   🔍 Проверок риска: {report['risk_checks_performed']}")
        print(f"   🤖 ML-предсказаний: {report['ml_predictions_processed']}")
        print(f"   ❌ Ошибок: {report['errors_count']}")
        print(f"   ⚠️ Предупреждений: {report['warnings_count']}")
        print(f"   🔑 Проблем с API: {report['api_issues_count']}")
        print(f"   🗄️ Проблем с БД: {report['database_issues_count']}")

        # Рекомендации по исправлению
        if report["api_issues_count"] > 0:
            print("\n🔧 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ API ПРОБЛЕМ:")
            print("   1. Проверьте правильность API ключей в .env файле")
            print("   2. Убедитесь, что API ключи имеют правильные права доступа")
            print("   3. Проверьте настройки подписи для каждой биржи")
            print("   4. Убедитесь, что IP адрес разрешен на бирже")
            print("   5. Проверьте, что API ключи не истекли")

        if report["database_issues_count"] > 0:
            print("\n🗄️ РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ ПРОБЛЕМ БД:")
            print("   1. Проверьте подключение к PostgreSQL на порту 5555")
            print("   2. Убедитесь, что база данных bot_trading_v3 существует")
            print("   3. Проверьте права доступа пользователя obertruper")
            print("   4. Запустите миграции: alembic upgrade head")

        if report["errors_count"] > 0:
            print("\n🚨 Обнаружены критические ошибки:")
            for error in report["errors"][:5]:  # Показываем первые 5
                print(f"   • {error}")

        if report["warnings_count"] > 0:
            print("\n⚠️ Обнаружены предупреждения:")
            for warning in report["warnings"][:5]:  # Показываем первые 5
                print(f"   • {warning}")


async def main():
    """Основная функция"""
    monitor = EnhancedSystemMonitor()

    try:
        await monitor.initialize()
        await monitor.monitor_system_health()
        await monitor.generate_report()

        print("\n✅ Мониторинг завершен успешно!")

    except Exception as e:
        print(f"\n❌ Ошибка мониторинга: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
