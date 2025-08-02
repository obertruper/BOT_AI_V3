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
LOG_DIR="$PROJECT_ROOT/logs"

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
        echo "1) Просмотр логов Core System в реальном времени"
        echo "2) Просмотр логов API Backend в реальном времени"
        echo "3) Просмотр логов Web Frontend в реальном времени"
        echo "4) Показать последние записи всех логов"
        echo "5) Поиск в логах"
        echo "6) Очистить логи"
        echo "7) Экспорт логов"
        echo "8) Выход"
        read -p "Ваш выбор (1-8): " choice

        case $choice in
            1)
                echo -e "\n${GREEN}📋 Логи Core System (Ctrl+C для остановки):${NC}\n"
                tail -f "$LOG_DIR/core.log"
                ;;

            2)
                echo -e "\n${GREEN}📋 Логи API Backend (Ctrl+C для остановки):${NC}\n"
                tail -f "$LOG_DIR/api.log"
                ;;

            3)
                echo -e "\n${GREEN}📋 Логи Web Frontend (Ctrl+C для остановки):${NC}\n"
                tail -f "$LOG_DIR/frontend.log"
                ;;

            4)
                echo -e "\n${BLUE}📊 Последние записи всех логов:${NC}\n"
                show_recent_logs "$LOG_DIR/core.log" "Core System" 30
                show_recent_logs "$LOG_DIR/api.log" "API Backend" 30
                show_recent_logs "$LOG_DIR/frontend.log" "Web Frontend" 30
                ;;

            5)
                read -p "Введите строку для поиска: " search_term
                echo -e "\n${BLUE}🔍 Поиск '$search_term' в логах:${NC}\n"

                echo -e "${YELLOW}Core System:${NC}"
                grep -n "$search_term" "$LOG_DIR/core.log" 2>/dev/null || echo "Не найдено"

                echo -e "\n${YELLOW}API Backend:${NC}"
                grep -n "$search_term" "$LOG_DIR/api.log" 2>/dev/null || echo "Не найдено"

                echo -e "\n${YELLOW}Web Frontend:${NC}"
                grep -n "$search_term" "$LOG_DIR/frontend.log" 2>/dev/null || echo "Не найдено"
                echo ""
                ;;

            6)
                echo -e "\n${YELLOW}⚠️ Очистка логов удалит всю историю!${NC}"
                read -p "Вы уверены? (y/N): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    > "$LOG_DIR/core.log"
                    > "$LOG_DIR/api.log"
                    > "$LOG_DIR/frontend.log"
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
