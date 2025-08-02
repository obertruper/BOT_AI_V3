# 🚀 Комплексный план миграции BOT Trading v2 → v3

## 📌 Резюме текущего состояния

### Что уже готово в v3

- ✅ Асинхронная архитектура (SystemOrchestrator, TradingEngine)
- ✅ PatchTST ML модель перенесена (models/saved/best_model_20250728_215703.pth)
- ✅ Веб-интерфейс (FastAPI + React)
- ✅ Мульти-биржевая поддержка (7 бирж)
- ✅ База данных структура (но с другими моделями)

### Что критически отсутствует

- ❌ Telegram бот (основной интерфейс в v2)
- ❌ XGBoost модели (рабочие ML из v2)
- ❌ Миграция данных из v2
- ❌ Конфигурация API ключей бирж
- ❌ Enhanced SL/TP система из v2

## 🎯 Стратегия миграции

### Принципы

1. **Сохранение работоспособности v2** - v2 продолжает работать во время миграции
2. **Постепенный переход** - компоненты мигрируют по очереди
3. **Гибридный ML подход** - используем обе модели (XGBoost + PatchTST)
4. **Минимальные изменения БД** - расширяем структуру v2, не ломаем

## 📅 План по дням (14 дней)

### День 1-2: Подготовка инфраструктуры

```bash
# 1. Резервное копирование v2
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V2
./backup_all.sh

# 2. Настройка БД для v3
# Используем ту же БД bot_trading_v3 на порту 5555
# Проверяем подключение
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
python database/connections/postgres.py

# 3. Копирование конфигураций
cp BOT_AI_V2/BOT_Trading/BOT_Trading/config.yaml config/legacy_v2_config.yaml
cp BOT_AI_V2/BOT_Trading/BOT_Trading/.env .env.v2_backup
```

### День 3-4: Миграция Telegram бота

```python
# Создаем notifications/telegram/ структуру
mkdir -p notifications/telegram
cp -r BOT_AI_V2/BOT_Trading/BOT_Trading/api/telegram_bot.py notifications/telegram/
cp -r BOT_AI_V2/BOT_Trading/BOT_Trading/utils/telegram_utils.py notifications/telegram/

# Адаптируем под асинхронную архитектуру
# Создаем TelegramNotificationService для v3
```

### День 5-7: Интеграция ML моделей

```python
# 1. Копируем XGBoost модели
cp -r BOT_AI_V2/BOT_Trading/BOT_Trading/models/combined_model_* models/xgboost/

# 2. Создаем унифицированный ML менеджер
# ml/unified_manager.py - работает с обеими моделями

# 3. Настраиваем конфигурацию
# config/ml/ml_config.yaml - параметры обеих моделей
```

### День 8-9: Миграция данных

```bash
# 1. Выравнивание структур БД
python scripts/align_database_schema.py

# 2. Миграция торговых данных
python scripts/migrate_v2_data.py --source=v2 --target=v3

# 3. Проверка целостности
python scripts/verify_migration.py
```

### День 10-11: Интеграция компонентов

```python
# 1. Enhanced SL/TP из v2
cp -r BOT_AI_V2/BOT_Trading/BOT_Trading/trading/sltp/ trading/risk/enhanced_sltp/

# 2. Webhook интеграция для TradingView
# Адаптируем webhook_server.py под v3 архитектуру

# 3. Настройка SystemOrchestrator
# Добавляем Telegram и ML компоненты
```

### День 12-13: Тестирование

```bash
# 1. Запуск в тестовом режиме
ENVIRONMENT=test python main.py

# 2. Параллельный запуск v2 и v3
# v2 на основном сервере
# v3 на COPE сервере для тестов

# 3. Сравнение результатов
python scripts/compare_v2_v3_performance.py
```

### День 14: Развертывание

```bash
# 1. Финальное резервирование
./create_final_backup.sh

# 2. Переключение на v3
systemctl stop bot-trading-v2
systemctl start bot-trading-v3

# 3. Мониторинг
tail -f logs/trading_*.log
```

## 🔧 Технические детали интеграции

### База данных

```sql
-- Расширение таблиц v2 для v3
ALTER TABLE trades ADD COLUMN IF NOT EXISTS trader_id VARCHAR(100);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS exchange VARCHAR(50);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS strategy_name VARCHAR(100);

-- Новые таблицы для v3
CREATE TABLE IF NOT EXISTS ml_predictions (
    id SERIAL PRIMARY KEY,
    model_type VARCHAR(50),  -- 'xgboost' или 'patchtst'
    signal_id INTEGER,
    predictions JSONB,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Конфигурация

```yaml
# config/system.yaml
system:
  version: "3.0"
  compatibility_mode: true  # Поддержка v2 компонентов

database:
  port: 5555  # ВАЖНО: правильный порт!
  user: obertruper

telegram:
  enabled: true
  legacy_mode: true  # Использовать код из v2

ml_models:
  ensemble: true  # Использовать обе модели
  xgboost:
    enabled: true
    path: "models/xgboost/"
  patchtst:
    enabled: true
    path: "models/saved/best_model_20250728_215703.pth"
```

### API ключи

```bash
# Копируем из v2 .env
BYBIT_API_KEY=xxx
BYBIT_API_SECRET=xxx
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx
# ... остальные биржи

# Telegram
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx
```

## 🚨 Критические точки проверки

### После каждого этапа

1. ✅ База данных доступна и данные целы
2. ✅ Telegram бот отвечает на команды
3. ✅ ML модели делают предсказания
4. ✅ Торговые операции выполняются корректно
5. ✅ Логи не содержат критических ошибок

### Процедура отката

```bash
# В случае проблем
systemctl stop bot-trading-v3
systemctl start bot-trading-v2

# Восстановление БД если нужно
psql -p 5555 -U obertruper bot_trading_v3 < backup_v2_latest.sql
```

## 📊 Метрики успеха

- **Downtime**: < 1 час
- **Потеря данных**: 0%
- **Функциональность**: 100% v2 + новые возможности v3
- **Производительность**: улучшение на 30-50% за счет async
- **ML точность**: сохранение или улучшение

## 🎯 Результат миграции

После успешной миграции получаем:

1. **Современную асинхронную архитектуру** с обратной совместимостью
2. **Гибридную ML систему** (XGBoost + PatchTST)
3. **Полнофункциональный Telegram бот** + веб-интерфейс
4. **Сохранение всех данных и истории**
5. **Готовность к масштабированию** и новым функциям

## 📝 Чек-лист готовности к запуску

- [ ] Все резервные копии созданы
- [ ] БД мигрирована и проверена
- [ ] Telegram бот интегрирован и работает
- [ ] ML модели подключены (обе)
- [ ] API ключи настроены
- [ ] Тесты пройдены
- [ ] Мониторинг настроен
- [ ] План отката готов

---

**Начало миграции**: _____________
**Планируемое завершение**: _____________
**Ответственный**: _____________
