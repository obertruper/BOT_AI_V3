# 📋 План миграции BOT Trading v2 → v3

## Обзор миграции

### Текущее состояние

- **V2**: Синхронная архитектура, XGBoost ML, Telegram бот, PostgreSQL:5555
- **V3**: Асинхронная архитектура, PatchTST ML, веб-интерфейс, PostgreSQL:5555

### Цели миграции

- ✅ Сохранить все торговые данные и историю
- ✅ Интегрировать Telegram бот из v2
- ✅ Объединить ML модели (XGBoost + PatchTST)
- ✅ Минимальный downtime (< 1 час)
- ✅ Возможность отката

## 📊 Этапы миграции

### Этап 1: Подготовка (2-3 дня)

#### 1.1 Резервное копирование

```bash
# Полный дамп базы v2
pg_dump -p 5555 -U obertruper bot_trading_v2 > backup_v2_$(date +%Y%m%d_%H%M%S).sql

# Архив конфигураций v2
tar -czf bot_v2_configs_$(date +%Y%m%d).tar.gz BOT_AI_V2/config.yaml BOT_AI_V2/.env

# Архив ML моделей
tar -czf bot_v2_models_$(date +%Y%m%d).tar.gz BOT_AI_V2/models/
```

#### 1.2 Создание тестовой среды

```bash
# Клонирование v3 для тестов
cp -r BOT_AI_V3 BOT_AI_V3_TEST
cd BOT_AI_V3_TEST

# Создание тестовой БД
sudo -u postgres psql -p 5555 -c "CREATE DATABASE bot_trading_v3_test OWNER obertruper;"

# Настройка тестового окружения
cp .env.example .env.test
# Отредактировать .env.test: PGDATABASE=bot_trading_v3_test
```

### Этап 2: Миграция базы данных (1 день)

#### 2.1 Применение миграций совместимости

```bash
# В v3 директории
cd BOT_AI_V3
source venv/bin/activate

# Применить миграции для v2 совместимости
alembic upgrade head

# Проверка структуры
psql -p 5555 -U obertruper -d bot_trading_v3 -c "\dt"
```

#### 2.2 Импорт данных из v2

```bash
# Запуск скрипта миграции данных
python scripts/migrate_v2_data.py \
  --source-db bot_trading_v2 \
  --target-db bot_trading_v3 \
  --batch-size 1000 \
  --verify

# Проверка целостности
python scripts/verify_migration.py
```

### Этап 3: Интеграция Telegram бота (2 дня)

#### 3.1 Копирование кода бота

```bash
# Создание модуля telegram в v3
mkdir -p BOT_AI_V3/monitoring/telegram
cp BOT_AI_V2/telegram_bot.py BOT_AI_V3/monitoring/telegram/bot.py
```

#### 3.2 Адаптация к асинхронной архитектуре

```python
# monitoring/telegram/adapter.py
import asyncio
from typing import Optional
from telegram_bot import TelegramBot as SyncBot

class AsyncTelegramBotAdapter:
    """Адаптер для интеграции синхронного Telegram бота в асинхронную архитектуру v3"""

    def __init__(self, config: dict):
        self.sync_bot = SyncBot(config)
        self.loop = asyncio.get_event_loop()

    async def start(self):
        """Запуск бота в отдельном потоке"""
        await self.loop.run_in_executor(None, self.sync_bot.start)

    async def send_notification(self, message: str):
        """Асинхронная отправка уведомлений"""
        await self.loop.run_in_executor(
            None,
            self.sync_bot.send_message,
            message
        )
```

#### 3.3 Интеграция в SystemOrchestrator

```python
# Добавить в core/system/orchestrator.py
from monitoring.telegram.adapter import AsyncTelegramBotAdapter

# В методе start()
if self.config.get('telegram', {}).get('enabled'):
    self.telegram_bot = AsyncTelegramBotAdapter(self.config['telegram'])
    await self.telegram_bot.start()
```

### Этап 4: Объединение ML моделей (3 дня)

#### 4.1 Копирование XGBoost моделей

```bash
# Копирование моделей и конфигураций
cp -r BOT_AI_V2/models/xgboost BOT_AI_V3/models/
cp BOT_AI_V2/ml/predictor.py BOT_AI_V3/ml/logic/xgboost_predictor.py
```

#### 4.2 Создание унифицированного ML менеджера

```python
# strategies/ml_strategy/unified_model_manager.py
from typing import Dict, Any, Optional
import numpy as np

class UnifiedModelManager:
    """Менеджер для работы с XGBoost и PatchTST моделями"""

    def __init__(self, config: Dict[str, Any]):
        self.xgboost_enabled = config.get('xgboost_enabled', True)
        self.patchtst_enabled = config.get('patchtst_enabled', True)

        if self.xgboost_enabled:
            from ml.logic.xgboost_predictor import XGBoostPredictor
            self.xgboost = XGBoostPredictor(config['xgboost'])

        if self.patchtst_enabled:
            from strategies.ml_strategy.model_manager import ModelManager
            self.patchtst = ModelManager(config['patchtst'])

    async def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """Комбинированное предсказание от обеих моделей"""
        predictions = {}

        if self.xgboost_enabled:
            xgb_pred = await self._run_xgboost(features)
            predictions['xgboost'] = xgb_pred

        if self.patchtst_enabled:
            tst_pred = await self._run_patchtst(features)
            predictions['patchtst'] = tst_pred

        # Взвешенное усреднение
        if len(predictions) == 2:
            predictions['ensemble'] = self._ensemble_predict(predictions)

        return predictions
```

### Этап 5: Миграция конфигураций (1 день)

#### 5.1 Унификация конфигураций

```yaml
# config/migration.yaml
migration:
  telegram:
    enabled: true
    token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"

  ml_models:
    xgboost:
      enabled: true
      path: "models/xgboost/combined_model_20250423_214043"
      risk_profile: "standard"  # standard, conservative, very_conservative

    patchtst:
      enabled: true
      path: "models/saved/best_model_UnifiedPatchTST.pth"

  enhanced_sltp:
    enabled: true
    trailing_stop:
      enabled: true
      activation_profit: 1.0
      trail_percent: 0.5
```

#### 5.2 Перенос API ключей

```bash
# Безопасный перенос ключей
# 1. Экспортировать из v2
cd BOT_AI_V2
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
keys = {k: v for k, v in os.environ.items() if 'API' in k or 'SECRET' in k}
import json
with open('../keys_export.json', 'w') as f:
    json.dump(keys, f)
"

# 2. Импортировать в v3
cd ../BOT_AI_V3
python scripts/import_api_keys.py --file ../keys_export.json

# 3. Удалить временный файл
rm ../keys_export.json
```

### Этап 6: Тестирование (2 дня)

#### 6.1 Функциональные тесты

```bash
# Тест миграции данных
pytest tests/migration/test_data_integrity.py -v

# Тест Telegram бота
pytest tests/integration/test_telegram_bot.py -v

# Тест ML моделей
pytest tests/unit/ml/test_unified_models.py -v

# Интеграционные тесты
pytest tests/integration/ --slow -v
```

#### 6.2 Нагрузочное тестирование

```bash
# Симуляция торговли на исторических данных
python scripts/backtest_migration.py \
  --start-date 2025-01-01 \
  --end-date 2025-01-30 \
  --symbols BTCUSDT,ETHUSDT
```

### Этап 7: Развертывание (1 день)

#### 7.1 Остановка v2

```bash
# Мягкая остановка с завершением текущих операций
cd BOT_AI_V2
python -c "
from core.ipc import IPCClient
client = IPCClient()
client.send_command('stop_trading')
client.send_command('close_all_positions')
"

# Ждем завершения
sleep 60

# Полная остановка
pkill -f "python.*main.py"
```

#### 7.2 Запуск v3

```bash
cd BOT_AI_V3

# Запуск в режиме мониторинга
python main.py --mode monitor --duration 300

# Если все OK, полный запуск
python main.py --config config/migration.yaml

# Запуск веб-интерфейса
python web/launcher.py --port 8080
```

#### 7.3 Верификация

```bash
# Проверка здоровья системы
curl http://localhost:8080/api/health

# Проверка Telegram бота
python -c "
from monitoring.telegram.adapter import AsyncTelegramBotAdapter
import asyncio
bot = AsyncTelegramBotAdapter({'token': 'YOUR_TOKEN'})
asyncio.run(bot.send_notification('V3 migration completed!'))
"

# Мониторинг логов
tail -f data/logs/trading.log | grep -E "(ERROR|WARNING|MIGRATION)"
```

## 🔄 Процедура отката

### Быстрый откат (< 5 минут)

```bash
# 1. Остановка v3
pkill -f "python.*main.py"

# 2. Запуск v2
cd BOT_AI_V2
python main.py

# 3. Восстановление БД (если нужно)
psql -p 5555 -U obertruper -d bot_trading_v2 < backup_v2_latest.sql
```

### Частичный откат компонентов

```bash
# Откат только Telegram бота
rm -rf BOT_AI_V3/monitoring/telegram
# Перезапуск без Telegram

# Откат ML моделей
# В config/migration.yaml установить xgboost.enabled: false
```

## ⏱️ Временная диаграмма

```
День 1-2:   [====] Подготовка и резервирование
День 3:     [==] Миграция БД
День 4-5:   [====] Интеграция Telegram
День 6-8:   [======] Объединение ML
День 9:     [==] Миграция конфигураций
День 10-11: [====] Тестирование
День 12:    [==] Развертывание
День 13-14: [====] Мониторинг и оптимизация
```

## ✅ Контрольные точки

### После каждого этапа проверить

- [ ] Логи без критических ошибок
- [ ] Все тесты проходят успешно
- [ ] База данных консистентна
- [ ] API ключи работают
- [ ] Telegram уведомления приходят
- [ ] ML предсказания генерируются
- [ ] Производительность не деградировала

## 🚨 Критические моменты

1. **Миграция БД** - самый критичный этап, требует полного бэкапа
2. **API ключи** - проверить лимиты и разрешения для v3
3. **Telegram бот** - может потребовать обновления webhook
4. **ML модели** - проверить совместимость версий библиотек

## 📊 Метрики успеха

- Downtime < 1 час
- 100% данных мигрировано без потерь
- Производительность v3 > v2 минимум в 10 раз
- Все функции v2 работают в v3
- Новые функции v3 (веб-интерфейс) доступны

## 🔧 Пост-миграционные задачи

1. Оптимизация производительности ensemble ML
2. Настройка алертов и мониторинга
3. Обучение команды новому интерфейсу
4. Документирование изменений
5. Планирование следующих улучшений

---

**Статус**: Готов к выполнению
**Оценка времени**: 12-14 дней
**Риск**: Средний (с возможностью отката)
