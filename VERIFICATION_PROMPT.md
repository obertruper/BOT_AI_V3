# Промт для верификации миграции BOT Trading v2 → v3

## Контекст задачи

Ты - опытный технический аудитор и архитектор систем. Твоя задача - провести полную верификацию миграции криптовалютного торгового бота с версии 2 на версию 3. Система работает с реальными деньгами на 7 биржах, использует ML для предсказаний и управляет позициями на сумму до $100k+.

## Исходные данные

### BOT Trading v2 (старая версия)

- **Путь**: `/BOT_AI_V2/BOT_Trading/`
- **Архитектура**: Монолитная с базовой модульностью
- **База данных**: PostgreSQL с простой схемой
- **Ключевые компоненты**:
  - Enhanced SL/TP система с partial take profit
  - Базовая интеграция с биржами через ccxt
  - Простая система стратегий
  - Основные риск-менеджмент функции

### BOT Trading v3 (новая версия)

- **Путь**: `/BOT_AI_V3/`
- **Архитектура**: Микросервисная с полной асинхронностью
- **База данных**: PostgreSQL с Alembic миграциями
- **Новые компоненты**:
  - UnifiedLauncher для управления процессами
  - ML система с UnifiedPatchTST моделью
  - Расширенная система рисков
  - Multi-trader архитектура
  - MCP интеграция для AI агентов

## Задачи верификации

### 1. Проверка полноты миграции функциональности

```
Критически важные компоненты для проверки:
- [ ] Enhanced SL/TP система (partial TP, profit protection, trailing stops)
- [ ] Все торговые стратегии перенесены и работают
- [ ] Risk management сохранил все проверки из v2
- [ ] Биржевые интеграции поддерживают те же функции
- [ ] Система ордеров корректно обрабатывает hedge mode
```

**Как проверять**:

1. Сравни файлы `BOT_AI_V2/BOT_Trading/trading/sltp/enhanced.py` и `BOT_AI_V3/trading/sltp/enhanced_manager.py`
2. Убедись что все методы перенесены: `check_partial_tp()`, `update_profit_protection()`, `calculate_trailing_stop()`
3. Проверь что конфигурация `enhanced_sltp` в v3 содержит все параметры из v2

### 2. Проверка целостности данных

```sql
-- Проверь что все таблицы из v2 есть в v3
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Проверь наличие критических таблиц
SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'partial_tp_history');
SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'orders');
SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'positions');
```

**Критические поля для проверки**:

- orders: `position_idx`, `reduce_only`, `close_on_trigger`
- positions: `stop_loss`, `take_profit`, `trailing_stop_active`
- signals: `suggested_position_size`, `confidence`, `signal_strength`

### 3. Проверка обратной совместимости

```python
# Тестовый код для проверки
async def verify_compatibility():
    # 1. Проверка загрузки конфигурации v2 в v3
    from core.config.config_manager import ConfigManager
    config = ConfigManager.get_config()

    # 2. Проверка что все exchange API работают
    from exchanges.factory import ExchangeFactory
    for exchange_name in ['bybit', 'binance', 'okx']:
        exchange = await ExchangeFactory.create(exchange_name)
        balance = await exchange.get_balance()
        assert balance is not None

    # 3. Проверка стратегий
    from strategies.factory import StrategyFactory
    strategies = StrategyFactory.get_available_strategies()
    assert len(strategies) >= 5  # Минимум стратегий из v2
```

### 4. Проверка новой функциональности

**ML система**:

```bash
# Проверь что ML модель загружается и работает
python3 test_ml_predictions.py

# Проверь что сигналы генерируются каждую минуту
python3 monitor_ml_signals_realtime.py
```

**Unified Launcher**:

```bash
# Проверь все режимы запуска
python3 unified_launcher.py --status
python3 unified_launcher.py --mode=core --dry-run
python3 unified_launcher.py --mode=ml --dry-run
```

### 5. Проверка производительности

Сравни метрики v2 и v3:

