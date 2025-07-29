#!/bin/bash

# Скрипт для синхронизации BOT_Trading_v3 с сервером

# Параметры подключения
SERVER_HOST="linux-home-cf"
SERVER_PATH="/mnt/SSD/PYCHARMPRODJECT/BOT_Trading_v3"
LOCAL_PATH="."
PASSWORD="ilpnqw1234"

echo "🚀 Начинаю синхронизацию BOT_Trading_v3 с сервером..."

# Создание директории на сервере
echo "📁 Создаю директорию на сервере..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_HOST "mkdir -p $SERVER_PATH"

# Синхронизация с исключением больших файлов и временных директорий
echo "📤 Синхронизирую файлы..."
sshpass -p "$PASSWORD" rsync -avz --progress \
  --max-size=50M \
  --exclude='*.pyc' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='venv*/' \
  --exclude='*.log' \
  --exclude='*.tar.gz' \
  --exclude='*.zip' \
  --exclude='node_modules/' \
  --exclude='data/historical/' \
  --exclude='data/cache/' \
  --exclude='data/temp/' \
  --exclude='.DS_Store' \
  --exclude='*.tmp' \
  --exclude='*.deb' \
  -e "ssh -o StrictHostKeyChecking=no" \
  "$LOCAL_PATH/" \
  "$SERVER_HOST:$SERVER_PATH/"

# Проверка статуса
if [ $? -eq 0 ]; then
    echo "✅ Синхронизация завершена успешно!"
    
    # Показать информацию о проекте на сервере
    echo "📊 Информация о проекте на сервере:"
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_HOST "cd $SERVER_PATH && ls -la | head -20"
else
    echo "❌ Ошибка при синхронизации!"
    exit 1
fi

# Настройка Git на сервере
echo "🔧 Настраиваю Git на сервере..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_HOST "cd $SERVER_PATH && git init && git config user.email 'bot@trading.com' && git config user.name 'BOT Trading'"

echo "🎉 Готово!"