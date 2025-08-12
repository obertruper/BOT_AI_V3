# 🔧 Руководство по устранению неполадок SL/TP

## 🚨 Частые проблемы и решения

### 1. SL/TP не устанавливаются на бирже

#### Симптомы

- В логах есть создание ордера, но нет вызова `set_sltp_for_order`
- В БД есть значения stop_loss/take_profit, но на бирже их нет
- Позиции открыты без защитных ордеров

#### Проверка

```bash
# Проверить логи
grep -E "set_sltp_for_order|Устанавливаем SL/TP" ./data/logs/bot_trading_*.log | tail -20

# Проверить позиции на бирже
python3 check_positions_and_sltp.py
```

#### Решения

1. **Убедитесь, что используется обновленный OrderExecutor**:

   ```bash
   grep -n "_set_sltp_for_order" /trading/order_executor.py
   # Должно показать метод на строке ~193
   ```

2. **Проверьте вызов после создания ордера**:

   ```python
   # /trading/order_executor.py:111-115
   if order.stop_loss or order.take_profit:
       try:
           await self._set_sltp_for_order(order, exchange)
       except Exception as e:
           logger.error(f"Ошибка установки SL/TP: {e}")
   ```

3. **Перезапустите систему**:

   ```bash
   pkill -f "python.*unified_launcher"
   python3 unified_launcher.py --mode=ml
   ```

### 2. Ошибка API: "Invalid API key"

#### Симптомы

```
APIError: API error in bybit.POST /v5/position/trading-stop (Code: 10003): API key is invalid
```

#### Решения

1. **Проверьте .env файл**:

   ```bash
   cat .env | grep BYBIT
   # Должны быть:
   # BYBIT_API_KEY=ваш_ключ
   # BYBIT_API_SECRET=ваш_секрет
   ```

2. **Проверьте права API ключа на Bybit**:
   - Зайдите на bybit.com → API Management
   - Убедитесь, что включены: Spot&Margin Trading, Derivatives Trading
   - Проверьте IP whitelist (если включен)

3. **Проверьте загрузку переменных**:

   ```python
   python3 -c "
   import os
   from dotenv import load_dotenv
   load_dotenv()
   print(f'API Key: {os.getenv(\"BYBIT_API_KEY\", \"NOT_FOUND\")[:10]}...')
   print(f'Secret: {\"***\" if os.getenv(\"BYBIT_API_SECRET\") else \"NOT_FOUND\"}')
   "
   ```

### 3. Ошибка: "Position not found"

#### Симптомы

```
Failed to set stop loss: Position not found
```

#### Причины

- Попытка установить SL/TP до того, как позиция появилась на бирже
- Неправильный symbol или positionIdx

#### Решения

1. **Добавьте задержку перед установкой SL/TP**:

   ```python
   # В _set_sltp_for_order добавить:
   await asyncio.sleep(1)  # Ждем 1 секунду
   ```

2. **Проверьте правильность positionIdx**:

   ```python
   # One-way mode
   position_idx = 0

   # Hedge mode
   if hedge_mode:
       position_idx = 1 if order.side.value.upper() == "BUY" else 2
   ```

### 4. Ошибка: "Order does not meet minimum order value"

#### Симптомы

```
Order does not meet minimum order value 5USDT
```

#### Решения

1. **Проверьте конфигурацию**:

   ```yaml
   # /config/system.yaml
   trading:
     min_order_value_usdt: 5.0
     default_position_sizes:
       BTCUSDT: 0.001   # Должно быть > $5
       ETHUSDT: 0.002   # При текущей цене
   ```

2. **Проверьте расчет в коде**:

   ```python
   # Должна быть автокоррекция размера
   if position_value_usdt < min_order_value_usdt:
       min_quantity = min_order_value_usdt / current_price
       adjusted_quantity = min_quantity * Decimal("1.1")
   ```

### 5. Неправильный режим позиций

#### Симптомы

```
position idx not match position mode
```

#### Решения

1. **Проверьте режим в конфигурации**:

   ```yaml
   # /config/system.yaml
   trading:
     hedge_mode: true  # или false для one-way
   ```

