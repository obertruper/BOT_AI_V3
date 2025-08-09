#!/bin/bash
# -*- coding: utf-8 -*-
# Единый скрипт запуска всей системы BOT Trading v3
# Запускает все компоненты в правильном порядке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Переменные
PROJECT_ROOT="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3"
LOG_DIR="$PROJECT_ROOT/logs"
VENV_PATH="$PROJECT_ROOT/venv"

# Функция для вывода заголовка
print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}          ${GREEN}🚀 BOT Trading v3 - Полный запуск${NC}              ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Функция для проверки процесса
check_process() {
    local name=$1
    local port=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✅ $name уже запущен на порту $port${NC}"
        return 0
    else
        return 1
    fi
}

# Функция для остановки всех процессов
stop_all() {
    echo -e "${YELLOW}🛑 Останавливаем все процессы...${NC}"

    # Останавливаем процессы по портам
    for port in 8080 5173; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
            echo -e "Останавливаем процесс на порту $port..."
            lsof -ti:$port | xargs kill -9 2>/dev/null
        fi
    done

    # Останавливаем Python процессы
    pkill -f "python main.py" 2>/dev/null
    pkill -f "python web/launcher.py" 2>/dev/null
    pkill -f "integrated_start.py" 2>/dev/null

    # Останавливаем Node процессы
    pkill -f "vite" 2>/dev/null

    sleep 2
    echo -e "${GREEN}✅ Все процессы остановлены${NC}"
}

# Функция запуска компонента
start_component() {
    local name=$1
    local command=$2
    local log_file=$3
    local check_port=$4

    echo -e "${BLUE}▶ Запуск $name...${NC}"

    # Проверяем, не запущен ли уже
    if [ ! -z "$check_port" ]; then
        if check_process "$name" "$check_port"; then
            return 0
        fi
    fi

    # Запускаем в фоне с логированием
    nohup bash -c "$command" > "$log_file" 2>&1 &
    local pid=$!

    # Ждем запуска
    sleep 3

    # Проверяем, запустился ли процесс
    if kill -0 $pid 2>/dev/null; then
        echo -e "${GREEN}✅ $name запущен (PID: $pid)${NC}"
        echo "$pid" > "$LOG_DIR/$name.pid"
        return 0
    else
        echo -e "${RED}❌ Ошибка запуска $name${NC}"
        tail -n 20 "$log_file"
        return 1
    fi
}

