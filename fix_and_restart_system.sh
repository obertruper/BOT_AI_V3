#!/bin/bash

echo "=========================================="
echo "🔧 ИСПРАВЛЕНИЕ И ПЕРЕЗАПУСК СИСТЕМЫ BOT_AI_V3"
echo "=========================================="
echo ""

# Функция для цветного вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Остановка всех процессов
echo -e "${YELLOW}⏹️  Остановка всех процессов...${NC}"
./stop_all.sh

sleep 2

# 2. Проверка что все остановлено
echo ""
echo -e "${YELLOW}🔍 Проверка остановки процессов...${NC}"
if pgrep -f "unified_launcher" > /dev/null; then
    echo -e "${RED}⚠️  Обнаружены неостановленные процессы, принудительная остановка...${NC}"
    pkill -9 -f "unified_launcher"
    pkill -9 -f "main.py"
    pkill -9 -f "uvicorn"
    sleep 2
fi

# 3. Очистка логов ошибок API
echo ""
echo -e "${YELLOW}🧹 Очистка счетчиков перезапусков...${NC}"
# Удаляем файл состояния процессов если он есть
rm -f data/process_state.json 2>/dev/null
rm -f data/launcher_state.json 2>/dev/null

# 4. Активация виртуального окружения
echo ""
echo -e "${YELLOW}🐍 Активация виртуального окружения...${NC}"
source venv/bin/activate

# 5. Проверка конфигурации
echo ""
echo -e "${YELLOW}📋 Проверка конфигурации...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    exit 1
fi

# Проверяем наличие ключевых переменных
if ! grep -q "BYBIT_API_KEY" .env; then
    echo -e "${YELLOW}⚠️  API ключи Bybit не настроены${NC}"
fi

# 6. Запуск системы поэтапно
echo ""
echo -e "${GREEN}🚀 Запуск системы...${NC}"

# Сначала запускаем основную систему (trading core)
echo -e "${YELLOW}  1. Запуск Trading Core...${NC}"
nohup python3 unified_launcher.py --mode=core > data/logs/launcher_core.log 2>&1 &
CORE_PID=$!
sleep 5

# Проверяем что core запустился
if ps -p $CORE_PID > /dev/null; then
    echo -e "${GREEN}    ✅ Trading Core запущен (PID: $CORE_PID)${NC}"
else
    echo -e "${RED}    ❌ Ошибка запуска Trading Core${NC}"
    tail -5 data/logs/launcher_core.log
    exit 1
fi

# Запускаем ML систему
echo -e "${YELLOW}  2. Запуск ML System...${NC}"
nohup python3 unified_launcher.py --mode=ml > data/logs/launcher_ml.log 2>&1 &
ML_PID=$!
sleep 5

if ps -p $ML_PID > /dev/null; then
    echo -e "${GREEN}    ✅ ML System запущен (PID: $ML_PID)${NC}"
else
    echo -e "${RED}    ❌ Ошибка запуска ML System${NC}"
    tail -5 data/logs/launcher_ml.log
fi

# Пробуем запустить API отдельно
echo -e "${YELLOW}  3. Запуск API Server...${NC}"
# Убиваем все что может занимать порт 8080
lsof -ti :8080 | xargs kill -9 2>/dev/null
sleep 1

# Запускаем API напрямую через uvicorn
cd web/api
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload > ../../data/logs/api_direct.log 2>&1 &
API_PID=$!
cd ../..
sleep 5

# Проверяем что API запустился
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}    ✅ API Server доступен на http://localhost:8080${NC}"
else
    echo -e "${YELLOW}    ⚠️  API Server не отвечает, пробуем альтернативный запуск...${NC}"

    # Альтернативный запуск через unified_launcher
    nohup python3 unified_launcher.py --mode=api > data/logs/launcher_api.log 2>&1 &
    sleep 5

    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}    ✅ API Server запущен через launcher${NC}"
    else
        echo -e "${RED}    ❌ API Server недоступен${NC}"
        echo "    Последние ошибки:"
        tail -5 data/logs/api_direct.log 2>/dev/null
        tail -5 data/logs/launcher_api.log 2>/dev/null
    fi
fi

# 7. Финальная проверка статуса
echo ""
echo -e "${YELLOW}📊 Проверка статуса системы...${NC}"
sleep 3

# Проверяем процессы
echo ""
echo "Запущенные процессы:"
ps aux | grep -E "unified_launcher|main.py|uvicorn" | grep -v grep | awk '{print "  •", $11, $12, $13}'

# Проверяем порты
echo ""
echo "Занятые порты:"
lsof -i :8080 2>/dev/null | grep LISTEN && echo "  • API: порт 8080 ✅" || echo "  • API: порт 8080 ❌"
lsof -i :5173 2>/dev/null | grep LISTEN && echo "  • Frontend: порт 5173 ✅" || echo "  • Frontend: порт 5173 ⏸️"

# 8. Проверка логов на ошибки
echo ""
echo -e "${YELLOW}🔍 Проверка последних ошибок...${NC}"
ERROR_COUNT=$(tail -100 data/logs/errors.log 2>/dev/null | grep -c "ERROR")
if [ "$ERROR_COUNT" -gt "0" ]; then
    echo -e "${YELLOW}  ⚠️  Обнаружено $ERROR_COUNT ошибок в последних 100 строках логов${NC}"
    echo "  Последние 3 ошибки:"
    tail -100 data/logs/errors.log | grep "ERROR" | tail -3 | sed 's/^/    /'
else
    echo -e "${GREEN}  ✅ Критических ошибок не обнаружено${NC}"
fi

# 9. Запуск мониторинга
echo ""
echo "=========================================="
echo -e "${GREEN}✅ СИСТЕМА ПЕРЕЗАПУЩЕНА${NC}"
echo "=========================================="
echo ""
echo "Полезные команды:"
echo "  • Мониторинг логов:    tail -f data/logs/bot_trading_$(date +%Y%m%d).log"
echo "  • Проверка ML:         tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep -E 'ML PREDICTION|признаков'"
echo "  • Проверка API:        curl http://localhost:8080/health"
echo "  • Остановка системы:   ./stop_all.sh"
echo ""
echo "API endpoints:"
echo "  • Health:     http://localhost:8080/health"
echo "  • Docs:       http://localhost:8080/docs"
echo "  • Dashboard:  http://localhost:8080/api/dashboard"
echo ""
