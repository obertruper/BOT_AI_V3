# 🚀 BOT Trading v3 - Руководство по запуску

## 🎯 Способы запуска

### 1. 🟢 Самый простой способ - Quick Start

```bash
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
./quick_start.sh
```

Запустит все компоненты автоматически!

### 2. 🔧 Интерактивный запуск - Start All

```bash
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
./start_all.sh
```

Предоставляет меню с опциями:

- 1) Полный запуск всех компонентов
- 2) Только Web интерфейс (без торговли)
- 3) Только Core система
- 4) Остановить все
- 5) Показать статус

### 3. 📋 Ручной запуск (3 терминала)

**Терминал 1 - Core System:**

```bash
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
source venv/bin/activate
python main.py
```

**Терминал 2 - API Backend:**

```bash
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
source venv/bin/activate
python web/launcher.py
```

**Терминал 3 - Web Frontend:**

```bash
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/web/frontend
npm run dev
```

### 4. 🤖 Автозапуск через systemd

```bash
# Копирование сервис файла
sudo cp bot-trading-v3.service /etc/systemd/system/

# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable bot-trading-v3

# Запуск сервиса
sudo systemctl start bot-trading-v3

# Проверка статуса
sudo systemctl status bot-trading-v3
```

## 📊 После запуска

### Доступные интерфейсы

- 🌐 **Web Dashboard**: <http://localhost:5173>
- 📚 **API Documentation**: <http://localhost:8080/api/docs>
- 🔧 **API Endpoints**: <http://localhost:8080/api>

### Проверка работы

```bash
# Проверить статус системы
./start_all.sh
# Выбрать опцию 5

# Проверить процессы
ps aux | grep -E "main.py|launcher.py|vite"

# Проверить порты
lsof -i :8080  # API
lsof -i :5173  # Frontend
lsof -i :5555  # PostgreSQL
```

## 🛑 Остановка системы

### Способ 1 - Через скрипт

```bash
./start_all.sh
# Выбрать опцию 4
```

### Способ 2 - Вручную

```bash
pkill -f "python main.py"
pkill -f "python web/launcher.py"
pkill -f "vite"
```

### Способ 3 - Через systemd

```bash
sudo systemctl stop bot-trading-v3
```

## 📝 Логи

Все логи сохраняются в директории `logs/`:

```bash
# Просмотр логов в реальном времени
tail -f logs/core.log      # Core система
tail -f logs/api.log       # API Backend
tail -f logs/frontend.log  # Web Frontend

# Все логи сразу
tail -f logs/*.log
```

## 🔧 Настройка

### Переменные окружения (.env)

```env
# Database
PGPASSWORD=your_password

# API Keys
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Frontend настройки (web/frontend/.env.local)

```env
VITE_API_URL=http://localhost:8080/api
VITE_WS_URL=ws://localhost:8080/ws
```

## ⚡ Быстрые команды

### Запуск в фоне

```bash
nohup ./quick_start.sh > /dev/null 2>&1 &
```

### Запуск с логированием

```bash
./quick_start.sh 2>&1 | tee launch.log
```

### Запуск в tmux

```bash
tmux new-session -d -s bot-trading './quick_start.sh'
tmux attach -t bot-trading
```

### Запуск в screen

```bash
screen -dmS bot-trading ./quick_start.sh
screen -r bot-trading
```

## 🆘 Решение проблем

### Порт уже занят

```bash
# Найти процесс
lsof -i :8080
# Убить процесс
kill -9 <PID>
```

### Ошибка с правами

```bash
chmod +x start_all.sh quick_start.sh
```

### Не хватает памяти

```bash
# Увеличить swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 🎉 Готово

Теперь вы можете запустить всю систему одной командой:

```bash
./quick_start.sh
```

И наслаждаться полнофункциональным торговым ботом с красивым веб-интерфейсом!

---

*BOT Trading v3 © 2025*