- Latency обработки сигналов: должна быть <50ms (v2: ~100ms)
- Throughput: >1000 сигналов/сек (v2: ~500)
- Memory usage: <2GB в idle (v2: ~1GB)
- CPU usage: <20% в нормальном режиме

### 6. Проверка безопасности

```bash
# Проверь что нет секретов в коде
grep -r "api_key\|secret\|password" --exclude-dir=venv --exclude-dir=.git --exclude="*.example"

# Проверь права доступа к файлам
find . -type f -name "*.yaml" -o -name "*.json" | xargs ls -la

# Проверь что .env не в репозитории
git ls-files | grep -E "\.env$"
```

### 7. Проверка критических сценариев

**Сценарий 1: Создание ордера с Enhanced SL/TP**

```python
# Должен создать ордер с:
# - Основным SL/TP
# - Partial TP уровнями (20% на +1.2%, 30% на +2.4%)
# - Profit protection (breakeven на +0.8%)
# - Trailing stop активацией на +3%
```

**Сценарий 2: Обработка сбоя биржи**

```python
# При недоступности Bybit система должна:
# - Переключиться на запасную биржу
# - Сохранить все открытые позиции
# - Продолжить мониторинг через WebSocket
```

**Сценарий 3: Risk limit превышение**

```python
# При drawdown > 5% система должна:
# - Остановить открытие новых позиций
# - Активировать emergency close для убыточных
# - Отправить алерт в Telegram
```

## Чек-лист финальной проверки

### Критические компоненты (MUST HAVE)

- [ ] Enhanced SL/TP полностью работает как в v2
- [ ] Все биржи подключаются и торгуют
- [ ] Risk management блокирует опасные операции
- [ ] База данных содержит все необходимые таблицы
- [ ] Hedge mode корректно обрабатывается

### Важные компоненты (SHOULD HAVE)

- [ ] ML предсказания генерируются и уникальны
- [ ] Monitoring и алерты работают
- [ ] API endpoints доступны и защищены
- [ ] Логирование структурировано

### Улучшения (NICE TO HAVE)

- [ ] Performance лучше чем v2
- [ ] Код покрыт тестами >80%
- [ ] Документация актуальна
- [ ] CI/CD настроен

## Инструкция по запуску проверки

```bash
# 1. Клонируй репозиторий
git clone https://github.com/obertruper/BOT_AI_V3.git
cd BOT_AI_V3

# 2. Настрой окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Проверь подключение к БД
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT version();"

# 4. Запусти тесты миграции
python3 scripts/test_v3_readiness.py

# 5. Проверь критические компоненты
python3 test_enhanced_sltp.py
python3 test_ml_predictions.py
python3 test_bybit_connection.py

# 6. Запусти в тестовом режиме
python3 unified_launcher.py --mode=core --dry-run
```

## Критерии успешной миграции

✅ **Миграция считается успешной если**:

1. Все функции из v2 работают в v3 без потери качества
2. Новые функции (ML, multi-trader) работают стабильно
3. Performance не деградировала (latency <50ms)
4. Нет критических багов в production сценариях
5. Risk management предотвращает катастрофические потери

❌ **Миграция НЕ готова к production если**:

1. Enhanced SL/TP работает не как в v2
2. Есть проблемы с hedge mode позициями
3. ML предсказания одинаковые для всех пар
4. Risk limits можно обойти
5. Критические данные теряются при сбоях

## Формат отчета

После проверки предоставь отчет в формате:

```markdown
# Отчет верификации миграции v2 → v3

## Резюме
- Статус: [READY/NOT READY/NEEDS FIXES]
- Критических проблем: [количество]
- Рекомендация: [запускать/не запускать/исправить и перепроверить]

## Детальные результаты

### ✅ Что работает хорошо
- ...

### ⚠️ Требует внимания
- ...

### ❌ Критические проблемы
- ...

## Рекомендации
1. ...
2. ...
```

---

**ВАЖНО**: Эта система управляет реальными деньгами. Любая ошибка может привести к финансовым потерям. Будь предельно внимателен и проверяй каждую деталь!
