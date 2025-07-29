#!/bin/bash
# -*- coding: utf-8 -*-
"""
Скрипт автоматического обновления документации BOT Trading v3

Может запускаться по расписанию (cron) для регулярного обновления
локальной технической документации из официальных источников.

Использование:
    ./scripts/update_docs.sh                 # Обновить только устаревшие
    ./scripts/update_docs.sh --force         # Принудительное обновление всех
    ./scripts/update_docs.sh --status        # Показать статус
"""

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Корневая папка проекта
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}=== BOT Trading v3 - Обновление документации ===${NC}"
echo "Проект: $PROJECT_ROOT"
echo "Время: $(date '+%d.%m.%Y %H:%M:%S')"
echo ""

# Проверка существования Python виртуального окружения
if [ -d ".venv" ]; then
    echo -e "${GREEN}Активация виртуального окружения...${NC}"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo -e "${GREEN}Активация виртуального окружения...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}Внимание: виртуальное окружение не найдено${NC}"
fi

# Проверка установки зависимостей
if ! python -c "import aiohttp" 2>/dev/null; then
    echo -e "${YELLOW}Установка недостающих зависимостей...${NC}"
    pip install aiohttp
fi

# Создание папки lib/external если не существует
mkdir -p lib/external

# Запуск скрипта обновления документации
echo -e "${BLUE}Запуск обновления документации...${NC}"

case "$1" in
    --force)
        echo -e "${YELLOW}Принудительное обновление всей документации${NC}"
        python scripts/docs_downloader.py --update-all --force
        ;;
    --status)
        echo -e "${BLUE}Статус документации:${NC}"
        python scripts/docs_downloader.py --status
        ;;
    --check)
        echo -e "${BLUE}Проверка необходимости обновлений:${NC}"
        python scripts/docs_downloader.py --check-updates
        ;;
    --library)
        if [ -z "$2" ]; then
            echo -e "${RED}Ошибка: укажите название библиотеки${NC}"
            echo "Использование: $0 --library <имя_библиотеки>"
            exit 1
        fi
        echo -e "${BLUE}Обновление библиотеки: $2${NC}"
        python scripts/docs_downloader.py --library "$2"
        ;;
    *)
        echo -e "${BLUE}Обновление устаревшей документации...${NC}"
        python scripts/docs_downloader.py
        ;;
esac

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ Обновление документации завершено успешно${NC}"

    # Показать краткий статус после обновления
    echo -e "\n${BLUE}Текущий статус:${NC}"
    python scripts/docs_downloader.py --status

    # Обновить информацию в git (если есть изменения)
    if [ -n "$(git status --porcelain lib/)" ]; then
        echo -e "\n${YELLOW}Обнаружены изменения в документации${NC}"
        echo "Файлы для коммита:"
        git status --porcelain lib/

        # Автоматический коммит (если установлена переменная окружения)
        if [ "$AUTO_COMMIT_DOCS" = "true" ]; then
            echo -e "${GREEN}Автоматический коммит изменений...${NC}"
            git add lib/
            git commit -m "docs: обновление технической документации $(date '+%d.%m.%Y')"
            echo -e "${GREEN}✅ Изменения зафиксированы в git${NC}"
        else
            echo -e "${YELLOW}Для автоматического коммита установите: export AUTO_COMMIT_DOCS=true${NC}"
        fi
    else
        echo -e "${GREEN}Изменений в документации не обнаружено${NC}"
    fi

else
    echo -e "${RED}❌ Ошибка при обновлении документации (код: $exit_code)${NC}"
    exit $exit_code
fi

echo -e "\n${BLUE}=== Обновление завершено ===${NC}"
