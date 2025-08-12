#!/bin/bash

echo "=========================================="
echo "🛑 ОСТАНОВКА BOT_AI_V3"
echo "=========================================="

echo ""
echo "Поиск запущенных процессов..."

# Ищем процессы unified_launcher и связанные процессы
LAUNCHER_PIDS=$(pgrep -f "python.*unified_launcher" | tr '\n' ' ')
TRADING_PIDS=$(pgrep -f "python.*main\.py" | tr '\n' ' ')
API_PIDS=$(pgrep -f "python.*uvicorn" | tr '\n' ' ')
FRONTEND_PIDS=$(pgrep -f "npm.*dev" | tr '\n' ' ')
NODE_PIDS=$(pgrep -f "node.*vite" | tr '\n' ' ')
OTHER_PIDS=$(pgrep -f "python.*(trading_engine|bot_trading)" | tr '\n' ' ')

# Также ищем процессы на конкретных портах
PORT_8080_PID=$(lsof -ti :8080 2>/dev/null | tr '\n' ' ')
PORT_5173_PID=$(lsof -ti :5173 2>/dev/null | tr '\n' ' ')

# Объединяем все PID
PIDS="$LAUNCHER_PIDS $TRADING_PIDS $API_PIDS $FRONTEND_PIDS $NODE_PIDS $OTHER_PIDS $PORT_8080_PID $PORT_5173_PID"
PIDS=$(echo $PIDS | tr -s ' ')

if [ -z "$PIDS" ]; then
    echo "✅ Нет запущенных процессов"
else
    echo "Найдены процессы: $PIDS"
    echo "Останавливаем..."

    # Сначала пробуем мягкую остановку
    for pid in $PIDS; do
        kill -TERM $pid 2>/dev/null
    done

    sleep 2

    # Проверяем, остались ли процессы
    REMAINING_LAUNCHER=$(pgrep -f "python.*unified_launcher")
    REMAINING_TRADING=$(pgrep -f "python.*main\.py")
    REMAINING_OTHER=$(pgrep -f "python.*(trading_engine|bot_trading)")
    REMAINING="$REMAINING_LAUNCHER $REMAINING_TRADING $REMAINING_OTHER"
    REMAINING=$(echo $REMAINING | tr -s ' ')

    if [ ! -z "$REMAINING" ]; then
        echo "Принудительная остановка оставшихся процессов..."
        for pid in $REMAINING; do
            kill -9 $pid 2>/dev/null
        done
    fi

    echo "✅ Все процессы остановлены"
fi

# Финальная проверка портов
echo ""
echo "Проверка освобождения портов..."
PORT_8080_CHECK=$(lsof -ti :8080 2>/dev/null)
PORT_5173_CHECK=$(lsof -ti :5173 2>/dev/null)

if [ ! -z "$PORT_8080_CHECK" ]; then
    echo "⚠️  Порт 8080 все еще занят, освобождаем..."
    kill -9 $PORT_8080_CHECK 2>/dev/null
fi

if [ ! -z "$PORT_5173_CHECK" ]; then
    echo "⚠️  Порт 5173 все еще занят, освобождаем..."
    kill -9 $PORT_5173_CHECK 2>/dev/null
fi

# Очищаем временные файлы
echo ""
echo "Очистка временных файлов..."
rm -f nohup.out 2>/dev/null
rm -f *.pid 2>/dev/null
rm -f test_system_status.py 2>/dev/null
rm -f final_system_check.py 2>/dev/null

# Убиваем фоновые bash процессы мониторинга
pkill -f "tail.*bot_trading.*log" 2>/dev/null

echo ""
echo "=========================================="
echo "✅ СИСТЕМА ОСТАНОВЛЕНА"
echo "=========================================="
echo ""
echo "Для запуска используйте:"
echo "  ./start_with_logs.sh"
