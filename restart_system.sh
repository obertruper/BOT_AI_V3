#!/bin/bash

echo "🔄 Перезапуск системы BOT_AI_V3..."

# Остановка всех процессов
echo "⏹️ Остановка существующих процессов..."
pkill -f "python.*unified_launcher"
pkill -f "python.*main.py"
pkill -f "npm.*dev"
sleep 2

# Проверка что все остановлено
if pgrep -f "unified_launcher" > /dev/null; then
    echo "⚠️ Принудительная остановка..."
    pkill -9 -f "unified_launcher"
    pkill -9 -f "main.py"
    sleep 1
fi

echo "✅ Процессы остановлены"

# Активация виртуального окружения
source venv/bin/activate

# Запуск системы
echo "🚀 Запуск системы..."
python unified_launcher.py --mode=ml &

sleep 3

# Проверка статуса
if pgrep -f "unified_launcher" > /dev/null; then
    echo "✅ Система запущена успешно!"
    echo ""
    echo "📊 Мониторинг логов:"
    echo "tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep -E 'LONG|SHORT|признаков'"
else
    echo "❌ Ошибка запуска системы"
fi
