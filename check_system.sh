#!/bin/bash
# -*- coding: utf-8 -*-
# Скрипт быстрой диагностики системы BOT Trading v3

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Переменные
PROJECT_ROOT="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3"
LOG_DIR="$PROJECT_ROOT/logs"

print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}       ${GREEN}🔍 BOT Trading v3 - Диагностика системы${NC}          ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_component_status() {
    local name=$1
    local check_cmd=$2
    local log_file=$3

    echo -e "\n${CYAN}=== Проверка $name ===${NC}"

    # Проверяем запущен ли процесс
    if eval "$check_cmd" > /dev/null 2>&1; then
        echo -e "Статус:         ${GREEN}✅ Работает${NC}"
    else
        echo -e "Статус:         ${RED}❌ Остановлен${NC}"
        return 1
    fi

    # Анализируем логи
    if [ -f "$log_file" ]; then
        # Считаем ошибки за последние 5 минут
        recent_errors=$(tail -1000 "$log_file" | grep -c "ERROR\|CRITICAL" 2>/dev/null)
        recent_errors=${recent_errors:-0}
        if [ "$recent_errors" -gt 0 ]; then
            echo -e "Недавние ошибки: ${RED}$recent_errors${NC}"
            echo -e "${YELLOW}Последние ошибки:${NC}"
            grep "ERROR\|CRITICAL" "$log_file" | tail -3 | while read line; do
                echo -e "  ${RED}>${NC} $(echo "$line" | cut -d' ' -f1-4) - $(echo "$line" | cut -d' ' -f6-)"
            done
        else
            echo -e "Ошибки:         ${GREEN}✅ Не обнаружены${NC}"
        fi

        # Проверяем предупреждения
        warnings=$(tail -1000 "$log_file" | grep -c "WARNING" 2>/dev/null)
        warnings=${warnings:-0}
        if [ "$warnings" -gt 0 ]; then
            echo -e "Предупреждения: ${YELLOW}$warnings${NC}"
        fi
    else
        echo -e "Лог файл:       ${RED}❌ Не найден${NC}"
    fi
}

check_services() {
    echo -e "\n${PURPLE}=== Проверка доступности сервисов ===${NC}"

    # API Health
    echo -n "API Health Check: "
    response=$(curl -s -w "\n%{http_code}" http://localhost:8080/api/health 2>/dev/null)
    http_code=$(echo "$response" | tail -1)
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ OK${NC}"
        # Парсим JSON ответ
        health_data=$(echo "$response" | head -n -1)
        if echo "$health_data" | grep -q "\"status\":\"healthy\""; then
            echo -e "  Статус системы: ${GREEN}Healthy${NC}"
        else
            echo -e "  Статус системы: ${YELLOW}Проверьте данные${NC}"
        fi
    else
        echo -e "${RED}❌ Недоступен (HTTP $http_code)${NC}"
    fi

    # Dashboard
    echo -n "Web Dashboard: "
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 | grep -q "200"; then
        echo -e "${GREEN}✅ Доступен${NC}"
    else
        echo -e "${YELLOW}⚠️ Недоступен или загружается${NC}"
    fi

    # API Docs
    echo -n "API Documentation: "
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/docs | grep -q "200"; then
        echo -e "${GREEN}✅ Доступна${NC}"
    else
        echo -e "${RED}❌ Недоступна${NC}"
    fi
}

check_database() {
    echo -e "\n${PURPLE}=== Проверка базы данных ===${NC}"

    if psql -p 5555 -U obertruper -d bot_trading_v3 -c '\dt' > /dev/null 2>&1; then
        echo -e "PostgreSQL:     ${GREEN}✅ Подключение успешно${NC}"

        # Считаем записи в таблицах
        tables=$(psql -p 5555 -U obertruper -d bot_trading_v3 -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public'" 2>/dev/null)

        echo -e "\nТаблицы БД:"
        for table in $tables; do
            count=$(psql -p 5555 -U obertruper -d bot_trading_v3 -t -c "SELECT COUNT(*) FROM $table" 2>/dev/null | tr -d ' ')
            printf "  %-20s: %s записей\n" "$table" "$count"
        done
    else
        echo -e "PostgreSQL:     ${RED}❌ Подключение не удалось${NC}"
    fi
}

check_resources() {
    echo -e "\n${PURPLE}=== Системные ресурсы ===${NC}"

    # CPU и память
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    mem_total=$(free -m | awk 'NR==2{print $2}')
    mem_used=$(free -m | awk 'NR==2{print $3}')
    mem_percent=$(awk "BEGIN {printf \"%.1f\", $mem_used/$mem_total*100}")

    echo -e "CPU использование:  ${cpu_usage}%"
    echo -e "Память:            ${mem_used}MB / ${mem_total}MB (${mem_percent}%)"

    # Диск
    disk_usage=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $5}')
    disk_free=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    echo -e "Диск использован:  ${disk_usage} (свободно: ${disk_free})"

    # Размер логов
    if [ -d "$LOG_DIR" ]; then
        log_size=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
        echo -e "Размер логов:      ${log_size}"
    fi
}

suggest_fixes() {
    echo -e "\n${PURPLE}=== Рекомендации ===${NC}"

    # Проверяем наличие ошибок в логах
    total_errors=0
    if [ -f "$LOG_DIR/core.log" ]; then
        core_errors=$(grep -c "ERROR\|CRITICAL" "$LOG_DIR/core.log" 2>/dev/null)
        core_errors=${core_errors:-0}
        total_errors=$((total_errors + core_errors))
    fi

    if [ "$total_errors" -gt 0 ]; then
        echo -e "${YELLOW}⚠️ Обнаружены ошибки в логах:${NC}"
        echo -e "   1. Проверьте логи: ${BLUE}./view_logs.sh${NC}"
        echo -e "   2. Перезапустите систему: ${BLUE}./start_all.sh${NC} (опция 4, затем 1)"
    fi

    # Проверяем размер логов
    if [ -d "$LOG_DIR" ]; then
        log_size_mb=$(du -sm "$LOG_DIR" 2>/dev/null | cut -f1)
        if [ "$log_size_mb" -gt 1000 ]; then
            echo -e "${YELLOW}⚠️ Логи занимают много места (>1GB):${NC}"
            echo -e "   Очистите старые логи: ${BLUE}./view_logs.sh${NC} (опция 6)"
        fi
    fi

    # Проверяем использование памяти
    mem_percent_int=$(echo "$mem_percent" | cut -d'.' -f1)
    if [ "$mem_percent_int" -gt 80 ]; then
        echo -e "${YELLOW}⚠️ Высокое использование памяти (>80%):${NC}"
        echo -e "   Перезапустите систему или добавьте swap"
    fi
}

# Основная функция
main() {
    print_header

    # Проверяем компоненты
    check_component_status "Core System" "pgrep -f 'python main.py'" "$LOG_DIR/core.log"
    check_component_status "API Backend" "lsof -i:8080" "$LOG_DIR/api.log"
    check_component_status "Web Frontend" "lsof -i:5173" "$LOG_DIR/frontend.log"

    # Проверяем сервисы
    check_services

    # Проверяем БД
    check_database

    # Проверяем ресурсы
    check_resources

    # Рекомендации
    suggest_fixes

    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Диагностика завершена${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Запуск
main
