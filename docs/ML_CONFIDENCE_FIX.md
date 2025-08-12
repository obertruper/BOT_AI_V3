# Исправление проблемы с ML Confidence

## Дата: 11 августа 2025

## Автор: Claude AI Assistant

## Обнаруженная проблема

### Симптомы

1. Все ML сигналы имели confidence ≈ 0.599-0.600 (точно на пороге 0.60)
2. 8 открытых позиций вместо максимальных 5 настроенных
3. Размеры позиций не соответствовали настройкам риск-менеджмента

### Анализ базы данных

```sql
-- Все сигналы PatchTST_RealTime имели confidence около 0.60
SELECT strategy_name, COUNT(*), AVG(confidence), STDDEV(confidence)
FROM signals
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY strategy_name;

-- Результат: PatchTST_RealTime | 20 | 0.5995 | 0.0003
```

## Найденная причина

### Проблемный код в ml_manager.py (строки 505-507, 633-640)

```python
# ПРОБЛЕМА: Использование risk_metrics как confidence_scores
confidence_scores = risk_metrics  # risk_metrics обычно близки к 0

# Применение sigmoid к значениям близким к 0
model_confidence = np.mean(1.0 / (1.0 + np.exp(-confidence_scores)))
# sigmoid(0) = 0.5

# Формула давала фиксированный результат
combined_confidence = signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2
# При signal_strength=0.5: confidence = 0.5*0.4 + 0.5*0.4 + 1.0*0.2 = 0.60
```

### Математический анализ

При risk_metrics ≈ 0 (что обычно и происходит):

- sigmoid(0) = 0.5
- model_confidence ≈ 0.5
- Формула: confidence ≈ signal_strength * 0.4 + 0.4

Результат:

- signal_strength = 0.25 → confidence = 0.50
- signal_strength = 0.50 → confidence = 0.60 ✅ (наш случай)
- signal_strength = 0.75 → confidence = 0.70
- signal_strength = 1.00 → confidence = 0.80

## Примененное решение

### 1. Исправление расчета confidence_scores (строки 506-514)

```python
# ИСПРАВЛЕНИЕ: Используем вероятности направлений как индикатор уверенности
confidence_scores = np.zeros(4)
for i in range(4):
    logits = direction_logits[i * 3 : (i + 1) * 3]
    probs = np.exp(logits) / np.sum(np.exp(logits))
    # Используем максимальную вероятность как уверенность
    confidence_scores[i] = np.max(probs)
```

### 2. Улучшение формулы (строки 639-646)

```python
# confidence_scores уже содержат вероятности (0-1), не нужен sigmoid
model_confidence = float(np.mean(confidence_scores))

# Даем больший вес model_confidence для разнообразия
combined_confidence = (
    signal_strength * 0.3 + model_confidence * 0.5 + (1.0 - avg_risk) * 0.2
)
```

## Результаты исправления

### До исправления

- Confidence: 0.5995 ± 0.0003 (все значения ≈ 0.60)
- 100% значений в пределах ±0.005 от 0.60

### После исправления

- Confidence: 0.6178 ± 0.0091 (диапазон 0.603-0.629)
- Только 28.6% значений в пределах ±0.01 от 0.60
- ✅ Более разнообразные и реалистичные значения

## Дополнительные находки

### 1. Проблемы с конфигурацией

- `max_open_positions: 5` не соблюдается (8 позиций открыто)
- Размеры позиций не соответствуют формуле риск-менеджмента
- Leverage варьируется между 5x и 10x

### 2. Проблемы с данными

- SmartDataManager: ошибки timezone при обновлении свечей
- Дублирование сигналов в БД

## Рекомендации

### Срочные

1. ✅ Исправить расчет confidence (выполнено)
2. ⚠️ Исправить соблюдение max_open_positions
3. ⚠️ Исправить расчет размера позиций
4. ⚠️ Исправить ошибки timezone в SmartDataManager

### Долгосрочные

1. Переобучить модель с правильной интерпретацией выходов
2. Добавить мониторинг распределения confidence
3. Внедрить алерты при аномальных значениях
4. Улучшить логирование ML предсказаний

## Команды для проверки

```bash
# Проверить новые confidence значения
python3 -c "
import asyncio
from sqlalchemy import select, desc
from database.models.signal import Signal
from database.connections import get_async_db
from datetime import datetime, timedelta, timezone

async def check():
    async with get_async_db() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = await db.execute(
            select(Signal)
            .where(Signal.created_at > cutoff)
            .order_by(desc(Signal.created_at))
            .limit(10)
        )
        signals = result.scalars().all()

        for s in signals:
            print(f'{s.symbol}: confidence={s.confidence:.6f}')

asyncio.run(check())
"

# Проверить открытые позиции
python3 check_real_positions.py
```

## Файлы изменены

1. `/ml/ml_manager.py` - строки 506-514, 639-646
2. Создан `/test_confidence_calc.py` - для анализа формулы
3. Создан `/analyze_db_signals.py` - для анализа БД
4. Создан `/docs/ML_CONFIDENCE_FIX.md` - эта документация
