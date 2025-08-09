#!/bin/bash

# Быстрый запуск BOT_AI_V3 с проверками

echo "🚀 Запуск BOT_AI_V3 Trading Bot"
echo "================================"

# Проверка что мы в правильной директории
if [ ! -f "unified_launcher.py" ]; then
    echo "❌ Ошибка: запустите скрипт из директории BOT_AI_V3"
    exit 1
fi

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено"
    echo "Создаю виртуальное окружение..."
    python3 -m venv venv
fi

# Активация venv
source venv/bin/activate

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден"
    echo "Копирую .env.example..."
    cp .env.example .env
    echo "⚠️  Отредактируйте .env и добавьте API ключи бирж!"
    exit 1
fi

# Проверка API ключей
if ! grep -q "BYBIT_API_KEY=.*[a-zA-Z0-9]" .env; then
    echo "⚠️  Предупреждение: API ключи не настроены в .env"
    echo "   Бот будет работать в режиме симуляции"
fi

# Проверка PostgreSQL
if ! psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ PostgreSQL не доступен на порту 5555"
    echo "Проверьте что PostgreSQL запущен и настроен"
    exit 1
fi

echo "✅ Все проверки пройдены"
echo ""

# Меню выбора режима
echo "Выберите режим запуска:"
echo "1) ML Trading (рекомендуется)"
echo "2) Простая торговля без ML"
echo "3) Все компоненты (с веб-интерфейсом)"
echo "4) Проверить статус"
echo "5) Остановить бота"

read -p "Выбор (1-5): " choice

case $choice in
    1)
        echo "🚀 Запуск ML Trading..."
        python3 unified_launcher.py --mode=ml --logs
        ;;
    2)
        echo "🚀 Запуск простой торговли..."
        python3 unified_launcher.py --mode=core --logs
        ;;
    3)
        echo "🚀 Запуск всех компонентов..."
        python3 unified_launcher.py --logs
        ;;
    4)
        echo "📊 Проверка статуса..."
        python3 unified_launcher.py --status
        ;;
    5)
        echo "🛑 Остановка бота..."
        python3 unified_launcher.py --stop
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac
