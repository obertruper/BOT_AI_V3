#!/bin/bash
# Скрипт настройки базы данных для BOT Trading v3

echo "🚀 Настройка базы данных PostgreSQL для BOT Trading v3"
echo "======================================================"

# Проверка PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL не установлен. Установите его командой:"
    echo "   sudo apt install postgresql postgresql-contrib"
    exit 1
fi

echo "✅ PostgreSQL установлен"

# Проверка статуса сервиса
if systemctl is-active --quiet postgresql; then
    echo "✅ PostgreSQL сервис запущен"
else
    echo "❌ PostgreSQL сервис не запущен. Запустите его:"
    echo "   sudo systemctl start postgresql"
    exit 1
fi

echo ""
echo "📝 Инструкции по настройке базы данных:"
echo ""
echo "1. Создайте пользователя и базу данных:"
echo "   sudo -u postgres psql"
echo ""
echo "   В psql выполните:"
echo "   CREATE USER obertruper WITH PASSWORD 'your_secure_password';"
echo "   CREATE DATABASE bot_trading_v3 OWNER obertruper;"
echo "   GRANT ALL PRIVILEGES ON DATABASE bot_trading_v3 TO obertruper;"
echo "   \\q"
echo ""
echo "2. Обновите файл .env с вашим паролем:"
echo "   Откройте .env и замените 'your_password_here' на ваш пароль"
echo ""
echo "3. Проверьте подключение:"
echo "   PGPASSWORD=your_password psql -h localhost -U obertruper -d bot_trading_v3 -c '\\l'"
echo ""
echo "4. Запустите миграции (если используете Alembic):"
echo "   alembic upgrade head"
echo ""
echo "💡 Альтернативный вариант - использовать peer аутентификацию:"
echo "   Создайте пользователя с именем вашего системного пользователя:"
echo "   sudo -u postgres createuser --createdb obertruper"
echo "   sudo -u postgres createdb -O obertruper bot_trading_v3"
