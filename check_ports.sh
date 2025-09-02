#!/bin/bash

# Цветовые константы
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=========================================="
echo "📊 ДИАГНОСТИКА ПОРТОВ BOT_AI_V3"
echo "==========================================${NC}"
echo ""

# Список портов для проверки
declare -A PORTS=(
    ["PostgreSQL"]="5555"
    ["API_Server"]="8083"
    ["REST_API"]="8084"
    ["WebSocket"]="8085"
    ["Webhook"]="8086"
    ["Frontend"]="5173"
    ["Alt_API"]="8080"
)

echo -e "${YELLOW}Проверяем состояние портов...${NC}"
echo ""

# Функция для получения информации о процессе
get_process_info() {
    local pid=$1
    if [ -z "$pid" ]; then
        echo "N/A"
        return
    fi
    
    # Получаем информацию о процессе
    local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
    local args=$(ps -p $pid -o args= 2>/dev/null | head -c 100)
    echo "PID: $pid | CMD: $cmd | ARGS: ${args:0:50}..."
}

# Проверяем каждый порт
for service in "${!PORTS[@]}"; do
    port="${PORTS[$service]}"
    echo -e "${BLUE}Порт $port ($service):${NC}"
    
    # Проверяем с помощью lsof
    pids=$(lsof -ti :$port 2>/dev/null)
    
    if [ -z "$pids" ]; then
        echo -e "  ${GREEN}✅ Свободен${NC}"
    else
        echo -e "  ${RED}❌ Занят${NC}"
        for pid in $pids; do
            info=$(get_process_info $pid)
            echo -e "  ${YELLOW}   └─ $info${NC}"
            
            # Проверяем, это наш процесс или чужой
            if ps -p $pid -o args= 2>/dev/null | grep -q "BOT_AI_V3\|unified_launcher\|web.api.main"; then
                echo -e "  ${CYAN}      [Это процесс BOT_AI_V3]${NC}"
            else
                echo -e "  ${RED}      [Сторонний процесс]${NC}"
            fi
        done
    fi
    echo ""
done

# Поиск всех процессов проекта
echo -e "${CYAN}=========================================="
echo "🔍 ПОИСК ПРОЦЕССОВ BOT_AI_V3"
echo "==========================================${NC}"
echo ""

# Ищем процессы по разным паттернам
echo -e "${YELLOW}Поиск процессов по ключевым словам...${NC}"

patterns=(
    "unified_launcher"
    "web.api.main"
    "BOT_AI_V3"
    "bot_trading"
    "trading_engine"
    "uvicorn.*8083"
    "python.*main\.py"
)

found_any=false
for pattern in "${patterns[@]}"; do
    pids=$(pgrep -f "$pattern" 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo -e "${RED}Найдены процессы для паттерна '$pattern':${NC}"
        for pid in $pids; do
            info=$(get_process_info $pid)
            echo -e "  ${YELLOW}$info${NC}"
        done
        found_any=true
        echo ""
    fi
done

if [ "$found_any" = false ]; then
    echo -e "${GREEN}✅ Процессы BOT_AI_V3 не найдены${NC}"
fi

echo ""
echo -e "${CYAN}=========================================="
echo "💡 РЕКОМЕНДАЦИИ"
echo "==========================================${NC}"
echo ""

# Проверяем, есть ли занятые порты
occupied_ports=""
for service in "${!PORTS[@]}"; do
    port="${PORTS[$service]}"
    if lsof -ti :$port 2>/dev/null > /dev/null; then
        occupied_ports="$occupied_ports $port"
    fi
done

if [ -z "$occupied_ports" ]; then
    echo -e "${GREEN}✅ Все порты свободны! Система готова к запуску.${NC}"
    echo -e "${WHITE}   Запустите: ./start_with_logs_filtered.sh${NC}"
else
    echo -e "${RED}⚠️  Обнаружены занятые порты:$occupied_ports${NC}"
    echo ""
    echo -e "${YELLOW}Рекомендуемые действия:${NC}"
    echo -e "${WHITE}1. Остановите все процессы:${NC}"
    echo -e "${CYAN}   ./stop_all.sh${NC}"
    echo ""
    echo -e "${WHITE}2. Если порты все еще заняты, освободите их вручную:${NC}"
    for port in $occupied_ports; do
        echo -e "${CYAN}   sudo fuser -k $port/tcp${NC}"
    done
    echo ""
    echo -e "${WHITE}3. После освобождения портов запустите систему:${NC}"
    echo -e "${CYAN}   ./start_with_logs_filtered.sh${NC}"
fi

echo ""
echo -e "${CYAN}=========================================="
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "==========================================${NC}"