# Решения для постоянного доступа между Mac и Linux

## 1. Tailscale (Рекомендуется) ⭐
**Mesh VPN сеть с автоматической настройкой**

### Преимущества:
- ✅ Работает через любой NAT/firewall
- ✅ Автоматическое подключение
- ✅ Шифрование WireGuard
- ✅ Бесплатно для личного использования
- ✅ Не требует публичного IP

### Установка на Mac:
```bash
# Через Homebrew
brew install --cask tailscale

# Или скачать с сайта
open https://tailscale.com/download/mac
```

### Установка на Linux:
```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh

# Или вручную
wget https://pkgs.tailscale.com/stable/tailscale_latest_amd64.tgz
tar xvf tailscale_latest_amd64.tgz
sudo mv tailscale_*/tailscaled /usr/sbin/
sudo mv tailscale_*/tailscale /usr/bin/
```

### Настройка:
```bash
# На обеих машинах
sudo tailscale up

# Получить IP адреса
tailscale ip -4

# Подключение
ssh obertruper@<tailscale-ip>
```

## 2. ZeroTier
**P2P VPN с виртуальной сетью**

### Установка на Mac:
```bash
brew install --cask zerotier-one
```

### Установка на Linux:
```bash
curl -s https://install.zerotier.com | sudo bash
```

### Настройка:
```bash
# Создать сеть на https://my.zerotier.com
# Присоединиться к сети
sudo zerotier-cli join <network-id>

# Проверить статус
sudo zerotier-cli status
```

## 3. Cloudflare Tunnel (Постоянный)
**Туннель с фиксированным доменом**

### Установка на Linux:
```bash
# Скачать cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# Авторизация
cloudflared tunnel login

# Создать туннель
cloudflared tunnel create home-server

# Настроить конфигурацию
cat > ~/.cloudflared/config.yml << EOF
url: ssh://localhost:22
tunnel: <tunnel-id>
credentials-file: /home/obertruper/.cloudflared/<tunnel-id>.json
EOF

# Запустить как сервис
sudo cloudflared service install
sudo systemctl start cloudflared
```

### Подключение с Mac:
```bash
# Установить cloudflared
brew install cloudflare/tap/cloudflared

# SSH через туннель
ssh -o ProxyCommand="cloudflared access ssh --hostname <your-domain>.trycloudflare.com" obertruper@<your-domain>.trycloudflare.com
```

## 4. WireGuard VPN
**Быстрый и безопасный VPN**

### На Linux (сервер):
```bash
# Установка
sudo apt install wireguard

# Генерация ключей
wg genkey | tee server_private.key | wg pubkey > server_public.key

# Конфигурация
sudo cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = 10.0.0.1/24
PrivateKey = $(cat server_private.key)
ListenPort = 51820

[Peer]
PublicKey = <mac_public_key>
AllowedIPs = 10.0.0.2/32
EOF

# Запуск
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

### На Mac (клиент):
```bash
# Установка
brew install wireguard-tools

# Конфигурация через GUI приложение
open https://apps.apple.com/us/app/wireguard/id1451685025
```

## 5. ngrok (Для временного доступа)
**Простой туннель для разработки**

### На Linux:
```bash
# Скачать
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvf ngrok-v3-stable-linux-amd64.tgz

# Авторизация (нужна регистрация)
./ngrok config add-authtoken <your-token>

# Запуск SSH туннеля
./ngrok tcp 22
```

## Сравнительная таблица

| Решение | Сложность | Надежность | Скорость | Бесплатно | Автоподключение |
|---------|-----------|------------|----------|-----------|-----------------|
| Tailscale | ⭐ Легко | Отлично | Быстро | ✅ Да | ✅ Да |
| ZeroTier | ⭐⭐ Средне | Хорошо | Быстро | ✅ Да | ✅ Да |
| Cloudflare | ⭐⭐ Средне | Отлично | Средне | ✅ Да | ✅ Да |
| WireGuard | ⭐⭐⭐ Сложно | Отлично | Очень быстро | ✅ Да | ⚡ Настраивается |
| ngrok | ⭐ Легко | Средне | Средне | ⚠️ Ограничено | ❌ Нет |

## Рекомендация

Для вашего случая рекомендую **Tailscale**:
1. Простая установка за 5 минут
2. Работает без настройки роутера
3. Автоматически переподключается
4. Бесплатно для 20 устройств
5. Безопасное шифрование

## Быстрый старт с Tailscale

```bash
# Mac
brew install --cask tailscale
tailscale up

# Linux (через SSH если есть временный доступ)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Получить IP и подключиться
tailscale status
ssh obertruper@<linux-tailscale-ip>
```

После настройки подключение будет работать автоматически, даже при смене IP адресов!