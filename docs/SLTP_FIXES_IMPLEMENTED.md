# 📚 Исправления SL/TP системы BOT_AI_V3

## 🎯 Выполненные задачи (10.08.2025)

### 1. ✅ Исправлена ошибка enum в базе данных

**Проблема**: `invalid input value for enum signaltype: 'long'` - база данных ожидает uppercase значения

**Решение**:

- Файл: `/trading/engine.py:501`
- Добавлено преобразование signal_type в uppercase перед сохранением в БД:

```python
"signal_type": (
    signal.signal_type.value.upper()
    if hasattr(signal.signal_type, "value")
    else str(signal.signal_type).upper()
),
```

### 2. ✅ Исправлена ошибка минимального размера ордера

**Проблема**: `Order does not meet minimum order value 5USDT` - Bybit требует минимум $5 на ордер

**Решение**:

- Файл: `/config/system.yaml`
  - Добавлен параметр `min_order_value_usdt: 5.0`
  - Обновлены размеры позиций по умолчанию для всех пар

- Файл: `/trading/engine.py:1089-1135`
  - Добавлена проверка минимального объема ордера
  - Автоматический пересчет количества для соответствия минимуму

### 3. ✅ Реализована установка SL/TP на бирже после создания ордера

**Проблема**: SL/TP сохранялись в БД, но не устанавливались на бирже Bybit

**Решение**:

- Файл: `/trading/order_executor.py`
  - Добавлен вызов `_set_sltp_for_order()` после успешного создания ордера (строка 113)
  - Реализован метод `_set_sltp_for_order()` (строки 193-241):
    - Автоматическое определение hedge/one-way режима
    - Прямой API вызов к Bybit `/v5/position/trading-stop`
    - Обработка ошибок и логирование

## 📋 Технические детали

### Параметры API Bybit для SL/TP

```python
params = {
    "category": "linear",
    "symbol": order.symbol,
    "tpslMode": "Full",  # Полное закрытие позиции
    "positionIdx": position_idx,  # 0 для one-way, 1/2 для hedge
    "stopLoss": str(order.stop_loss),
    "takeProfit": str(order.take_profit)
}
```

### Определение position index

- One-way mode: `positionIdx = 0`
- Hedge mode:
  - BUY/LONG: `positionIdx = 1`
  - SELL/SHORT: `positionIdx = 2`

## 🔍 Проверка работы

### 1. Создание тестового скрипта

- Файл: `/set_sltp_on_exchange.py`
- Проверяет активные позиции и устанавливает SL/TP напрямую через API

### 2. Проверка в базе данных

```sql
SELECT id, symbol, side, quantity, status, stop_loss, take_profit, created_at
FROM orders
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

### 3. Мониторинг логов

```bash
grep -E "set_sltp_for_order|Устанавливаем SL/TP|set_trading_stop" ./data/logs/bot_trading_*.log
```

## ⚠️ Важные моменты

1. **API аутентификация**: Требуются валидные API ключи Bybit в `.env`:

   ```
   BYBIT_API_KEY=ваш_ключ
   BYBIT_API_SECRET=ваш_секрет
   ```

2. **Режим позиций**: Система автоматически определяет hedge/one-way режим из конфигурации

3. **Минимальные размеры**: Все ордера автоматически корректируются для соответствия минимуму $5

## 🚀 Результат

После внедрения исправлений:

- ✅ Ордера успешно создаются с правильными enum значениями
- ✅ Размеры позиций соответствуют минимальным требованиям биржи
- ✅ SL/TP автоматически устанавливаются на бирже сразу после создания ордера
- ✅ Система работает как в hedge, так и в one-way режиме

## 📝 Сравнение с BOT_AI_V2

В версии V2 использовался метод `set_trading_stop()` из модуля `api.client`.
В V3 реализован аналогичный функционал напрямую через API клиент биржи с учетом новой архитектуры.

---

**Автор исправлений**: Claude AI
**Дата**: 10.08.2025
