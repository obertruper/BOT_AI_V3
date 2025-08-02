# 🚀 Быстрый старт миграции v2 → v3

## Первоочередные задачи (можно начать сегодня)

### 1. Исправить подключение к БД (5 минут)

```bash
# В файле config/system.yaml поменять:
database:
  host: localhost
  port: 5555  # Вместо 5432
  name: bot_trading_v3
  user: obertruper
  password: ваш_пароль
```

### 2. Скопировать Telegram бота (30 минут)

```bash
# Копируем модуль Telegram из v2
mkdir -p notifications/telegram
cp BOT_AI_V2/BOT_Trading/BOT_Trading/api/telegram_bot.py notifications/telegram/bot.py
cp BOT_AI_V2/BOT_Trading/BOT_Trading/utils/telegram_utils.py notifications/telegram/utils.py

# Копируем переменные окружения
grep TELEGRAM BOT_AI_V2/BOT_Trading/BOT_Trading/.env >> .env
```

### 3. Перенести API ключи бирж (10 минут)

```bash
# Копируем все API ключи из v2
grep -E "(BYBIT|BINANCE|OKX|BITGET|GATEIO|KUCOIN|HUOBI)_(API_KEY|API_SECRET|PASSPHRASE)" \
  BOT_AI_V2/BOT_Trading/BOT_Trading/.env >> .env
```

### 4. Проверить работу ML модели (15 минут)

```bash
# Проверяем что PatchTST модель на месте
ls -la models/saved/best_model_20250728_215703.pth

# Запускаем тест
python ml/logic/patchtst_usage_example.py
```

### 5. Создать адаптер для Telegram (1-2 часа)

```python
# notifications/telegram/telegram_service.py
import asyncio
from typing import Optional
from core.config.config_manager import ConfigManager

class TelegramNotificationService:
    """Адаптер для синхронного Telegram бота в асинхронной архитектуре"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.bot = None  # Будет инициализирован из v2 кода

    async def initialize(self):
        """Инициализация Telegram бота"""
        # Импортируем и адаптируем код из v2
        from notifications.telegram.bot import TelegramBot
        self.bot = TelegramBot(self.config.get_telegram_config())

    async def send_notification(self, message: str):
        """Отправка уведомления через Telegram"""
        # Запускаем синхронный код в executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.bot.send_message, message)
```

## Что получим после этих шагов

1. ✅ Правильное подключение к БД
2. ✅ Работающий Telegram бот
3. ✅ Доступ к биржам через API
4. ✅ Работающая ML модель
5. ✅ Основа для дальнейшей интеграции

## Следующие шаги

1. Интегрировать Telegram в SystemOrchestrator
2. Добавить XGBoost модели из v2
3. Создать унифицированный ML manager
4. Мигрировать данные из v2
5. Запустить параллельное тестирование

---

**Время на первые шаги**: ~3 часа
**Результат**: Базовая работоспособность v3 с ключевыми компонентами из v2
