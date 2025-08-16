#!/bin/bash
# -*- coding: utf-8 -*-
# Скрипт для удобного просмотра логов BOT Trading v3

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
LOG_DIR="$PROJECT_ROOT/data/logs"

# Функция для вывода заголовка
print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}          ${GREEN}📋 BOT Trading v3 - Просмотр логов${NC}             ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Функция для показа последних записей лога
show_recent_logs() {
    local log_file=$1
    local title=$2
    local lines=${3:-50}

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}📄 $title (последние $lines строк)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -f "$log_file" ]; then
        tail -n $lines "$log_file"
    else
        echo -e "${RED}Файл лога не найден: $log_file${NC}"
    fi
    echo ""
}

# Основная функция
main() {
    print_header

    # Переходим в директорию проекта
    cd "$PROJECT_ROOT" || exit 1

    # Проверяем существование директории логов
    if [ ! -d "$LOG_DIR" ]; then
        echo -e "${RED}❌ Директория логов не найдена!${NC}"
        echo -e "${YELLOW}Запустите систему для создания логов${NC}"
        exit 1
    fi

    # Меню выбора
    while true; do
        echo -e "${PURPLE}Выберите действие:${NC}"
        echo "1) Просмотр логов Trading System в реальном времени"
        echo "2) Просмотр логов API (фильтрованные)"
        echo "3) Информация о Frontend"
        echo "4) Показать последние записи логов"
        echo "5) Поиск в логах"
        echo "6) Очистить логи"
        echo "7) Экспорт логов"
        echo "8) Показать ERROR и WARNING"
        echo "9) Выход"
        read -p "Ваш выбор (1-8): " choice

        case $choice in
            1)
                echo -e "\n${GREEN}📋 Логи Core System (Ctrl+C для остановки):${NC}\n"
                # Ищем последний файл лога
                LATEST_LOG=$(ls -t "$LOG_DIR"/bot_trading_*.log 2>/dev/null | head -1)
                if [ -f "$LATEST_LOG" ]; then
                    tail -f "$LATEST_LOG"
                else
                    echo -e "${RED}Лог файл не найден${NC}"
                fi
                ;;

            2)
                echo -e "\n${GREEN}📋 Логи API Backend (Ctrl+C для остановки):${NC}\n"
                # Пробуем найти процесс API и его логи
                if pgrep -f "uvicorn" > /dev/null; then
                    LATEST_LOG=$(ls -t "$LOG_DIR"/bot_trading_*.log 2>/dev/null | head -1)
                    if [ -f "$LATEST_LOG" ]; then
                        tail -f "$LATEST_LOG" | grep -E "(API|uvicorn|FastAPI)"
                    else
                        echo -e "${YELLOW}API запущен, но логи не найдены${NC}"
                    fi
                else
                    echo -e "${YELLOW}API не запущен${NC}"
                fi
                ;;

            3)
                echo -e "\n${GREEN}📋 Логи Web Frontend (Ctrl+C для остановки):${NC}\n"
                # Frontend обычно логирует в консоль npm
                if pgrep -f "vite" > /dev/null; then
                    echo -e "${YELLOW}Frontend запущен. Логи доступны в консоли npm run dev${NC}"
                else
                    echo -e "${YELLOW}Frontend не запущен${NC}"
                fi
                ;;

            4)
                echo -e "\n${BLUE}📊 Последние записи всех логов:${NC}\n"
                # Показываем последний лог файл
                LATEST_LOG=$(ls -t "$LOG_DIR"/bot_trading_*.log 2>/dev/null | head -1)
                if [ -f "$LATEST_LOG" ]; then
                    echo -e "${CYAN}Файл: $(basename "$LATEST_LOG")${NC}"
                    show_recent_logs "$LATEST_LOG" "Trading System" 50
                else
                    echo -e "${RED}Логи не найдены${NC}"
                fi
                ;;

            5)
                read -p "Введите строку для поиска: " search_term
                echo -e "\n${BLUE}🔍 Поиск '$search_term' в логах:${NC}\n"

                # Ищем во всех логах
                for log_file in "$LOG_DIR"/bot_trading_*.log; do
                    if [ -f "$log_file" ]; then
                        echo -e "${YELLOW}$(basename "$log_file"):${NC}"
                        grep --color=always -n "$search_term" "$log_file" 2>/dev/null || echo "Не найдено"
                        echo ""
                    fi
                done
                echo ""
                ;;

            6)
                echo -e "\n${YELLOW}⚠️ Очистка логов удалит всю историю!${NC}"
                read -p "Вы уверены? (y/N): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    # Очищаем все логи
                    for log_file in "$LOG_DIR"/bot_trading_*.log; do
                        if [ -f "$log_file" ]; then
                            > "$log_file"
                        fi
                    done
                    echo -e "${GREEN}✅ Логи очищены${NC}"
                fi
                ;;

            7)
                timestamp=$(date +%Y%m%d_%H%M%S)
                export_dir="$PROJECT_ROOT/logs_export_$timestamp"
                mkdir -p "$export_dir"

                echo -e "\n${BLUE}📦 Экспорт логов...${NC}"
                cp "$LOG_DIR"/*.log "$export_dir/" 2>/dev/null

                # Создаем архив
                tar -czf "$export_dir.tar.gz" -C "$PROJECT_ROOT" "logs_export_$timestamp"
                rm -rf "$export_dir"

                echo -e "${GREEN}✅ Логи экспортированы в: $export_dir.tar.gz${NC}"
                ;;

            8)
                echo -e "\n${RED}📋 Ошибки и предупреждения:${NC}\n"
                LATEST_LOG=$(ls -t "$LOG_DIR"/bot_trading_*.log 2>/dev/null | head -1)
                if [ -f "$LATEST_LOG" ]; then
                    echo -e "${YELLOW}Последние ERROR:${NC}"
                    grep -E "ERROR" "$LATEST_LOG" | tail -20
                    echo -e "\n${YELLOW}Последние WARNING:${NC}"
                    grep -E "WARNING" "$LATEST_LOG" | tail -20
                else
                    echo -e "${RED}Лог файл не найден${NC}"
                fi
                ;;

            9)
                echo -e "${GREEN}👋 До свидания!${NC}"
                exit 0
                ;;

            *)
                echo -e "${RED}❌ Неверный выбор${NC}"
                ;;
        esac

        echo ""
        read -p "Нажмите Enter для продолжения..."
        clear
        print_header
    done
}

# Обработка Ctrl+C
trap 'echo -e "\n${YELLOW}Прервано пользователем${NC}"; echo ""; ' INT

# Запуск
main
