#!/bin/bash

# Скрипт для мониторинга логов BOT_AI_V3 в реальном времени
# Показывает все логи в одном терминале с цветовой разметкой

# Цвета для разных компонентов
COLOR_RESET='\033[0m'
COLOR_CORE='\033[1;34m'    # Синий
COLOR_API='\033[1;32m'      # Зеленый
COLOR_ML='\033[1;35m'       # Пурпурный
COLOR_ERROR='\033[1;31m'    # Красный
COLOR_WARNING='\033[1;33m'  # Желтый
COLOR_TRADE='\033[1;36m'    # Циан

# Функция для цветной печати
print_colored() {
    local color=$1
    local component=$2
    local message=$3
    echo -e "${color}[${component}]${COLOR_RESET} ${message}"
}

# Проверка наличия multitail
if ! command -v multitail &> /dev/null; then
    echo "📦 Установка multitail для продвинутого мониторинга..."
    sudo apt-get update && sudo apt-get install -y multitail
fi

echo "🚀 Запуск мониторинга логов BOT_AI_V3..."
echo "📍 Нажмите Ctrl+C для выхода"
echo "=================================================================================="

# Опции запуска
MODE=${1:-"all"}  # all, simple, errors, trades

case $MODE in
    "all")
        echo "📊 Режим: Все логи с multitail"
        # Multitail с разными окнами для каждого типа логов
        multitail \
            -i data/logs/bot_trading_$(date +%Y%m%d).log \
            -I data/logs/errors.log \
            --label "[TRADING] " \
            --label "[ERRORS] " \
            -c
        ;;

    "simple")
        echo "📊 Режим: Простой tail с цветами"
        # Объединенный вывод с цветовой разметкой
        tail -f data/logs/bot_trading_$(date +%Y%m%d).log | while IFS= read -r line; do
            if [[ $line == *"ERROR"* ]]; then
                print_colored "$COLOR_ERROR" "ERROR" "$line"
            elif [[ $line == *"WARNING"* ]]; then
                print_colored "$COLOR_WARNING" "WARN" "$line"
            elif [[ $line == *"ml_"* ]] || [[ $line == *"ML"* ]]; then
                print_colored "$COLOR_ML" "ML" "$line"
            elif [[ $line == *"api"* ]] || [[ $line == *"API"* ]]; then
                print_colored "$COLOR_API" "API" "$line"
            elif [[ $line == *"trading"* ]] || [[ $line == *"order"* ]] || [[ $line == *"signal"* ]]; then
                print_colored "$COLOR_TRADE" "TRADE" "$line"
            elif [[ $line == *"core"* ]] || [[ $line == *"system"* ]]; then
                print_colored "$COLOR_CORE" "CORE" "$line"
            else
                echo "$line"
            fi
        done
        ;;

    "errors")
        echo "📊 Режим: Только ошибки и предупреждения"
        tail -f data/logs/bot_trading_$(date +%Y%m%d).log data/logs/errors.log | \
            grep -E "ERROR|WARNING|CRITICAL|Exception|Failed" --color=always
        ;;

    "trades")
        echo "📊 Режим: Только торговые операции"
        tail -f data/logs/bot_trading_$(date +%Y%m%d).log | \
            grep -E "signal_type|order|trade|position|returns_15m|buy|sell|profit|loss" --color=always | \
            while IFS= read -r line; do
                if [[ $line == *"profit"* ]] || [[ $line == *"returns_15m.*[0-9]"* ]]; then
                    print_colored "$COLOR_TRADE" "PROFIT" "$line"
                elif [[ $line == *"loss"* ]]; then
                    print_colored "$COLOR_ERROR" "LOSS" "$line"
                elif [[ $line == *"buy"* ]] || [[ $line == *"BUY"* ]]; then
                    print_colored "$COLOR_API" "BUY" "$line"
                elif [[ $line == *"sell"* ]] || [[ $line == *"SELL"* ]]; then
                    print_colored "$COLOR_WARNING" "SELL" "$line"
                else
                    echo "$line"
                fi
            done
        ;;

    *)
        echo "❌ Неизвестный режим: $MODE"
        echo "Доступные режимы: all, simple, errors, trades"
        exit 1
        ;;
esac
