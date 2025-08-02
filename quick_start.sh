#!/bin/bash
# Быстрый запуск всей системы BOT Trading v3

echo "🚀 Запуск BOT Trading v3..."

# Переход в директорию проекта
cd "$(dirname "$0")"

# Активация виртуального окружения
source venv/bin/activate

# Запуск всех компонентов в фоне
echo "▶ Запуск Core System..."
python main.py > logs/core.log 2>&1 &
CORE_PID=$!

echo "▶ Запуск API Backend..."
python web/launcher.py > logs/api.log 2>&1 &
API_PID=$!

echo "▶ Запуск Web Frontend..."
cd web/frontend && npm run dev -- --host > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Ждем немного для инициализации
sleep 5

echo ""
echo "✅ Система запущена!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Dashboard: http://localhost:5173"
echo "📚 API Docs:  http://localhost:8080/api/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Процессы:"
echo "  Core System: PID $CORE_PID"
echo "  API Backend: PID $API_PID"
echo "  Frontend:    PID $FRONTEND_PID"
echo ""
echo "Для остановки используйте: pkill -f 'python main.py|python web/launcher.py|vite'"
echo ""

# Сохраняем PID'ы
echo $CORE_PID > logs/core.pid
echo $API_PID > logs/api.pid
echo $FRONTEND_PID > logs/frontend.pid

# Ждем нажатия клавиши
read -p "Нажмите Enter для продолжения..."
