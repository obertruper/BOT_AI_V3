#!/bin/bash
# 🚀 Быстрый запуск BOT_AI_V3
# Автоматизированный скрипт для развертывания и запуска торгового бота

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для красивого вывода
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Проверка, что мы в правильной директории
if [ ! -f "main.py" ]; then
    error "Скрипт должен запускаться из корневой директории BOT_AI_V3"
fi

# ASCII баннер
echo -e "${BLUE}"
cat << "EOF"
 ____   ___ _____      _    ___  __     ______
| __ ) / _ \_   _|    / \  |_ _| \ \   / |___ /
|  _ \| | | || |     / _ \  | |   \ \ / /  |_ \
| |_) | |_| || |    / ___ \ | |    \ V /  ___) |
|____/ \___/ |_|   /_/   \_\___|    \_/  |____/

        Multi-Exchange AI Trading Platform
EOF
echo -e "${NC}"

# ЭТАП 1: Проверка системных требований
log "Проверка системных требований..."

# Python версия
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    error "Требуется Python $required_version или выше. Установлена версия: $python_version"
fi
info "Python версия: $python_version ✓"

# PostgreSQL
if ! command -v psql &> /dev/null; then
    error "PostgreSQL не установлен"
fi

# Проверка PostgreSQL на порту 5555
if psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 1;" &> /dev/null; then
    info "PostgreSQL доступен на порту 5555 ✓"
else
    error "PostgreSQL недоступен на порту 5555. Проверьте настройки БД."
fi

# Node.js
if command -v node &> /dev/null; then
    node_version=$(node --version)
    info "Node.js версия: $node_version ✓"
else
    warning "Node.js не установлен. MCP серверы не будут работать."
fi

# ЭТАП 2: Настройка окружения
log "Настройка виртуального окружения..."

# Создание venv если не существует
if [ ! -d "venv" ]; then
    log "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация venv
source venv/bin/activate
info "Виртуальное окружение активировано ✓"

# Обновление pip
log "Обновление pip..."
pip install --upgrade pip setuptools wheel --quiet

# ЭТАП 3: Установка зависимостей
log "Установка Python зависимостей..."
pip install -r requirements.txt --quiet
info "Основные зависимости установлены ✓"

# Установка дополнительных компонентов
log "Установка дополнительных компонентов..."
pip install -e ".[monitoring]" --quiet 2>/dev/null || warning "Monitoring компоненты не установлены"
pip install -e ".[telegram]" --quiet 2>/dev/null || warning "Telegram компоненты не установлены"

# Node.js зависимости
if command -v npm &> /dev/null; then
    log "Установка Node.js зависимостей..."
    npm install --silent
    info "Node.js зависимости установлены ✓"
fi

# ЭТАП 4: Конфигурация
log "Настройка конфигурации..."

# Создание .env если не существует
if [ ! -f ".env" ]; then
    cp .env.example .env
    warning ".env файл создан из примера. Необходимо настроить API ключи!"

    # Интерактивная настройка минимальных параметров
    read -p "Хотите настроить базовые параметры сейчас? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Генерация секретного ключа
        SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
        sed -i "s/your_secret_key_for_jwt/$SECRET_KEY/g" .env

        echo "Введите API ключи для Bybit (или нажмите Enter для пропуска):"
        read -p "BYBIT_API_KEY: " bybit_key
        read -p "BYBIT_API_SECRET: " bybit_secret

        if [ ! -z "$bybit_key" ] && [ ! -z "$bybit_secret" ]; then
            sed -i "s/your_bybit_api_key/$bybit_key/g" .env
            sed -i "s/your_bybit_api_secret/$bybit_secret/g" .env
            info "API ключи Bybit сохранены ✓"
        fi
    fi
else
    info "Файл .env уже существует ✓"
fi

# ЭТАП 5: База данных
log "Проверка и миграция базы данных..."

# Проверка подключения
if python3 scripts/test_local_db.py &> /dev/null; then
    info "Подключение к БД успешно ✓"
else
    error "Не удалось подключиться к БД. Проверьте настройки в .env"
fi

# Применение миграций
log "Применение миграций Alembic..."
alembic upgrade head
info "Миграции применены ✓"

# ЭТАП 6: Проверка ML модели
log "Проверка ML модели..."

model_path="models/saved/best_model_20250728_215703.pth"
scaler_path="models/saved/data_scaler.pkl"
config_path="models/saved/config.pkl"

if [ -f "$model_path" ] && [ -f "$scaler_path" ] && [ -f "$config_path" ]; then
    info "ML модель найдена ✓"
else
    warning "ML модель не найдена. ML стратегия не будет работать."
    warning "Скопируйте файлы модели из LLM TRANSFORM проекта в models/saved/"
fi

# ЭТАП 7: Создание systemd сервисов (опционально)
read -p "Создать systemd сервисы для автозапуска? (требует sudo) (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Создание systemd сервисов..."

    # Сервис для торгового движка
    sudo tee /etc/systemd/system/bot-trading.service > /dev/null << EOF
[Unit]
Description=BOT Trading v3 Engine
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Сервис для веб-панели
    sudo tee /etc/systemd/system/bot-trading-web.service > /dev/null << EOF
[Unit]
Description=BOT Trading v3 Web Interface
After=network.target bot-trading.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/python web/launcher.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable bot-trading
    sudo systemctl enable bot-trading-web
    info "Systemd сервисы созданы ✓"
fi

# ФИНАЛ: Инструкции по запуску
echo
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Установка завершена успешно!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo
echo "Для запуска системы выполните:"
echo
echo "1. В первом терминале (торговый движок):"
echo "   ${BLUE}source venv/bin/activate${NC}"
echo "   ${BLUE}python3 main.py${NC}"
echo
echo "2. Во втором терминале (веб-панель):"
echo "   ${BLUE}source venv/bin/activate${NC}"
echo "   ${BLUE}python3 web/launcher.py --reload --debug${NC}"
echo
echo "3. Веб-интерфейс будет доступен по адресу:"
echo "   ${YELLOW}http://localhost:8080${NC}"
echo "   API документация: ${YELLOW}http://localhost:8080/api/docs${NC}"
echo

if [ -f ".env" ] && grep -q "your_" .env; then
    echo -e "${YELLOW}⚠️  ВАЖНО: Не забудьте настроить API ключи в файле .env${NC}"
fi

echo
echo "Для автоматического запуска используйте:"
echo "   ${BLUE}sudo systemctl start bot-trading${NC}"
echo "   ${BLUE}sudo systemctl start bot-trading-web${NC}"
echo
echo -e "${GREEN}Happy Trading! 🚀${NC}"
