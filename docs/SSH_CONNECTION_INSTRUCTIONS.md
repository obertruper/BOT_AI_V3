# SSH подключение к Linux серверу через Cloudflare Tunnel

## Краткое описание
Инструкция для подключения к домашнему Linux серверу с Mac через Cloudflare Tunnel.

## Настройка подключения

### 1. Cloudflared клиент
Убедитесь что cloudflared установлен на Mac:
```bash
which cloudflared
# Должен показать: /opt/homebrew/bin/cloudflared
```

### 2. SSH конфигурация
Файл: `~/.ssh/config`
```bash
# Домашний Linux через Cloudflare Tunnel
Host linux-home-cf
    HostName pre-looks-specially-gsm.trycloudflare.com
    User obertruper
    Port 22
    PreferredAuthentications password
    StrictHostKeyChecking no
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

### 3. Подключение через cloudflared туннель
```bash
# Шаг 1: Создать туннель
cloudflared access tcp --hostname pre-looks-specially-gsm.trycloudflare.com --url tcp://localhost:2222 &

# Шаг 2: Подключиться через локальный порт
sshpass -p "ilpnqw1234" ssh -o StrictHostKeyChecking=no -p 2222 obertruper@localhost
```

### 4. Альтернативные способы подключения

#### Через SSH config (если туннель работает напрямую):
```bash
sshpass -p "ilpnqw1234" ssh linux-home-cf
```

#### Через внешний IP (если порт 22 открыт):
```bash
sshpass -p "ilpnqw1234" ssh -o StrictHostKeyChecking=no obertruper@93.109.63.226
```

#### Через порт 2222 (если настроен на сервере):
```bash
sshpass -p "ilpnqw1234" ssh -o StrictHostKeyChecking=no -p 2222 obertruper@93.109.63.226
```

## Проверка подключения

### Проверить доступность сервера:
```bash
sshpass -p "ilpnqw1234" ssh -o StrictHostKeyChecking=no -p 2222 obertruper@localhost "pwd && ls -la /mnt/SSD/PYCHARMPRODJECT/"
```

### Проверить проекты на сервере:
```bash
sshpass -p "ilpnqw1234" ssh -o StrictHostKeyChecking=no -p 2222 obertruper@localhost "ls -la '/mnt/SSD/PYCHARMPRODJECT/LLM TRANSFORM/'"
```

## Синхронизация проектов

### Копирование BOT_Trading_v3 на сервер:
```bash
# Создать директорию на сервере
sshpass -p "ilpnqw1234" ssh -o StrictHostKeyChecking=no -p 2222 obertruper@localhost "mkdir -p '/mnt/SSD/PYCHARMPRODJECT/BOT_Trading_v3'"

# Синхронизация (исключая большие файлы >50MB)
sshpass -p "ilpnqw1234" rsync -avz --progress \
  --max-size=50M \
  --exclude='*.pyc' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='venv*/' \
  --exclude='node_modules/' \
  --exclude='data/logs/' \
  --exclude='data/cache/' \
  --exclude='data/temp/' \
  --exclude='*.log' \
  --exclude='*.tar.gz' \
  --exclude='*.zip' \
  -e "ssh -o StrictHostKeyChecking=no -p 2222" \
  ./ obertruper@localhost:'/mnt/SSD/PYCHARMPRODJECT/BOT_Trading_v3/'
```

### Копирование LLM TRANSFORM модулей:
```bash
# Скопировать crypto_ai_trading модуль
sshpass -p "ilpnqw1234" rsync -avz --progress \
  --max-size=50M \
  -e "ssh -o StrictHostKeyChecking=no -p 2222" \
  obertruper@localhost:'/mnt/SSD/PYCHARMPRODJECT/LLM TRANSFORM/crypto_ai_trading/' \
  ./llm_models/crypto_ai_trading/
```

## Важные пути на сервере

- Основные проекты: `/mnt/SSD/PYCHARMPRODJECT/`
- LLM TRANSFORM: `/mnt/SSD/PYCHARMPRODJECT/LLM TRANSFORM/`
- BOT_Trading_v3: `/mnt/SSD/PYCHARMPRODJECT/BOT_Trading_v3/`
- Домашняя директория: `/home/obertruper/`

## Учетные данные

- **Пользователь**: obertruper
- **Пароль**: ilpnqw1234
- **Внешний IP**: 93.109.63.226
- **Cloudflare туннель**: pre-looks-specially-gsm.trycloudflare.com

## Диагностика проблем

### Если туннель не отвечает:
1. Проверить статус туннеля на Linux сервере
2. Перезапустить cloudflared на Mac
3. Использовать альтернативные порты (2222, 22)

### Если rsync зависает:
- Добавить флаг `--max-size=50M` для исключения больших файлов
- Использовать `--exclude` для исключения ненужных директорий
- Проверить свободное место на сервере

### Проверка портов на сервере:
```bash
sshpass -p "ilpnqw1234" ssh -o StrictHostKeyChecking=no -p 2222 obertruper@localhost "sudo ss -tlnp | grep -E ':(22|2222)'"
```

---
**Создано**: 13 июля 2025  
**Статус**: Рабочая конфигурация