# 🚀 Enhanced SL/TP - Быстрый старт

## Что сделано

✅ **Интегрированы все функции из V2**:

- Partial Take Profit (частичное закрытие позиций)
- Profit Protection (защита прибыли с breakeven и lock levels)
- Enhanced Trailing Stop
- База данных для истории операций
- Полная интеграция с Trading Engine

## Запуск в продакшене

### 1. Основная система с Enhanced SL/TP

```bash
source venv/bin/activate
python3 unified_launcher.py --mode=ml
```

### 2. Тестирование отдельно

```bash
python3 test_enhanced_sltp.py
```

## Мониторинг работы

### Просмотр логов

```bash
tail -f data/logs/trading.log | grep -E "enhanced|partial|profit|trailing"
```

### Проверка БД

```sql
-- Подключение
psql -p 5555 -U obertruper -d bot_trading_v3

-- История partial TP
SELECT * FROM partial_tp_history ORDER BY created_at DESC LIMIT 10;

-- Статистика
SELECT
    COUNT(*) as total_executions,
    SUM(CASE WHEN status = 'filled' THEN 1 ELSE 0 END) as successful,
    AVG(percent) as avg_profit_percent
FROM partial_tp_history;
```

## Конфигурация

Все настройки в `config/system.yaml` секция `enhanced_sltp`:

```yaml
enhanced_sltp:
  enabled: true  # Включить/выключить
  partial_take_profit:
    levels:      # Настроить уровни закрытия
  profit_protection:
    lock_percent: # Настроить защиту прибыли
```

## Особенности

1. **Автоматическая работа**: После запуска система сама проверяет позиции каждые 30 секунд
2. **Мультибиржевая поддержка**: Работает со всеми подключенными биржами
3. **Hedge mode**: Полная поддержка hedge режима Bybit
4. **Безопасность**: Все операции логируются и сохраняются в БД

## Возможные проблемы

- **"Нет активных позиций"**: Создайте позицию через основную систему или вручную
- **"Условия не выполнены"**: Позиция еще не достигла уровней прибыли для срабатывания
- **Ошибки подключения**: Проверьте API ключи и сетевое соединение

---

🎉 **Enhanced SL/TP из V2 успешно интегрирован в V3!**
