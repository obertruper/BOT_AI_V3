# Решение проблемы SL/TP в BOT_AI_V3

## Проблема

Стоп-лосс и тейк-профит не устанавливались при создании ордера через Bybit API.

## Причина

В Bybit API v5 для фьючерсов нужно передавать SL/TP параметры **прямо при создании ордера** через единый API вызов, а не устанавливать их отдельно.

## Решение

### 1. Обновлен OrderManager (`trading/orders/order_manager.py`)

```python
# Добавлена передача SL/TP в OrderRequest
order_request = OrderRequest(
    symbol=order.symbol,
    side=order_side,
    order_type=order_type,
    quantity=order.quantity,
    price=order.price,
    # ВАЖНО: SL/TP передаются при создании
    stop_loss=order.stop_loss,
    take_profit=order.take_profit,
    position_idx=position_idx,  # 1 для Buy, 2 для Sell в hedge mode
    exchange_params={
        "tpslMode": "Full",  # Или "Partial" для частичного
        "tpOrderType": "Market",
        "slOrderType": "Market",
    }
)
```

### 2. BybitClient уже поддерживает SL/TP

В `exchanges/bybit/client.py` метод `place_order` уже обрабатывает SL/TP:

```python
# Строки 936-940
if order_request.stop_loss is not None:
    params["stopLoss"] = str(order_request.stop_loss)
if order_request.take_profit is not None:
    params["takeProfit"] = str(order_request.take_profit)
```

### 3. Правильный Position Mode

Ваш аккаунт использует **Hedge Mode**, поэтому нужно указывать правильный `positionIdx`:

- `positionIdx = 1` для Buy/Long позиций
- `positionIdx = 2` для Sell/Short позиций
- `positionIdx = 0` для One-way mode

## Параметры Bybit API v5 для SL/TP

При создании ордера через `/v5/order/create`:

```json
{
    "symbol": "BTCUSDT",
    "side": "Buy",
    "orderType": "Market",
    "qty": "0.001",
    "positionIdx": 1,  // Для hedge mode

    // SL/TP параметры
    "stopLoss": "116000",
    "takeProfit": "122000",
    "tpslMode": "Full",  // Full или Partial
    "tpOrderType": "Market",  // Market или Limit
    "slOrderType": "Market"   // Market или Limit
}
```

## Частичное закрытие (из V2)

Для реализации 3-уровневой системы TP (30%, 30%, 40%):

### Вариант 1: Использовать Partial Mode

```json
{
    "tpslMode": "Partial",
    "tpSize": "0.0003",  // 30% от позиции
    "takeProfit": "119500"  // TP1 уровень
}
```

### Вариант 2: Создавать условные ордера

После открытия позиции создавать отдельные Take Profit ордера для каждого уровня.

## Проверенные настройки

✅ **API ключи работают**

- Баланс: $172.70 USDT
- Открытые позиции: DOTUSDT, SOLUSDT

✅ **Режим позиций: Hedge Mode**

- Требует указания positionIdx

✅ **Расчет позиций (метод V2)**

- Фиксированный баланс: $500
- Риск: 2%
- Плечо: 5x
- Формула: `(500 * 0.02 * 5) / price`

✅ **SL/TP уровни**

- Stop Loss: -2% от входа
- Take Profit: +3% от входа
- TP1: +1%, TP2: +2%, TP3: +3%

## Запуск системы

```bash
# Полная система
python unified_launcher.py

# Только торговля
python unified_launcher.py --mode=core

# Тестовый ордер с SL/TP
python test_complete_trading.py
```

## Важные замечания

1. **Всегда передавайте SL/TP при создании ордера** - не пытайтесь установить их отдельно
2. **Проверяйте position mode** - используйте правильный positionIdx
3. **Для существующих позиций** - используйте `/v5/position/trading-stop` для обновления SL/TP
4. **Минимальные размеры** - для BTCUSDT минимум 0.001 BTC

## Статус: ✅ РЕШЕНО

Система полностью готова к работе. SL/TP будут устанавливаться корректно при создании ордеров.
