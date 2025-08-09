#!/bin/bash
# -*- coding: utf-8 -*-
#
# Единый скрипт запуска торговой системы BOT_AI_V3
# с веб-интерфейсом и мониторингом ML сигналов
#

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}🤖 BOT Trading v3.0 - ML Edition${NC}"
echo -e "${BLUE}======================================${NC}"

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Виртуальное окружение не найдено!${NC}"
    echo -e "${YELLOW}Создайте его командой: python3 -m venv venv${NC}"
    exit 1
fi

# Активация виртуального окружения
echo -e "${YELLOW}🔧 Активация виртуального окружения...${NC}"
source venv/bin/activate

# Проверка PostgreSQL
echo -e "${YELLOW}🔍 Проверка PostgreSQL на порту 5555...${NC}"
if pg_isready -p 5555 -q; then
    echo -e "${GREEN}✅ PostgreSQL работает${NC}"
else
    echo -e "${RED}❌ PostgreSQL не доступен на порту 5555${NC}"
    echo -e "${YELLOW}Запустите PostgreSQL или проверьте настройки${NC}"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    echo -e "${YELLOW}Скопируйте .env.example и настройте API ключи${NC}"
    exit 1
fi

# Проверка модели
MODEL_PATH="models/saved/best_model_20250728_215703.pth"
if [ ! -f "$MODEL_PATH" ]; then
    echo -e "${YELLOW}⚠️  ML модель не найдена: $MODEL_PATH${NC}"
    echo -e "${YELLOW}Система будет работать без ML сигналов${NC}"
else
    echo -e "${GREEN}✅ ML модель найдена${NC}"
fi

# Остановка старых процессов
echo -e "${YELLOW}🛑 Остановка старых процессов...${NC}"
pkill -f "python main.py" 2>/dev/null || true
pkill -f "python scripts/monitor_ml_signals.py" 2>/dev/null || true
sleep 2

# Создание директорий для логов
mkdir -p data/logs

# Запуск основной системы
echo -e "${YELLOW}🚀 Запуск торговой системы...${NC}"
LOG_FILE="data/logs/main_$(date +%Y%m%d_%H%M%S).log"
nohup python main.py > "$LOG_FILE" 2>&1 &
MAIN_PID=$!

echo -e "${GREEN}✅ Система запущена (PID: $MAIN_PID)${NC}"
echo -e "${YELLOW}📝 Логи: $LOG_FILE${NC}"

# Ждем инициализации
echo -e "${YELLOW}⏳ Ожидание инициализации (30 сек)...${NC}"
sleep 30

# Проверка доступности API
echo -e "${YELLOW}🔍 Проверка веб-интерфейса...${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/health | grep -q "200"; then
    echo -e "${GREEN}✅ Web API доступен${NC}"
    echo -e "${BLUE}🌐 Веб-интерфейс: http://localhost:8080${NC}"
    echo -e "${BLUE}📚 API документация: http://localhost:8080/api/docs${NC}"
else
    echo -e "${RED}❌ Web API не отвечает${NC}"
    echo -e "${YELLOW}Проверьте логи: tail -f $LOG_FILE${NC}"
fi

# Опциональный запуск мониторинга
echo -e ""
echo -e "${YELLOW}Запустить мониторинг ML сигналов? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${YELLOW}🖥️  Запуск монитора ML сигналов...${NC}"
    python scripts/monitor_ml_signals.py
else
    echo -e "${GREEN}✅ Система запущена в фоновом режиме${NC}"
    echo -e ""
    echo -e "${YELLOW}Полезные команды:${NC}"
    echo -e "  ${BLUE}Мониторинг ML:${NC} python scripts/monitor_ml_signals.py"
    echo -e "  ${BLUE}Логи системы:${NC} tail -f $LOG_FILE"
    echo -e "  ${BLUE}Тест ML:${NC} python scripts/test_ml_signals.py"
    echo -e "  ${BLUE}Остановка:${NC} pkill -f 'python main.py'"
    echo -e ""
    echo -e "${GREEN}🚀 Happy Trading!${NC}"
fi
