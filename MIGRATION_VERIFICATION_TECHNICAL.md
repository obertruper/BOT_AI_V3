# Технический промт для LLM: Верификация миграции BOT Trading v2 → v3

## Системный контекст

Ты - Senior DevOps/SRE инженер с экспертизой в:

- Python async/await архитектуре
- PostgreSQL и миграциях данных
- Криптовалютных биржевых API
- ML системах в production
- High-frequency trading системах

## Технические требования к анализу

### 1. Анализ кода и архитектуры

```python
# Сравни архитектурные паттерны v2 vs v3

# V2 паттерн (синхронный):
class TradingEngine:
    def process_signal(self, signal):
        order = self.create_order(signal)
        self.risk_manager.check(order)
        return self.exchange.place_order(order)

# V3 паттерн (асинхронный):
class TradingEngine:
    async def process_signal(self, signal: Signal) -> Order:
        async with self._lock:
            order = await self._create_order(signal)
            await self.risk_manager.check_async(order)
            return await self.exchange.place_order_async(order)
```

**Проверь**:

- Все ли критические пути стали асинхронными?
- Правильно ли обрабатываются race conditions?
- Есть ли deadlock-и в async/await коде?

### 2. Анализ схемы БД

```sql
-- Сравни схемы v2 и v3
-- V2 схема
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    side VARCHAR(10),
    quantity DECIMAL(20, 8),
    price DECIMAL(20, 8),
    status VARCHAR(20)
);

-- V3 схема (должна включать)
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    side order_side_enum NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL CHECK (quantity > 0),
    price DECIMAL(20, 8),
    status order_status_enum NOT NULL,
    position_idx INTEGER DEFAULT 0,  -- КРИТИЧНО для hedge mode
    reduce_only BOOLEAN DEFAULT FALSE,
    time_in_force VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Проверь индексы
CREATE INDEX idx_orders_symbol_status ON orders(symbol, status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
```

### 3. Проверка ML pipeline

```python
# Проверь полный flow ML предсказаний

async def verify_ml_pipeline():
    # 1. Загрузка данных
    data = await db.fetch("""
        SELECT * FROM processed_market_data
        WHERE symbol = $1
        ORDER BY timestamp DESC
        LIMIT 200
    """, "BTCUSDT")

    # 2. Feature engineering (240+ features)
    features = FeatureEngineer.calculate_features(data)
    assert features.shape[1] >= 240

    # 3. Модель inference
    model = MLManager.get_model()
    predictions = await model.predict_async(features)

    # 4. Проверка уникальности
    btc_pred = predictions["BTCUSDT"]
    eth_pred = predictions["ETHUSDT"]
    assert btc_pred != eth_pred  # Предсказания должны быть уникальными

    # 5. Signal generation
    signal = SignalGenerator.create_from_prediction(predictions)
    assert signal.confidence > 0 and signal.confidence < 1
```

### 4. Проверка Exchange интеграции

```python
# Критические методы для проверки
class ExchangeVerification:
    async def verify_order_lifecycle(self):
        # 1. Create order с position_idx
        order = Order(
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            position_idx=1,  # Long position в hedge mode
            reduce_only=False
        )

        # 2. Place order
        result = await exchange.place_order(order)
        assert result.order_id is not None

        # 3. Modify order (SL/TP)
        await exchange.modify_order(
            order_id=result.order_id,
            stop_loss=95000,
            take_profit=105000
        )

        # 4. Partial close (Enhanced SL/TP)
        await exchange.close_position_partial(
            symbol="BTCUSDT",
            position_idx=1,
            close_ratio=0.2  # Закрыть 20%
        )
```

### 5. Performance профилирование

```python
import cProfile
import asyncio
from memory_profiler import profile

@profile
async def performance_test():
    # Замер latency
    start = time.perf_counter()

    # 1. Signal processing
    signals = []
    for _ in range(1000):
        signal = await generate_ml_signal("BTCUSDT")
        signals.append(signal)

    signal_time = time.perf_counter() - start
    assert signal_time < 1.0  # <1ms per signal

    # 2. Order execution
    start = time.perf_counter()
    orders = await asyncio.gather(*[
        place_order_async(sig) for sig in signals[:10]
    ])

    order_time = time.perf_counter() - start
    assert order_time < 0.5  # <50ms per order

    # 3. Memory usage
    import psutil
    process = psutil.Process()
    memory = process.memory_info().rss / 1024 / 1024  # MB
    assert memory < 2048  # <2GB
```

### 6. Проверка отказоустойчивости

```python
class ResilienceTest:
    async def test_exchange_failover(self):
        # 1. Симулируем сбой primary exchange
        with mock.patch('exchanges.bybit.client.get_balance',
                       side_effect=ConnectionError):

            # 2. Система должна переключиться
            balance = await exchange_manager.get_total_balance()
            assert balance > 0  # Получили баланс с другой биржи

    async def test_database_reconnect(self):
        # 1. Обрываем соединение
        await db.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity")

        # 2. Пытаемся записать
        await asyncio.sleep(1)
        order = await db.save_order(test_order)
        assert order.id is not None  # Реконнект успешен

    async def test_ml_model_fallback(self):
        # 1. Портим модель
        MLManager._model = None

        # 2. Запрашиваем предсказание
        prediction = await MLManager.predict(data)
        assert prediction is not None  # Fallback на простую модель
```

### 7. Интеграционные тесты

