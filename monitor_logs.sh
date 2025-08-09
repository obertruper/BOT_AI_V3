#!/bin/bash

# Real-time Log Monitor for BOT_AI_V3
# ===================================

# Цвета для разных типов логов
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

clear
echo -e "${PURPLE}============================================================${NC}"
echo -e "${PURPLE}📊 BOT_AI_V3 - Real-time Log Monitor${NC}"
echo -e "${PURPLE}============================================================${NC}"
echo ""

# Функция для форматирования логов с цветами
format_logs() {
    local prefix=$1
    local color=$2
    while IFS= read -r line; do
        # Подсветка уровней логов
        line=$(echo "$line" | sed -E "s/ERROR/$(printf '\033[0;31mERROR\033[0m')/g")
        line=$(echo "$line" | sed -E "s/WARNING/$(printf '\033[1;33mWARNING\033[0m')/g")
        line=$(echo "$line" | sed -E "s/INFO/$(printf '\033[0;32mINFO\033[0m')/g")
        line=$(echo "$line" | sed -E "s/DEBUG/$(printf '\033[0;36mDEBUG\033[0m')/g")

        # Подсветка важных слов
        line=$(echo "$line" | sed -E "s/(BUY|SELL)/$(printf '\033[1;32m\1\033[0m')/g")
        line=$(echo "$line" | sed -E "s/(PROFIT|WIN)/$(printf '\033[1;32m\1\033[0m')/g")
        line=$(echo "$line" | sed -E "s/(LOSS|STOP)/$(printf '\033[0;31m\1\033[0m')/g")
        line=$(echo "$line" | sed -E "s/(\$[0-9]+\.?[0-9]*)/$(printf '\033[1;33m\1\033[0m')/g")

        echo -e "${color}[$prefix]${NC} $line"
    done
}

# Проверка наличия логов
if [ ! -d "data/logs" ]; then
    echo -e "${RED}Директория логов не найдена!${NC}"
    exit 1
fi

# Меню выбора режима мониторинга
echo -e "${YELLOW}Режимы мониторинга:${NC}"
echo "  1) Все логи одновременно (рекомендуется)"
echo "  2) Только торговые логи"
echo "  3) Только ошибки"
echo "  4) Только системные логи"
echo "  5) Критические события (ошибки + важные торговые события)"
echo ""
read -p "Выберите режим (1-5) [по умолчанию 1]: " mode

case $mode in
    2)
        echo -e "${GREEN}Мониторинг торговых логов...${NC}"
        tail -f data/logs/trading.log | format_logs "TRADE" "$GREEN"
        ;;
    3)
        echo -e "${RED}Мониторинг ошибок...${NC}"
        tail -f data/logs/error.log | format_logs "ERROR" "$RED"
        ;;
    4)
        echo -e "${BLUE}Мониторинг системных логов...${NC}"
        tail -f data/logs/system.log 2>/dev/null | format_logs "SYSTEM" "$BLUE"
        ;;
    5)
        echo -e "${YELLOW}Мониторинг критических событий...${NC}"
        # Фильтруем только важные события
        tail -f data/logs/trading.log data/logs/error.log | \
        grep -E "(ERROR|CRITICAL|PROFIT|LOSS|LIQUIDATION|MARGIN|executed|filled)" | \
        format_logs "CRITICAL" "$YELLOW"
        ;;
    *)
        # Режим по умолчанию - все логи
        echo -e "${CYAN}Мониторинг всех логов...${NC}"
        echo -e "${WHITE}Легенда: ${GREEN}[TRADE]${NC} ${RED}[ERROR]${NC} ${BLUE}[SYSTEM]${NC} ${PURPLE}[ML]${NC} ${CYAN}[API]${NC}"
        echo ""

        # Проверяем наличие multitail
        if command -v multitail &> /dev/null; then
            # Используем multitail для удобного просмотра
            multitail \
                -cT ANSI --label "[TRADE] " -ci green data/logs/trading.log \
                -cT ANSI --label "[ERROR] " -ci red data/logs/error.log \
                -cT ANSI --label "[SYSTEM] " -ci blue data/logs/system.log \
                -cT ANSI --label "[ML] " -ci magenta data/logs/ml_*.log \
                -cT ANSI --label "[API] " -ci cyan data/logs/api.log
        else
            # Fallback на параллельный tail
            (
                tail -f data/logs/trading.log 2>/dev/null | format_logs "TRADE" "$GREEN" &
                tail -f data/logs/error.log 2>/dev/null | format_logs "ERROR" "$RED" &
                tail -f data/logs/system.log 2>/dev/null | format_logs "SYSTEM" "$BLUE" &
                tail -f data/logs/ml_*.log 2>/dev/null | format_logs "ML" "$PURPLE" &
                tail -f data/logs/api.log 2>/dev/null | format_logs "API" "$CYAN" &

                # Также мониторим production логи если есть
                if [ -d "data/logs/production" ]; then
                    tail -f data/logs/production/*.log 2>/dev/null | format_logs "PROD" "$WHITE" &
                fi

                wait
            )
        fi
        ;;
esac
