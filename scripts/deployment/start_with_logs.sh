#!/bin/bash

# Скрипт для запуска BOT_AI_V3 с отслеживанием логов в реальном времени

echo "🚀 Запуск BOT_AI_V3 с мониторингом логов"
echo "========================================"
echo ""

# Активируем виртуальное окружение
source venv/bin/activate

# Проверяем PostgreSQL
export PGPORT=5555
if ! psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 1;" > /dev/null 2>&1; then
    echo "❌ PostgreSQL не доступен на порту 5555"
    exit 1
fi
echo "✅ PostgreSQL доступен"

# Создаем директорию для логов если нет
mkdir -p data/logs

# Очищаем старые логи (опционально)
# rm -f data/logs/*.log

# Запускаем систему в фоне
echo ""
echo "🔧 Запуск Unified Launcher..."
python3 unified_launcher.py --mode=ml > data/logs/launcher.log 2>&1 &
LAUNCHER_PID=$!
echo "✅ Launcher запущен (PID: $LAUNCHER_PID)"

# Ждем немного для инициализации
sleep 3

# Проверяем что процесс запущен
if ! ps -p $LAUNCHER_PID > /dev/null; then
    echo "❌ Launcher не смог запуститься. Проверьте логи:"
    tail -50 data/logs/launcher.log
    exit 1
fi

echo ""
echo "📊 Мониторинг логов (Ctrl+C для выхода):"
echo "========================================"
echo ""
echo "Отслеживаемые события:"
echo "- 🎯 Торговые сигналы"
echo "- 📈 Открытие позиций"
echo "- 🛡️ Создание SL/TP"
echo "- 💰 Закрытие позиций"
echo "- ⚠️ Ошибки и предупреждения"
echo ""
echo "Подсказки:"
echo "- Для фильтрации только SL/TP: ./start_with_logs.sh | grep -E 'SL|TP|stop|profit'"
echo "- Для просмотра всех логов: tail -f data/logs/*.log"
echo "- Для остановки: ./stop_all.sh"
echo ""
echo "========================================"
echo ""

# Следим за всеми важными логами
tail -f data/logs/bot_trading_*.log data/logs/trading.log 2>/dev/null | grep --line-buffered -E "signal|order|position|SL|TP|stop_loss|take_profit|ERROR|WARNING|✅|❌|🎯|📈|💰|🛡️" | while read line; do
    # Цветовое выделение
    if echo "$line" | grep -q "ERROR"; then
        echo -e "\033[31m$line\033[0m"  # Красный для ошибок
    elif echo "$line" | grep -q "WARNING"; then
        echo -e "\033[33m$line\033[0m"  # Желтый для предупреждений
    elif echo "$line" | grep -qE "SL|TP|stop_loss|take_profit"; then
        echo -e "\033[36m$line\033[0m"  # Голубой для SL/TP
    elif echo "$line" | grep -q "signal"; then
        echo -e "\033[35m$line\033[0m"  # Пурпурный для сигналов
    elif echo "$line" | grep -q "position"; then
        echo -e "\033[32m$line\033[0m"  # Зеленый для позиций
    else
        echo "$line"
    fi
done
