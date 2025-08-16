# 📁 Анализ файловой структуры BOT_AI_V3

## 🟢 АКТИВНЫЕ КОМПОНЕНТЫ (Работающие)

### 🚀 Core System (Ядро системы)

```
✅ unified_launcher.py          - ГЛАВНАЯ ТОЧКА ВХОДА, запускает всю систему
✅ main.py                       - Основное приложение торговли
✅ core/
   ├── system/
   │   ├── orchestrator.py      - Координатор всех компонентов
   │   ├── process_manager.py   - Управление процессами
   │   ├── health_monitor.py    - Мониторинг здоровья системы
   │   └── data_manager.py      - Управление потоками данных
   ├── config/
   │   └── config_manager.py    - Централизованное управление конфигурацией
   └── logger.py                 - Система логирования
```

### 💹 Trading Engine (Торговый движок)

```
✅ trading/
   ├── engine.py                 - ГЛАВНЫЙ ТОРГОВЫЙ ДВИЖОК (597 строк)
   ├── orders/
   │   ├── order_manager.py     - Управление ордерами
   │   └── sltp_integration.py  - Интеграция Stop Loss/Take Profit
   ├── signals/
   │   ├── ai_signal_generator.py    - Генератор AI сигналов
   │   └── signal_processor.py       - Обработчик сигналов
   └── positions/
       └── position_manager.py       - Управление позициями
```

### 🧠 ML System (Машинное обучение)

```
✅ ml/
   ├── ml_manager.py                  - Менеджер ML моделей
   ├── ml_signal_processor.py         - Обработчик ML сигналов
   ├── realtime_indicator_calculator.py - Расчет индикаторов в реальном времени
   ├── logic/
   │   ├── feature_engineering_v2.py - АКТИВНАЯ версия feature engineering
   │   ├── patchtst_model.py         - Основная ML модель UnifiedPatchTST
   │   └── patchtst_unified.py       - Унифицированная версия модели
   └── models/saved/
       ├── best_model.pth             - Обученная модель
       └── data_scaler.pkl            - Скейлер данных
```

### 🏦 Exchange Integration (Интеграция с биржами)

```
✅ exchanges/
   ├── exchange_manager.py      - Менеджер всех бирж
   ├── factory.py               - Фабрика создания exchange адаптеров
   ├── base/
   │   ├── exchange_interface.py - Базовый интерфейс
   │   └── api_key_manager.py    - Управление API ключами
   └── bybit/                    - Основная биржа
       ├── bybit_exchange.py     - Реализация Bybit
       └── adapter.py            - Адаптер Bybit
```

### 🗄️ Database Layer (База данных)

```
✅ database/
   ├── connections/
   │   └── postgres.py          - PostgreSQL пул соединений (порт 5555!)
   ├── models/
   │   ├── base_models.py      - Базовые SQLAlchemy модели
   │   ├── market_data.py      - Модели рыночных данных
   │   └── signal.py           - Модели сигналов
   └── repositories/
       └── trade_repository.py  - Репозиторий сделок
```

### 🌐 Web Interface (Веб-интерфейс)

```
✅ web/
   ├── api/
   │   ├── main.py             - FastAPI приложение (порт 8080)
   │   └── endpoints/          - REST endpoints
   └── frontend/
       ├── src/
       │   ├── App.tsx         - React приложение
       │   └── main.tsx        - Entry point
       └── vite.config.ts      - Vite конфигурация (порт 5173)
```

### ⚙️ Configuration (Конфигурация)

```
✅ config/
   ├── trading.yaml            - Торговые параметры
   ├── system.yaml             - Системные настройки
   ├── ml/ml_config.yaml       - ML конфигурация
   └── strategies/             - Стратегии
```

### 🛡️ Risk Management (Управление рисками)

```
✅ risk_management/
   ├── manager.py              - Основной риск-менеджер
   ├── calculators.py          - Калькуляторы рисков
   └── sltp/                   - Stop Loss/Take Profit логика
```

---

## 🟡 ВСПОМОГАТЕЛЬНЫЕ КОМПОНЕНТЫ

### 📊 Monitoring & Testing

```
⚡ scripts/
   ├── monitoring/             - Скрипты мониторинга
   ├── deployment/            - Скрипты деплоя
   └── check_*.py            - Различные проверки системы

⚡ tests/
   ├── unit/                 - Unit тесты
   └── integration/          - Интеграционные тесты

⚡ utils/
   └── checks/              - Утилиты проверки состояния
```

### 📝 Documentation

```
📄 docs/                    - Вся документация проекта
📄 *.md файлы в корне      - README, руководства, отчеты
```

---

## 🔴 ДУБЛИКАТЫ И УСТАРЕВШИЕ ФАЙЛЫ

### ❌ Старые версии ML