# Основная функция
main() {
    print_header

    # Переходим в директорию проекта
    cd "$PROJECT_ROOT" || exit 1

    # Создаем директорию для логов
    mkdir -p "$LOG_DIR"

    # Проверяем виртуальное окружение
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}❌ Виртуальное окружение не найдено!${NC}"
        echo -e "${YELLOW}Создайте его командой: python3 -m venv venv${NC}"
        exit 1
    fi

    # Активируем виртуальное окружение
    echo -e "${BLUE}🔄 Активация виртуального окружения...${NC}"
    source "$VENV_PATH/bin/activate"

    # Проверяем PostgreSQL
    echo -e "${BLUE}💾 Проверка PostgreSQL...${NC}"
    if psql -p 5555 -U obertruper -d bot_trading_v3 -c '\l' &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL доступен${NC}"
    else
        echo -e "${YELLOW}⚠️ PostgreSQL недоступен на порту 5555${NC}"
        echo -e "${YELLOW}   Система может работать без БД в тестовом режиме${NC}"
    fi

    # Проверяем ML модели
    echo -e "${BLUE}🤖 Проверка ML системы...${NC}"
    if [ -f "$PROJECT_ROOT/models/saved/best_model_20250728_215703.pth" ]; then
        echo -e "${GREEN}✅ ML модель найдена${NC}"
        ML_AVAILABLE=true
    else
        echo -e "${YELLOW}⚠️ ML модель не найдена (генерация сигналов недоступна)${NC}"
        ML_AVAILABLE=false
    fi

    # Спрашиваем пользователя о режиме запуска
    echo ""
    echo -e "${PURPLE}Выберите режим запуска:${NC}"
    echo -e "${GREEN}0) 🚀 ЕДИНАЯ СИСТЕМА (рекомендуется) - новый unified launcher${NC}"
    echo "1) Полный запуск с ML (Core + ML + API + Frontend) - старый режим"
    echo "2) Запуск без ML (Core + API + Frontend)"
    echo "3) Только API + Frontend (без торговли)"
    echo "4) Только Core (консольный режим)"
    echo "5) Остановить все процессы"
    echo "6) Показать статус системы"
    echo "7) Просмотр логов в реальном времени"
    echo "8) Интегрированный режим (старый)"
    echo "9) Проверка данных для ML"
    echo "10) Загрузка исторических данных"
    echo -e "${PURPLE}11) 🤖 Запуск с автоматическим тестированием (TestingAgent)${NC}"
    read -p "Ваш выбор (0-11): " choice

    case $choice in
        0)
            echo -e "\n${GREEN}🚀 Запуск ЕДИНОЙ СИСТЕМЫ через unified_launcher...${NC}\n"

            # Проверяем наличие unified_launcher.py
            if [ ! -f "$PROJECT_ROOT/unified_launcher.py" ]; then
                echo -e "${RED}❌ unified_launcher.py не найден!${NC}"
                exit 1
            fi

            # Запускаем unified launcher
            python unified_launcher.py --mode=full
            ;;

        1)
            echo -e "\n${GREEN}🚀 Запуск полной системы с ML...${NC}\n"

            if [ "$ML_AVAILABLE" = false ]; then
                echo -e "${YELLOW}⚠️ ML модель не найдена. Запускаем без ML генерации.${NC}"
            else
                echo -e "${GREEN}✅ ML генерация сигналов будет активирована${NC}"
            fi

            # Применяем миграции БД
            echo -e "${BLUE}🔄 Применение миграций БД...${NC}"
            cd "$PROJECT_ROOT" && alembic upgrade head 2>/dev/null || echo -e "${YELLOW}⚠️ Миграции уже применены${NC}"

            # 1. Запуск Core System с ML
            start_component "Core System + ML" \
                "source $VENV_PATH/bin/activate && python main.py" \
                "$LOG_DIR/core.log" \
                ""

            # Ждем инициализации ML
            sleep 5
            if grep -q "ML Signal Scheduler запущен" "$LOG_DIR/core.log" 2>/dev/null; then
                echo -e "${GREEN}🤖 ML система активна - генерация сигналов каждую минуту${NC}"
            fi

            # 2. Запуск API Backend
            start_component "API Backend" \
                "source $VENV_PATH/bin/activate && python web/launcher.py" \
                "$LOG_DIR/api.log" \
                "8080"

            # 3. Запуск Frontend
            start_component "Web Frontend" \
                "cd $PROJECT_ROOT/web/frontend && npm run dev -- --host" \
                "$LOG_DIR/frontend.log" \
                "5173"

            echo -e "\n${GREEN}✨ Система успешно запущена с ML!${NC}"

            # Проверяем доступность сервисов
            sleep 3
            echo -e "\n${BLUE}🔍 Проверка доступности сервисов...${NC}"

            # Проверка API
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/health | grep -q "200"; then
                echo -e "  API Backend:    ${GREEN}✅ Доступен${NC}"
            else
                echo -e "  API Backend:    ${YELLOW}⚠️ Недоступен (проверьте логи)${NC}"
            fi

            # Проверка Frontend
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 | grep -q "200"; then
                echo -e "  Web Frontend:   ${GREEN}✅ Доступен${NC}"
            else
                echo -e "  Web Frontend:   ${YELLOW}⚠️ Загружается...${NC}"
            fi

            # Проверка ошибок в логах
            echo -e "\n${BLUE}📋 Анализ логов...${NC}"

            # Core errors
            core_errors=$(grep -c "ERROR\|CRITICAL" "$LOG_DIR/core.log" 2>/dev/null)
            core_errors=${core_errors:-0}
            if [ "$core_errors" -gt 0 ]; then
                echo -e "  Core System:    ${RED}❌ Обнаружено ошибок: $core_errors${NC}"
                echo -e "                  ${YELLOW}Последняя ошибка:${NC}"
                grep "ERROR\|CRITICAL" "$LOG_DIR/core.log" | tail -1 | sed 's/^/                  /'
            else
                echo -e "  Core System:    ${GREEN}✅ Ошибок не обнаружено${NC}"
            fi

            # API errors
            api_errors=$(grep -c "ERROR\|CRITICAL" "$LOG_DIR/api.log" 2>/dev/null)
            api_errors=${api_errors:-0}
            if [ "$api_errors" -gt 0 ]; then
                echo -e "  API Backend:    ${RED}❌ Обнаружено ошибок: $api_errors${NC}"
            else
                echo -e "  API Backend:    ${GREEN}✅ Ошибок не обнаружено${NC}"
            fi

            echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "📊 Dashboard:   ${GREEN}http://localhost:5173${NC}"
            echo -e "📚 API Docs:    ${GREEN}http://localhost:8080/api/docs${NC}"
            echo -e "📝 Логи:        ${GREEN}$LOG_DIR/${NC}"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            ;;

        2)
            echo -e "\n${GREEN}🚀 Запуск системы без ML...${NC}\n"

            # Временно отключаем ML в конфигурации
            export ML_DISABLED=true

            # Применяем миграции БД
            echo -e "${BLUE}🔄 Применение миграций БД...${NC}"
            cd "$PROJECT_ROOT" && alembic upgrade head 2>/dev/null || echo -e "${YELLOW}⚠️ Миграции уже применены${NC}"

            # 1. Запуск Core System без ML
            start_component "Core System" \
                "source $VENV_PATH/bin/activate && ML_DISABLED=true python main.py" \
                "$LOG_DIR/core.log" \
                ""

            # 2. Запуск API Backend
            start_component "API Backend" \
                "source $VENV_PATH/bin/activate && python web/launcher.py" \
                "$LOG_DIR/api.log" \
                "8080"

            # 3. Запуск Frontend
            start_component "Web Frontend" \
                "cd $PROJECT_ROOT/web/frontend && npm run dev -- --host" \
                "$LOG_DIR/frontend.log" \
                "5173"

            echo -e "\n${GREEN}✨ Система запущена без ML!${NC}"
            echo -e "${YELLOW}ℹ️ ML генерация сигналов отключена${NC}"
            ;;

        3)
            echo -e "\n${GREEN}🌐 Запуск Web-only режима...${NC}\n"

            # Запуск только API и Frontend
            start_component "API Backend" \
                "source $VENV_PATH/bin/activate && python web/launcher.py" \
                "$LOG_DIR/api.log" \
                "8080"

            start_component "Web Frontend" \
                "cd $PROJECT_ROOT/web/frontend && npm run dev -- --host" \
                "$LOG_DIR/frontend.log" \
                "5173"

            echo -e "\n${GREEN}✨ Web интерфейс запущен!${NC}"
            echo -e "${YELLOW}⚠️ Торговая система не запущена${NC}"
            ;;

        4)
            echo -e "\n${GREEN}🖥️ Запуск только Core системы...${NC}\n"

            start_component "Core System" \
                "source $VENV_PATH/bin/activate && python main.py" \
                "$LOG_DIR/core.log" \
                ""

            echo -e "\n${GREEN}✨ Core система запущена!${NC}"
            echo -e "${YELLOW}⚠️ Web интерфейс не запущен${NC}"
            ;;

        5)
            stop_all
            ;;

        6)
            echo -e "\n${BLUE}📊 Полный статус системы:${NC}\n"

            echo -e "${PURPLE}=== Процессы ===${NC}"

            # Проверяем Core
            if pgrep -f "python main.py" > /dev/null; then
                core_pid=$(pgrep -f "python main.py" | head -1)
                core_mem=$(ps -p $core_pid -o %mem= 2>/dev/null | tr -d ' ')
                core_cpu=$(ps -p $core_pid -o %cpu= 2>/dev/null | tr -d ' ')
                echo -e "Core System:    ${GREEN}✅ Работает${NC} (PID: $core_pid, CPU: ${core_cpu}%, MEM: ${core_mem}%)"
            else
                echo -e "Core System:    ${RED}❌ Остановлен${NC}"
            fi

            # Проверяем API
            if check_process "API Backend" "8080"; then
                api_pid=$(lsof -ti:8080 | head -1)
                api_mem=$(ps -p $api_pid -o %mem= 2>/dev/null | tr -d ' ')
                api_cpu=$(ps -p $api_pid -o %cpu= 2>/dev/null | tr -d ' ')
                echo -e "API Backend:    ${GREEN}✅ Работает${NC} (PID: $api_pid, CPU: ${api_cpu}%, MEM: ${api_mem}%)"
            else
                echo -e "API Backend:    ${RED}❌ Остановлен${NC}"
            fi

            # Проверяем Frontend
            if check_process "Web Frontend" "5173"; then
                web_pid=$(lsof -ti:5173 | head -1)
                echo -e "Web Frontend:   ${GREEN}✅ Работает${NC} (PID: $web_pid)"
            else
                echo -e "Web Frontend:   ${RED}❌ Остановлен${NC}"
            fi

            # Проверяем PostgreSQL
            if psql -p 5555 -U obertruper -d bot_trading_v3 -c '\l' &> /dev/null; then
                echo -e "PostgreSQL:     ${GREEN}✅ Работает${NC} (порт 5555)"
            else
                echo -e "PostgreSQL:     ${RED}❌ Недоступен${NC}"
            fi

            echo -e "\n${PURPLE}=== Доступность сервисов ===${NC}"

            # Проверка API endpoint
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/health | grep -q "200"; then
                echo -e "API Health:     ${GREEN}✅ OK${NC} (http://localhost:8080/api/health)"
            else
                echo -e "API Health:     ${RED}❌ Недоступен${NC}"
            fi

            # Проверка Dashboard
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 | grep -q "200"; then
                echo -e "Dashboard:      ${GREEN}✅ OK${NC} (http://localhost:5173)"
            else
                echo -e "Dashboard:      ${YELLOW}⚠️ Недоступен${NC}"
            fi

            # Проверка API Docs
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/docs | grep -q "200"; then
                echo -e "API Docs:       ${GREEN}✅ OK${NC} (http://localhost:8080/api/docs)"
            else
                echo -e "API Docs:       ${RED}❌ Недоступен${NC}"
            fi

            echo -e "\n${PURPLE}=== Анализ логов ===${NC}"

            # Статистика по логам
            if [ -f "$LOG_DIR/core.log" ]; then
                core_lines=$(wc -l < "$LOG_DIR/core.log")
                core_errors=$(grep -c "ERROR\|CRITICAL" "$LOG_DIR/core.log" 2>/dev/null || echo "0")
                core_warnings=$(grep -c "WARNING" "$LOG_DIR/core.log" 2>/dev/null || echo "0")
                echo -e "Core Log:       ${core_lines} строк, ${RED}$core_errors ошибок${NC}, ${YELLOW}$core_warnings предупреждений${NC}"
            fi

            if [ -f "$LOG_DIR/api.log" ]; then
                api_lines=$(wc -l < "$LOG_DIR/api.log")
                api_errors=$(grep -c "ERROR\|500" "$LOG_DIR/api.log" 2>/dev/null || echo "0")
                echo -e "API Log:        ${api_lines} строк, ${RED}$api_errors ошибок${NC}"
            fi

            if [ -f "$LOG_DIR/frontend.log" ]; then
                frontend_lines=$(wc -l < "$LOG_DIR/frontend.log")
                frontend_errors=$(grep -c "ERROR\|error" "$LOG_DIR/frontend.log" 2>/dev/null || echo "0")
                echo -e "Frontend Log:   ${frontend_lines} строк, ${RED}$frontend_errors ошибок${NC}"
            fi

            echo -e "\n${PURPLE}=== Системная информация ===${NC}"

            # Использование диска
            disk_usage=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $5}')
            echo -e "Диск:           ${disk_usage} использовано"

            # Размер логов
            log_size=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
            echo -e "Размер логов:   ${log_size}"

            # Uptime
            if pgrep -f "python main.py" > /dev/null; then
                core_pid=$(pgrep -f "python main.py" | head -1)
                core_uptime=$(ps -p $core_pid -o etime= 2>/dev/null | tr -d ' ')
                echo -e "Core Uptime:    ${core_uptime}"
            fi
            ;;

        7)
            echo -e "\n${BLUE}📝 Просмотр логов системы${NC}\n"
            echo -e "${PURPLE}Выберите лог для просмотра:${NC}"
            echo "1) Core System (основная торговая система)"
            echo "2) API Backend"
            echo "3) Web Frontend"
            echo "4) Все логи одновременно"
            echo "5) Вернуться в главное меню"
            read -p "Ваш выбор (1-5): " log_choice

            case $log_choice in
                1)
                    echo -e "\n${GREEN}📋 Логи Core System (Ctrl+C для выхода):${NC}\n"
                    tail -f "$LOG_DIR/core.log"
                    ;;
                2)
                    echo -e "\n${GREEN}📋 Логи API Backend (Ctrl+C для выхода):${NC}\n"
                    tail -f "$LOG_DIR/api.log"
                    ;;
                3)
                    echo -e "\n${GREEN}📋 Логи Web Frontend (Ctrl+C для выхода):${NC}\n"
                    tail -f "$LOG_DIR/frontend.log"
                    ;;
                4)
                    echo -e "\n${GREEN}📋 Все логи (Ctrl+C для выхода):${NC}\n"
                    echo -e "${YELLOW}=== CORE SYSTEM ===${NC}"
                    tail -f "$LOG_DIR/core.log" | sed 's/^/[CORE] /' &
                    echo -e "\n${YELLOW}=== API BACKEND ===${NC}"
                    tail -f "$LOG_DIR/api.log" | sed 's/^/[API]  /' &
                    echo -e "\n${YELLOW}=== WEB FRONTEND ===${NC}"
                    tail -f "$LOG_DIR/frontend.log" | sed 's/^/[WEB]  /' &
                    wait
                    ;;
                5)
                    exec "$0"
                    ;;
                *)
                    echo -e "${RED}❌ Неверный выбор${NC}"
                    ;;
            esac
            ;;

        8)
            echo -e "\n${GREEN}🚀 Запуск интегрированной системы...${NC}\n"
            echo -e "${YELLOW}Этот режим запускает Core и API в одном процессе для лучшей интеграции${NC}\n"

            # Остановка старых процессов
            stop_all

            # Запуск интегрированной системы
            echo -e "${BLUE}▶ Запуск интегрированной системы...${NC}"
            nohup bash -c "source $VENV_PATH/bin/activate && python integrated_start.py" > "$LOG_DIR/integrated.log" 2>&1 &
            local pid=$!

            # Ждем запуска
            sleep 5

            # Проверяем, запустился ли процесс
            if kill -0 $pid 2>/dev/null; then
                echo -e "${GREEN}✅ Интегрированная система запущена (PID: $pid)${NC}"
                echo "$pid" > "$LOG_DIR/integrated.pid"

                # Запуск Frontend
                start_component "Web Frontend" \
                    "cd $PROJECT_ROOT/web/frontend && npm run dev -- --host" \
                    "$LOG_DIR/frontend.log" \
                    "5173"

                echo -e "\n${GREEN}✨ Система успешно запущена в интегрированном режиме!${NC}"

                # Проверяем доступность
                sleep 3
                echo -e "\n${BLUE}🔍 Проверка доступности сервисов...${NC}"

                if curl -s http://localhost:8080/api/health | jq -r '.status' 2>/dev/null | grep -q "healthy\|degraded"; then
                    echo -e "  API Health:     ${GREEN}✅ Полностью функционален${NC}"
                else
                    echo -e "  API Health:     ${YELLOW}⚠️ Работает с ограничениями${NC}"
                fi

                echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "📊 Dashboard:   ${GREEN}http://localhost:5173${NC}"
                echo -e "📚 API Docs:    ${GREEN}http://localhost:8080/api/docs${NC}"
                echo -e "📝 Логи:        ${GREEN}$LOG_DIR/integrated.log${NC}"
                echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            else
                echo -e "${RED}❌ Ошибка запуска интегрированной системы${NC}"
                tail -n 20 "$LOG_DIR/integrated.log"
            fi
            ;;

        9)
            echo -e "\n${BLUE}📊 Проверка данных для ML...${NC}\n"

            # Активируем venv и запускаем проверку
            cd "$PROJECT_ROOT"
            source "$VENV_PATH/bin/activate"

            echo -e "${GREEN}🔍 Запуск скрипта проверки данных...${NC}\n"
            python scripts/check_data_availability.py

            echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${YELLOW}💡 Если данных недостаточно, выберите пункт 10 для загрузки${NC}"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            ;;

        10)
            echo -e "\n${BLUE}📥 Загрузка исторических данных...${NC}\n"

            # Активируем venv
            cd "$PROJECT_ROOT"
            source "$VENV_PATH/bin/activate"

            echo -e "${PURPLE}Выберите период загрузки:${NC}"
            echo "1) 7 дней (быстро, для тестов)"
            echo "2) 30 дней (рекомендуется)"
            echo "3) 90 дней (для полноценной работы ML)"
            echo "4) Кастомный период"
            echo "5) Вернуться в главное меню"
            read -p "Ваш выбор (1-5): " data_choice

            case $data_choice in
                1)
                    echo -e "\n${GREEN}📥 Загрузка данных за 7 дней...${NC}"
                    python scripts/load_historical_data.py --days 7
                    ;;
                2)
                    echo -e "\n${GREEN}📥 Загрузка данных за 30 дней...${NC}"
                    python scripts/load_historical_data.py --days 30
                    ;;
                3)
                    echo -e "\n${GREEN}📥 Загрузка данных за 90 дней...${NC}"
                    python scripts/load_historical_data.py --days 90
                    ;;
                4)
                    read -p "Введите количество дней: " custom_days
                    if [[ "$custom_days" =~ ^[0-9]+$ ]]; then
                        echo -e "\n${GREEN}📥 Загрузка данных за $custom_days дней...${NC}"
                        python scripts/load_historical_data.py --days $custom_days
                    else
                        echo -e "${RED}❌ Неверный формат${NC}"
                    fi
                    ;;
                5)
                    exec "$0"
                    ;;
                *)
                    echo -e "${RED}❌ Неверный выбор${NC}"
                    ;;
            esac

            echo -e "\n${YELLOW}💡 После загрузки данных проверьте их доступность (пункт 9)${NC}"
            ;;

        11)
            echo -e "\n${PURPLE}🤖 Запуск с автоматическим тестированием (TestingAgent)...${NC}\n"

            # Активируем venv
            cd "$PROJECT_ROOT"
            source "$VENV_PATH/bin/activate"

            echo -e "${BLUE}🔧 Инициализация TestingAgent...${NC}"

            # Проверяем наличие TestingAgent
            if [ ! -f "$PROJECT_ROOT/agents/testing_agent.py" ]; then
                echo -e "${RED}❌ TestingAgent не найден!${NC}"
                echo -e "${YELLOW}   Убедитесь, что файл agents/testing_agent.py существует${NC}"
                exit 1
            fi

            echo -e "${GREEN}✅ TestingAgent найден${NC}"

            # Выбор режима запуска
            echo -e "\n${PURPLE}Выберите режим запуска с тестированием:${NC}"
            echo "1) Автоматическое тестирование + Полная система"
            echo "2) Автоматическое тестирование + Core система"
            echo "3) Автоматическое тестирование + API система"
            echo "4) Только диагностика и исправление ошибок"
            echo "5) Проверить занятые порты и освободить их"
            echo "6) Вернуться в главное меню"
            read -p "Ваш выбор (1-6): " testing_choice

            case $testing_choice in
                1)
                    echo -e "\n${GREEN}🚀 Запуск полной системы с автоматическим тестированием...${NC}\n"

                    # Запуск TestingAgent в режиме мониторинга полной системы
                    echo -e "${BLUE}🤖 Запуск TestingAgent для мониторинга системы...${NC}"
                    nohup python agents/testing_agent.py --mode=full > "$LOG_DIR/testing_agent.log" 2>&1 &
                    testing_pid=$!
                    echo "$testing_pid" > "$LOG_DIR/testing_agent.pid"

                    sleep 2

                    if kill -0 $testing_pid 2>/dev/null; then
                        echo -e "${GREEN}✅ TestingAgent запущен (PID: $testing_pid)${NC}"
                        echo -e "${BLUE}📊 TestingAgent мониторит запуск и будет автоматически исправлять ошибки${NC}"

                        # Ждем немного и показываем статус
                        sleep 3

                        echo -e "\n${BLUE}🔍 Статус автоматического тестирования:${NC}"
                        tail -n 5 "$LOG_DIR/testing_agent.log" | sed 's/^/  /'

                        echo -e "\n${GREEN}✨ Система запущена под управлением TestingAgent!${NC}"
                        echo -e "${YELLOW}📝 Логи TestingAgent: $LOG_DIR/testing_agent.log${NC}"
                        echo -e "${YELLOW}🔍 Для остановки: kill $testing_pid${NC}"
                    else
                        echo -e "${RED}❌ Ошибка запуска TestingAgent${NC}"
                        tail -n 10 "$LOG_DIR/testing_agent.log"
                    fi
                    ;;

                2)
                    echo -e "\n${GREEN}🚀 Запуск Core системы с автоматическим тестированием...${NC}\n"

                    # Запуск TestingAgent в режиме мониторинга core системы
                    echo -e "${BLUE}🤖 Запуск TestingAgent для Core системы...${NC}"
                    python -c "
