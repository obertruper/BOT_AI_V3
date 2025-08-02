#!/bin/bash
# -*- coding: utf-8 -*-
"""
Скрипт быстрого запуска BOT Trading v3
"""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🚀 BOT Trading v3 - Скрипт запуска${NC}"
echo -e "${BLUE}================================================${NC}"

# Проверка текущей директории
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Ошибка: main.py не найден. Запустите скрипт из корневой директории проекта${NC}"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ Файл .env не найден. Создаем из примера...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Создан файл .env${NC}"
    echo -e "${YELLOW}📝 Обязательно отредактируйте .env и добавьте ваши API ключи!${NC}"
    exit 1
fi

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️ Виртуальное окружение не найдено. Создаем...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Виртуальное окружение создано${NC}"
fi

# Активация виртуального окружения
echo -e "${BLUE}🔄 Активация виртуального окружения...${NC}"
source venv/bin/activate

# Проверка и установка зависимостей
echo -e "${BLUE}📦 Проверка зависимостей...${NC}"
pip install -q --upgrade pip

# Проверяем основные пакеты
required_packages=(
    "asyncio"
    "asyncpg"
    "fastapi"
    "sqlalchemy"
    "ccxt"
    "torch"
    "pandas"
    "aiohttp"
    "python-telegram-bot"
)

missing_packages=()
for package in "${required_packages[@]}"; do
    if ! python -c "import $package" 2>/dev/null; then
        missing_packages+=($package)
    fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️ Отсутствуют пакеты: ${missing_packages[*]}${NC}"
    echo -e "${BLUE}📦 Установка зависимостей...${NC}"
    pip install -r requirements.txt
else
    echo -e "${GREEN}✅ Все зависимости установлены${NC}"
fi

# Проверка PostgreSQL
echo -e "${BLUE}💾 Проверка PostgreSQL...${NC}"
if command -v psql &> /dev/null; then
    if psql -p 5555 -U obertruper -d bot_trading_v3 -c '\l' &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL доступен на порту 5555${NC}"
    else
        echo -e "${RED}❌ Не удается подключиться к PostgreSQL на порту 5555${NC}"
        echo -e "${YELLOW}💡 Убедитесь, что PostgreSQL запущен и база данных bot_trading_v3 создана${NC}"
        echo -e "${YELLOW}   sudo -u postgres psql -p 5555 -c \"CREATE DATABASE bot_trading_v3 OWNER obertruper;\"${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ psql не найден. Проверьте подключение к БД вручную${NC}"
fi

# Проверка готовности системы
echo -e "${BLUE}🔍 Проверка готовности системы...${NC}"
if [ -f "scripts/check_v3_readiness.py" ]; then
    python scripts/check_v3_readiness.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Система не готова к запуску${NC}"
        echo -e "${YELLOW}💡 Исправьте указанные проблемы и попробуйте снова${NC}"
        exit 1
    fi
fi

# Предложение запустить в режиме разработки или production
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}Выберите режим запуска:${NC}"
echo -e "1) Development (с отладкой и hot-reload)"
echo -e "2) Production (оптимизированный)"
echo -e "3) Только проверка (без запуска)"
read -p "Ваш выбор (1-3): " choice

case $choice in
    1)
        echo -e "${GREEN}🚀 Запуск в режиме Development...${NC}"
        export ENVIRONMENT=development
        export LOG_LEVEL=DEBUG
        python main.py
        ;;
    2)
        echo -e "${GREEN}🚀 Запуск в режиме Production...${NC}"
        export ENVIRONMENT=production
        export LOG_LEVEL=INFO
        python main.py
        ;;
    3)
        echo -e "${GREEN}✅ Проверка завершена. Система готова к запуску.${NC}"
        echo -e "${BLUE}Для запуска выполните: python main.py${NC}"
        ;;
    *)
        echo -e "${RED}❌ Неверный выбор${NC}"
        exit 1
        ;;
esac
