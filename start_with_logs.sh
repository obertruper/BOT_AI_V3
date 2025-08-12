#!/bin/bash

echo "=========================================="
echo "🚀 ЗАПУСК BOT_AI_V3 С МОНИТОРИНГОМ"
echo "=========================================="

# Проверяем, не запущена ли уже система
if pgrep -f "python.*unified_launcher" > /dev/null; then
    echo "⚠️  Система уже запущена!"
    echo "Используйте ./stop_all.sh для остановки"
    exit 1
fi

# Активируем виртуальное окружение
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Виртуальное окружение активировано"
else
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте его: python3 -m venv venv"
    exit 1
fi

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    exit 1
fi

# Создаем директорию для логов если её нет
mkdir -p data/logs

echo ""
echo "📊 Конфигурация:"
echo "   Режим: core (торговля)"
echo "   Плечо: 5x (из config/trading.yaml)"
echo "   Риск: 2% на сделку"
echo "   Фиксированный баланс: $500"

echo ""
echo "🔧 Запуск системы..."

# Проверяем и загружаем исторические данные если нужно
echo "   → Проверка рыночных данных..."
python3 -c "
import asyncio
from database.connections.postgres import AsyncPGPool

async def check_data():
    result = await AsyncPGPool.fetch(
        '''SELECT COUNT(*) as cnt FROM raw_market_data
           WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000'''
    )
    return result[0]['cnt'] > 0

has_data = asyncio.run(check_data())
exit(0 if has_data else 1)
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "   ⚠️  Данные устарели, загружаем свежие..."
    python3 scripts/load_historical_data_quick.py > data/logs/data_load.log 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ Рыночные данные загружены"
    else
        echo "   ⚠️  Не удалось загрузить данные, продолжаем без них"
    fi
else
    echo "   ✅ Рыночные данные актуальны"
fi

# Запускаем торговое ядро
echo "   → Запуск торгового ядра с автообновлением данных..."
nohup python unified_launcher.py --mode=core > data/logs/launcher.log 2>&1 &
LAUNCHER_PID=$!
echo "   ✅ Торговое ядро запущено (PID: $LAUNCHER_PID)"

# Ждем инициализации ядра
sleep 5

# Запускаем API сервер
echo "   → Запуск API сервера..."
nohup python unified_launcher.py --mode=api > data/logs/api.log 2>&1 &
API_PID=$!
echo "   ✅ API сервер запущен (PID: $API_PID, http://localhost:8080)"

# Запускаем веб-интерфейс
echo "   → Запуск веб-интерфейса..."
cd web/frontend
nohup npm run dev > ../../data/logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..
echo "   ✅ Веб-интерфейс запущен (PID: $FRONTEND_PID, http://localhost:5173)"

echo ""
echo "✅ Все компоненты запущены:"
echo "   • Торговое ядро: PID $LAUNCHER_PID"
echo "   • API сервер: http://localhost:8080 (PID $API_PID)"
echo "   • Веб-интерфейс: http://localhost:5173 (PID $FRONTEND_PID)"
echo "   • API документация: http://localhost:8080/api/docs"

# Проверяем что процессы работают
sleep 2
if ps -p $LAUNCHER_PID > /dev/null && ps -p $API_PID > /dev/null; then
    echo "✅ Все процессы активны"
else
    echo "❌ Один или несколько процессов завершились с ошибкой!"
    echo "Проверьте логи:"
    echo "  • tail -f data/logs/launcher.log"
    echo "  • tail -f data/logs/api.log"
    echo "  • tail -f data/logs/frontend.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "📋 МОНИТОРИНГ ЛОГОВ"
echo "=========================================="
echo ""
echo "Отслеживаем логи в реальном времени..."
echo "Нажмите Ctrl+C для выхода из мониторинга (система продолжит работать)"
echo ""

# Запускаем мониторинг логов
tail -f data/logs/bot_trading_*.log | grep --line-buffered -E "signal|order|position|SL|TP|leverage|ERROR|WARNING"
