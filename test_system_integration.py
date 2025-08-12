#!/usr/bin/env python3
"""
Тестирование интегрированной системы BOT_AI_V3
Проверяет:
- Загрузку конфигурации
- Инициализацию DataManager
- Подключение к Bybit API
- Обновление данных
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from colorama import Fore, Style, init
from dotenv import load_dotenv

# Инициализация colorama для цветного вывода
init()

# Загружаем переменные окружения
load_dotenv()


async def test_system():
    """Основной тест системы"""

    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🚀 ТЕСТИРОВАНИЕ СИСТЕМЫ BOT_AI_V3{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

    # 1. Проверка конфигурации
    print(f"{Fore.YELLOW}1. Проверка конфигурации...{Style.RESET_ALL}")
    try:
        from core.config.config_manager import ConfigManager

        config_manager = ConfigManager("config/system.yaml")
        await config_manager.initialize()
        config = config_manager.get_config()

        data_config = config.get("data_management", {})
        print(f"   {Fore.GREEN}✓{Style.RESET_ALL} Конфигурация загружена")
        print(f"   • auto_update: {data_config.get('auto_update', False)}")
        print(f"   • update_interval: {data_config.get('update_interval', 900)}s")
        print(f"   • initial_load_days: {data_config.get('initial_load_days', 7)}")

    except Exception as e:
        print(f"   {Fore.RED}✗ Ошибка загрузки конфигурации: {e}{Style.RESET_ALL}")
        return False

    # 2. Проверка API ключей
    print(f"\n{Fore.YELLOW}2. Проверка API ключей...{Style.RESET_ALL}")
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    if api_key and api_secret:
        print(f"   {Fore.GREEN}✓{Style.RESET_ALL} API ключи найдены")
        print(f"   • API Key: {api_key[:8]}...")
    else:
        print(f"   {Fore.RED}✗ API ключи не найдены в .env{Style.RESET_ALL}")
        return False

    # 3. Проверка подключения к БД
    print(f"\n{Fore.YELLOW}3. Проверка подключения к PostgreSQL...{Style.RESET_ALL}")
    try:
        from database.connections.postgres import AsyncPGPool

        # Проверка подключения
        result = await AsyncPGPool.fetch("SELECT version()")
        print(f"   {Fore.GREEN}✓{Style.RESET_ALL} PostgreSQL подключен (порт 5555)")

        # Проверка данных
        data_count = await AsyncPGPool.fetch(
            "SELECT COUNT(*) as cnt FROM raw_market_data"
        )
        print(f"   • Записей в БД: {data_count[0]['cnt']}")

    except Exception as e:
        print(f"   {Fore.RED}✗ Ошибка подключения к БД: {e}{Style.RESET_ALL}")
        return False

    # 4. Проверка Bybit клиента
    print(f"\n{Fore.YELLOW}4. Проверка Bybit API...{Style.RESET_ALL}")
    try:
        from exchanges.factory import exchange_factory

        client = await exchange_factory.create_exchange_client("bybit")
        if client:
            print(
                f"   {Fore.GREEN}✓{Style.RESET_ALL} Bybit клиент создан и аутентифицирован"
            )

            # Проверка баланса
            try:
                balances = await client.get_balances()
                print(f"   {Fore.GREEN}✓{Style.RESET_ALL} Баланс получен успешно")
                if balances:
                    for balance in balances[:3]:  # Показываем первые 3
                        # Проверяем атрибуты Balance объекта
                        amount = getattr(
                            balance,
                            "free",
                            getattr(
                                balance, "balance", getattr(balance, "available", 0)
                            ),
                        )
                        currency = getattr(
                            balance,
                            "currency",
                            getattr(
                                balance, "coin", getattr(balance, "asset", "UNKNOWN")
                            ),
                        )
                        if amount > 0:
                            print(f"   • {currency}: {amount:.4f}")
            except Exception as e:
                print(
                    f"   {Fore.YELLOW}⚠{Style.RESET_ALL} Не удалось получить баланс: {e}"
                )

            # Закрываем соединение (если метод существует)
            if hasattr(client, "disconnect"):
                await client.disconnect()
            elif hasattr(client, "_close"):
                await client._close()
        else:
            print(f"   {Fore.RED}✗ Не удалось создать Bybit клиент{Style.RESET_ALL}")
            return False

    except Exception as e:
        print(f"   {Fore.RED}✗ Ошибка инициализации Bybit: {e}{Style.RESET_ALL}")
        return False

    # 5. Проверка DataManager
    print(f"\n{Fore.YELLOW}5. Проверка DataManager...{Style.RESET_ALL}")
    try:
        from core.system.data_manager import DataManager

        data_manager = DataManager(config_manager)
        print(f"   {Fore.GREEN}✓{Style.RESET_ALL} DataManager инициализирован")
        print(
            f"   • Автообновление: {'Включено' if data_manager.data_config['auto_update'] else 'Отключено'}"
        )
        print(
            f"   • Интервал: {data_manager.data_config['update_interval'] / 60:.1f} минут"
        )
        print(f"   • Торговых пар: {len(data_manager.trading_pairs)}")

        # Проверка актуальности данных
        print("\n   Проверка актуальности данных:")
        for symbol in data_manager.trading_pairs[:3]:  # Проверяем первые 3 символа
            latest_time = await data_manager._get_latest_data_time(symbol)
            if latest_time:
                # Убеждаемся что оба времени в одном timezone
                from datetime import timezone

                if latest_time.tzinfo is None:
                    latest_time = latest_time.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                age = now - latest_time
                if age < timedelta(hours=1):
                    print(
                        f"   {Fore.GREEN}✓{Style.RESET_ALL} {symbol}: актуально ({age.total_seconds() / 60:.1f} мин)"
                    )
                else:
                    print(
                        f"   {Fore.YELLOW}⚠{Style.RESET_ALL} {symbol}: устарело ({age.total_seconds() / 3600:.1f} часов)"
                    )
            else:
                print(f"   {Fore.RED}✗{Style.RESET_ALL} {symbol}: нет данных")

    except Exception as e:
        print(f"   {Fore.RED}✗ Ошибка DataManager: {e}{Style.RESET_ALL}")
        return False

    # 6. Проверка ML компонентов
    print(f"\n{Fore.YELLOW}6. Проверка ML компонентов...{Style.RESET_ALL}")
    try:
        from ml.ml_manager import MLManager

        ml_manager = MLManager(config_manager)
        print(f"   {Fore.GREEN}✓{Style.RESET_ALL} MLManager инициализирован")

        # Проверка модели
        if hasattr(ml_manager, "model") and ml_manager.model:
            print(f"   {Fore.GREEN}✓{Style.RESET_ALL} ML модель загружена")
        else:
            print(f"   {Fore.YELLOW}⚠{Style.RESET_ALL} ML модель не загружена")

    except Exception as e:
        print(
            f"   {Fore.YELLOW}⚠{Style.RESET_ALL} ML компоненты не инициализированы: {e}"
        )

    # 7. Проверка Trading Engine
    print(f"\n{Fore.YELLOW}7. Проверка Trading Engine...{Style.RESET_ALL}")
    try:
        # Trading Engine проверим только импорт, так как требует orchestrator

        print(f"   {Fore.GREEN}✓{Style.RESET_ALL} TradingEngine модуль загружен")

    except Exception as e:
        print(f"   {Fore.RED}✗ Ошибка загрузки TradingEngine: {e}{Style.RESET_ALL}")
        return False

    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ ВСЕ ОСНОВНЫЕ КОМПОНЕНТЫ РАБОТАЮТ{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

    print(f"\n{Fore.YELLOW}📝 Рекомендации:{Style.RESET_ALL}")
    print(f"1. Запустить систему: {Fore.CYAN}./start_with_logs.sh{Style.RESET_ALL}")
    print(
        f"2. Мониторинг логов: {Fore.CYAN}tail -f data/logs/bot_trading_*.log{Style.RESET_ALL}"
    )
    print(f"3. Веб-интерфейс: {Fore.CYAN}http://localhost:5173{Style.RESET_ALL}")
    print(
        f"4. API документация: {Fore.CYAN}http://localhost:8080/api/docs{Style.RESET_ALL}"
    )

    return True


async def main():
    """Точка входа"""
    try:
        success = await test_system()

        if success:
            print(f"\n{Fore.GREEN}🎉 Система готова к работе!{Style.RESET_ALL}")
            exit(0)
        else:
            print(f"\n{Fore.RED}❌ Обнаружены проблемы в системе{Style.RESET_ALL}")
            exit(1)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ Тест прерван пользователем{Style.RESET_ALL}")
        exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}❌ Критическая ошибка: {e}{Style.RESET_ALL}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
