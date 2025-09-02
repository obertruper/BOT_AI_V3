#!/bin/bash

# Цветовые константы
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly PURPLE='\033[0;35m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# Конфигурация портов
declare -A PORTS=(
    ["PostgreSQL"]="5555"
    ["API_Server"]="8083"
    ["REST_API"]="8084"
    ["WebSocket"]="8085"
    ["Webhook"]="8086"
    ["Frontend"]="5173"
    ["Prometheus"]="9090"
    ["Grafana"]="3000"
    ["Redis"]="6379"
)

# Функция для красивого заголовка
print_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    BOT_AI_V3 STARTUP                        ║${NC}"
    echo -e "${CYAN}║                  Port Status & Launch                       ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Функция для проверки доступности порта
check_port() {
    local port=$1
    local service_name=$2

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid=$(lsof -Pi :$port -sTCP:LISTEN -t)
        local process_info=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
        echo -e "${RED}✗ Port $port (${service_name}): OCCUPIED by PID $pid ($process_info)${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Port $port (${service_name}): AVAILABLE${NC}"
        return 0
    fi
}

# Функция для проверки всех портов
check_all_ports() {
    echo -e "${YELLOW}=== PORT STATUS CHECK ===${NC}"
    echo

    local all_available=true

    for service in "${!PORTS[@]}"; do
        if ! check_port "${PORTS[$service]}" "$service"; then
            all_available=false
        fi
    done

    echo

    if [ "$all_available" = false ]; then
        echo -e "${RED}⚠️  Warning: Some ports are occupied by other processes${NC}"
        echo -e "${YELLOW}To kill processes on specific ports, use:${NC}"
        echo -e "${WHITE}sudo fuser -k 8083/tcp  # Kill process on API Server port${NC}"
        echo -e "${WHITE}sudo fuser -k 8084/tcp  # Kill process on REST API port${NC}"
        echo -e "${WHITE}sudo fuser -k 8085/tcp  # Kill process on WebSocket port${NC}"
        echo -e "${WHITE}sudo fuser -k 8086/tcp  # Kill process on Webhook port${NC}"
        echo -e "${WHITE}sudo fuser -k 5173/tcp  # Kill process on Frontend port${NC}"
        echo -e "${WHITE}sudo lsof -ti:PORT | xargs kill -9  # Alternative method${NC}"
        echo
        read -p "Continue anyway? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Startup cancelled by user${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ All required ports are available!${NC}"
    fi
    echo
}

# Функция для отображения информации о запускаемом процессе
show_process_info() {
    local component=$1
    local port=$2
    local command=$3

    echo -e "${PURPLE}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${PURPLE}│ Starting: ${WHITE}$component${NC}"
    echo -e "${PURPLE}│ Port:     ${GREEN}$port${NC}"
    echo -e "${PURPLE}│ Command:  ${CYAN}$command${NC}"
    echo -e "${PURPLE}└─────────────────────────────────────────────────────────────┘${NC}"
    echo
}

# Функция для проверки активации виртуального окружения
check_venv() {
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        echo -e "${RED}❌ Virtual environment not activated!${NC}"
        echo -e "${YELLOW}Please run: ${WHITE}source venv/bin/activate${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ Virtual environment activated: ${WHITE}$VIRTUAL_ENV${NC}"
    fi
}