```
🗑️ ml/logic/feature_engineering.py         - СТАРАЯ версия (v1)
🗑️ ml/logic/feature_engineering_v2_backup.py - Бэкап
🗑️ ml/logic/feature_engineering_v2_backup_full.py - Полный бэкап
🗑️ ml/logic/feature_engineering_v4.py     - Экспериментальная версия
```

### ❌ Тестовые и временные файлы

```
🗑️ test_*.py (в корне)     - Временные тест-скрипты
   ├── test_api_keys.py
   ├── test_bybit_balance.py
   ├── test_ml_diversity_final.py
   └── ... (еще ~20 файлов)

🗑️ check_*.py (в корне)    - Временные проверки
   ├── check_feature_count.py
   ├── check_positions_now.py
   └── ... (еще ~10 файлов)

🗑️ analyze_*.py (в корне)  - Временные анализы
```

### ❌ Старые отчеты и логи

```
🗑️ *_REPORT.md файлы       - Старые отчеты о исправлениях
🗑️ *_SUMMARY.md файлы      - Старые сводки
🗑️ *_FIX_*.md файлы        - Документация исправлений
```

### ❌ Дублированные сигнальные процессоры

```
🗑️ trading/signals/signal_processor_old.py  - Старая версия
🗑️ trading/signals/simple_ai_signal_generator.py - Упрощенная версия
```

### ❌ Старые модели

```
🗑️ models/saved/best_model_*.pth  - Старые версии моделей
🗑️ models/saved/data_scaler_backup_*.pkl - Бэкапы скейлеров
```

---

## 📂 СТРУКТУРА ДИРЕКТОРИЙ

### ✅ Активные директории

```
BOT_AI_V3/
├── 🟢 core/               # Ядро системы
├── 🟢 trading/            # Торговая логика
├── 🟢 ml/                 # ML система
├── 🟢 exchanges/          # Интеграция с биржами
├── 🟢 database/           # База данных
├── 🟢 web/                # Веб-интерфейс
├── 🟢 risk_management/    # Управление рисками
├── 🟢 config/             # Конфигурации
├── 🟢 strategies/         # Торговые стратегии
├── 🟡 scripts/            # Вспомогательные скрипты
├── 🟡 tests/              # Тесты
├── 🟡 utils/              # Утилиты
├── 🟡 docs/               # Документация
├── 🟡 alembic/            # Миграции БД
└── 🟡 logs/               # Логи
```

### 🔴 Можно удалить

```
├── 🔴 BOT_AI_V2/          # Старая версия проекта (вложенная!)
├── 🔴 temp/               # Временные файлы
├── 🔴 test_results/       # Старые результаты тестов
├── 🔴 ai_agents/          # Экспериментальные AI агенты (не используются)
├── 🔴 agents/             # Дубликат AI агентов
└── 🔴 examples/           # Примеры (не актуальны)
```

---

## 🎯 РЕКОМЕНДАЦИИ ПО ОЧИСТКЕ

### 1. Срочно удалить (не влияет на работу)

- Все `test_*.py` файлы в корне проекта
- Все `check_*.py` файлы в корне проекта
- Все `analyze_*.py` файлы в корне проекта
- Директорию `BOT_AI_V2/` (старая версия)
- Все `*_backup*.py` файлы

### 2. Переместить в архив

- Старые отчеты `*_REPORT.md`, `*_SUMMARY.md`
- Старые модели из `models/saved/`
- Экспериментальные версии feature_engineering

### 3. Оставить для истории

- `docs/` - документация может пригодиться
- `scripts/` - вспомогательные скрипты полезны
- `tests/` - тесты нужны для CI/CD

---

## 💡 КЛЮЧЕВЫЕ ФАЙЛЫ ДЛЯ РАБОТЫ

### Минимальный набор для запуска

1. `unified_launcher.py` - точка входа
2. `main.py` - основное приложение
3. `config/*.yaml` - конфигурации
4. `.env` - переменные окружения с API ключами
5. `ml/models/saved/best_model.pth` - обученная модель
6. `ml/models/saved/data_scaler.pkl` - скейлер данных

### Команда запуска

```bash
# Полная система с ML
python3 unified_launcher.py --mode=ml

# Только торговля
python3 unified_launcher.py --mode=core

# С веб-интерфейсом
python3 unified_launcher.py
```

---

## 📊 СТАТИСТИКА

- **Активных файлов**: ~350 (52%)
- **Вспомогательных**: ~200 (30%)
- **Дубликатов/мусора**: ~123 (18%)
- **Можно освободить**: ~15-20 MB удалив дубликаты
- **Критически важных файлов**: 47

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

1. **PostgreSQL на порту 5555** - не 5432! Это критично!
2. **feature_engineering_v2.py** - единственная рабочая версия
3. **best_model.pth** - актуальная модель, остальные можно удалить
4. **BOT_AI_V2/** - целая старая версия внутри новой (!)
5. Множество тестовых скриптов в корне создают путаницу
