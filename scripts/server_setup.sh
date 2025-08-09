#!/bin/bash

# Скрипт установки BOT_AI_V3 на production сервер
# Запускать с правами sudo

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Установка BOT_AI_V3 на сервер${NC}"

# Проверка что запущено с sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Запустите скрипт с sudo${NC}"
    exit 1
fi

# Переменные
BOT_USER="bot_ai_v3"
BOT_DIR="/opt/bot_ai_v3"
POSTGRES_VERSION="15"
PYTHON_VERSION="3.8"

# 1. Обновление системы
echo -e "${YELLOW}📦 Обновление системы...${NC}"
apt-get update && apt-get upgrade -y

# 2. Установка зависимостей
echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
apt-get install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    postgresql-${POSTGRES_VERSION} \
    postgresql-contrib-${POSTGRES_VERSION} \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    htop \
    multitail \
    supervisor \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev

# 3. Создание пользователя
echo -e "${YELLOW}👤 Создание пользователя ${BOT_USER}...${NC}"
if ! id -u ${BOT_USER} > /dev/null 2>&1; then
    useradd -m -s /bin/bash ${BOT_USER}
    usermod -aG sudo ${BOT_USER}
fi

# 4. Настройка PostgreSQL
echo -e "${YELLOW}🐘 Настройка PostgreSQL...${NC}"
sudo -u postgres psql << EOF
CREATE USER obertruper WITH PASSWORD '${POSTGRES_PASSWORD}';
CREATE DATABASE bot_trading_v3 OWNER obertruper;
GRANT ALL PRIVILEGES ON DATABASE bot_trading_v3 TO obertruper;
EOF

# Изменение порта PostgreSQL на 5555
sed -i 's/port = 5432/port = 5555/g' /etc/postgresql/${POSTGRES_VERSION}/main/postgresql.conf
systemctl restart postgresql

# 5. Клонирование репозитория
echo -e "${YELLOW}📥 Клонирование репозитория...${NC}"
if [ ! -d "$BOT_DIR" ]; then
    git clone https://github.com/${GITHUB_USER}/bot_ai_v3.git $BOT_DIR
fi

cd $BOT_DIR
chown -R ${BOT_USER}:${BOT_USER} $BOT_DIR

# 6. Настройка Python окружения
echo -e "${YELLOW}🐍 Настройка Python окружения...${NC}"
sudo -u ${BOT_USER} bash << EOF
cd $BOT_DIR
python${PYTHON_VERSION} -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF

# 7. Настройка окружения
echo -e "${YELLOW}⚙️ Настройка окружения...${NC}"
cat > $BOT_DIR/.env << EOF
# PostgreSQL
PGHOST=localhost
PGPORT=5555
PGUSER=obertruper
PGPASSWORD=${POSTGRES_PASSWORD}
PGDATABASE=bot_trading_v3

# Redis
REDIS_URL=redis://localhost:6379

# Режим
ENVIRONMENT=production
LOG_LEVEL=INFO

# Биржи (заполнить реальными ключами)
BYBIT_API_KEY=
BYBIT_API_SECRET=

# AI (опционально)
CLAUDE_API_KEY=
GITHUB_TOKEN=
EOF

chown ${BOT_USER}:${BOT_USER} $BOT_DIR/.env
chmod 600 $BOT_DIR/.env

# 8. Systemd сервисы
echo -e "${YELLOW}🔧 Создание systemd сервисов...${NC}"

# Основной сервис
cat > /etc/systemd/system/bot-ai-v3.service << EOF
[Unit]
Description=BOT_AI_V3 Trading System
After=network.target postgresql.service redis.service
Wants=bot-ai-v3-monitor.timer

[Service]
Type=forking
User=${BOT_USER}
Group=${BOT_USER}
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/unified_launcher.py --mode=ml --daemon
ExecStop=$BOT_DIR/venv/bin/python $BOT_DIR/unified_launcher.py --stop
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=append:$BOT_DIR/data/logs/systemd.log
StandardError=append:$BOT_DIR/data/logs/systemd_error.log

# Лимиты
LimitNOFILE=65536
LimitNPROC=4096

# Безопасность
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$BOT_DIR/data $BOT_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

# Сервис мониторинга
cat > /etc/systemd/system/bot-ai-v3-monitor.service << EOF
[Unit]
Description=BOT_AI_V3 Health Monitor
After=bot-ai-v3.service

[Service]
Type=oneshot
User=${BOT_USER}
Group=${BOT_USER}
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/scripts/health_check.py
EOF

# Таймер для мониторинга
cat > /etc/systemd/system/bot-ai-v3-monitor.timer << EOF
[Unit]
Description=Run BOT_AI_V3 Health Monitor every 5 minutes
Requires=bot-ai-v3-monitor.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

# 9. Nginx конфигурация
echo -e "${YELLOW}🌐 Настройка Nginx...${NC}"
cat > /etc/nginx/sites-available/bot-ai-v3 << EOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOF

ln -sf /etc/nginx/sites-available/bot-ai-v3 /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 10. Логротейт
echo -e "${YELLOW}📋 Настройка логротейта...${NC}"
cat > /etc/logrotate.d/bot-ai-v3 << EOF
$BOT_DIR/data/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ${BOT_USER} ${BOT_USER}
    sharedscripts
    postrotate
        systemctl reload bot-ai-v3 > /dev/null 2>&1 || true
    endscript
}
EOF

# 11. Firewall
echo -e "${YELLOW}🔥 Настройка firewall...${NC}"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5173/tcp  # Frontend (закрыть после настройки nginx)
ufw allow 8080/tcp  # API (закрыть после настройки nginx)
ufw --force enable

# 12. Запуск сервисов
echo -e "${YELLOW}🚀 Запуск сервисов...${NC}"
systemctl daemon-reload
systemctl enable bot-ai-v3.service
systemctl enable bot-ai-v3-monitor.timer
systemctl start bot-ai-v3-monitor.timer
systemctl start bot-ai-v3.service

# 13. Проверка статуса
echo -e "${YELLOW}✅ Проверка статуса...${NC}"
sleep 5
systemctl status bot-ai-v3.service --no-pager
systemctl status bot-ai-v3-monitor.timer --no-pager

echo -e "${GREEN}✅ Установка завершена!${NC}"
echo -e "${GREEN}📊 Мониторинг логов: multitail -f $BOT_DIR/data/logs/*.log${NC}"
echo -e "${GREEN}🌐 Frontend: http://${DOMAIN_NAME}${NC}"
echo -e "${GREEN}📚 API Docs: http://${DOMAIN_NAME}/api/docs${NC}"
