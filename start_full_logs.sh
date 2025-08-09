#!/bin/bash
# Запуск BOT_AI_V3 с ПОЛНЫМ выводом всех логов в терминал

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Запуск BOT_AI_V3 с ПОЛНЫМ выводом логов${NC}"
echo -e "${YELLOW}📊 Режим: ML Trading для 9 символов${NC}"
echo -e "${BLUE}🔍 ВСЕ логи выводятся в терминал${NC}"
echo ""

# Активация виртуального окружения
source venv/bin/activate

# Установка переменных окружения для максимального вывода логов
export PYTHONUNBUFFERED=1
export BOT_AI_V3_LOG_LEVEL=DEBUG
export BOT_AI_V3_LOG_TO_CONSOLE=true
export LOG_LEVEL=DEBUG

# Проверка PostgreSQL
echo -e "${YELLOW}Проверка PostgreSQL на порту 5555...${NC}"
if pg_isready -p 5555 -q; then
    echo -e "${GREEN}✅ PostgreSQL работает${NC}"
else
    echo -e "${RED}❌ PostgreSQL не доступен на порту 5555${NC}"
    exit 1
fi

# Удаление старых логов для чистого старта
echo -e "${YELLOW}Очистка старых логов...${NC}"
rm -f data/logs/*.log

# Функция для обработки сигнала выхода
cleanup() {
    echo -e "\n${YELLOW}⚠️  Получен сигнал остановки...${NC}"
    # Убиваем все дочерние процессы
    pkill -P $$
    # Убиваем процессы по имени
    pkill -f "python.*unified_launcher"
    pkill -f "python.*main.py"
    pkill -f "tail -f"
    echo -e "${GREEN}✅ Все процессы остановлены${NC}"
    exit 0
}

# Устанавливаем обработчик сигналов
trap cleanup SIGINT SIGTERM

# Запуск системы с выводом всех логов
echo -e "${GREEN}🚀 Запуск системы...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Запускаем систему и следим за логами
{
    # Запускаем unified_launcher
    python3 unified_launcher.py --mode=ml 2>&1 &
    LAUNCHER_PID=$!

    # Даем время на инициализацию
    sleep 3

    # Следим за всеми логами в реальном времени
    tail -f data/logs/bot_trading_*.log 2>/dev/null | while IFS= read -r line; do
        # Раскрашиваем вывод по типу сообщения
        if [[ "$line" == *"ERROR"* ]] || [[ "$line" == *"CRITICAL"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ "$line" == *"WARNING"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ "$line" == *"SUCCESS"* ]] || [[ "$line" == *"✅"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ "$line" == *"INFO"* ]]; then
            echo -e "${BLUE}$line${NC}"
        elif [[ "$line" == *"DEBUG"* ]]; then
            echo -e "${PURPLE}$line${NC}"
        elif [[ "$line" == *"ML"* ]] || [[ "$line" == *"signal"* ]] || [[ "$line" == *"prediction"* ]]; then
            echo -e "${CYAN}🤖 $line${NC}"
        elif [[ "$line" == *"BUY"* ]]; then
            echo -e "${GREEN}💰 $line${NC}"
        elif [[ "$line" == *"SELL"* ]]; then
            echo -e "${RED}💸 $line${NC}"
        elif [[ "$line" == *"NEUTRAL"* ]]; then
            echo -e "${YELLOW}⚖️  $line${NC}"
        elif [[ "$line" == *"confidence"* ]] || [[ "$line" == *"signal_strength"* ]]; then
            echo -e "${CYAN}📊 $line${NC}"
        else
            echo "$line"
        fi
    done &

    # Ждем завершения launcher
    wait $LAUNCHER_PID
}

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⚠️  Система остановлена${NC}"
