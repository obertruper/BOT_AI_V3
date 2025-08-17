#!/bin/bash
# Скрипт для полного перезапуска системы и проверки ошибок

echo "🛑 Останавливаем все процессы..."
pkill -f "python.*unified_launcher" 2>/dev/null
pkill -f "python.*main.py" 2>/dev/null
sleep 2

echo "🔍 Проверяем что все остановлено..."
if ps aux | grep -E "python.*(unified_launcher|main\.py)" | grep -v grep > /dev/null; then
    echo "⚠️ Принудительная остановка..."
    ps aux | grep -E "python.*(unified_launcher|main\.py)" | grep -v grep | awk '{print $2}' | xargs -r kill -9
    sleep 2
fi

echo "🚀 Запускаем систему..."
source venv/bin/activate
nohup python3 unified_launcher.py --mode=ml > /tmp/launcher.log 2>&1 &
LAUNCHER_PID=$!

echo "⏳ Ждем запуска (30 сек)..."
sleep 30

echo "📊 Проверяем логи на ошибки total_seconds..."
ERROR_COUNT=$(tail -100 data/logs/bot_trading_$(date +%Y%m%d).log | grep -c "ERROR.*total_seconds" || echo "0")

if [ "$ERROR_COUNT" -gt "0" ]; then
    echo "❌ Найдено $ERROR_COUNT ошибок 'total_seconds'"
    tail -5 data/logs/bot_trading_$(date +%Y%m%d).log | grep "ERROR.*total_seconds"
else
    echo "✅ Ошибок 'total_seconds' не найдено!"
fi

echo "📈 Проверяем ML предсказания..."
ML_COUNT=$(tail -100 data/logs/bot_trading_$(date +%Y%m%d).log | grep -c "ML предсказание\|returns_15m" || echo "0")
echo "   Найдено $ML_COUNT ML событий за последние 100 строк"

echo "🏥 Статус системы:"
python3 unified_launcher.py --status 2>/dev/null || echo "   Не удалось получить статус"
