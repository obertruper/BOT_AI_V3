# 📁 Структура файлов BOT_AI_V3

## Организация выполнена 10.08.2025

### До организации

- **178 Python файлов** в корневой директории
- Множество тестов, утилит и скриптов вперемешку
- Сложно найти нужный файл

### После организации

- **11 основных файлов** в корне
- Четкая структура каталогов
- Легкая навигация

## 📂 Новая структура

```
BOT_AI_V3/
│
├── 📁 core/                    # Ядро системы
│   ├── config/                 # Конфигурация
│   ├── logging/                # Логирование
│   └── system/                 # Системные компоненты
│
├── 📁 trading/                 # Торговая логика
│   ├── engine.py              # Торговый движок
│   ├── orders/                # Управление ордерами
│   ├── signals/               # Обработка сигналов
│   └── sltp/                  # Stop Loss / Take Profit
│
├── 📁 exchanges/               # Интеграция с биржами
│   ├── bybit/                 # Bybit API
│   ├── binance/               # Binance API
│   └── base/                  # Базовые классы
│
├── 📁 ml/                      # Machine Learning
│   ├── models/                # ML модели
│   ├── logic/                 # ML логика
│   └── preprocessing/         # Подготовка данных
│
├── 📁 tests/                   # ВСЕ ТЕСТЫ
│   ├── integration/           # Интеграционные тесты
│   │   ├── test_complete_trading.py
│   │   ├── test_real_trading.py
│   │   └── test_*.py          # 50+ тестов
│   ├── unit/                  # Юнит тесты
│   └── scripts/               # Тестовые скрипты
│       ├── force_long_signal.py
│       ├── debug_*.py
│       └── analyze_*.py
│
├── 📁 utils/                   # Утилиты
│   ├── checks/                # Проверочные скрипты
│   │   ├── check_all_positions.py
│   │   ├── check_balance.py
│   │   └── check_*.py
│   ├── fixes/                 # Скрипты исправлений
│   │   ├── fix_solana_sltp.py
│   │   └── fix_*.py
│   └── *.py                   # Общие утилиты
│
├── 📁 scripts/                 # Скрипты
│   ├── deployment/            # Развертывание
│   │   ├── start_trading_bot.sh
│   │   ├── stop_all.sh
│   │   └── start_*.sh
│   └── monitoring/            # Мониторинг
│       └── monitor_*.py
│
├── 📁 docs/                    # Документация
│   ├── solutions/             # Решения проблем
│   │   ├── SLTP_SOLUTION.md
│   │   ├── LEVERAGE_SOLUTION.md
│   │   └── *_SOLUTION.md
│   ├── FILE_STRUCTURE.md      # Этот файл
│   └── README.md              # Основная документация
│
├── 📁 config/                  # Конфигурации
│   ├── trading.yaml           # Торговые настройки
│   ├── ml/                    # ML конфигурации
│   └── system.yaml            # Системные настройки
│
├── 📁 data/                    # Данные
│   ├── logs/                  # Логи
│   ├── cache/                 # Кэш
│   └── models/                # Сохраненные модели
│
└── 📁 web/                     # Веб-интерфейс
    ├── frontend/              # React приложение
    └── backend/               # FastAPI сервер
```

## 🚀 Основные файлы в корне (только необходимые)

| Файл | Назначение |
|------|------------|
| `main.py` | Главная точка входа системы |
| `unified_launcher.py` | Унифицированный запуск всех компонентов |
| `integrated_start.py` | Интегрированный старт |
| `interactive_trading.py` | Интерактивная торговля |
| `.env` | Переменные окружения |
| `requirements.txt` | Зависимости Python |
| `pyproject.toml` | Конфигурация проекта |
| `CLAUDE.md` | Инструкции для Claude |
| `README.md` | Документация проекта |

## 📋 Быстрый доступ к важным файлам

### Тестирование торговли

```bash
# Полный тест с SL/TP
python tests/integration/test_complete_trading.py

# Реальная торговля
python tests/integration/test_real_trading.py

# Проверка позиций
python utils/checks/check_all_positions.py
```

### Запуск системы

```bash
# Основной запуск
python unified_launcher.py

# Только торговля
python unified_launcher.py --mode=core

# С ML
python unified_launcher.py --mode=ml
```

### Мониторинг

```bash
# Проверка баланса
python utils/checks/check_balance.py

# Проверка позиций
python utils/checks/check_positions_and_orders.py

# Логи
tail -f data/logs/bot_trading_*.log
```

## 🗑️ Что было удалено

- Временные файлы (*.log,*.tmp, *.bak)
- Дубликаты тестов
- Неиспользуемые скрипты
- Старые версии файлов

## ✅ Преимущества новой структуры

1. **Четкая организация** - каждый файл на своем месте
2. **Легкая навигация** - понятная иерархия каталогов
3. **Быстрый поиск** - тесты в tests/, утилиты в utils/
4. **Чистый корень** - только основные файлы
5. **Масштабируемость** - легко добавлять новые модули

## 📝 Правила для будущей разработки

1. **Тесты** → всегда в `tests/`
2. **Утилиты проверки** → в `utils/checks/`
3. **Скрипты исправлений** → в `utils/fixes/`
4. **Документация решений** → в `docs/solutions/`
5. **Скрипты запуска** → в `scripts/deployment/`
6. **НЕ создавать файлы в корне** без крайней необходимости

## 🔄 Миграция

Если нужен старый файл:

1. Проверьте в соответствующем каталоге
2. Используйте: `find . -name "имя_файла.py"`
3. Симлинки созданы для критичных файлов

---

**Дата организации**: 10.08.2025
**Файлов до**: 178
**Файлов после**: 11
**Статус**: ✅ ЗАВЕРШЕНО
