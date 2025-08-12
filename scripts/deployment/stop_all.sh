#!/bin/bash

# Скрипт для остановки всех процессов BOT_AI_V3

echo "🛑 Остановка BOT_AI_V3"
echo "====================="
echo ""

# Останавливаем все процессы BOT_AI_V3
echo "Поиск процессов BOT_AI_V3..."

# Получаем PID всех процессов
PIDS=""

# Unified Launcher
LAUNCHER_PIDS=$(pgrep -f "python.*unified_launcher" 2>/dev/null)
if [ ! -z "$LAUNCHER_PIDS" ]; then
    echo "Найден Unified Launcher: PIDs $LAUNCHER_PIDS"
    PIDS="$PIDS $LAUNCHER_PIDS"
fi

# Main trading
MAIN_PIDS=$(pgrep -f "python.*main.py.*BOT_AI" 2>/dev/null)
if [ ! -z "$MAIN_PIDS" ]; then
    echo "Найден Trading Engine: PIDs $MAIN_PIDS"
    PIDS="$PIDS $MAIN_PIDS"
fi

# Web API
API_PIDS=$(pgrep -f "python.*web/api/main.py" 2>/dev/null)
if [ ! -z "$API_PIDS" ]; then
    echo "Найден Web API: PIDs $API_PIDS"
    PIDS="$PIDS $API_PIDS"
fi

# Любые другие процессы BOT_AI
OTHER_PIDS=$(pgrep -f "python.*BOT_AI" 2>/dev/null)
if [ ! -z "$OTHER_PIDS" ]; then
    echo "Найдены другие процессы BOT_AI: PIDs $OTHER_PIDS"
    PIDS="$PIDS $OTHER_PIDS"
fi

# Останавливаем найденные процессы
if [ ! -z "$PIDS" ]; then
    echo ""
    echo "Останавливаем процессы..."

    # Сначала пробуем мягкую остановку
    for PID in $PIDS; do
        if ps -p $PID > /dev/null 2>&1; then
            echo "Отправляем SIGTERM процессу $PID..."
            kill $PID 2>/dev/null
        fi
    done

    # Ждем 3 секунды
    sleep 3

    # Проверяем и делаем принудительную остановку если нужно
    for PID in $PIDS; do
        if ps -p $PID > /dev/null 2>&1; then
            echo "Процесс $PID не остановился, отправляем SIGKILL..."
            kill -9 $PID 2>/dev/null
        fi
    done

    echo "✅ Все процессы остановлены"
else
    echo "ℹ️ Процессы BOT_AI_V3 не найдены"
fi

# Ждем завершения процессов
sleep 2

# Проверяем что все остановлено
echo ""
echo "Проверка статуса:"
echo "-----------------"

STILL_RUNNING=false

if pgrep -f "python.*unified_launcher" > /dev/null; then
    echo "⚠️ Unified Launcher все еще работает!"
    STILL_RUNNING=true
fi

if pgrep -f "python.*main.py" > /dev/null; then
    echo "⚠️ Trading Engine все еще работает!"
    STILL_RUNNING=true
fi

if pgrep -f "python.*web/api/main.py" > /dev/null; then
    echo "⚠️ Web API все еще работает!"
    STILL_RUNNING=true
fi

if [ "$STILL_RUNNING" = true ]; then
    echo ""
    echo "❌ Некоторые процессы не удалось остановить"
    echo "Используйте: pkill -9 -f 'python.*BOT_AI_V3' для принудительной остановки"
else
    echo ""
    echo "✅ Все процессы BOT_AI_V3 успешно остановлены"
fi

echo ""
echo "📊 Сводка последней сессии:"
echo "---------------------------"

# Показываем статистику из логов
if ls data/logs/*.log 1> /dev/null 2>&1; then
    echo "Обработано сигналов: $(grep -h "signal" data/logs/*.log 2>/dev/null | wc -l)"
    echo "Создано ордеров: $(grep -h "order.*created" data/logs/*.log 2>/dev/null | wc -l)"
    echo "SL/TP событий: $(grep -hE "SL|TP|stop_loss|take_profit" data/logs/*.log 2>/dev/null | wc -l)"
    echo "Ошибок: $(grep -h "ERROR" data/logs/*.log 2>/dev/null | wc -l)"
fi

echo ""
echo "💡 Для запуска снова используйте:"
echo "- ./start_with_logs.sh - запуск с мониторингом логов"
echo "- python3 unified_launcher.py - обычный запуск"