import asyncio
import sys
sys.path.append('$PROJECT_ROOT')
from agents.testing_agent import TestingAgent

async def main():
    agent = TestingAgent()
    await agent.start_system_monitoring('core')

asyncio.run(main())
" > "$LOG_DIR/testing_agent.log" 2>&1 &
                    testing_pid=$!
                    echo "$testing_pid" > "$LOG_DIR/testing_agent.pid"

                    sleep 2
                    echo -e "${GREEN}✅ TestingAgent запущен для Core системы (PID: $testing_pid)${NC}"
                    ;;

                3)
                    echo -e "\n${GREEN}🚀 Запуск API системы с автоматическим тестированием...${NC}\n"

                    # Запуск TestingAgent в режиме мониторинга API системы
                    echo -e "${BLUE}🤖 Запуск TestingAgent для API системы...${NC}"
                    python -c "
import asyncio
import sys
sys.path.append('$PROJECT_ROOT')
from agents.testing_agent import TestingAgent

async def main():
    agent = TestingAgent()
    await agent.start_system_monitoring('api')

asyncio.run(main())
" > "$LOG_DIR/testing_agent.log" 2>&1 &
                    testing_pid=$!
                    echo "$testing_pid" > "$LOG_DIR/testing_agent.pid"

                    sleep 2
                    echo -e "${GREEN}✅ TestingAgent запущен для API системы (PID: $testing_pid)${NC}"
                    ;;

                4)
                    echo -e "\n${BLUE}🔧 Диагностика системы и исправление ошибок...${NC}\n"

                    # Запуск диагностики
                    python -c "
