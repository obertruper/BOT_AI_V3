#!/bin/bash

echo "🏠 Настройка локальной машины как сервера для BOT_AI_V3"
echo "======================================================="
echo ""

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Переменные
PROJECT_DIR="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3"
SERVICE_NAME="bot-ai-v3"
USER=$(whoami)
PYTHON_PATH="$PROJECT_DIR/venv/bin/python"

echo "📋 Конфигурация:"
echo "  Директория проекта: $PROJECT_DIR"
echo "  Пользователь: $USER"
echo "  Сервис: $SERVICE_NAME"
echo ""

# 1. Создание systemd сервиса
echo "1️⃣ Создание systemd сервиса..."
SERVICE_FILE="/tmp/${SERVICE_NAME}.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=BOT_AI_V3 Trading System (Local)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=$PROJECT_DIR"
Environment="PGPORT=5555"
ExecStart=$PYTHON_PATH $PROJECT_DIR/unified_launcher.py --mode=ml
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_DIR/data/logs/systemd.log
StandardError=append:$PROJECT_DIR/data/logs/systemd_error.log

# Лимиты для production
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅${NC} Сервис файл создан: $SERVICE_FILE"

# 2. Установка сервиса
echo ""
echo "2️⃣ Установка systemd сервиса..."
echo "Требуется пароль для sudo:"
echo "${SUDO_PASSWORD:-your-password-here}" | sudo -S cp "$SERVICE_FILE" "/etc/systemd/system/${SERVICE_NAME}.service"  # Используем переменную окружения
echo "${SUDO_PASSWORD:-your-password-here}" | sudo -S systemctl daemon-reload

echo -e "${GREEN}✅${NC} Сервис установлен"

# 3. Создание скрипта управления
echo ""
echo "3️⃣ Создание скриптов управления..."

# Start script
cat > "$PROJECT_DIR/start_server.sh" <<'EOF'
#!/bin/bash
echo "🚀 Запуск BOT_AI_V3 сервера..."
sudo systemctl start bot-ai-v3
sleep 2
sudo systemctl status bot-ai-v3 --no-pager
echo ""
echo "📊 Логи: tail -f data/logs/systemd.log"
EOF

# Stop script
cat > "$PROJECT_DIR/stop_server.sh" <<'EOF'
#!/bin/bash
echo "🛑 Остановка BOT_AI_V3 сервера..."
sudo systemctl stop bot-ai-v3
echo "✅ Сервер остановлен"
EOF

# Restart script
cat > "$PROJECT_DIR/restart_server.sh" <<'EOF'
#!/bin/bash
echo "🔄 Перезапуск BOT_AI_V3 сервера..."
sudo systemctl restart bot-ai-v3
sleep 2
sudo systemctl status bot-ai-v3 --no-pager
EOF

# Status script
cat > "$PROJECT_DIR/server_status.sh" <<'EOF'
#!/bin/bash
echo "📊 Статус BOT_AI_V3 сервера:"
echo "============================="
sudo systemctl status bot-ai-v3 --no-pager
echo ""
echo "📈 Последние логи:"
tail -n 20 data/logs/systemd.log 2>/dev/null || echo "Логи пока пусты"
EOF

chmod +x "$PROJECT_DIR"/*.sh
echo -e "${GREEN}✅${NC} Скрипты управления созданы"

# 4. Настройка автозапуска
echo ""
echo "4️⃣ Настройка автозапуска при загрузке системы..."
echo "${SUDO_PASSWORD:-your-password-here}" | sudo -S systemctl enable "$SERVICE_NAME" 2>/dev/null
echo -e "${GREEN}✅${NC} Автозапуск настроен"

# 5. Создание локального деплой хука
echo ""
echo "5️⃣ Создание Git hook для автоматического деплоя..."

HOOK_FILE="$PROJECT_DIR/.git/hooks/post-merge"
cat > "$HOOK_FILE" <<'EOF'
#!/bin/bash
# Автоматический деплой после git pull

echo "🔄 Автоматический деплой после обновления..."

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем зависимости
pip install -r requirements.txt --quiet

# Применяем миграции БД
alembic upgrade head

# Перезапускаем сервис
sudo systemctl restart bot-ai-v3

echo "✅ Деплой завершён!"
EOF

chmod +x "$HOOK_FILE"
echo -e "${GREEN}✅${NC} Git hook создан"

# 6. Создание скрипта для локального деплоя
echo ""
echo "6️⃣ Создание скрипта локального деплоя..."

cat > "$PROJECT_DIR/local_deploy.sh" <<'EOF'
#!/bin/bash
# Локальный деплой с GitHub

echo "📦 Локальный деплой BOT_AI_V3"
echo "=============================="

# Переходим в директорию проекта
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3

# Получаем последние изменения
echo "📥 Получение обновлений с GitHub..."
git pull origin main

# Git hook автоматически выполнит деплой
# Или можно выполнить вручную:

echo "🔧 Обновление зависимостей..."
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "🗄️ Применение миграций БД..."
alembic upgrade head

echo "🔄 Перезапуск сервиса..."
sudo systemctl restart bot-ai-v3

echo "✅ Деплой завершён!"
echo ""
echo "📊 Статус сервиса:"
sudo systemctl status bot-ai-v3 --no-pager
EOF

chmod +x "$PROJECT_DIR/local_deploy.sh"
echo -e "${GREEN}✅${NC} Скрипт локального деплоя создан"

# 7. Настройка cron для автоматического деплоя
echo ""
echo "7️⃣ Настройка автоматической проверки обновлений (опционально)..."

CRON_SCRIPT="$PROJECT_DIR/auto_update.sh"
cat > "$CRON_SCRIPT" <<'EOF'
#!/bin/bash
# Автоматическая проверка и деплой обновлений

cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3

# Проверяем есть ли обновления
git fetch origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Найдены обновления, запускаем деплой..." >> data/logs/auto_update.log
    ./local_deploy.sh >> data/logs/auto_update.log 2>&1
else
    echo "$(date): Обновлений нет" >> data/logs/auto_update.log
fi
EOF

chmod +x "$CRON_SCRIPT"

# Добавление в crontab (закомментировано, включить по желанию)
# (crontab -l 2>/dev/null; echo "*/5 * * * * $CRON_SCRIPT") | crontab -

echo -e "${GREEN}✅${NC} Скрипт автообновления создан (не активирован)"

# 8. Финальная проверка
echo ""
echo "🎉 Настройка завершена!"
echo ""
echo "📝 Доступные команды:"
echo -e "  ${YELLOW}./start_server.sh${NC}   - Запустить сервер"
echo -e "  ${YELLOW}./stop_server.sh${NC}    - Остановить сервер"
echo -e "  ${YELLOW}./restart_server.sh${NC} - Перезапустить сервер"
echo -e "  ${YELLOW}./server_status.sh${NC}  - Проверить статус"
echo -e "  ${YELLOW}./local_deploy.sh${NC}   - Выполнить деплой с GitHub"
echo ""
echo "🚀 Для запуска сервера выполните:"
echo -e "  ${GREEN}./start_server.sh${NC}"
echo ""
echo "🔄 Для автоматического деплоя после коммитов:"
echo "  1. Делаете коммит и push на GitHub"
echo "  2. Выполняете: ./local_deploy.sh"
echo "  3. Сервис автоматически перезапустится с новым кодом"
echo ""
echo "⚙️ Для включения автопроверки обновлений каждые 5 минут:"
echo "  Раскомментируйте строку с crontab в этом скрипте"
