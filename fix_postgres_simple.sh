#!/bin/bash
# Простое решение для настройки доступа PostgreSQL

echo "🔧 Настройка PostgreSQL для Docker доступа..."

# Создаем backup существующих настроек
echo "📁 Создание резервной копии..."
sudo cp /etc/postgresql/16/main/pg_hba.conf /etc/postgresql/16/main/pg_hba.conf.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null

# Добавляем строки для Docker сетей
echo "📝 Добавление правил доступа..."
{
    echo ""
    echo "# Docker networks access for Metabase"
    echo "host    all             obertruper      172.17.0.0/16           trust"
    echo "host    all             obertruper      172.21.0.0/16           trust"
    echo "host    all             obertruper      172.18.0.0/16           trust"
    echo "host    all             obertruper      172.19.0.0/16           trust"
    echo "host    all             obertruper      172.20.0.0/16           trust"
    echo "# End Docker access rules"
} | sudo tee -a /etc/postgresql/16/main/pg_hba.conf

# Перезагружаем конфигурацию PostgreSQL
echo "🔄 Перезагрузка конфигурации PostgreSQL..."
sudo systemctl reload postgresql 2>/dev/null || sudo service postgresql reload 2>/dev/null

echo "✅ Настройка завершена!"

# Проверяем подключение
echo "🧪 Тестирование подключения..."
sleep 2
docker exec bot_metabase psql -h 172.21.0.1 -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT current_database(), current_user;" 2>/dev/null && echo "✅ Подключение успешно!" || echo "❌ Подключение не удалось"