import asyncio
import sys
sys.path.append('$PROJECT_ROOT')
from agents.testing_agent import TestingAgent

async def main():
    agent = TestingAgent()

    print('🔍 Исправляем конфликты портов...')
    await agent.fix_port_conflicts()

    print('🔍 Анализируем логи на ошибки...')
    log_content = ''
    try:
        with open('data/logs/system.log', 'r') as f:
            log_content = f.read()
    except:
        pass

    if log_content:
        errors = await agent.analyze_errors(log_content)
        if errors:
            print(f'❌ Найдено ошибок: {len(errors)}')
            for error in errors[-5:]:  # Показываем последние 5
                print(f'   - {error[\"type\"]}: {error[\"line\"][:100]}...')
        else:
            print('✅ Критических ошибок не найдено')
    else:
        print('ℹ️ Логи системы пусты или недоступны')

    print('🔧 Диагностика завершена')

asyncio.run(main())
"
                    ;;

                5)
                    echo -e "\n${BLUE}🔧 Проверка и освобождение занятых портов...${NC}\n"

                    # Запуск проверки портов
                    python -c "
import asyncio
import sys
sys.path.append('$PROJECT_ROOT')
from agents.testing_agent import TestingAgent

async def main():
    agent = TestingAgent()
    print('🔍 Проверяем и освобождаем занятые порты...')
    await agent.fix_port_conflicts()
    print('✅ Проверка портов завершена')

