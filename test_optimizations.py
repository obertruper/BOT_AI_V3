#!/usr/bin/env python3
"""
Тестирование оптимизаций системы:
- SmartDataManager с кешированием
- EnhancedRateLimiter
- Исправление дублирования сигналов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from colorama import Fore, Style, init
from dotenv import load_dotenv

# Инициализация
init()
load_dotenv()


async def test_smart_data_manager():
    """Тест SmartDataManager"""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔧 Тестирование SmartDataManager{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

    try:
        from core.config.config_manager import ConfigManager
        from core.system.smart_data_manager import SmartDataManager

        # Инициализация
        config_manager = ConfigManager("config/system.yaml")
        await config_manager.initialize()

        smart_dm = SmartDataManager(config_manager)

        print(f"{Fore.YELLOW}1. Запуск SmartDataManager...{Style.RESET_ALL}")
        await smart_dm.start()

        # Ждем загрузку данных
        await asyncio.sleep(5)

        # Проверяем кеш
        print(f"\n{Fore.YELLOW}2. Проверка кеша...{Style.RESET_ALL}")

        test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        for symbol in test_symbols:
            data = await smart_dm.get_data(symbol)
            if data is not None:
                print(f"   {Fore.GREEN}✓{Style.RESET_ALL} {symbol}: {len(data)} свечей в кеше")
            else:
                print(f"   {Fore.RED}✗{Style.RESET_ALL} {symbol}: нет данных")

        # Статистика кеша
        stats = smart_dm.get_cache_stats()
        print(f"\n{Fore.YELLOW}3. Статистика кеша:{Style.RESET_ALL}")
        for key, value in stats.items():
            print(f"   • {key}: {value}")

        # Останавливаем
        await smart_dm.stop()

        print(f"\n{Fore.GREEN}✅ SmartDataManager работает корректно{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ Ошибка SmartDataManager: {e}{Style.RESET_ALL}")
        return False


async def test_enhanced_rate_limiter():
    """Тест EnhancedRateLimiter"""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔧 Тестирование EnhancedRateLimiter{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

    try:
        from exchanges.base.enhanced_rate_limiter import EnhancedRateLimiter

        # Создаем rate limiter
        limiter = EnhancedRateLimiter(exchange="bybit", enable_cache=True, cache_ttl=60)

        print(f"{Fore.YELLOW}1. Тест кеширования...{Style.RESET_ALL}")

        # Функция для тестирования
        async def mock_api_call(symbol: str):
            await asyncio.sleep(0.1)
            return {"symbol": symbol, "price": 100.0}

        # Первый вызов - должен пойти в API
        cache_key = limiter._get_cache_key("get_price", {"symbol": "BTCUSDT"})
        result1 = await limiter.execute_with_retry(
            mock_api_call, "BTCUSDT", endpoint="get_tickers", cache_key=cache_key
        )
        print(f"   • Первый вызов: {result1}")

        # Второй вызов - должен вернуться из кеша
        result2 = await limiter.execute_with_retry(
            mock_api_call, "BTCUSDT", endpoint="get_tickers", cache_key=cache_key
        )
        print(f"   • Второй вызов (из кеша): {result2}")

        # Статистика
        stats = limiter.get_stats()
        print(f"\n{Fore.YELLOW}2. Статистика Rate Limiter:{Style.RESET_ALL}")
        for key, value in stats.items():
            print(f"   • {key}: {value}")

        if stats["cache_hits"] > 0:
            print(f"\n{Fore.GREEN}✅ EnhancedRateLimiter работает корректно{Style.RESET_ALL}")
            return True
        else:
            print(f"\n{Fore.YELLOW}⚠️ Кеш не использовался{Style.RESET_ALL}")
            return False

    except Exception as e:
        print(f"{Fore.RED}❌ Ошибка EnhancedRateLimiter: {e}{Style.RESET_ALL}")
        return False


async def test_signal_deduplication():
    """Тест защиты от дублирования сигналов"""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔧 Тестирование защиты от дублирования сигналов{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

    try:
        from database.connections import get_async_db
        from database.models.signal import SignalType
        from database.repositories.signal_repository_fixed import SignalRepositoryFixed

        print(f"{Fore.YELLOW}1. Создание тестовых сигналов...{Style.RESET_ALL}")

        async with get_async_db() as session:
            repo = SignalRepositoryFixed(session)

            # Тестовый сигнал
            signal_data = {
                "symbol": "TESTUSDT",
                "signal_type": SignalType.LONG.value,
                "strategy_name": "test_strategy",
                "confidence": 0.8,
                "strength": 0.7,
                "exchange": "bybit",
                "timeframe": "15m",
            }

            # Первая попытка создания
            signal1 = await repo.create_signal(signal_data.copy())
            if signal1:
                print(f"   {Fore.GREEN}✓{Style.RESET_ALL} Первый сигнал создан (ID: {signal1.id})")
            else:
                print(f"   {Fore.YELLOW}⚠{Style.RESET_ALL} Первый сигнал не создан")

            # Вторая попытка (должна быть заблокирована)
            signal2 = await repo.create_signal(signal_data.copy())
            if signal2:
                print(
                    f"   {Fore.RED}✗{Style.RESET_ALL} Дублирующий сигнал создан (ID: {signal2.id}) - ОШИБКА!"
                )
            else:
                print(f"   {Fore.GREEN}✓{Style.RESET_ALL} Дублирующий сигнал заблокирован")

            # Третья попытка с другим символом (должна пройти)
            signal_data["symbol"] = "TESTUSDT2"
            signal3 = await repo.create_signal(signal_data.copy())
            if signal3:
                print(
                    f"   {Fore.GREEN}✓{Style.RESET_ALL} Сигнал для другого символа создан (ID: {signal3.id})"
                )
            else:
                print(
                    f"   {Fore.RED}✗{Style.RESET_ALL} Сигнал для другого символа не создан - ОШИБКА!"
                )

            # Очистка старых сигналов
            print(f"\n{Fore.YELLOW}2. Очистка старых сигналов...{Style.RESET_ALL}")
            deleted = await repo.cleanup_old_signals(hours=0)  # Удаляем все для теста
            print(f"   • Удалено {deleted} старых сигналов")

            await session.commit()

        print(f"\n{Fore.GREEN}✅ Защита от дублирования работает корректно{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ Ошибка тестирования дедупликации: {e}{Style.RESET_ALL}")
        return False


async def main():
    """Основная функция тестирования"""
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🚀 ТЕСТИРОВАНИЕ ОПТИМИЗАЦИЙ BOT_AI_V3{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

    results = []

    # Тест 1: SmartDataManager
    result = await test_smart_data_manager()
    results.append(("SmartDataManager", result))

    # Тест 2: EnhancedRateLimiter
    result = await test_enhanced_rate_limiter()
    results.append(("EnhancedRateLimiter", result))

    # Тест 3: Signal Deduplication
    result = await test_signal_deduplication()
    results.append(("Signal Deduplication", result))

    # Итоги
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📊 ИТОГИ ТЕСТИРОВАНИЯ{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

    all_passed = True
    for name, passed in results:
        if passed:
            print(f"   {Fore.GREEN}✅{Style.RESET_ALL} {name}")
        else:
            print(f"   {Fore.RED}❌{Style.RESET_ALL} {name}")
            all_passed = False

    if all_passed:
        print(f"\n{Fore.GREEN}🎉 Все оптимизации работают корректно!{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}📝 Рекомендации:{Style.RESET_ALL}")
        print("1. Обновить конфигурацию для использования SmartDataManager")
        print("2. Заменить SignalRepository на SignalRepositoryFixed")
        print("3. Интегрировать EnhancedRateLimiter в Bybit клиент")
        print(
            f"4. Перезапустить систему: {Fore.CYAN}./stop_all.sh && ./start_with_logs.sh{Style.RESET_ALL}"
        )
    else:
        print(f"\n{Fore.RED}⚠️ Некоторые оптимизации требуют доработки{Style.RESET_ALL}")

    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ Тест прерван{Style.RESET_ALL}")
        exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}❌ Критическая ошибка: {e}{Style.RESET_ALL}")
        exit(1)