2. **Проверьте режим на бирже**:
   - Зайдите в настройки Bybit
   - Preferences → Position Mode
   - Должен соответствовать конфигурации

3. **Синхронизируйте режим**:

   ```python
   # Скрипт для переключения режима
   await exchange.set_position_mode("BTCUSDT", hedge_mode=True)
   ```

## 🛠️ Инструменты диагностики

### 1. Скрипт проверки SL/TP

```python
# check_sltp_status.py
import asyncio
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

async def check_sltp():
    # 1. Проверка конфигурации
    print("1. Checking configuration...")
    # ... код проверки ...

    # 2. Проверка API подключения
    print("2. Checking API connection...")
    # ... код проверки ...

    # 3. Проверка активных позиций
    print("3. Checking active positions...")
    # ... код проверки ...

    # 4. Проверка SL/TP на позициях
    print("4. Checking SL/TP on positions...")
    # ... код проверки ...

asyncio.run(check_sltp())
```

### 2. Мониторинг в реальном времени

```bash
# monitor_sltp.sh
#!/bin/bash

echo "Monitoring SL/TP operations..."

# Следим за логами
tail -f ./data/logs/bot_trading_*.log | grep --line-buffered -E "set_sltp|stop.*loss|take.*profit" | while read line
do
    echo "[$(date '+%H:%M:%S')] $line"

    # Если есть ошибка, выделяем красным
    if echo "$line" | grep -q "ERROR"; then
        echo -e "\033[31m>>> ERROR DETECTED <<<\033[0m"
    fi
done
```

### 3. SQL запросы для анализа

```sql
-- Проверка ордеров без SL/TP
SELECT
    id, symbol, side, quantity, status,
    CASE
        WHEN stop_loss IS NULL THEN 'NO SL'
        ELSE 'HAS SL'
    END as sl_status,
    CASE
        WHEN take_profit IS NULL THEN 'NO TP'
        ELSE 'HAS TP'
    END as tp_status,
    created_at
FROM orders
WHERE status IN ('OPEN', 'PARTIALLY_FILLED')
AND (stop_loss IS NULL OR take_profit IS NULL)
ORDER BY created_at DESC;

-- Анализ успешности SL/TP
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_orders,
    COUNT(stop_loss) as orders_with_sl,
    COUNT(take_profit) as orders_with_tp,
    ROUND(COUNT(stop_loss)::numeric / COUNT(*) * 100, 2) as sl_coverage_percent
FROM orders
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## 📊 Чек-лист проверки

### Перед запуском

- [ ] Проверены API ключи в .env
- [ ] Загружена последняя версия кода
- [ ] Проверена конфигурация hedge_mode
- [ ] Установлены правильные размеры позиций

### После запуска

- [ ] Проверить логи на ошибки
- [ ] Проверить создание ордеров в БД
- [ ] Проверить вызовы set_sltp_for_order
- [ ] Проверить позиции на бирже

### При проблемах

- [ ] Собрать логи за последний час
- [ ] Проверить статус API подключения
- [ ] Запустить диагностические скрипты
- [ ] Проверить изменения в коде

## 🆘 Экстренные действия

### Если SL/TP не работают в продакшене

1. **Немедленно установите SL/TP вручную**:

   ```bash
   python3 set_sltp_on_exchange.py
   ```

2. **Переключитесь на безопасный режим**:

   ```yaml
   # /config/system.yaml
   trading:
     safe_mode: true  # Останавливает новые сделки
   ```

3. **Проверьте все открытые позиции**:

   ```bash
   python3 emergency_check_positions.py
   ```

4. **Откатитесь на предыдущую версию** (если нужно):

   ```bash
   git checkout HEAD~1
   python3 unified_launcher.py --mode=ml
   ```

## 📞 Контакты поддержки

- **Bybit API Support**: <https://www.bybit.com/en-US/help-center>
- **GitHub Issues**: <https://github.com/your-repo/issues>
- **Telegram**: @your_support_bot

---

**Последнее обновление**: 10.08.2025
