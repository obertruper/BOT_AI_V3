#!/bin/bash
# Мониторинг ML сигналов в реальном времени

echo "📊 Мониторинг ML сигналов BOT_AI_V3"
echo "=================================="
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Следим за логами и раскрашиваем вывод
tail -f data/logs/bot_trading_*.log | while read line; do
    if [[ "$line" == *"BUY"* ]] || [[ "$line" == *"signal_type': 'BUY'"* ]]; then
        echo -e "${GREEN}💰 $line${NC}"
    elif [[ "$line" == *"SELL"* ]] || [[ "$line" == *"signal_type': 'SELL'"* ]]; then
        echo -e "${RED}💸 $line${NC}"
    elif [[ "$line" == *"NEUTRAL"* ]]; then
        echo -e "${YELLOW}⚖️  $line${NC}"
    elif [[ "$line" == *"ML предсказание"* ]] || [[ "$line" == *"ML Предсказание"* ]]; then
        echo -e "${CYAN}🤖 $line${NC}"
    elif [[ "$line" == *"confidence"* ]] || [[ "$line" == *"signal_strength"* ]]; then
        echo -e "${BLUE}📊 $line${NC}"
    elif [[ "$line" == *"ERROR"* ]]; then
        echo -e "${RED}❌ $line${NC}"
    else
        echo "$line"
    fi
done
