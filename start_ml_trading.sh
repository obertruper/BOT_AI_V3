#!/bin/bash
# Скрипт запуска торговой системы с ML генерацией сигналов

echo "🚀 BOT_AI_V3 - Запуск торговой системы с ML"
echo "================================================"

# Переходим в директорию проекта
cd "$(dirname "$0")"

# Загружаем переменные окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Переменные окружения загружены"
else
    echo "❌ Файл .env не найден!"
    echo "   Создайте .env на основе .env.example"
    exit 1
fi

# Активируем виртуальное окружение если оно есть
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Виртуальное окружение активировано"
fi

# Проверяем доступность PostgreSQL
echo "🔍 Проверка PostgreSQL на порту 5555..."
if PGPASSWORD=$PGPASSWORD psql -p 5555 -U $PGUSER -d $PGDATABASE -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ PostgreSQL доступен"
else
    echo "❌ PostgreSQL недоступен на порту 5555"
    echo "   Убедитесь что PostgreSQL запущен:"
    echo "   sudo systemctl status postgresql"
    exit 1
fi

# Применяем миграции
echo "🔄 Применение миграций БД..."
alembic upgrade head

# Опциональная загрузка данных
echo ""
read -p "❓ Загрузить исторические данные? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📥 Загрузка исторических данных..."
    python scripts/load_historical_data.py --days 7
fi

# Проверка готовности
echo ""
echo "🔍 Проверка готовности системы..."
python scripts/check_data_availability.py

echo ""
read -p "❓ Запустить торговую систему? (Y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "🚀 Запуск торговой системы..."
    echo "================================================"
    echo ""

    # Запускаем main.py
    python main.py
else
    echo "❌ Запуск отменен"
fi
