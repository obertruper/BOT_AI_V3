# Решение проблемы установки плеча в BOT_AI_V3

## Проблема

Плечо не устанавливалось перед открытием позиции, что приводило к использованию стандартного плеча биржи вместо настроенного в конфигурации.

## Причина

В отличие от V2, где плечо устанавливалось перед каждой сделкой, в V3 этот шаг был пропущен в `OrderManager`.

## Решение

### Как работало в V2

В файле `/BOT_AI_V2/BOT_Trading/BOT_Trading/api/bybit/bybit_api_client.py`:

```python
def set_leverage(self, leverage=5):
    """
    Устанавливаем плечо для заданного символа.
    Важно: нужно устанавливать и для Buy и для Sell сторон отдельно
    """
    for symbol in self.symbols:
        # Устанавливаем для Buy стороны
        buy_leverage = leverage
        # Устанавливаем для Sell стороны
        sell_leverage = leverage
```

### Исправление в V3

#### 1. Обновлен OrderManager (`trading/orders/order_manager.py`)

Добавлена установка плеча перед созданием ордера:

```python
# ВАЖНО: Устанавливаем плечо перед открытием позиции (как в V2)
try:
    # Получаем плечо из конфигурации
    leverage = float(self.config.get("trading", {}).get("orders", {}).get("default_leverage", 5))

    self.logger.info(f"⚙️ Устанавливаем плечо {leverage}x для {order.symbol}")
    leverage_set = await exchange.set_leverage(order.symbol, leverage)

    if leverage_set:
        self.logger.info(f"✅ Плечо {leverage}x успешно установлено для {order.symbol}")
    else:
        self.logger.warning(f"⚠️ Не удалось установить плечо для {order.symbol}, продолжаем с текущим")
except Exception as e:
    self.logger.warning(f"⚠️ Ошибка установки плеча: {e}, продолжаем с текущим плечом")
```

#### 2. Методы уже существуют в V3

В `exchanges/bybit/client.py`:

```python
async def set_leverage(self, symbol: str, leverage: float) -> bool:
    """Установка плеча для символа"""
    params = {
        "category": self.trading_category,
        "symbol": symbol,
        "buyLeverage": str(leverage),
        "sellLeverage": str(leverage),
    }
    response = await self._make_request(
        "POST", "/v5/position/set-leverage", params, auth=True
    )
```

В `exchanges/bybit/bybit_exchange.py`:

```python
async def set_leverage(self, symbol: str, leverage: float) -> bool:
    """Установка плеча"""
    return await self.client.set_leverage(symbol, leverage)
```

### Конфигурация (`config/trading.yaml`)

```yaml
trading:
  orders:
    default_leverage: 5  # Плечо по умолчанию
    max_leverage: 10     # Максимальное плечо
```

### Особенности Bybit API

1. **Плечо устанавливается для символа**, а не для позиции
2. **Нужно установить для обеих сторон** (Buy и Sell) в hedge mode
3. **Изменения применяются к новым позициям**, не влияют на существующие
4. **Установка плеча - отдельный API вызов** перед созданием ордера

## Последовательность действий при открытии позиции

1. **Подключение к бирже**
2. **Установка плеча** ← НОВЫЙ ШАГ (был пропущен)
3. **Создание ордера с SL/TP**
4. **Отправка на биржу**

## Тестирование

Используйте обновленный тестовый скрипт:

```bash
python test_complete_trading.py
```

Скрипт теперь:

1. Устанавливает плечо перед созданием ордера
2. Логирует успешность установки
3. Продолжает даже если установка не удалась

## Логирование

В логах теперь будет видно:

```
⚙️ Устанавливаем плечо 5x для BTCUSDT
✅ Плечо 5x успешно установлено для BTCUSDT
📤 Отправка ордера на биржу: buy 0.001 BTCUSDT...
```

## Важные замечания

1. **Плечо устанавливается один раз для символа** и сохраняется до следующего изменения
2. **Проверяйте максимальное плечо** для каждого символа (у разных пар разные лимиты)
3. **В hedge mode** плечо применяется к обеим сторонам (Buy и Sell)
4. **Ошибка установки плеча не блокирует создание ордера** - используется текущее плечо

## Проверка текущего плеча

Чтобы проверить установленное плечо:

```python
# Получить информацию о позиции
positions = await exchange.get_positions("BTCUSDT")
for pos in positions:
    print(f"Плечо: {pos.leverage}x")
```

## Статус: ✅ РЕШЕНО

Система теперь корректно устанавливает плечо перед открытием позиций, как это было реализовано в BOT_AI_V2.
