#!/bin/bash

# Скрипт чистого запуска системы с проверками

echo "🧹 Очистка старых процессов..."
pkill -f "python.*unified_launcher" 2>/dev/null
pkill -f "python.*web/launcher" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 2

echo "✅ Активация виртуального окружения..."
source venv/bin/activate

echo "🔍 Проверка свободных портов..."
for port in 8083 8084 8085 8086 5173; do
    if lsof -i :$port >/dev/null 2>&1; then
        echo "⚠️ Порт $port занят, освобождаем..."
        fuser -k $port/tcp 2>/dev/null
    else
        echo "✅ Порт $port свободен"
    fi
done

echo "🚀 Запуск системы..."
python unified_launcher.py --mode=full 2>&1 | tee -a data/logs/startup_$(date +%Y%m%d_%H%M%S).log &

echo "⏳ Ожидание запуска (10 секунд)..."
sleep 10

echo "📊 Проверка статуса..."
if curl -s http://localhost:8083/api/health >/dev/null 2>&1; then
    echo "✅ API сервер работает"
else
    echo "❌ API сервер не отвечает"
fi

echo ""
echo "🌐 Доступные сервисы:"
echo "   • Dashboard:   http://localhost:5173"
echo "   • ML Panel:    http://localhost:5173/ml"
echo "   • API:         http://localhost:8083"
echo "   • API Docs:    http://localhost:8083/api/docs"
echo ""
echo "🛑 Для остановки: ./stop_all.sh"
