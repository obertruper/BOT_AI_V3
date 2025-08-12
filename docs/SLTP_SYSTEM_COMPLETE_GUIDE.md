# 📖 Полное руководство по системе SL/TP в BOT_AI_V3

## 📋 Оглавление

1. [Обзор системы](#обзор-системы)
2. [Архитектура](#архитектура)
3. [Компоненты системы](#компоненты-системы)
4. [Процесс работы](#процесс-работы)
5. [Конфигурация](#конфигурация)
6. [API интеграция](#api-интеграция)
7. [Решенные проблемы](#решенные-проблемы)
8. [Примеры использования](#примеры-использования)
9. [Отладка и мониторинг](#отладка-и-мониторинг)
10. [FAQ](#faq)

## 🎯 Обзор системы

Система Stop Loss / Take Profit (SL/TP) в BOT_AI_V3 обеспечивает автоматическое управление рисками и фиксацию прибыли для всех торговых позиций.

### Ключевые возможности

- ✅ Автоматическая установка SL/TP сразу после открытия позиции
- ✅ Поддержка hedge и one-way режимов
- ✅ Интеграция с 7+ криптобиржами
- ✅ Расширенные функции: трейлинг-стоп, частичное закрытие
- ✅ Гибкая конфигурация через YAML

## 🏗️ Архитектура

### Основные компоненты

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Signal Source  │────▶│  Trading Engine  │────▶│  Order Manager  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Exchange API  │◀────│  Order Executor  │◀────│ SLTP Integration│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │ Enhanced SLTP    │
                        │    Manager       │
                        └──────────────────┘
```

## 📦 Компоненты системы

### 1. **OrderExecutor** (`/trading/order_executor.py`)

Отвечает за исполнение ордеров и установку SL/TP на бирже.

```python
class OrderExecutor:
    async def execute_order(self, order: Order) -> bool:
        # 1. Отправка ордера на биржу
        exchange_order = await exchange.create_order(**order_params)

        # 2. Установка SL/TP сразу после создания
        if order.stop_loss or order.take_profit:
            await self._set_sltp_for_order(order, exchange)
```

### 2. **EnhancedSLTPManager** (`/trading/sltp/enhanced_manager.py`)

Расширенный менеджер с дополнительными функциями.

```python
class EnhancedSLTPManager:
    # Основные функции
    - create_sltp_orders()      # Создание SL/TP ордеров
    - update_trailing_stop()    # Обновление трейлинг-стопа
    - apply_profit_protection() # Защита прибыли
    - handle_partial_close()    # Частичное закрытие
```

### 3. **SLTPIntegration** (`/trading/orders/sltp_integration.py`)

Интеграционный слой между OrderManager и SLTPManager.

```python
class SLTPIntegration:
    async def handle_filled_order(self, order: Order, exchange) -> bool:
        # Создание SL/TP для исполненного ордера
        return await self.create_sltp_for_order(order, exchange)
```

## 🔄 Процесс работы

### 1. Создание сигнала

```python
signal = Signal(
    symbol="BTCUSDT",
    signal_type=SignalType.LONG,
    entry_price=50000,
    stop_loss=48500,    # -3%
    take_profit=52500   # +5%
)
```

### 2. Создание ордера

```python
# Trading Engine обрабатывает сигнал
order = await order_manager.create_order_from_signal(signal)
```

### 3. Исполнение ордера

```python
# OrderExecutor отправляет на биржу
success = await order_executor.execute_order(order)
```

### 4. Установка SL/TP

```python
# Автоматически после создания ордера
async def _set_sltp_for_order(self, order: Order, exchange):
    params = {
        "category": "linear",
        "symbol": order.symbol,
        "tpslMode": "Full",
        "positionIdx": position_idx,
        "stopLoss": str(order.stop_loss),
        "takeProfit": str(order.take_profit)
    }

    response = await client._make_request(
        "POST", "/v5/position/trading-stop", params, auth=True
    )
```

## ⚙️ Конфигурация

### `/config/system.yaml`

```yaml
trading:
  hedge_mode: true              # Режим хеджирования
  min_order_value_usdt: 5.0     # Минимальный размер ордера

  # Размеры позиций по умолчанию
  default_position_sizes:
    BTCUSDT: 0.001    # ~$50 при цене $50k
    ETHUSDT: 0.02     # ~$50 при цене $2.5k
    SOLUSDT: 0.25     # ~$50 при цене $200

  # Настройки SL/TP по умолчанию
  default_sltp:
    stop_loss_percent: 2.0      # 2% стоп-лосс
    take_profit_percent: 3.0    # 3% тейк-профит
```

### `/config/sltp/enhanced.yaml`

```yaml
sltp:
  # Базовые настройки
  enabled: true
  mode: aggressive  # conservative, moderate, aggressive

  # Трейлинг-стоп
  trailing_stop:
    enabled: true
    activation_profit: 1.5    # Активация при 1.5% прибыли
    trailing_distance: 0.5    # Отступ 0.5%

  # Защита прибыли
  profit_protection:
    enabled: true
    breakeven_at: 1.0         # Безубыток при 1% прибыли
    lock_profit_levels:
      - trigger: 2.0          # При 2% прибыли
        lock: 1.0             # Защитить 1%
      - trigger: 5.0          # При 5% прибыли
        lock: 3.0             # Защитить 3%

  # Частичное закрытие
  partial_close:
    enabled: true
    levels:
      - profit: 2.0           # При 2% прибыли
        close: 25             # Закрыть 25%
      - profit: 5.0           # При 5% прибыли
        close: 50             # Закрыть еще 50%
```

## 🔌 API интеграция

### Bybit API v5

```python
# Endpoint для установки SL/TP
POST /v5/position/trading-stop

# Параметры
{
    "category": "linear",      # Тип продукта
    "symbol": "BTCUSDT",      # Торговая пара
    "tpslMode": "Full",       # Режим SL/TP (Full/Partial)
    "positionIdx": 0,         # 0: one-way, 1: hedge-buy, 2: hedge-sell
    "stopLoss": "48500",      # Цена стоп-лосса
    "takeProfit": "52500"     # Цена тейк-профита
}
```

### Position Index в разных режимах

- **One-way mode**: `positionIdx = 0`
- **Hedge mode**:
  - BUY/LONG: `positionIdx = 1`
  - SELL/SHORT: `positionIdx = 2`

## 🐛 Решенные проблемы

### 1. Ошибка enum в базе данных

**Проблема**: `invalid input value for enum signaltype: 'long'`

**Решение**: Преобразование в uppercase перед сохранением

```python
# /trading/engine.py:501
"signal_type": signal.signal_type.value.upper()
```

### 2. Минимальный размер ордера

**Проблема**: `Order does not meet minimum order value 5USDT`

**Решение**: Автоматическая корректировка размера

```python
# /trading/engine.py:1089
min_order_value_usdt = Decimal(str(
    self.config.get("trading", {}).get("min_order_value_usdt", 5.0)
))

if position_value_usdt < min_order_value_usdt:
    min_quantity = min_order_value_usdt / current_price
    adjusted_quantity = min_quantity * Decimal("1.1")  # +10% запас
```

### 3. SL/TP не устанавливались на бирже

**Проблема**: SL/TP сохранялись в БД, но не отправлялись на биржу

**Решение**: Добавлен вызов после создания ордера

```python
# /trading/order_executor.py:111
if order.stop_loss or order.take_profit:
    await self._set_sltp_for_order(order, exchange)
```

## 📝 Примеры использования

### 1. Создание сигнала с SL/TP

```python
from database.models.signal import Signal, SignalType

signal = Signal(
    symbol="ETHUSDT",
    signal_type=SignalType.LONG,
    entry_price=2500.0,
    stop_loss=2450.0,     # -2%
    take_profit=2575.0,   # +3%
    source="ml_strategy",
    metadata={
        "confidence": 0.85,
        "ml_score": 0.92
    }
)

# Эмитировать сигнал
await signal_generator.emit_signal(signal)
```

### 2. Ручная установка SL/TP

```python
# Скрипт set_sltp_on_exchange.py
exchange = await factory.create_and_connect("bybit")
positions = await exchange.get_positions()

for pos in positions:
    if pos.side.upper() == "BUY":
        sl_price = float(pos.entry_price) * 0.98  # -2%
        tp_price = float(pos.entry_price) * 1.03  # +3%
    else:
        sl_price = float(pos.entry_price) * 1.02  # +2%
        tp_price = float(pos.entry_price) * 0.97  # -3%

    # Установка через API
    params = {
        "category": "linear",
        "symbol": pos.symbol,
        "tpslMode": "Full",
        "stopLoss": str(sl_price),
        "takeProfit": str(tp_price),
        "positionIdx": position_idx
    }

    response = await client._make_request(
        "POST", "/v5/position/trading-stop", params, auth=True
    )
```

### 3. Проверка активных SL/TP

```python
# Проверка в базе данных
orders = await AsyncPGPool.fetch("""
    SELECT id, symbol, side, stop_loss, take_profit, status
    FROM orders
    WHERE status = 'OPEN'
    AND stop_loss IS NOT NULL
    ORDER BY created_at DESC
""")

# Проверка на бирже
positions = await exchange.get_positions()
for pos in positions:
    print(f"{pos.symbol}: SL={pos.stop_loss}, TP={pos.take_profit}")
```

## 🔍 Отладка и мониторинг

### 1. Логирование

```bash
# Мониторинг SL/TP операций
tail -f ./data/logs/bot_trading_*.log | grep -E "set_sltp_for_order|SL/TP"

# Проверка ошибок
grep -E "ERROR.*sltp|ERROR.*stop.*loss" ./data/logs/bot_trading_*.log
```

### 2. База данных

```sql
-- Проверка ордеров с SL/TP
SELECT
    id,
    symbol,
    side,
    quantity,
    stop_loss,
    take_profit,
    status,
    created_at
FROM orders
WHERE stop_loss IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;

-- Статистика по SL/TP
SELECT
    COUNT(*) as total_orders,
    COUNT(stop_loss) as with_sl,
    COUNT(take_profit) as with_tp,
    AVG(CASE
        WHEN side = 'BUY' THEN (entry_price - stop_loss) / entry_price * 100
        ELSE (stop_loss - entry_price) / entry_price * 100
    END) as avg_sl_percent
FROM orders
WHERE created_at > NOW() - INTERVAL '24 hours';
```

### 3. Мониторинг в реальном времени

```python
# Скрипт monitor_sltp.py
async def monitor_sltp():
    while True:
        positions = await exchange.get_positions()

        for pos in positions:
            if pos.size > 0:
                print(f"\n{datetime.now()}")
                print(f"Symbol: {pos.symbol}")
                print(f"Side: {pos.side}")
                print(f"Entry: {pos.entry_price}")
                print(f"Current: {pos.mark_price}")
                print(f"SL: {pos.stop_loss or 'NOT SET'}")
                print(f"TP: {pos.take_profit or 'NOT SET'}")
                print(f"PnL: {pos.unrealized_pnl}")

        await asyncio.sleep(30)  # Проверка каждые 30 секунд
```

## ❓ FAQ

### Q: Почему SL/TP не устанавливаются?

**A**: Проверьте:

1. API ключи в `.env` файле
2. Режим позиций (hedge/one-way) в конфигурации
3. Минимальный размер ордера ($5 для Bybit)
4. Логи на наличие ошибок API

### Q: Как изменить процент SL/TP по умолчанию?

**A**: Отредактируйте `/config/system.yaml`:

```yaml
trading:
  default_sltp:
    stop_loss_percent: 3.0    # Изменить на 3%
    take_profit_percent: 5.0  # Изменить на 5%
```

### Q: Как отключить автоматическую установку SL/TP?

**A**: В `/config/sltp/enhanced.yaml`:

```yaml
sltp:
  enabled: false  # Отключить всю систему SL/TP
```

### Q: Поддерживаются ли другие биржи кроме Bybit?

**A**: Да, система поддерживает:

- Binance
- OKX
- Bitget
- KuCoin
- Gate.io
- MEXC

Каждая биржа имеет свои особенности API для SL/TP.

### Q: Как работает трейлинг-стоп?

**A**: Трейлинг-стоп автоматически следует за ценой:

1. Активируется при достижении заданной прибыли (например, 1.5%)
2. Поддерживает фиксированное расстояние от максимальной цены
3. Двигается только в сторону прибыли, никогда против

### Q: Можно ли использовать разные SL/TP для разных пар?

**A**: Да, через стратегии или прямое указание в сигнале:

```python
# В стратегии
if symbol == "BTCUSDT":
    sl_percent = 1.5  # Меньший риск для BTC
elif symbol in ["DOGEUSDT", "SHIBUSDT"]:
    sl_percent = 5.0  # Больший риск для мем-коинов
```

## 📚 Дополнительные ресурсы

- [Bybit API Documentation](https://bybit-exchange.github.io/docs/v5/position/trading-stop)
- [Risk Management Best Practices](./RISK_MANAGEMENT_GUIDE.md)
- [Trading Strategy Development](./STRATEGY_DEVELOPMENT.md)
- [System Architecture Overview](./ARCHITECTURE.md)

---

**Версия документа**: 1.0
**Последнее обновление**: 10.08.2025
**Автор**: Claude AI