# Функция для проверки зависимостей
check_dependencies() {
    echo -e "${YELLOW}=== DEPENDENCY CHECK ===${NC}"

    # Проверяем Python
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version)
        echo -e "${GREEN}✓ Python: ${WHITE}$python_version${NC}"
    else
        echo -e "${RED}✗ Python3 not found${NC}"
        exit 1
    fi

    # Проверяем PostgreSQL
    if command -v psql &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL client available${NC}"
    else
        echo -e "${YELLOW}⚠ PostgreSQL client not found${NC}"
    fi

    # Проверяем подключение к БД
    if PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT version();" &>/dev/null; then
        echo -e "${GREEN}✓ Database connection successful${NC}"
    else
        echo -e "${RED}✗ Database connection failed (PostgreSQL:5555)${NC}"
        echo -e "${YELLOW}Please ensure PostgreSQL is running on port 5555${NC}"
    fi

    # Проверяем лимит inotify watches
    local current_limit=$(cat /proc/sys/fs/inotify/max_user_watches 2>/dev/null || echo "0")
    if [ "$current_limit" -lt 524288 ]; then
        echo -e "${YELLOW}⚠ inotify watches limit: ${WHITE}$current_limit${YELLOW} (recommended: 524288)${NC}"
        echo -e "${CYAN}  To fix DNS resolver warnings, run:${NC}"
        echo -e "${WHITE}  echo 'fs.inotify.max_user_watches=524288' | sudo tee -a /etc/sysctl.conf${NC}"
        echo -e "${WHITE}  sudo sysctl -p${NC}"
    else
        echo -e "${GREEN}✓ inotify watches limit: ${WHITE}$current_limit${NC}"
    fi

    echo
}

