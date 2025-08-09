# 🚀 BOT_AI_V3 Deployment Guide

## 📊 Мониторинг логов в реальном времени

### Быстрый запуск мониторинга

```bash
# Все логи с цветовой разметкой
./monitor_realtime.sh all

# Простой режим с цветами
./monitor_realtime.sh simple

# Только ошибки
./monitor_realtime.sh errors

# Только торговые операции
./monitor_realtime.sh trades
```

### Примеры использования

```bash
# Запуск системы с логами в реальном времени (2 терминала)
# Терминал 1:
python3 unified_launcher.py --mode=ml

# Терминал 2:
./monitor_realtime.sh trades
```

## 🔧 GitHub Actions CI/CD

### Настройка секретов в GitHub

1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте следующие секреты:

```yaml
# Для staging сервера
STAGING_HOST: your-staging-server.com
STAGING_USER: bot_ai_v3
STAGING_SSH_KEY: (ваш SSH приватный ключ)
STAGING_PORT: 22

# Для production сервера
PRODUCTION_HOST: your-production-server.com
PRODUCTION_USER: bot_ai_v3
PRODUCTION_SSH_KEY: (ваш SSH приватный ключ)
PRODUCTION_PORT: 22

# PostgreSQL
POSTGRES_PASSWORD: your-secure-password

# Уведомления (опционально)
SLACK_WEBHOOK: https://hooks.slack.com/services/...
```

### Workflow процесс

1. **Pull Request → main**: Запускаются тесты
2. **Push в main**: Автоматический деплой на staging
3. **Push в production**: Автоматический деплой на production

### Ручной деплой

```bash
# Через GitHub Actions UI
Actions → Deploy BOT_AI_V3 → Run workflow → Choose environment
```

## 🖥️ Установка на сервер

### Требования к серверу

- Ubuntu 20.04+ или Debian 11+
- Минимум 4 GB RAM (рекомендуется 8 GB)
- 20 GB свободного места на диске
- Python 3.8+
- PostgreSQL 15
- Redis 7+

### Автоматическая установка

```bash
# Скачайте и запустите установочный скрипт
wget https://raw.githubusercontent.com/YOUR_USERNAME/bot_ai_v3/main/scripts/server_setup.sh
chmod +x server_setup.sh

# Установите переменные окружения
export GITHUB_USER="your-github-username"
export POSTGRES_PASSWORD="secure-password"  # pragma: allowlist secret
export DOMAIN_NAME="your-domain.com"

# Запустите установку
sudo ./server_setup.sh
```

### Ручная установка

1. **Клонирование репозитория**

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/bot_ai_v3.git
cd bot_ai_v3
```

2. **Создание виртуального окружения**

```bash
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Настройка PostgreSQL**

```bash
sudo -u postgres psql
CREATE USER obertruper WITH PASSWORD 'your-password';  -- pragma: allowlist secret
CREATE DATABASE bot_trading_v3 OWNER obertruper;
\q

# Изменение порта на 5555
sudo nano /etc/postgresql/15/main/postgresql.conf
# port = 5555
sudo systemctl restart postgresql
```

4. **Настройка .env файла**

```bash
cp .env.example .env
nano .env
# Заполните все необходимые переменные
```

5. **Запуск миграций**

```bash
alembic upgrade head
```

6. **Запуск системы**

```bash
python3 unified_launcher.py --mode=ml
```

## 📱 Systemd сервисы

### Основной сервис

```bash
# Управление
sudo systemctl start bot-ai-v3
sudo systemctl stop bot-ai-v3
sudo systemctl restart bot-ai-v3
sudo systemctl status bot-ai-v3

# Логи
sudo journalctl -u bot-ai-v3 -f
```

### Мониторинг

```bash
# Проверка здоровья системы
python3 scripts/health_check.py

# Автоматический мониторинг каждые 5 минут
sudo systemctl enable bot-ai-v3-monitor.timer
sudo systemctl start bot-ai-v3-monitor.timer
```

## 🔒 Безопасность

### SSL сертификат

```bash
# Получение Let's Encrypt сертификата
sudo certbot --nginx -d your-domain.com
```

### Firewall

```bash
# Базовая настройка
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Резервное копирование

```bash
# Backup базы данных
pg_dump -h localhost -p 5555 -U obertruper bot_trading_v3 > backup.sql

# Backup конфигурации
tar -czf bot_ai_v3_config_$(date +%Y%m%d).tar.gz .env config/
```

## 📊 Мониторинг производительности

### Grafana Dashboard

1. Установите Grafana:

```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get install grafana
```

2. Импортируйте dashboard из `monitoring/grafana_dashboard.json`

### Проверка состояния

```bash
# Системные метрики
htop

# Использование диска
df -h

# Логи в реальном времени
./monitor_realtime.sh all

# Health check
curl http://localhost:8080/api/health
```

## 🚨 Troubleshooting

### Проблема: API не запускается

```bash
# Проверка порта
sudo lsof -i:8080

# Проверка логов
tail -f data/logs/errors.log

# Перезапуск
sudo systemctl restart bot-ai-v3
```

### Проблема: Нет подключения к PostgreSQL

```bash
# Проверка статуса
sudo systemctl status postgresql

# Проверка порта
sudo netstat -plnt | grep 5555

# Тест подключения
psql -h localhost -p 5555 -U obertruper -d bot_trading_v3
```

### Проблема: ML модель не загружается

```bash
# Проверка CUDA (если GPU)
nvidia-smi

# Проверка модели
ls -la models/saved/

# Запуск без GPU
python3 unified_launcher.py --mode=core
```

## 📞 Поддержка

- **Документация**: `/docs/`
- **Логи**: `/data/logs/`
- **Health check**: `http://your-domain.com/api/health`
- **API Docs**: `http://your-domain.com/api/docs`

## 🔄 Обновление

```bash
# Остановка системы
sudo systemctl stop bot-ai-v3

# Получение обновлений
cd /opt/bot_ai_v3
git pull origin main

# Обновление зависимостей
source venv/bin/activate
pip install -r requirements.txt

# Миграции БД
alembic upgrade head

# Запуск
sudo systemctl start bot-ai-v3
```