```bash
# Запусти полный integration test suite
pytest tests/integration/ -v --asyncio-mode=auto

# Критические тесты:
# - test_full_trading_cycle.py
# - test_enhanced_sltp_flow.py
# - test_multi_exchange_arbitrage.py
# - test_ml_signal_to_order.py
# - test_risk_limits_enforcement.py
```

## Автоматизированная проверка

```python
# scripts/verify_migration.py
import asyncio
from typing import Dict, List, Tuple

class MigrationVerifier:
    def __init__(self):
        self.results = {}
        self.critical_issues = []

    async def run_all_checks(self) -> Dict:
        checks = [
            ("Database Schema", self.check_database_schema),
            ("Enhanced SL/TP", self.check_enhanced_sltp),
            ("ML Pipeline", self.check_ml_pipeline),
            ("Exchange APIs", self.check_exchanges),
            ("Risk Management", self.check_risk_management),
            ("Performance", self.check_performance),
            ("Data Integrity", self.check_data_integrity)
        ]

        for name, check_func in checks:
            try:
                result = await check_func()
                self.results[name] = result
            except Exception as e:
                self.results[name] = {"status": "FAILED", "error": str(e)}
                self.critical_issues.append(f"{name}: {e}")

        return self.generate_report()

    async def check_enhanced_sltp(self) -> Dict:
        # Детальная проверка всех функций Enhanced SL/TP
        checks = {
            "partial_tp_levels": False,
            "profit_protection": False,
            "trailing_stop": False,
            "database_tracking": False
        }

        # 1. Проверка конфигурации
        config = ConfigManager.get_config()
        sltp_config = config.get("enhanced_sltp", {})

        if sltp_config.get("partial_take_profit", {}).get("levels"):
            checks["partial_tp_levels"] = True

        # 2. Проверка методов
        manager = EnhancedSLTPManager()
        if hasattr(manager, 'check_partial_tp'):
            checks["profit_protection"] = True

        # 3. Проверка БД
        table_exists = await db.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'partial_tp_history'
            )
        """)
        checks["database_tracking"] = table_exists

        return {
            "status": "PASSED" if all(checks.values()) else "FAILED",
            "details": checks
        }
```

## Критические точки проверки

### 1. Position Index Handling (КРИТИЧНО!)

```python
# V2 часто использовал position_idx=0 (one-way mode)
# V3 ДОЛЖЕН правильно обрабатывать hedge mode

# Проверь:
assert order.position_idx in [1, 2]  # 1=long, 2=short
assert position.position_idx != 0    # НЕ one-way mode

# В конфиге должно быть:
trading:
  hedge_mode: true  # ОБЯЗАТЕЛЬНО!
```

### 2. Partial Close Logic

```python
# V2 закрывал позиции через market orders
# V3 должен использовать reduce_only

# Правильно:
partial_order = Order(
    symbol=position.symbol,
    side="sell" if position.side == "buy" else "buy",
    quantity=position.quantity * 0.2,  # 20%
    reduce_only=True,  # КРИТИЧНО!
    position_idx=position.position_idx
)
```

### 3. WebSocket Reconnection

```python
# V3 должен автоматически переподключаться
class WebSocketManager:
    async def _reconnect_loop(self):
        while self._running:
            try:
                await self._connect()
                await self._subscribe()
            except Exception as e:
                logger.error(f"WS reconnect failed: {e}")
                await asyncio.sleep(min(self._reconnect_delay, 30))
                self._reconnect_delay *= 2  # Exponential backoff
```

## Команда для запуска полной проверки

```bash
# Создай скрипт run_migration_verification.sh
#!/bin/bash
set -e

echo "🔍 Starting migration verification v2 → v3"

# 1. Environment check
echo "✓ Checking environment..."
python3 --version
psql --version

# 2. Database verification
echo "✓ Verifying database..."
python3 scripts/verify_database_migration.py

# 3. Code verification
echo "✓ Running code analysis..."
python3 scripts/analyze_code_migration.py

# 4. Integration tests
echo "✓ Running integration tests..."
pytest tests/integration/test_v2_compatibility.py -v

# 5. Performance tests
echo "✓ Running performance benchmarks..."
python3 scripts/benchmark_v3_performance.py

# 6. Live test (dry-run)
echo "✓ Running live test (dry-run mode)..."
python3 unified_launcher.py --mode=all --dry-run --duration=300

echo "✅ Verification complete!"
```

## Ожидаемый результат от LLM

LLM должен предоставить:

1. **Технический отчет** с конкретными находками
2. **Список критических проблем** (если есть)
3. **Performance метрики** v2 vs v3
4. **Рекомендации** по исправлению
5. **Risk assessment** для production запуска

Формат ответа:

```yaml
migration_status: READY|NOT_READY|NEEDS_FIXES
risk_level: LOW|MEDIUM|HIGH|CRITICAL
confidence: 85%  # Уверенность в оценке

critical_issues:
  - issue: "Position index handling broken"
    severity: CRITICAL
    fix: "Update order creation logic"

performance_comparison:
  signal_latency:
    v2: 100ms
    v3: 45ms
    improvement: 55%

recommendations:
  immediate:
    - "Fix position_idx in order creation"
    - "Add reconnection logic to WebSocket"
  before_production:
    - "Increase test coverage to 80%"
    - "Add monitoring for ML predictions"
```

---

**Помни**: Эта система работает с реальными деньгами 24/7. Один баг может стоить тысячи долларов. Будь максимально внимателен к деталям!
