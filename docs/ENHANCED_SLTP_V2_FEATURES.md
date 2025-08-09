# Enhanced SL/TP - Функции из V2

## 📋 Список внедренных функций из BOT_AI_V2

### ✅ 1. Partial Take Profit (Частичное закрытие позиций)

**Описание**: Система поэтапного закрытия позиции при достижении определенных уровней прибыли.

**Реализация**:

- Таблица `partial_tp_history` для отслеживания истории
- Метод `check_partial_tp()` в `enhanced_manager.py`
- Конфигурация через `close_ratio` (0.25 = 25% позиции)
- Автоматическое обновление SL после частичного закрытия

**Пример конфигурации**:

```yaml
partial_take_profit:
  enabled: true
  update_sl_after_partial: true
  levels:
    - percent: 1.0      # При 1% прибыли
      close_ratio: 0.25 # Закрыть 25% позиции
    - percent: 2.0      # При 2% прибыли
      close_ratio: 0.25 # Закрыть еще 25%
    - percent: 3.0      # При 3% прибыли
      close_ratio: 0.50 # Закрыть оставшиеся 50%
```

### ✅ 2. Profit Protection (Защита прибыли)

**Описание**: Многоуровневая система защиты накопленной прибыли.

**Функции**:

- **Breakeven** (безубыток): Перенос SL на уровень входа + offset при достижении целевой прибыли
- **Lock Levels**: Защита определенного процента прибыли на разных уровнях
- Максимальное количество обновлений для предотвращения чрезмерной активности

**Пример конфигурации**:

```yaml
profit_protection:
  enabled: true
  breakeven_percent: 1.0    # Активация безубытка при 1% прибыли
  breakeven_offset: 0.2     # Смещение от цены входа 0.2%
  lock_percent:
    - trigger: 2.0          # При 2% прибыли
      lock: 1.0             # Защитить 1% прибыли
    - trigger: 3.0          # При 3% прибыли
      lock: 2.0             # Защитить 2% прибыли
    - trigger: 4.0          # При 4% прибыли
      lock: 3.0             # Защитить 3% прибыли
  max_updates: 5            # Максимум 5 обновлений
```

### ✅ 3. Enhanced Trailing Stop

**Описание**: Адаптивный трейлинг стоп с учетом рыночных условий.

**Функции**:

- Процентный шаг трейлинга
- Минимальная прибыль для активации
- Максимальное расстояние от текущей цены
- Поддержка различных типов (fixed, percentage, ATR-based, adaptive)

### ✅ 4. База данных для истории

**Таблица `partial_tp_history`**:

```sql
CREATE TABLE partial_tp_history (
    id INTEGER PRIMARY KEY,
    trade_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    percent DECIMAL(10,2) NOT NULL,
    close_ratio DECIMAL(10,4) NOT NULL,
    close_qty DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    order_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### ✅ 5. Интеграция с Trading Engine

**Реализовано**:

- Автоматическая проверка enhanced SL/TP каждые 30 секунд
- Получение текущих цен через exchange API
- Динамическое назначение exchange клиента для каждой позиции
- Логирование всех действий

## 📊 Преимущества системы V2

1. **Гибкость**: Полная настройка через YAML конфигурацию
2. **Масштабируемость**: Поддержка неограниченного количества уровней TP
3. **Безопасность**: Защита прибыли на нескольких уровнях
4. **Прозрачность**: Полная история всех действий в БД
5. **Производительность**: Асинхронная обработка всех операций

## 🚀 Использование

### Тестирование

```bash
python test_enhanced_sltp.py
```

### Боевой режим

Enhanced SL/TP автоматически активируется при запуске системы если в `config/system.yaml`:

```yaml
enhanced_sltp:
  enabled: true
```

### Мониторинг

```sql
-- Просмотр истории partial TP
SELECT * FROM partial_tp_history ORDER BY created_at DESC;

-- Статистика по уровням
SELECT level, COUNT(*) as count, AVG(percent) as avg_percent
FROM partial_tp_history
WHERE status = 'filled'
GROUP BY level;
```

## 📝 Заметки по миграции

1. Все функции V2 успешно интегрированы в V3
2. Добавлена поддержка hedge mode (positionIdx)
3. Улучшена обработка ошибок
4. Оптимизирована производительность для 50+ торговых пар

## ⚠️ Важно

- Убедитесь, что на бирже включен hedge mode если `trading.hedge_mode: true`
- Минимальные размеры ордеров должны соответствовать требованиям биржи
- Регулярно проверяйте логи для отслеживания работы системы