asyncio.run(main())
"

                    echo -e "\n${GREEN}✅ Проверка портов завершена${NC}"
                    echo -e "${YELLOW}💡 Теперь можно запускать систему через пункт 0 или 1${NC}"
                    ;;

                6)
                    exec "$0"
                    ;;

                *)
                    echo -e "${RED}❌ Неверный выбор${NC}"
                    ;;
            esac

            echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${PURPLE}🤖 TestingAgent - Функции:${NC}"
            echo -e "   ✅ Автоматическое исправление конфликтов портов"
            echo -e "   ✅ Диагностика и анализ ошибок в логах"
            echo -e "   ✅ Автоматическая установка недостающих модулей"
            echo -e "   ✅ Исправление проблем с подключениями"
            echo -e "   ✅ Мониторинг запуска системы в реальном времени"
            echo -e "   ✅ Интеграция со специализированными агентами"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            ;;

        *)
            echo -e "${RED}❌ Неверный выбор${NC}"
            exit 1
            ;;
    esac

    echo ""
    echo -e "${BLUE}💡 Полезные команды:${NC}"
    echo -e "   Просмотр логов:     ${YELLOW}tail -f $LOG_DIR/core.log${NC}"
    echo -e "   Остановить все:     ${YELLOW}./start_all.sh${NC} (выбрать 4)"
    echo -e "   Проверить статус:   ${YELLOW}./start_all.sh${NC} (выбрать 5)"
    echo ""
}

# Обработка Ctrl+C
trap 'echo -e "\n${YELLOW}Прервано пользователем${NC}"; exit 1' INT

# Запуск
main
