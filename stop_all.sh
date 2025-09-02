#!/bin/bash

echo "=========================================="
echo "🛑 ОСТАНОВКА BOT_AI_V3"
echo "=========================================="

echo ""
echo "Поиск запущенных процессов..."

# Функция для безопасного поиска PID
get_pids() {
    pgrep -f "$1" 2>/dev/null | tr '\n' ' ' || echo ""
}

# Ищем только конкретные процессы нашей системы
LAUNCHER_PIDS=$(get_pids "python.*unified_launcher\.py")
TRADING_PIDS=$(get_pids "python.*\/main\.py.*BOT_AI_V3")
API_PIDS=$(get_pids "python.*uvicorn.*8083")
WEB_API_PIDS=$(get_pids "python.*web\/api\/main")
FASTAPI_PIDS=$(get_pids "python.*fastapi.*BOT_AI_V3")
WEB_LAUNCHER_PIDS=$(get_pids "python.*web\/launcher\.py")
FRONTEND_PIDS=$(get_pids "npm.*dev.*BOT_AI_V3")
NODE_PIDS=$(get_pids "node.*vite.*5173")
OTHER_PIDS=$(get_pids "python.*BOT_AI_V3.*(trading_engine|bot_trading)")
# Убрали слишком общий поиск BOT_V3_PIDS

# Также ищем процессы на конкретных портах
PORT_8080_PID=$(lsof -ti :8080 2>/dev/null | tr '\n' ' ' || echo "")
PORT_8083_PID=$(lsof -ti :8083 2>/dev/null | tr '\n' ' ' || echo "")
PORT_8084_PID=$(lsof -ti :8084 2>/dev/null | tr '\n' ' ' || echo "")
PORT_8085_PID=$(lsof -ti :8085 2>/dev/null | tr '\n' ' ' || echo "")
PORT_8086_PID=$(lsof -ti :8086 2>/dev/null | tr '\n' ' ' || echo "")
PORT_5173_PID=$(lsof -ti :5173 2>/dev/null | tr '\n' ' ' || echo "")

# Объединяем все PID и удаляем дубликаты
PIDS="$LAUNCHER_PIDS $TRADING_PIDS $API_PIDS $WEB_API_PIDS $FASTAPI_PIDS $WEB_LAUNCHER_PIDS $FRONTEND_PIDS $NODE_PIDS $OTHER_PIDS $PORT_8080_PID $PORT_8083_PID $PORT_8084_PID $PORT_8085_PID $PORT_8086_PID $PORT_5173_PID"
PIDS=$(echo $PIDS | tr ' ' '\n' | sort -u | tr '\n' ' ')

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
    REMAINING_LAUNCHER=$(get_pids "python.*unified_launcher")
    REMAINING_TRADING=$(get_pids "python.*main\.py")
    REMAINING_API=$(get_pids "python.*web[/\.]api[/\.]main")
    REMAINING_FASTAPI=$(get_pids "python.*uvicorn|python.*fastapi")
    REMAINING_OTHER=$(get_pids "python.*(trading_engine|bot_trading)")
    REMAINING_BOT=$(get_pids "BOT_AI_V3")
    REMAINING="$REMAINING_LAUNCHER $REMAINING_TRADING $REMAINING_API $REMAINING_FASTAPI $REMAINING_OTHER $REMAINING_BOT"
    REMAINING=$(echo $REMAINING | tr ' ' '\n' | sort -u | tr '\n' ' ')

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
PORTS_TO_CHECK="8080 8083 8084 8085 8086 5173"

for PORT in $PORTS_TO_CHECK; do
    PORT_CHECK=$(lsof -ti :$PORT 2>/dev/null)
    if [ ! -z "$PORT_CHECK" ]; then
        echo "⚠️  Порт $PORT все еще занят процессами: $PORT_CHECK"
        echo "   Принудительное освобождение порта $PORT..."

        # Используем несколько методов для освобождения порта
        for pid in $PORT_CHECK; do
            echo "   Завершаем процесс PID: $pid"
            kill -9 $pid 2>/dev/null || true
        done

        # Альтернативный метод через fuser
        fuser -k $PORT/tcp 2>/dev/null || true

        # Проверяем еще раз
        sleep 1
        STILL_USED=$(lsof -ti :$PORT 2>/dev/null)
        if [ -z "$STILL_USED" ]; then
            echo "   ✅ Порт $PORT успешно освобожден"
        else
            echo "   ❌ Не удалось освободить порт $PORT (PID: $STILL_USED)"
        fi
    else
        echo "✅ Порт $PORT свободен"
    fi
done

# Очищаем временные файлы
echo ""
echo "Очистка временных файлов..."
rm -f nohup.out 2>/dev/null
rm -f *.pid 2>/dev/null
rm -f test_system_status.py 2>/dev/null
rm -f final_system_check.py 2>/dev/null

# Убиваем фоновые bash процессы мониторинга
pkill -f "tail.*bot_trading.*log" 2>/dev/null || true

# Дополнительная очистка всех процессов Python, связанных с BOT_AI_V3
echo ""
echo "Финальная очистка процессов..."
PROJECT_DIR=$(dirname "$(realpath "$0")")
PYTHON_PROCS=$(ps aux | grep -E "python.*$PROJECT_DIR" | grep -v grep | awk '{print $2}')
if [ ! -z "$PYTHON_PROCS" ]; then
    echo "Найдены Python процессы проекта: $PYTHON_PROCS"
    for pid in $PYTHON_PROCS; do
        kill -9 $pid 2>/dev/null || true
    done
    echo "✅ Python процессы очищены"
fi

# Очистка зомби-процессов
pkill -9 -f "BOT_AI_V3" 2>/dev/null || true
pkill -9 -f "unified_launcher" 2>/dev/null || true
pkill -9 -f "web.api.main" 2>/dev/null || true

echo ""
echo "=========================================="
echo "✅ СИСТЕМА ПОЛНОСТЬЮ ОСТАНОВЛЕНА"
echo "=========================================="
echo ""
echo "Для запуска используйте:"
echo "  ./start_with_logs_filtered.sh"
echo "  или"
echo "  ./start_with_logs.sh"
