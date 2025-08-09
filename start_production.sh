#!/bin/bash

# BOT_AI_V3 Production Launcher with Real-time Logs
# =================================================

set -e  # Exit on error

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Функция для вывода с временной меткой
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Заголовок
clear
echo -e "${PURPLE}============================================================${NC}"
echo -e "${PURPLE}🚀 BOT_AI_V3 - Production Trading System${NC}"
echo -e "${PURPLE}============================================================${NC}"
echo ""

# Проверка окружения
log "Проверка окружения..."

# Проверка venv
if [ ! -d "venv" ]; then
    error "Virtual environment не найден!"
    exit 1
fi

# Активация venv
source venv/bin/activate
log "✅ Virtual environment активирован"

# Проверка PostgreSQL
if ! pg_isready -p 5555 -h localhost > /dev/null 2>&1; then
    error "PostgreSQL не доступен на порту 5555!"
    exit 1
fi
log "✅ PostgreSQL доступен"

# Проверка .env
if [ ! -f ".env" ]; then
    error ".env файл не найден!"
    exit 1
fi

# Проверка production режима
if ! grep -q "ENVIRONMENT=production" .env; then
    warning "Система не в production режиме! Переключаю..."
    sed -i 's/ENVIRONMENT=.*/ENVIRONMENT=production/' .env
fi
log "✅ Production режим активирован"

# Остановка старых процессов
log "Остановка старых процессов..."
pkill -f "python.*unified_launcher.py" 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*launcher.py" 2>/dev/null || true
sleep 2

# Создание директории для логов
mkdir -p data/logs/production
LOG_DIR="data/logs/production"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Функция для мониторинга логов
monitor_logs() {
    # Используем multitail если установлен
    if command -v multitail &> /dev/null; then
        log "Запуск multitail для мониторинга логов..."
        multitail \
            -cT ANSI -l "tail -f $LOG_DIR/core_$TIMESTAMP.log | sed 's/^/[CORE] /'" \
            -cT ANSI -l "tail -f $LOG_DIR/api_$TIMESTAMP.log | sed 's/^/[API] /'" \
            -cT ANSI -l "tail -f $LOG_DIR/ml_$TIMESTAMP.log | sed 's/^/[ML] /'" \
            -cT ANSI -l "tail -f data/logs/trading.log | sed 's/^/[TRADE] /'" \
            -cT ANSI -l "tail -f data/logs/error.log | sed 's/^/[ERROR] /'"
    else
        # Fallback на обычный tail с цветами
        log "Запуск мониторинга логов..."

        # Создаем именованные каналы для цветного вывода
        mkfifo /tmp/bot_logs_pipe 2>/dev/null || true

        # Запускаем мониторинг в фоне
        (
            tail -f $LOG_DIR/core_$TIMESTAMP.log 2>/dev/null | sed "s/^/$(echo -e ${BLUE})[CORE]$(echo -e ${NC}) /" &
            tail -f $LOG_DIR/api_$TIMESTAMP.log 2>/dev/null | sed "s/^/$(echo -e ${CYAN})[API]$(echo -e ${NC}) /" &
            tail -f $LOG_DIR/ml_$TIMESTAMP.log 2>/dev/null | sed "s/^/$(echo -e ${PURPLE})[ML]$(echo -e ${NC}) /" &
            tail -f data/logs/trading.log 2>/dev/null | sed "s/^/$(echo -e ${GREEN})[TRADE]$(echo -e ${NC}) /" &
            tail -f data/logs/error.log 2>/dev/null | sed "s/^/$(echo -e ${RED})[ERROR]$(echo -e ${NC}) /" &
            wait
        )
    fi
}

# Запуск системы с логированием
log "Запуск торговой системы..."
echo ""
echo -e "${YELLOW}Режимы запуска:${NC}"
echo "  1) Full - Все компоненты (Core + API + Frontend)"
echo "  2) Core - Только торговый движок"
echo "  3) ML - Торговля + ML без интерфейса"
echo "  4) API - Только API и интерфейс"
echo ""
read -p "Выберите режим (1-4) [по умолчанию 1]: " mode

case $mode in
    2) MODE="core" ;;
    3) MODE="ml" ;;
    4) MODE="api" ;;
    *) MODE="full" ;;
esac

log "Выбран режим: $MODE"
echo ""

# Запуск unified_launcher с перенаправлением логов
log "Запуск unified_launcher..."
python3 unified_launcher.py --mode=$MODE \
    > >(tee -a $LOG_DIR/unified_$TIMESTAMP.log) \
    2>&1 &

LAUNCHER_PID=$!
log "✅ Unified launcher запущен (PID: $LAUNCHER_PID)"

# Ждем инициализации
sleep 5

# Проверка статуса
log "Проверка статуса компонентов..."
python3 unified_launcher.py --status

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ Система запущена в production режиме${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${YELLOW}Полезные команды:${NC}"
echo "  • Статус: python3 unified_launcher.py --status"
echo "  • Логи: python3 unified_launcher.py --logs"
echo "  • Остановка: pkill -f unified_launcher.py"
echo ""
echo -e "${YELLOW}Доступные сервисы:${NC}"
echo "  • Dashboard: http://localhost:5173"
echo "  • API: http://localhost:8080"
echo "  • API Docs: http://localhost:8080/api/docs"
echo ""
echo -e "${YELLOW}Мониторинг:${NC}"
echo "  • Trading logs: tail -f data/logs/trading.log"
echo "  • Error logs: tail -f data/logs/error.log"
echo "  • All logs: tail -f data/logs/production/*_$TIMESTAMP.log"
echo ""
echo -e "${CYAN}Запуск мониторинга логов в реальном времени...${NC}"
echo -e "${CYAN}Для выхода нажмите Ctrl+C${NC}"
echo ""

# Запуск мониторинга логов
monitor_logs
