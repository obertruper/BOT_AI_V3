#!/bin/bash

# Скрипт синхронизации BOT_Trading_v3 на Linux сервер
# Использование: ./scripts/sync_to_linux_server.sh

# Конфигурация
PASSWORD="ilpnqw1234"
REMOTE_USER="obertruper"
REMOTE_PATH="/mnt/SSD/PYCHARMPRODJECT/BOT_Trading_v3"
LOCAL_PATH="."

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Синхронизация BOT_Trading_v3 на Linux сервер ===${NC}"

# Функция для проверки подключения
check_connection() {
    local method=$1
    local host=$2
    local port=$3
    
    echo -e "${YELLOW}Проверка подключения через $method...${NC}"
    
    if sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p "$port" "$REMOTE_USER@$host" "echo 'OK'" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Подключение через $method успешно${NC}"
        return 0
    else
        echo -e "${RED}✗ Подключение через $method не удалось${NC}"
        return 1
    fi
}

# Попытка подключения разными способами
CONNECTION_METHOD=""

# 1. Cloudflared туннель
if pgrep -f cloudflared > /dev/null; then
    if check_connection "Cloudflared туннель" "localhost" "2222"; then
        CONNECTION_METHOD="cloudflared"
        SSH_HOST="localhost"
        SSH_PORT="2222"
    fi
fi

# 2. Прямое подключение на порт 22
if [ -z "$CONNECTION_METHOD" ]; then
    if check_connection "прямое подключение (порт 22)" "93.109.63.226" "22"; then
        CONNECTION_METHOD="direct22"
        SSH_HOST="93.109.63.226"
        SSH_PORT="22"
    fi
fi

# 3. Прямое подключение на порт 2222
if [ -z "$CONNECTION_METHOD" ]; then
    if check_connection "прямое подключение (порт 2222)" "93.109.63.226" "2222"; then
        CONNECTION_METHOD="direct2222"
        SSH_HOST="93.109.63.226"
        SSH_PORT="2222"
    fi
fi

# Проверка доступности подключения
if [ -z "$CONNECTION_METHOD" ]; then
    echo -e "${RED}Ошибка: Не удалось установить подключение к серверу${NC}"
    echo "Возможные решения:"
    echo "1. Запустите cloudflared туннель:"
    echo "   cloudflared access tcp --hostname <ваш-туннель>.trycloudflare.com --url tcp://localhost:2222 &"
    echo "2. Проверьте доступность сервера и портов"
    echo "3. Обновите URL Cloudflare туннеля в SSH конфигурации"
    exit 1
fi

echo -e "${GREEN}Используется подключение: $CONNECTION_METHOD ($SSH_HOST:$SSH_PORT)${NC}"

# Создание директории на сервере
echo -e "${YELLOW}Создание директории на сервере...${NC}"
if sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" "$REMOTE_USER@$SSH_HOST" "mkdir -p '$REMOTE_PATH'"; then
    echo -e "${GREEN}✓ Директория создана${NC}"
else
    echo -e "${RED}✗ Ошибка создания директории${NC}"
    exit 1
fi

# Синхронизация файлов
echo -e "${YELLOW}Начинаю синхронизацию файлов...${NC}"
echo "Исключаются:"
echo "- Файлы больше 50MB"
echo "- .git, venv, node_modules"
echo "- Логи, кеш, временные файлы"

# Rsync с прогрессом
sshpass -p "$PASSWORD" rsync -avz --progress \
    --max-size=50M \
    --exclude='*.pyc' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='.idea/' \
    --exclude='venv*/' \
    --exclude='node_modules/' \
    --exclude='data/logs/' \
    --exclude='data/cache/' \
    --exclude='data/temp/' \
    --exclude='data/historical/*.csv' \
    --exclude='*.log' \
    --exclude='*.tar.gz' \
    --exclude='*.zip' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='.DS_Store' \
    --exclude='.env' \
    -e "ssh -o StrictHostKeyChecking=no -p $SSH_PORT" \
    "$LOCAL_PATH/" "$REMOTE_USER@$SSH_HOST:$REMOTE_PATH/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Синхронизация завершена успешно${NC}"
    
    # Показать статистику
    echo -e "${YELLOW}Проверка результата...${NC}"
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" "$REMOTE_USER@$SSH_HOST" \
        "echo 'Размер проекта на сервере:' && du -sh '$REMOTE_PATH' && echo && echo 'Количество файлов:' && find '$REMOTE_PATH' -type f | wc -l"
else
    echo -e "${RED}✗ Ошибка синхронизации${NC}"
    exit 1
fi

echo -e "${GREEN}=== Синхронизация завершена ===${NC}"