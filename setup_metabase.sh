#!/bin/bash

# Скрипт установки и настройки Metabase для BOT_AI_V3

echo "=================================="
echo "   УСТАНОВКА METABASE ДЛЯ ML АНАЛИТИКИ"
echo "=================================="

# Создаем директории
mkdir -p nginx/ssl

# Создаем конфигурацию nginx
cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream metabase {
        server metabase:3000;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://metabase;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
EOF

echo "✅ Конфигурация nginx создана"

# Запускаем Metabase
echo "🚀 Запуск Metabase..."
docker-compose -f docker-compose.metabase.yml up -d

# Ждем запуска
echo "⏳ Ожидание запуска Metabase (может занять 1-2 минуты)..."
sleep 30

# Проверяем статус
docker-compose -f docker-compose.metabase.yml ps

echo ""
echo "=================================="
echo "   METABASE УСПЕШНО УСТАНОВЛЕН!"
echo "=================================="
echo ""
echo "📊 Доступ к Metabase:"
echo "   URL: http://localhost:3000"
echo ""
echo "🔧 Первоначальная настройка:"
echo "   1. Откройте http://localhost:3000"
echo "   2. Создайте администратора"
echo "   3. Подключите БД PostgreSQL:"
echo "      Host: host.docker.internal"
echo "      Port: 5555"
echo "      Database: bot_trading_v3"
echo "      Username: obertruper"
echo "      Password: ilpnqw1234"
echo ""
echo "📈 Готовые дашборды будут в директории:"
echo "   dashboards/"
echo ""

# Создаем скрипт остановки
cat > stop_metabase.sh << 'EOF'
#!/bin/bash
echo "Остановка Metabase..."
docker-compose -f docker-compose.metabase.yml down
echo "✅ Metabase остановлен"
EOF
chmod +x stop_metabase.sh

echo "💡 Для остановки используйте: ./stop_metabase.sh"