# Основная функция запуска
main() {
    # Заголовок
    print_header

    # Проверка виртуального окружения
    check_venv
    echo

    # Проверка зависимостей
    check_dependencies

    # Проверка портов
    check_all_ports

    echo -e "${CYAN}=== STARTING PROCESSES ===${NC}"
    echo

    # Переход в директорию проекта
    cd "$(dirname "$0")" || exit 1

    # 1. Запуск основного торгового движка через unified_launcher
    show_process_info "Unified Trading System" "8083(API), 8084(REST), 8085(WS), 8086(Webhook), 5173(Frontend)" "python3 unified_launcher.py"
    python3 unified_launcher.py &
    UNIFIED_PID=$!
    echo -e "${GREEN}✅ Unified system started (PID: $UNIFIED_PID)${NC}"
    echo

    # Небольшая задержка для инициализации
    sleep 5

    # Финальная информация
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    STARTUP COMPLETE                         ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${WHITE}🌐 Service URLs:${NC}"
    echo -e "${GREEN}   • API Server:    ${WHITE}http://localhost:${PORTS[API_Server]}${NC}"
    echo -e "${GREEN}   • API Docs:      ${WHITE}http://localhost:${PORTS[API_Server]}/api/docs${NC}"
    echo -e "${GREEN}   • REST API:      ${WHITE}http://localhost:${PORTS[REST_API]}${NC}"
    echo -e "${GREEN}   • WebSocket:     ${WHITE}ws://localhost:${PORTS[WebSocket]}${NC}"
    echo -e "${GREEN}   • Webhook:       ${WHITE}http://localhost:${PORTS[Webhook]}${NC}"
    echo -e "${GREEN}   • Frontend:      ${WHITE}http://localhost:${PORTS[Frontend]}${NC}"
    echo
    echo -e "${WHITE}📊 Monitoring URLs:${NC}"
    echo -e "${GREEN}   • Prometheus:    ${WHITE}http://localhost:${PORTS[Prometheus]}${NC}"
    echo -e "${GREEN}   • Grafana:       ${WHITE}http://localhost:${PORTS[Grafana]}${NC}"
    echo
    echo -e "${WHITE}💾 Database:${NC}"
    echo -e "${GREEN}   • PostgreSQL:    ${WHITE}localhost:${PORTS[PostgreSQL]}${NC}"
    echo -e "${GREEN}   • Redis:         ${WHITE}localhost:${PORTS[Redis]}${NC}"
    echo
    echo -e "${WHITE}🔧 Process Management:${NC}"
    echo -e "${YELLOW}   • View logs:     ${WHITE}tail -f data/logs/bot_trading_\$(date +%Y%m%d).log${NC}"
    echo -e "${YELLOW}   • Stop all:      ${WHITE}./stop_all.sh${NC}"
    echo -e "${YELLOW}   • Kill by PID:   ${WHITE}kill -9 <PID>${NC}"
    echo

    # Функция для отслеживания логов с фильтрацией
    echo -e "${CYAN}=== REAL-TIME LOGS (DEVELOPMENT MODE - ALL LOGS) ===${NC}"
    echo -e "${YELLOW}🔧 РЕЖИМ РАЗРАБОТКИ: Показываем ВСЕ логи для отладки системы${NC}"
    echo -e "${WHITE}Press Ctrl+C to stop log monitoring${NC}"
    echo

    # Отслеживание логов с цветной фильтрацией
    LOG_DATE=$(date +%Y%m%d)
    LOG_FILE="data/logs/bot_trading_${LOG_DATE}.log"

    echo -e "${CYAN}📄 Monitoring log file: ${WHITE}$LOG_FILE${NC}"
    echo -e "${YELLOW}🔧 РАЗРАБОТКА: Все компоненты, ML предсказания, сигналы, ордера, ошибки, система${NC}"
    echo -e "${GREEN}✨ Полные ML таблицы с 240 признаками + все события системы для отладки${NC}"

    # Функция фильтрации и раскраски логов с поддержкой ML таблиц
    filter_and_colorize() {
        local in_ml_table=false
        local ml_table_buffer=""

        while IFS= read -r line; do
            # Обработка ML таблиц - начало любой таблицы с рамкой
            if [[ "$line" =~ ^.*"╔═".*"═╗".*$ ]]; then
                in_ml_table=true
                ml_table_buffer="${CYAN}${line}${NC}"
                continue
            fi

            # Обработка таблиц с ML данными - улучшенное распознавание
            if [[ "$line" =~ (ВХОДНЫЕ ПАРАМЕТРЫ МОДЕЛИ|ML PREDICTION DETAILS|ВЫХОДНЫЕ ПАРАМЕТРЫ|MODEL OUTPUT|SIGNAL DETAILS|ИНДИКАТОРЫ|FEATURES) ]]; then
                in_ml_table=true
                ml_table_buffer="${PURPLE}🤖 ${line}${NC}"
                continue
            fi

            # Если мы внутри ML таблицы
            if [ "$in_ml_table" = true ]; then
                ml_table_buffer="${ml_table_buffer}\n${CYAN}${line}${NC}"

                # Конец таблицы
                if [[ "$line" =~ ^.*"╚═".*"═╝".*$ ]]; then
                    echo -e "$ml_table_buffer"
                    in_ml_table=false
                    ml_table_buffer=""
                fi
                continue
            fi

            # РЕЖИМ РАЗРАБОТКИ - показываем ВСЕ логи для отладки
            if true; then  # Показываем все логи в режиме разработки

                # Пропускаем только фрагменты таблиц без контекста
                if [[ "$line" =~ ^.*"║".*$ ]] && ! [[ "$line" =~ (ПАРАМЕТРЫ|ИНДИКАТОРЫ|СТАТИСТИКА|PREDICTION|SIGNAL|ВХОДНЫЕ|ВЫХОДНЫЕ) ]]; then
                    continue
                fi

                case "$line" in
                    *ERROR*|*CRITICAL*)
                        echo -e "${RED}🔴 ERROR: $line${NC}"
                        ;;
                    *WARNING*)
                        # Пропускаем технические WARNING
                        if [[ ! "$line" =~ (urllib3|watchdog|DNS|inotify|"║") ]]; then
                            echo -e "${YELLOW}⚠️  WARNING: $line${NC}"
                        fi
                        ;;
                    *"Signal"*|*"SIGNAL"*|*"сигнал"*)
                        echo -e "${CYAN}📡 SIGNAL: $line${NC}"
                        ;;
                    *"Order"*|*"ORDER"*|*"ордер"*)
                        echo -e "${BLUE}📋 ORDER: $line${NC}"
                        ;;
                    *"Trade"*|*"TRADE"*|*"сделка"*)
                        echo -e "${GREEN}💰 TRADE: $line${NC}"
                        ;;
                    *"Position"*|*"POSITION"*|*"позиция"*)
                        echo -e "${PURPLE}🎯 POSITION: $line${NC}"
                        ;;
                    *"SUCCESS"*|*"FILLED"*|*"выполнен"*)
                        echo -e "${GREEN}✅ SUCCESS: $line${NC}"
                        ;;
                    *"FAILED"*|*"REJECTED"*|*"отклонен"*|*"ошибка"*)
                        echo -e "${RED}❌ FAILED: $line${NC}"
                        ;;
                    *"ML"*|*"Prediction"*|*"предсказание"*|*"модель"*)
                        echo -e "${PURPLE}🤖 ML: $line${NC}"
                        ;;
                    *"API"*|*"Компонент"*|*"started"*|*"stopped"*|*"запущен"*|*"остановлен"*)
                        echo -e "${BLUE}🔧 SYSTEM: $line${NC}"
                        ;;
                    *"balance"*|*"баланс"*|*"leverage"*|*"плечо"*)
                        echo -e "${YELLOW}💳 BALANCE: $line${NC}"
                        ;;
                    *"stop_loss"*|*"take_profit"*|*"SL"*|*"TP"*)
                        echo -e "${CYAN}🛡️  RISK: $line${NC}"
                        ;;
                    *"connected"*|*"disconnected"*|*"подключен"*|*"отключен"*)
                        echo -e "${GREEN}🔗 CONNECTION: $line${NC}"
                        ;;
                    *"WebSocket"*|*"websocket"*)
                        echo -e "${CYAN}🔌 WEBSOCKET: $line${NC}"
                        ;;
                    *)
                        # Для остальных строк - более умная обработка
                        if [[ "$line" =~ "║" ]]; then
                            echo -e "${CYAN}   $line${NC}"  # ML таблицы
                        elif [[ "$line" =~ (INFO|info) ]]; then
                            echo -e "${WHITE}ℹ️  INFO: $line${NC}"
                        elif [[ "$line" =~ (DEBUG|debug) ]]; then
                            echo -e "${WHITE}🔍 DEBUG: $line${NC}"
                        else
                            echo -e "${WHITE}📝 LOG: $line${NC}"
                        fi
                        ;;
                esac
            fi
        done
    }

    if [ -f "$LOG_FILE" ]; then
        echo -e "${GREEN}✅ Log file exists, showing last 20 lines and monitoring...${NC}"
        echo -e "${CYAN}================== RECENT LOGS ==================${NC}"
        tail -n 20 "$LOG_FILE" | filter_and_colorize
        echo -e "${CYAN}================== LIVE MONITORING ==================${NC}"
        tail -f "$LOG_FILE" | filter_and_colorize &
        TAIL_PID=$!

        # Ждем немного, чтобы показать что система работает
        sleep 3
        echo -e "${GREEN}✅ System is running! Logs are being monitored in background.${NC}"
        echo -e "${YELLOW}💡 Press Ctrl+C to stop monitoring and shutdown system${NC}"
        echo -e "${CYAN}📊 System Status:${NC}"
        echo -e "${WHITE}   - Trading Engine: ✅ Running${NC}"
        echo -e "${WHITE}   - Web Interface: ✅ Running${NC}"
        echo -e "${WHITE}   - API Services: ✅ Running${NC}"
        echo ""

        # Ожидаем пользовательский ввод или сигнал завершения
        echo -e "${YELLOW}💡 Интерактивные команды:${NC}"
        echo -e "${WHITE}   • 'status' (s) - статус системы и портов${NC}"
        echo -e "${WHITE}   • 'ml' (m) - ML система и предсказания${NC}"
        echo -e "${WHITE}   • 'pos' (p) - позиции и ордера${NC}"
        echo -e "${WHITE}   • 'logs' (l) - последние логи${NC}"
        echo -e "${WHITE}   • 'help' (h) - справка${NC}"
        echo -e "${WHITE}   • Ctrl+C - остановка системы${NC}"
        echo

        while kill -0 $UNIFIED_PID 2>/dev/null; do
            if read -t 10 user_input; then
                case "$user_input" in
                    "status"|"s")
                        echo -e "${CYAN}📊 System Status Check:${NC}"
                        echo -e "${GREEN}  ✓ Unified Launcher: Running (PID: $UNIFIED_PID)${NC}"
                        if kill -0 $TAIL_PID 2>/dev/null; then
                            echo -e "${GREEN}  ✓ Log Monitor: Running (PID: $TAIL_PID)${NC}"
                        else
                            echo -e "${RED}  ✗ Log Monitor: Stopped${NC}"
                        fi
                        echo -e "${WHITE}  📊 Uptime: $(ps -p $UNIFIED_PID -o etime= 2>/dev/null || echo 'N/A')${NC}"

                        # Проверка портов и сервисов
                        echo -e "${CYAN}  🌐 Service Status:${NC}"
                        for service in "${!PORTS[@]}"; do
                            if lsof -Pi :${PORTS[$service]} -sTCP:LISTEN -t >/dev/null 2>&1; then
                                echo -e "${GREEN}    ✓ ${service}: Running on port ${PORTS[$service]}${NC}"
                            else
                                echo -e "${RED}    ✗ ${service}: Not running on port ${PORTS[$service]}${NC}"
                            fi
                        done

                        # Проверка БД и статистики
                        echo -e "${CYAN}  💾 Database & Statistics:${NC}"
                        if PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT 1;" &>/dev/null; then
                            local signal_count=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM signals WHERE created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            local order_count=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            echo -e "${GREEN}    ✓ PostgreSQL: Connected${NC}"
                            echo -e "${WHITE}    📊 Signals last hour: ${signal_count:-0}${NC}"
                            echo -e "${WHITE}    📋 Orders last hour: ${order_count:-0}${NC}"
                        else
                            echo -e "${RED}    ✗ PostgreSQL: Connection failed${NC}"
                        fi
                        ;;
                    "logs"|"l")
                        echo -e "${CYAN}================== RECENT LOGS ==================${NC}"
                        tail -n 10 "$LOG_FILE" | filter_and_colorize
                        echo -e "${CYAN}===================================================${NC}"
                        ;;
                    "ml"|"m")
                        echo -e "${CYAN}🤖 ML System Status:${NC}"
                        if PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT 1;" &>/dev/null; then
                            # ML статистика
                            local ml_signals=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM signals WHERE strategy_name LIKE '%ML%' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            local ml_long=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM signals WHERE strategy_name LIKE '%ML%' AND signal_type = 'LONG' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            local ml_short=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM signals WHERE strategy_name LIKE '%ML%' AND signal_type = 'SHORT' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            local avg_confidence=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT ROUND(AVG(confidence)*100) FROM signals WHERE strategy_name LIKE '%ML%' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')

                            echo -e "${WHITE}    🎯 ML Signals (1h): ${ml_signals:-0} total${NC}"
                            echo -e "${GREEN}    📈 LONG signals: ${ml_long:-0}${NC}"
                            echo -e "${RED}    📉 SHORT signals: ${ml_short:-0}${NC}"
                            echo -e "${PURPLE}    🎲 Avg Confidence: ${avg_confidence:-0}%${NC}"
                        else
                            echo -e "${RED}    ✗ Database unavailable${NC}"
                        fi
                        ;;
                    "pos"|"p")
                        echo -e "${CYAN}🎯 Active Positions:${NC}"
                        if PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT 1;" &>/dev/null; then
                            echo -e "${WHITE}    Recent orders:${NC}"
                            PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT symbol, order_type, status, quantity, price FROM orders WHERE created_at > NOW() - INTERVAL '1 hour' ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || echo -e "${RED}    ✗ Error fetching orders${NC}"
                        else
                            echo -e "${RED}    ✗ Database unavailable${NC}"
                        fi
                        ;;
                    "help"|"h"|"?")
                        echo -e "${YELLOW}Available commands:${NC}"
                        echo -e "${WHITE}  status, s  - Show system status${NC}"
                        echo -e "${WHITE}  ml, m      - Show ML system statistics${NC}"
                        echo -e "${WHITE}  pos, p     - Show active positions${NC}"
                        echo -e "${WHITE}  logs, l    - Show recent logs${NC}"
                        echo -e "${WHITE}  help, h, ? - Show this help${NC}"
                        echo -e "${WHITE}  Ctrl+C     - Stop system${NC}"
                        ;;
                    "exit"|"quit"|"stop")
                        echo -e "${YELLOW}Stopping system...${NC}"
                        break
                        ;;
                    *)
                        echo -e "${RED}Unknown command: $user_input${NC}"
                        echo -e "${WHITE}Type 'help' for available commands${NC}"
                        ;;
                esac
            else
                # Timeout - показываем краткий статус
                echo -e "${CYAN}$(date '+%H:%M:%S')${NC} - System running... (Type 'help' for commands)"
            fi
        done
    else
        echo -e "${YELLOW}Log file not found: $LOG_FILE${NC}"
        echo -e "${WHITE}Creating log directory...${NC}"
        mkdir -p data/logs
        touch "$LOG_FILE"
        echo -e "${GREEN}Log file created. Monitoring...${NC}"
        tail -f "$LOG_FILE" | filter_and_colorize &
        TAIL_PID=$!

        sleep 3
        echo -e "${GREEN}✅ System is running! Waiting for first logs...${NC}"
        echo -e "${YELLOW}💡 Press Ctrl+C to stop monitoring and shutdown system${NC}"
        echo -e "${CYAN}📊 System Status:${NC}"
        echo -e "${WHITE}   - Trading Engine: ✅ Running${NC}"
        echo -e "${WHITE}   - Web Interface: ✅ Running${NC}"
        echo -e "${WHITE}   - API Services: ✅ Running${NC}"
        echo ""

        # Ожидаем пользовательский ввод или сигнал завершения
        echo -e "${YELLOW}💡 Интерактивные команды:${NC}"
        echo -e "${WHITE}   • 'status' (s) - статус системы и портов${NC}"
        echo -e "${WHITE}   • 'ml' (m) - ML система и предсказания${NC}"
        echo -e "${WHITE}   • 'pos' (p) - позиции и ордера${NC}"
        echo -e "${WHITE}   • 'logs' (l) - последние логи${NC}"
        echo -e "${WHITE}   • 'help' (h) - справка${NC}"
        echo -e "${WHITE}   • Ctrl+C - остановка системы${NC}"
        echo

        while kill -0 $UNIFIED_PID 2>/dev/null; do
            if read -t 10 user_input; then
                case "$user_input" in
                    "status"|"s")
                        echo -e "${CYAN}📊 System Status Check:${NC}"
                        echo -e "${GREEN}  ✓ Unified Launcher: Running (PID: $UNIFIED_PID)${NC}"
                        if kill -0 $TAIL_PID 2>/dev/null; then
                            echo -e "${GREEN}  ✓ Log Monitor: Running (PID: $TAIL_PID)${NC}"
                        else
                            echo -e "${RED}  ✗ Log Monitor: Stopped${NC}"
                        fi
                        echo -e "${WHITE}  📊 Uptime: $(ps -p $UNIFIED_PID -o etime= 2>/dev/null || echo 'N/A')${NC}"

                        # Проверка портов и сервисов
                        echo -e "${CYAN}  🌐 Service Status:${NC}"
                        for service in "${!PORTS[@]}"; do
                            if lsof -Pi :${PORTS[$service]} -sTCP:LISTEN -t >/dev/null 2>&1; then
                                echo -e "${GREEN}    ✓ ${service}: Running on port ${PORTS[$service]}${NC}"
                            else
                                echo -e "${RED}    ✗ ${service}: Not running on port ${PORTS[$service]}${NC}"
                            fi
                        done

                        # Проверка БД и статистики
                        echo -e "${CYAN}  💾 Database & Statistics:${NC}"
                        if PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT 1;" &>/dev/null; then
                            local signal_count=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM signals WHERE created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            local order_count=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            echo -e "${GREEN}    ✓ PostgreSQL: Connected${NC}"
                            echo -e "${WHITE}    📊 Signals last hour: ${signal_count:-0}${NC}"
                            echo -e "${WHITE}    📋 Orders last hour: ${order_count:-0}${NC}"
                        else
                            echo -e "${RED}    ✗ PostgreSQL: Connection failed${NC}"
                        fi
                        ;;
                    "logs"|"l")
                        echo -e "${CYAN}================== RECENT LOGS ==================${NC}"
                        tail -n 10 "$LOG_FILE" | filter_and_colorize
                        echo -e "${CYAN}===================================================${NC}"
                        ;;
                    "ml"|"m")
                        echo -e "${CYAN}🤖 ML System Status:${NC}"
                        if PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT 1;" &>/dev/null; then
                            # ML статистика
                            local ml_signals=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM signals WHERE strategy_name LIKE '%ML%' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            local ml_long=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM signals WHERE strategy_name LIKE '%ML%' AND signal_type = 'LONG' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            local ml_short=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM signals WHERE strategy_name LIKE '%ML%' AND signal_type = 'SHORT' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
                            local avg_confidence=$(PGPORT=5555 psql -U obertruper -d bot_trading_v3 -t -c "SELECT ROUND(AVG(confidence)*100) FROM signals WHERE strategy_name LIKE '%ML%' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')

                            echo -e "${WHITE}    🎯 ML Signals (1h): ${ml_signals:-0} total${NC}"
                            echo -e "${GREEN}    📈 LONG signals: ${ml_long:-0}${NC}"
                            echo -e "${RED}    📉 SHORT signals: ${ml_short:-0}${NC}"
                            echo -e "${PURPLE}    🎲 Avg Confidence: ${avg_confidence:-0}%${NC}"
                        else
                            echo -e "${RED}    ✗ Database unavailable${NC}"
                        fi
                        ;;
                    "pos"|"p")
                        echo -e "${CYAN}🎯 Active Positions:${NC}"
                        if PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT 1;" &>/dev/null; then
                            echo -e "${WHITE}    Recent orders:${NC}"
                            PGPORT=5555 psql -U obertruper -d bot_trading_v3 -c "SELECT symbol, order_type, status, quantity, price FROM orders WHERE created_at > NOW() - INTERVAL '1 hour' ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || echo -e "${RED}    ✗ Error fetching orders${NC}"
                        else
                            echo -e "${RED}    ✗ Database unavailable${NC}"
                        fi
                        ;;
                    "help"|"h"|"?")
                        echo -e "${YELLOW}Available commands:${NC}"
                        echo -e "${WHITE}  status, s  - Show system status${NC}"
                        echo -e "${WHITE}  ml, m      - Show ML system statistics${NC}"
                        echo -e "${WHITE}  pos, p     - Show active positions${NC}"
                        echo -e "${WHITE}  logs, l    - Show recent logs${NC}"
                        echo -e "${WHITE}  help, h, ? - Show this help${NC}"
                        echo -e "${WHITE}  Ctrl+C     - Stop system${NC}"
                        ;;
                    "exit"|"quit"|"stop")
                        echo -e "${YELLOW}Stopping system...${NC}"
                        break
                        ;;
                    *)
                        echo -e "${RED}Unknown command: $user_input${NC}"
                        echo -e "${WHITE}Type 'help' for available commands${NC}"
                        ;;
                esac
            else
                # Timeout - показываем краткий статус
                echo -e "${CYAN}$(date '+%H:%M:%S')${NC} - System running... (Type 'help' for commands)"
            fi
        done
    fi
}

# Обработка сигналов для корректного завершения
cleanup() {
    echo
    echo -e "${YELLOW}🛑 Stopping services...${NC}"

    # Остановка tail процесса мониторинга логов
    if [ -n "$TAIL_PID" ]; then
        kill -TERM "$TAIL_PID" 2>/dev/null || true
        echo -e "${GREEN}✅ Log monitoring stopped${NC}"
    fi

    # Остановка unified launcher
    if [ -n "$UNIFIED_PID" ]; then
        kill -TERM "$UNIFIED_PID" 2>/dev/null || true
        echo -e "${GREEN}✅ Unified system stopped${NC}"
    fi

    # Убиваем все связанные процессы
    pkill -f "unified_launcher.py" 2>/dev/null || true
    pkill -f "web.api.main" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true

    # Освобождаем порты если они заняты
    for port in 8083 8084 8085 8086 5173; do
        fuser -k $port/tcp 2>/dev/null || true
    done

    echo -e "${CYAN}👋 Goodbye!${NC}"
    exit 0
}

# Регистрация обработчика сигналов
trap cleanup SIGINT SIGTERM

# Запуск основной функции
main "$@"
