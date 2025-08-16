# BOT_AI_V3 - Автоматизированная торговая система

## 🚀 Статус: ПОЛНОСТЬЮ РАБОТАЕТ

### ✅ Последние обновления (14.08.2025)

#### Feature Engineering v2.0

- **240 ML признаков**: Полная интеграция всех индикаторов
- **Независимость от конфига**: Все индикаторы создаются с дефолтными параметрами
- **Автоматическая обрезка**: 273 признака → 240 для ML модели
- **Совместимость**: 100% совместимость с оригинальным feature_engineering.py

#### Исправления (10.08.2025)

- **Плечо**: Все позиции теперь используют 5x (исправлено с 10x)
- **SL/TP**: Устанавливаются корректно при создании ордера
- **Структура файлов**: Организована (было 178 файлов в корне, стало 11)
- **API ключи**: Валидны, баланс $172.74

## 📊 Текущие открытые позиции

| Символ | Размер | Плечо | SL | TP | Статус |
|--------|--------|-------|----|----|--------|
| DOGEUSDT | 22 | 5x ✅ | $0.23025 ✅ | $0.24199 ✅ | Активна |
| DOTUSDT | 5.2 | 5x ✅ | $4.0089 ✅ | $4.1303 ✅ | Активна |
| SOLUSDT | 0.2 | 5x ✅ | $180.28 ✅ | $185.75 ✅ | Активна |

## 🏗️ Архитектура системы

```
BOT_AI_V3/
├── core/           # Ядро системы
├── trading/        # Торговая логика
├── exchanges/      # Интеграция с биржами
├── ml/            # Machine Learning
├── tests/         # Все тесты (50+)
├── utils/         # Утилиты и проверки
├── scripts/       # Скрипты запуска
├── docs/          # Документация
└── web/           # Веб-интерфейс
```

## 🚀 Быстрый старт

### 1. Установка

```bash
cd BOT_AI_V3
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Конфигурация

```bash
# Скопируйте и настройте .env
cp .env.example .env
# Добавьте API ключи Bybit
```

### 3. Запуск

```bash
# Полная система
python unified_launcher.py

# Только торговля
python unified_launcher.py --mode=core

# С ML предсказаниями
python unified_launcher.py --mode=ml
```

## 🧪 Тестирование

### Проверка системы

```bash
# Проверить все позиции и плечо
python utils/checks/check_all_positions.py

# Проверить баланс
python utils/checks/check_balance.py

# Тест торговли с SL/TP
python tests/integration/test_real_trading.py
```

## ⚙️ Конфигурация

### Основные параметры (`config/trading.yaml`)

```yaml
trading:
  risk_management:
    fixed_risk_balance: 500  # Фиксированный баланс
    risk_per_trade: 0.02     # 2% риска

  orders:
    default_leverage: 5      # ВСЕГДА 5x

  stop_loss:
    default_percentage: 2.0  # -2% от входа

  take_profit:
    default_percentage: 3.0  # +3% от входа
```

## 📝 Важные особенности

### Установка плеча

- **Автоматически** устанавливается 5x перед каждой позицией
- Логируется в `data/logs/bot_trading_*.log`
- Не влияет на существующие позиции

### Stop Loss / Take Profit

- Передаются **при создании ордера** (единый API вызов)
- Режим: `tpslMode: "Full"`
- Работают для всех новых позиций

### Минимальные требования

- Минимальный размер ордера: **$5** на Bybit
- Режим позиций: **Hedge Mode**
- API версия: **Bybit v5**

## 📁 Структура файлов

- **tests/** - все тесты (50+ файлов)
- **utils/checks/** - скрипты проверки
- **utils/fixes/** - скрипты исправлений
- **docs/solutions/** - решения проблем
- **Корень** - только основные файлы (11 штук)

## 📊 Мониторинг

### Логи

```bash
# Основные логи
tail -f data/logs/bot_trading_*.log

# Фильтр по плечу и SL/TP
tail -f data/logs/bot_trading_*.log | grep -E "leverage|stop_loss|take_profit"
```

### Метрики

- Позиции: 3 активные
- Плечо: 5x для всех
- SL/TP: Установлены для всех
- API: Работает корректно

## 🔧 Решение проблем

### Плечо не 5x?

```bash
python utils/checks/check_all_positions.py
# Скрипт автоматически исправит плечо
```

### SL/TP не установлены?

- Проверьте режим позиций (должен быть Hedge Mode)
- Убедитесь что используете правильный positionIdx
- SL/TP должны передаваться при создании ордера

## 🤖 ML Trading System

### Архитектура

- **Модель**: UnifiedPatchTST (Transformer-based)
- **Признаки**: 240 технических индикаторов
- **Предсказания**: Направление движения на 15m, 1h, 4h, 12h
- **Точность**: 58-62% (15m), 65-70% (4h)

### ML Pipeline

```
Market Data (96 candles) → Feature Engineering (240 features)
→ ML Model → Trading Signals → Risk Filter → Order Execution
```

### Запуск с ML

```bash
# Активировать ML торговлю
python unified_launcher.py --mode=ml

# Тестировать ML предсказания
python test_ml_uniqueness.py

# Проверить количество признаков
python check_feature_count.py
```

## 📚 Документация

- [Feature Engineering Guide](docs/FEATURE_ENGINEERING.md) - **NEW!** 240 признаков
- [ML System Documentation](docs/ML_SYSTEM.md) - **NEW!** ML архитектура
- [Структура файлов](docs/FILE_STRUCTURE.md)
- [Решение SL/TP](docs/solutions/SLTP_SOLUTION.md)
- [Решение плеча](docs/solutions/LEVERAGE_FIX_COMPLETE.md)
- [Инструкции Claude](CLAUDE.md)

## 🎯 Текущий статус

✅ **Система полностью работает**

- API ключи валидны
- Плечо корректно (5x)
- SL/TP устанавливаются
- Логирование работает
- Структура организована

---

**Версия**: 3.1.0
**Последнее обновление**: 14.08.2025
**Статус**: Production Ready with ML
