# 🎛️ Руководство по настройке ML системы

## Быстрый старт

Если система генерирует слишком много NEUTRAL сигналов, попробуйте:

1. **Изменить веса таймфреймов** в `ml/ml_manager.py`:

```python
# Текущие (консервативные)
weights = [0.4, 0.3, 0.2, 0.1]

# Более агрессивные для краткосрочной торговли
weights = [0.6, 0.3, 0.1, 0.0]

# Более сбалансированные
weights = [0.3, 0.3, 0.2, 0.2]
```

2. **Настроить пороги сигналов**:

```python
# Текущие пороги
if weighted_direction < 0.5:
    signal = "SHORT"
elif weighted_direction > 1.5:
    signal = "LONG"

# Более чувствительные пороги
if weighted_direction < 0.7:
    signal = "SHORT"
elif weighted_direction > 1.3:
    signal = "LONG"
```

3. **Снизить минимальные требования**:

```python
# В ml_signal_processor.py
min_confidence = 0.35  # Было 0.45
min_signal_strength = 0.15  # Было 0.2
```

## 📊 Анализ текущих предсказаний

### Почему много NEUTRAL сигналов?

1. **Разногласие между таймфреймами**
   - Пример: [0, 0, 2, 1] = SHORT на коротких, LONG на средних
   - Взвешенное среднее = 0.5 → NEUTRAL

2. **Консервативные пороги**
   - Диапазон NEUTRAL: 0.5 - 1.5 (широкий)
   - Большинство взвешенных значений попадают в этот диапазон

3. **Высокие требования к уверенности**
   - min_confidence = 0.45 отсекает слабые сигналы

## 🔧 Детальная настройка

### 1. Настройка для разных стилей торговли

#### Скальпинг (15м - 1ч)

```python
# Максимальный вес на 15м данные
weights = [0.7, 0.2, 0.1, 0.0]
short_threshold = 0.8
long_threshold = 1.2
min_confidence = 0.3
```

#### Дневная торговля (1ч - 4ч)

```python
# Сбалансированные веса
weights = [0.2, 0.4, 0.3, 0.1]
short_threshold = 0.6
long_threshold = 1.4
min_confidence = 0.4
```

#### Свинг торговля (4ч - 12ч)

```python
# Вес на долгосрочные тренды
weights = [0.1, 0.2, 0.4, 0.3]
short_threshold = 0.5
long_threshold = 1.5
min_confidence = 0.5
```

### 2. Настройка Stop Loss и Take Profit

```python
# В ml_manager.py, функция _interpret_predictions

# Консервативные (текущие)
stop_loss_pct = np.clip(abs(min_return) * 100, 1.0, 5.0) / 100.0
take_profit_pct = np.clip(max_return * 100, 2.0, 10.0) / 100.0

# Агрессивные
stop_loss_pct = np.clip(abs(min_return) * 100, 0.5, 3.0) / 100.0
take_profit_pct = np.clip(max_return * 100, 3.0, 15.0) / 100.0

# Адаптивные (на основе волатильности)
volatility = np.std(future_returns)
stop_loss_pct = np.clip(volatility * 2, 1.0, 5.0) / 100.0
take_profit_pct = np.clip(volatility * 4, 2.0, 10.0) / 100.0
```

### 3. Фильтрация по согласованности

```python
# Генерировать сигнал только при высокой согласованности
direction_counts = np.bincount(directions, minlength=3)
max_agreement = direction_counts.max() / len(directions)

if max_agreement < 0.75:  # Требуем 75% согласия
    signal_type = "NEUTRAL"
```

## 📈 Мониторинг эффективности

### Метрики для отслеживания

1. **Распределение сигналов**

   ```sql
   SELECT signal_type, COUNT(*) as count,
          COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
   FROM signals
   WHERE created_at > NOW() - INTERVAL '24 hours'
   GROUP BY signal_type;
   ```

2. **Средняя уверенность по типам**

   ```sql
   SELECT signal_type, AVG(confidence) as avg_confidence
   FROM signals
   WHERE created_at > NOW() - INTERVAL '24 hours'
   GROUP BY signal_type;
   ```

3. **Согласованность предсказаний**

   ```sql
   SELECT
     extra_data->>'predictions' as predictions,
     COUNT(*) as count
   FROM signals
   WHERE created_at > NOW() - INTERVAL '1 hour'
   GROUP BY predictions
   ORDER BY count DESC;
   ```

## 🛠️ Инструменты для тестирования

### 1. Тестирование с разными параметрами

```bash
# Создайте test_ml_params.py
python test_ml_params.py --weights "0.6,0.3,0.1,0.0" --threshold 0.7
```

### 2. Бэктестинг на исторических данных

```bash
# Проверка эффективности настроек
python backtest_ml_settings.py --start "2025-01-01" --end "2025-08-01"
```

### 3. A/B тестирование параметров

```python
# Запуск нескольких конфигураций параллельно
configs = [
    {"weights": [0.4, 0.3, 0.2, 0.1], "threshold": 0.5},
    {"weights": [0.6, 0.3, 0.1, 0.0], "threshold": 0.7},
    {"weights": [0.3, 0.3, 0.2, 0.2], "threshold": 0.6}
]
```

## 💡 Рекомендации

1. **Начните с малых изменений** - меняйте параметры постепенно
2. **Тестируйте на демо** перед применением в продакшене
3. **Мониторьте метрики** - отслеживайте эффективность изменений
4. **Документируйте изменения** - ведите лог настроек и результатов

## 📝 Чек-лист оптимизации

- [ ] Проанализировать текущее распределение сигналов
- [ ] Определить целевой стиль торговли
- [ ] Настроить веса таймфреймов
- [ ] Отрегулировать пороги SHORT/LONG
- [ ] Настроить минимальные требования
- [ ] Протестировать на исторических данных
- [ ] Мониторить результаты 24-48 часов
- [ ] Корректировать при необходимости

---

*См. также: [ML_SIGNAL_EVALUATION_SYSTEM.md](./ML_SIGNAL_EVALUATION_SYSTEM.md)*
