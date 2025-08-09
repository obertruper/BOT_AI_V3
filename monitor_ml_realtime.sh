#!/bin/bash

echo "📊 ML Trading Monitor - BOT_AI_V3"
echo "================================="
echo "🔍 Отслеживание торговых сигналов в реальном времени"
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Функция для вывода с цветами
colorize() {
    while IFS= read -r line; do
        if [[ $line =~ "BUY" ]] && [[ ! $line =~ "NEUTRAL" ]]; then
            echo -e "${GREEN}[BUY]${NC} $line"
        elif [[ $line =~ "SELL" ]] && [[ ! $line =~ "NEUTRAL" ]]; then
            echo -e "${RED}[SELL]${NC} $line"
        elif [[ $line =~ "NEUTRAL" ]]; then
            echo -e "${YELLOW}[NEUTRAL]${NC} $line"
        elif [[ $line =~ "signal_type" ]] || [[ $line =~ "returns_15m" ]]; then
            echo -e "${BLUE}[ML]${NC} $line"
        elif [[ $line =~ "ERROR" ]]; then
            echo -e "${RED}[ERROR]${NC} $line"
        elif [[ $line =~ "Exchange Registry" ]]; then
            echo -e "${PURPLE}[EXCHANGE]${NC} $line"
        else
            echo "$line"
        fi
    done
}

# Найти последний лог файл
LATEST_LOG=$(ls -t data/logs/bot_trading_*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "❌ Логи не найдены!"
    exit 1
fi

echo "📁 Читаем лог: $LATEST_LOG"
echo "🕐 Начинаем мониторинг..."
echo ""

# Мониторинг в реальном времени
tail -f "$LATEST_LOG" | grep -E "signal_type|returns_15m|BUY|SELL|NEUTRAL|ERROR|profit|loss|Exchange" | colorize
