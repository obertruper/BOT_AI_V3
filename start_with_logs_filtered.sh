#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Генерируем уникальный ID сессии
SESSION_ID=$(date +%Y%m%d_%H%M%S)
LOG_DATE=$(date +%Y%m%d)

echo -e "${CYAN}=========================================="
echo "🚀 ЗАПУСК BOT_AI_V3 С МОНИТОРИНГОМ"
echo "==========================================${NC}"
echo ""

# Создаем директории для логов
mkdir -p data/logs/sessions/${SESSION_ID}
mkdir -p data/logs/archive

# Показываем информацию о логах
echo -e "${BLUE}📁 ЛОГИ СЕССИИ #${SESSION_ID}${NC}"
echo -e "${GREEN}   Основная директория: $(pwd)/data/logs/${NC}"
echo -e "${GREEN}   Логи этой сессии: data/logs/sessions/${SESSION_ID}/${NC}"
echo -e "${GREEN}   Главный лог: data/logs/bot_trading_${LOG_DATE}.log${NC}"
echo ""
echo -e "${YELLOW}📋 Структура логов:${NC}"
echo "   • bot_trading_${LOG_DATE}.log - главный торговый лог"
echo "   • launcher_${SESSION_ID}.log - лог системы запуска"
echo "   • api_${SESSION_ID}.log - лог API сервера"
echo "   • frontend_${SESSION_ID}.log - лог веб-интерфейса"
echo "   • ml_${SESSION_ID}.log - лог ML системы"
echo ""

# Проверяем, не запущена ли уже система
if pgrep -f "python.*unified_launcher" > /dev/null; then
    echo -e "${RED}⚠️  Система уже запущена!${NC}"
    echo "Используйте ./stop_all.sh для остановки"
    exit 1
fi

# Активируем виртуальное окружение
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✅ Виртуальное окружение активировано${NC}"
else
    echo -e "${RED}❌ Виртуальное окружение не найдено!${NC}"
    echo "Создайте его: python3 -m venv venv"
    exit 1
fi

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    exit 1
fi

# Архивируем старые логи
if ls data/logs/bot_trading_*.log 1> /dev/null 2>&1; then
    echo -e "${YELLOW}📦 Архивирование старых логов...${NC}"
    find data/logs -name "bot_trading_*.log" -mtime +1 -exec mv {} data/logs/archive/ \; 2>/dev/null
    echo -e "${GREEN}   ✅ Старые логи перемещены в архив${NC}"
fi

echo ""
echo -e "${CYAN}📊 Конфигурация:${NC}"
echo "   Режим: core (торговля + ML)"
echo "   Плечо: 5x (из config/trading.yaml)"
echo "   Риск: 2% на сделку"
echo "   Фиксированный баланс: $100"
echo "   Partial TP: включен (1.2%, 2.4%, 3.5%)"

echo ""
echo -e "${BLUE}🔧 Запуск системы...${NC}"

# Проверяем и загружаем исторические данные если нужно
echo "   → Проверка рыночных данных..."
python3 -c "
import asyncio
from database.connections.postgres import AsyncPGPool

async def check_data():
    try:
        result = await AsyncPGPool.fetch(
            '''SELECT COUNT(*) as cnt FROM raw_market_data
               WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000'''
        )
        return result[0]['cnt'] > 0
    except:
        return False

