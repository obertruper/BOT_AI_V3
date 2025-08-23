#!/bin/bash

echo "=========================================="
echo "🚀 ЗАПУСК BOT_AI_V3 С ПОЛНЫМИ ПРОВЕРКАМИ"
echo "=========================================="

# Проверяем виртуальное окружение
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте его: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Активируем виртуальное окружение
source venv/bin/activate
echo "✅ Виртуальное окружение активировано"

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте его на основе .env.example"
    exit 1
fi

# Загружаем переменные окружения
source .env

# Проверяем базу данных
echo "🔍 Проверка подключения к базе данных..."
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from database.connections.postgres import AsyncPGPool

async def test_db():
    try:
        await AsyncPGPool.get_pool()
        result = await AsyncPGPool.fetch('SELECT 1 as test')
        print('✅ База данных доступна')
        await AsyncPGPool.close_pool()
        return True
    except Exception as e:
        print(f'❌ Ошибка базы данных: {e}')
        return False

success = asyncio.run(test_db())
exit(0 if success else 1)
"

if [ $? -ne 0 ]; then
    echo "❌ Проблемы с базой данных!"
    exit 1
fi

# Запускаем тесты системы
echo "🧪 Запуск тестов системы..."
python3 scripts/run_system_tests.py

if [ $? -ne 0 ]; then
    echo "❌ Тесты системы провалились!"
    exit 1
fi

# Проверяем позиции DOT
echo "🔍 Проверка позиций DOT..."
python3 scripts/check_dot_positions.py

# Исправляем дублирующие сигналы
echo "🔧 Исправление дублирующих сигналов..."
python3 scripts/fix_duplicate_signals.py

# Создаем директорию для логов
mkdir -p data/logs

echo ""
echo "📊 Конфигурация:"
echo "   Режим: core (торговля)"
echo "   Плечо: 5x (из config/trading.yaml)"
echo "   Риск: 2% на сделку"
echo "   Фиксированный баланс: $500"

echo ""
echo "🔧 Запуск системы..."

# Запускаем систему в фоне
nohup python unified_launcher.py --mode=core > data/logs/launcher.log 2>&1 &
LAUNCHER_PID=$!

echo "✅ Система запущена (PID: $LAUNCHER_PID)"

# Ждем инициализации
sleep 5

# Проверяем что процесс работает
if ps -p $LAUNCHER_PID > /dev/null; then
    echo "✅ Процесс активен"
else
    echo "❌ Процесс завершился с ошибкой!"
    echo "Проверьте логи: tail -f data/logs/launcher.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "📋 МОНИТОРИНГ СИСТЕМЫ"
echo "=========================================="
echo ""
echo "Отслеживаем логи в реальном времени..."
echo "Нажмите Ctrl+C для выхода из мониторинга (система продолжит работать)"
echo ""

# Запускаем мониторинг логов
tail -f data/logs/bot_trading_*.log | grep --line-buffered -E "signal|order|position|SL|TP|leverage|ERROR|WARNING"
