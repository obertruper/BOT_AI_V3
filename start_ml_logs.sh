#!/bin/bash
# Запуск BOT_AI_V3 с выводом только ML логов

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🤖 Запуск BOT_AI_V3 - только ML логи${NC}"
echo ""

source venv/bin/activate

# Запускаем систему в фоне
./start_with_logs.sh > /dev/null 2>&1 &
LAUNCHER_PID=$!

echo -e "${YELLOW}Ожидание запуска системы...${NC}"
sleep 5

echo -e "${GREEN}📊 Мониторинг ML сигналов:${NC}"
echo "=================================="

# Следим только за ML логами
tail -f data/logs/bot_trading_*.log | grep -E "ML|ml_|signal|prediction|confidence|BUY|SELL|NEUTRAL|Direction|Signal" | while read line; do
    if [[ "$line" == *"BUY"* ]]; then
        echo -e "${GREEN}💰 $line${NC}"
    elif [[ "$line" == *"SELL"* ]]; then
        echo -e "${RED}💸 $line${NC}"
    elif [[ "$line" == *"NEUTRAL"* ]]; then
        echo -e "${YELLOW}⚖️  $line${NC}"
    else
        echo -e "${CYAN}$line${NC}"
    fi
done

# Cleanup
trap "kill $LAUNCHER_PID 2>/dev/null; pkill -f 'tail -f'" EXIT