has_data = asyncio.run(check_data())
exit(0 if has_data else 1)
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}   ⚠️  Данные устарели, загружаем свежие...${NC}"
    python3 load_fresh_data.py > data/logs/sessions/${SESSION_ID}/data_load.log 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}   ✅ Рыночные данные загружены${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Не удалось загрузить данные, продолжаем без них${NC}"
    fi
else
    echo -e "${GREEN}   ✅ Рыночные данные актуальны${NC}"
fi

# Создаем симлинки для текущих логов
ln -sf sessions/${SESSION_ID}/launcher.log data/logs/launcher_current.log
ln -sf sessions/${SESSION_ID}/api.log data/logs/api_current.log
ln -sf sessions/${SESSION_ID}/frontend.log data/logs/frontend_current.log
ln -sf sessions/${SESSION_ID}/ml.log data/logs/ml_current.log

# Запускаем торговое ядро с ML
echo "   → Запуск торгового ядра с ML..."
nohup python unified_launcher.py --mode=ml > data/logs/sessions/${SESSION_ID}/launcher.log 2>&1 &
LAUNCHER_PID=$!
echo -e "${GREEN}   ✅ Торговое ядро запущено (PID: $LAUNCHER_PID)${NC}"

# Ждем инициализации ядра
sleep 5

# Запускаем API сервер
echo "   → Запуск API сервера..."
nohup python unified_launcher.py --mode=api > data/logs/sessions/${SESSION_ID}/api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}   ✅ API сервер запущен (PID: $API_PID, http://localhost:8080)${NC}"

# Запускаем веб-интерфейс
echo "   → Запуск веб-интерфейса..."
cd web/frontend
nohup npm run dev > ../../data/logs/sessions/${SESSION_ID}/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..
echo -e "${GREEN}   ✅ Веб-интерфейс запущен (PID: $FRONTEND_PID, http://localhost:5173)${NC}"

# Сохраняем PID'ы в файл для последующей остановки
echo "$LAUNCHER_PID" > data/logs/sessions/${SESSION_ID}/launcher.pid
echo "$API_PID" > data/logs/sessions/${SESSION_ID}/api.pid
echo "$FRONTEND_PID" > data/logs/sessions/${SESSION_ID}/frontend.pid

echo ""
echo -e "${GREEN}✅ Все компоненты запущены:${NC}"
echo "   • Торговое ядро: PID $LAUNCHER_PID"
echo "   • API сервер: http://localhost:8080 (PID $API_PID)"
echo "   • Веб-интерфейс: http://localhost:5173 (PID $FRONTEND_PID)"
echo "   • API документация: http://localhost:8080/api/docs"

# Проверяем что процессы работают
sleep 2
if ps -p $LAUNCHER_PID > /dev/null && ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}✅ Все процессы активны${NC}"
else
    echo -e "${RED}❌ Один или несколько процессов завершились с ошибкой!${NC}"
    echo "Проверьте логи:"
    echo "  • tail -f data/logs/sessions/${SESSION_ID}/launcher.log"
    echo "  • tail -f data/logs/sessions/${SESSION_ID}/api.log"
    echo "  • tail -f data/logs/sessions/${SESSION_ID}/frontend.log"
    exit 1
fi

echo ""
echo -e "${CYAN}=========================================="
echo "📋 МОНИТОРИНГ ЛОГОВ"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}🔍 Отслеживаемые события:${NC}"
echo "   • 🎯 Торговые сигналы (BUY/SELL)"
echo "   • 📊 ML предсказания и уникальность"
echo "   • 💰 Открытие/закрытие позиций"
echo "   • 🎯 Partial TP (частичное закрытие)"
echo "   • 🛡️ SL/TP обновления"
echo "   • ⚠️ Ошибки и предупреждения"
echo ""
echo -e "${BLUE}📂 Быстрый доступ к логам:${NC}"
echo "   Все логи сессии: tail -f data/logs/sessions/${SESSION_ID}/*.log"
echo "   Главный лог: tail -f data/logs/bot_trading_${LOG_DATE}.log"
echo "   ML система: tail -f data/logs/sessions/${SESSION_ID}/ml.log"
echo "   API: tail -f data/logs/sessions/${SESSION_ID}/api.log"
echo ""
echo -e "${GREEN}Отслеживаем логи в реальном времени...${NC}"
echo "Нажмите Ctrl+C для выхода из мониторинга (система продолжит работать)"
echo ""
echo "==========================================  "

# Функция для цветного вывода логов
colorize_logs() {
    while IFS= read -r line; do
        if echo "$line" | grep -q "ERROR\|CRITICAL"; then
            echo -e "${RED}$line${NC}"
        elif echo "$line" | grep -q "WARNING"; then
            echo -e "${YELLOW}$line${NC}"
        elif echo "$line" | grep -q "partial\|Partial\|PARTIAL"; then
            echo -e "${CYAN}💰 $line${NC}"
        elif echo "$line" | grep -q "signal.*BUY\|signal.*SELL\|Signal generated"; then
            echo -e "${GREEN}🎯 $line${NC}"
        elif echo "$line" | grep -q "position\|Position"; then
            echo -e "${BLUE}📊 $line${NC}"
        elif echo "$line" | grep -q "ML\|unique\|prediction"; then
            echo -e "${CYAN}🤖 $line${NC}"
        elif echo "$line" | grep -q "SL\|TP\|stop.loss\|take.profit"; then
            echo -e "${YELLOW}🛡️ $line${NC}"
        else
            echo "$line"
        fi
    done
}

# Запускаем мониторинг всех логов с цветным выводом
tail -f data/logs/bot_trading_${LOG_DATE}.log \
        data/logs/sessions/${SESSION_ID}/launcher.log \
        data/logs/sessions/${SESSION_ID}/api.log \
        data/logs/sessions/${SESSION_ID}/ml.log 2>/dev/null | \
    grep --line-buffered -E "signal|order|position|partial|SL|TP|ML|unique|prediction|ERROR|WARNING|CRITICAL" | \
    colorize_logs
