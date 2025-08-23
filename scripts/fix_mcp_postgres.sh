#!/bin/bash
# Скрипт для исправления MCP PostgreSQL подключения

echo "🔧 Исправление MCP PostgreSQL конфигурации..."

# Экспортируем переменные окружения для MCP
export PGHOST=localhost
export PGPORT=5555
export PGUSER=obertruper
export PGPASSWORD=${PGPASSWORD:-your-password-here}  # Используем переменную окружения
export PGDATABASE=bot_trading_v3

# Добавляем в .env если не существует
if ! grep -q "^PGHOST=" .env 2>/dev/null; then
    echo "PGHOST=localhost" >> .env
    echo "✅ Добавлен PGHOST в .env"
fi

# Проверяем подключение
echo "🔍 Проверка подключения к PostgreSQL..."
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 'MCP PostgreSQL connection OK' as status;" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL подключение работает корректно"
    echo ""
    echo "📋 Конфигурация:"
    echo "  Host: localhost"
    echo "  Port: 5555"
    echo "  Database: bot_trading_v3"
    echo "  User: obertruper"
else
    echo "❌ Ошибка подключения к PostgreSQL"
    echo "Проверьте что PostgreSQL запущен на порту 5555"
fi

echo ""
echo "💡 Для использования MCP PostgreSQL в Claude Code:"
echo "1. Перезапустите Claude Code"
echo "2. MCP автоматически подключится используя переменные окружения"
echo "3. Или используйте mcp__postgres__connect_db с параметрами выше"
