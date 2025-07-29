# Настройка Tailscale для постоянного доступа

## ✅ Mac (уже установлен)

1. **Запустите Tailscale** (уже запущен)
   ```bash
   open -a Tailscale
   ```

2. **Войдите в аккаунт**
   - Кликните на иконку Tailscale в строке меню
   - Выберите "Log in..."
   - Используйте Google/GitHub/Microsoft аккаунт

3. **Получите IP адрес Mac**
   ```bash
   tailscale ip -4
   ```

## 🐧 Linux (нужно установить)

### Команды для установки на Linux:
```bash
# Вариант 1: Автоматическая установка
curl -fsSL https://tailscale.com/install.sh | sh

# Вариант 2: Ручная установка для Ubuntu/Debian
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
sudo apt-get update
sudo apt-get install tailscale

# Запуск и авторизация
sudo tailscale up

# Получить IP адрес
tailscale ip -4
```

### SSH конфигурация после установки:

1. **Добавьте в ~/.ssh/config на Mac:**
```bash
# Tailscale подключение к Linux
Host linux-tailscale
    HostName <linux-tailscale-ip>
    User obertruper
    Port 22
    PreferredAuthentications password
    StrictHostKeyChecking no
```

2. **Проверка подключения:**
```bash
# Используя пароль
sshpass -p "ilpnqw1234" ssh linux-tailscale

# Или напрямую
ssh obertruper@<linux-tailscale-ip>
```

## 🔧 Автоматизация

### Скрипт установки для Linux (скопируйте и запустите):
```bash
#!/bin/bash
# install_tailscale.sh

echo "Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh

echo "Starting Tailscale..."
sudo tailscale up

echo "Tailscale IP:"
tailscale ip -4

echo "Setup complete! Use the IP above to connect from Mac"
```

### Обновленный sync скрипт с Tailscale:
```bash
#!/bin/bash
# sync_with_tailscale.sh

TAILSCALE_IP=$(tailscale status | grep "linux-" | awk '{print $1}')
if [ -z "$TAILSCALE_IP" ]; then
    echo "Error: Linux machine not found in Tailscale network"
    exit 1
fi

echo "Syncing to $TAILSCALE_IP..."
sshpass -p "ilpnqw1234" rsync -avz --progress \
    --max-size=50M \
    --exclude='*.pyc' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='venv*/' \
    --exclude='node_modules/' \
    ./ obertruper@$TAILSCALE_IP:/mnt/SSD/PYCHARMPRODJECT/BOT_Trading_v3/
```

## 📋 Преимущества Tailscale

1. **Автоматическое подключение** - работает даже при смене IP
2. **Безопасность** - WireGuard шифрование
3. **Простота** - не нужно настраивать порты
4. **Скорость** - прямое P2P соединение
5. **Бесплатно** - до 20 устройств

## 🚀 Быстрые команды

После настройки используйте:
```bash
# SSH подключение
ssh obertruper@<tailscale-ip>

# Синхронизация проекта
./scripts/sync_to_linux_server.sh

# Проверка статуса
tailscale status

# Ping тест
tailscale ping <linux-hostname>
```

## ⚠️ Важно

- Tailscale должен быть запущен на обеих машинах
- Используйте один аккаунт для всех устройств
- IP адреса в сети Tailscale начинаются с 100.x.x.x
- Подключение работает из любой сети

---
**Статус**: Mac ✅ Установлен | Linux ⏳ Ожидает установки