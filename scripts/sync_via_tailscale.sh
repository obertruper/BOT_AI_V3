#!/bin/bash

# Синхронизация BOT_Trading_v3 через Tailscale
# Использование: ./scripts/sync_via_tailscale.sh

PASSWORD="ilpnqw1234"
TAILSCALE_IP="100.118.184.106"
REMOTE_USER="obertruper"
REMOTE_PATH="/mnt/SSD/PYCHARMPRODJECT/BOT_Trading_v3"
LOCAL_PATH="."

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Синхронизация через Tailscale ===${NC}"

# Проверка подключения
echo -e "${YELLOW}Проверка подключения к $TAILSCALE_IP...${NC}"
if sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$REMOTE_USER@$TAILSCALE_IP" "echo 'OK'" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Подключение активно${NC}"
else
    echo -e "${RED}✗ Не удалось подключиться через Tailscale${NC}"
    echo "Проверьте:"
    echo "1. Tailscale запущен на обеих машинах"
    echo "2. Обе машины авторизованы в одной сети"
    echo "3. SSH доступен на Linux сервере"
    exit 1
fi

# Создание директории на сервере
echo -e "${YELLOW}Создание директории на сервере...${NC}"
if sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$TAILSCALE_IP" "mkdir -p '$REMOTE_PATH'"; then
    echo -e "${GREEN}✓ Директория готова${NC}"
else
    echo -e "${RED}✗ Ошибка создания директории${NC}"
    exit 1
fi

# Синхронизация файлов
echo -e "${YELLOW}Синхронизация файлов...${NC}"
echo "Исключения: файлы >50MB, .git, venv, node_modules, логи"

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
    -e "ssh -o StrictHostKeyChecking=no" \
    "$LOCAL_PATH/" "$REMOTE_USER@$TAILSCALE_IP:$REMOTE_PATH/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Синхронизация завершена${NC}"

    # Статистика
    echo -e "${YELLOW}Статистика на сервере:${NC}"
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$TAILSCALE_IP" \
        "echo 'Размер: ' && du -sh '$REMOTE_PATH' && echo 'Файлов: ' && find '$REMOTE_PATH' -type f | wc -l"

    echo -e "${GREEN}Готово! Проект синхронизирован через Tailscale${NC}"
else
    echo -e "${RED}✗ Ошибка синхронизации${NC}"
    exit 1
fi
