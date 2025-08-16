# 📚 Документация системных компонентов BOT_AI_V3

## 📋 Оглавление

1. [Обзор системы](#обзор-системы)
2. [Архитектура решения](#архитектура-решения)
3. [Компоненты системы](#компоненты-системы)
   - [WorkerCoordinator](#workercoordinator)
   - [SignalDeduplicator](#signaldeduplicator)
   - [RateLimiter](#ratelimiter)
   - [BalanceManager](#balancemanager)
   - [ProcessMonitor](#processmonitor)
4. [Установка и настройка](#установка-и-настройка)
5. [Использование](#использование)
6. [API Reference](#api-reference)
7. [Решение проблем](#решение-проблем)
8. [Мониторинг и метрики](#мониторинг-и-метрики)

---

## 🎯 Обзор системы

### Назначение

Система управления и координации компонентов BOT_AI_V3 предназначена для решения критических проблем в высоконагруженной торговой платформе:

- **Предотвращение дублирования процессов** - гарантирует запуск только одного экземпляра ML Manager
- **Дедупликация сигналов** - исключает повторную обработку идентичных торговых сигналов
- **Контроль API лимитов** - предотвращает превышение rate limits на биржах
- **Управление балансами** - резервирование средств перед созданием ордеров
- **Мониторинг системы** - отслеживание состояния всех компонентов в реальном времени

### Ключевые возможности

- ✅ **Единственность процессов** - автоматическое предотвращение запуска дубликатов
- ✅ **Уникальность сигналов** - хеширование и проверка на дубликаты
- ✅ **Rate limiting** - адаптивная задержка запросов к API
- ✅ **Резервирование баланса** - предварительная проверка средств
- ✅ **Heartbeat мониторинг** - отслеживание живости компонентов
- ✅ **Алерты и метрики** - система оповещений о проблемах

### Решаемые проблемы

1. **Database constraint violations** - ошибки уникальности при вставке дублирующих сигналов
2. **API Error Code: 10002** - превышение rate limits бирж
3. **API Error Code: 110007** - недостаточно средств для создания ордера
4. **Дублирующие ML процессы** - параллельная работа нескольких ML Manager
5. **Потеря контроля над воркерами** - отсутствие мониторинга состояния

---

## 🏗️ Архитектура решения

### Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                    SystemOrchestrator                        │
│                         (main.py)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌────────▼────────┐
│  ML Manager    │          │ Trading Engine  │
│                │          │                 │
│ ┌────────────┐ │          │ ┌─────────────┐ │
│ │   Worker   │ │          │ │    Rate     │ │
│ │Coordinator │ │          │ │   Limiter   │ │
│ └────────────┘ │          │ └─────────────┘ │
│                │          │                 │
│ ┌────────────┐ │          │ ┌─────────────┐ │
│ │   Signal   │ │          │ │   Balance   │ │
│ │Deduplicator│ │          │ │   Manager   │ │
│ └────────────┘ │          │ └─────────────┘ │
└────────────────┘          └─────────────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
              ┌────────▼────────┐
              │ Process Monitor │
              │                 │
              │  ┌──────────┐   │
              │  │ Heartbeat│   │
              │  │  System  │   │
              │  └──────────┘   │
              │                 │
              │  ┌──────────┐   │
              │  │  Alerts  │   │
              │  │  System  │   │
              │  └──────────┘   │
              └─────────────────┘
```

### Поток данных

1. **ML Manager** генерирует сигналы
2. **SignalDeduplicator** проверяет уникальность
3. **Trading Engine** обрабатывает уникальные сигналы
4. **RateLimiter** контролирует частоту API запросов
5. **BalanceManager** резервирует средства для ордеров
6. **ProcessMonitor** отслеживает состояние всех компонентов

---

## 🔧 Компоненты системы

### WorkerCoordinator

#### Описание

Централизованный координатор для управления воркерами и предотвращения дублирования процессов.

#### Основные функции

- **Регистрация воркеров** - уникальная идентификация каждого процесса
- **Heartbeat система** - отслеживание активности воркеров
- **Назначение задач** - распределение работы между воркерами
- **Автоматическая очистка** - удаление неактивных воркеров

#### Конфигурация

```python
# core/system/worker_coordinator.py
class WorkerCoordinator:
    def __init__(self):
        self.heartbeat_timeout = 60  # секунд
        self.cleanup_interval = 30   # секунд
        self.max_workers_per_type = 1  # только один воркер каждого типа
```

#### Использование

```python
from core.system.worker_coordinator import worker_coordinator

# Регистрация воркера
worker_id = await worker_coordinator.register_worker(
    worker_type='ml_manager',
    metadata={'version': '3.0', 'gpu': 'RTX 5090'}
)

if worker_id:
    # Воркер успешно зарегистрирован
    # Периодическая отправка heartbeat
    await worker_coordinator.heartbeat(worker_id, status='running')
else:
    # Воркер такого типа уже запущен
    logger.warning("ML Manager уже работает")
    sys.exit(0)
```

---

### SignalDeduplicator

#### Описание

Система дедупликации торговых сигналов на основе контентного хеширования.

#### Основные функции

- **Хеширование сигналов** - создание уникального fingerprint
- **Проверка на дубликаты** - сравнение с кешем и БД
- **Временное окно** - учет времени при определении уникальности
- **Статистика** - подсчет уникальных и дублирующих сигналов

#### Алгоритм хеширования

```python
def create_fingerprint(signal):
    data = {
        'symbol': signal['symbol'],
        'direction': signal['direction'],
        'strategy': signal['strategy'],
        'timestamp_minute': signal['timestamp'].replace(second=0, microsecond=0)
    }
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]
```

#### Использование

```python
from core.system.signal_deduplicator import signal_deduplicator

signal = {
    'symbol': 'BTCUSDT',
    'direction': 'BUY',
    'strategy': 'ml_strategy',
    'timestamp': datetime.now(),
    'signal_strength': 0.85
}

# Проверка и регистрация сигнала
is_unique = await signal_deduplicator.check_and_register_signal(signal)

if is_unique:
    # Обработка уникального сигнала
    await process_signal(signal)
else:
    logger.info(f"Пропущен дубликат сигнала: {signal['symbol']}")
```

---

### RateLimiter

#### Описание

Адаптивный контроллер частоты запросов к API бирж с поддержкой весов и endpoint-специфичных лимитов.

#### Основные функции

- **Sliding window алгоритм** - точный подсчет запросов в окне
- **Веса запросов** - учет сложности различных endpoint'ов
- **Биржевые конфигурации** - настройки для каждой биржи
- **Автоматическая задержка** - расчет времени ожидания

#### Конфигурация бирж

```python
EXCHANGE_LIMITS = {
    'bybit': {
        'global': {'requests': 120, 'window': 60},
        'endpoints': {
            'market_data': {'requests': 100, 'window': 60, 'weight': 1},
            'order': {'requests': 80, 'window': 60, 'weight': 2},
            'account': {'requests': 60, 'window': 60, 'weight': 1}
        }
    },
    'binance': {
        'global': {'requests': 1200, 'window': 60},
        'endpoints': {
            'market_data': {'requests': 2400, 'window': 60, 'weight': 1},
            'order': {'requests': 100, 'window': 10, 'weight': 1}
        }
    }
}
```

#### Использование

```python
from core.system.rate_limiter import rate_limiter

# Перед API запросом
wait_time = await rate_limiter.acquire('bybit', 'order', weight=2)

if wait_time > 0:
    logger.info(f"Rate limit: ожидание {wait_time:.2f}с")
    await asyncio.sleep(wait_time)

# Выполнение запроса
response = await exchange_api.create_order(...)
```

---

### BalanceManager

#### Описание

Менеджер управления балансами с системой резервирования средств для предотвращения превышения доступных средств.

#### Основные функции

- **Кеширование балансов** - быстрый доступ к данным
- **Резервирование средств** - блокировка суммы перед ордером
- **Проверка доступности** - валидация перед торговлей
- **Автоматическое обновление** - синхронизация с биржами

#### Система резервирования

```python
# Процесс создания ордера
1. Проверка доступности средств
2. Резервирование суммы
3. Создание ордера на бирже
4. Освобождение резерва (успех) или откат (ошибка)
```

#### Использование

```python
from core.system.balance_manager import balance_manager

# Обновление баланса
await balance_manager.update_balance(
    exchange='bybit',
    symbol='USDT',
    total=Decimal('10000'),
    available=Decimal('9500'),
    locked=Decimal('500')
)

# Проверка перед торговлей
amount_needed = Decimal('1000')
available, error = await balance_manager.check_balance_availability(
    exchange='bybit',
    symbol='USDT',
    amount=amount_needed
)

if available:
    # Резервирование средств
    reservation_id = await balance_manager.reserve_balance(
        exchange='bybit',
        symbol='USDT',
        amount=amount_needed,
        purpose='order_creation'
    )

    try:
        # Создание ордера
        order = await create_order(...)
        # Освобождение резерва после успеха
        await balance_manager.release_reservation(reservation_id)
    except Exception as e:
        # Откат резервирования при ошибке
        await balance_manager.release_reservation(reservation_id)
        raise
else:
    logger.warning(f"Недостаточно средств: {error}")
```

---

### ProcessMonitor

#### Описание

Система мониторинга состояния всех компонентов с heartbeat механизмом и алертами.

#### Основные функции

- **Регистрация компонентов** - учет всех активных модулей
- **Heartbeat мониторинг** - проверка живости процессов
- **Система алертов** - оповещения о проблемах
- **Сбор метрик** - CPU, память, задержки

#### Правила алертов

```python
ALERT_RULES = {
    'heartbeat_timeout': {
        'threshold': 120,  # секунд без heartbeat
        'severity': 'critical',
        'action': 'restart_component'
    },
    'high_error_rate': {
        'threshold': 10,  # ошибок в минуту
        'severity': 'warning',
        'action': 'notify'
    },
    'memory_usage': {
        'threshold': 90,  # процентов
        'severity': 'warning',
        'action': 'notify'
    }
}
```

#### Использование

```python
from core.system.process_monitor import process_monitor

# Регистрация компонента
await process_monitor.register_component(
    'trading_engine',
    metadata={'version': '3.0', 'critical': True}
)

# Периодическая отправка heartbeat
async def heartbeat_loop():
    while running:
        await process_monitor.heartbeat(
            'trading_engine',
            status='healthy',
            active_tasks=len(active_orders),
            metadata={'processed_signals': signal_count}
        )
        await asyncio.sleep(30)

# Сообщение об ошибке
try:
    # Критическая операция
    await process_critical_operation()
except Exception as e:
    await process_monitor.report_error(
        'trading_engine',
        str(e),
        is_critical=True
    )
```

---

## 🚀 Установка и настройка

### Требования

- Python 3.8+
- PostgreSQL 15+ (порт 5555)
- Redis 6+ (опционально, для распределенного кеша)
- 8GB+ RAM
- RTX 5090 GPU (для ML компонентов)

### Установка

1. **Клонирование репозитория**

```bash
git clone https://github.com/your-org/BOT_AI_V3.git
cd BOT_AI_V3
```

2. **Создание виртуального окружения**

```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Установка зависимостей**

```bash
pip install -r requirements.txt
```

4. **Настройка базы данных**

```bash
# Создание БД
createdb -p 5555 bot_trading_v3

# Применение миграций
alembic upgrade head
```

5. **Конфигурация**

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование .env
nano .env
```

### Переменные окружения

```env
# PostgreSQL (ВАЖНО: порт 5555!)
PGHOST=localhost
PGPORT=5555
PGUSER=obertruper
PGPASSWORD=your_password
PGDATABASE=bot_trading_v3

# Redis (опционально)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Биржи
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret

# Системные настройки
WORKER_HEARTBEAT_TIMEOUT=60
SIGNAL_DEDUP_WINDOW=300
RATE_LIMIT_SAFETY_MARGIN=0.9
BALANCE_UPDATE_INTERVAL=30
MONITOR_ALERT_THRESHOLD=10
```

---

## 💻 Использование

### Запуск системы

1. **Полный запуск с мониторингом**

```bash
./start_with_logs.sh
```

2. **Запуск отдельных компонентов**

```bash
# Только ML Manager
python3 unified_launcher.py --mode=ml

# Только Trading Engine
python3 unified_launcher.py --mode=core

# API и веб-интерфейс
python3 unified_launcher.py --mode=api
```

3. **Проверка статуса**

```bash
python3 unified_launcher.py --status
```

### Интеграция в код

#### В ML Manager

```python
class MLManager:
    async def initialize(self):
        # Регистрация как единственный ML воркер
        self.worker_id = await worker_coordinator.register_worker(
            worker_type='ml_manager',
            metadata={'model': 'UnifiedPatchTST', 'version': '3.0'}
        )

        if not self.worker_id:
            logger.error("ML Manager уже запущен в другом процессе")
            raise RuntimeError("Duplicate ML Manager instance")

        # Запуск heartbeat
        asyncio.create_task(self._heartbeat_loop())

    async def predict(self, data):
        # Генерация предсказания
        prediction = await self.model.predict(data)

        # Формирование сигнала
        signal = self._create_signal(prediction)

        # Проверка на дубликат
        if await signal_deduplicator.check_and_register_signal(signal):
            return signal
        else:
            logger.debug(f"Дубликат сигнала пропущен: {signal['symbol']}")
            return None
```

#### В Trading Engine

```python
class TradingEngine:
    async def _create_order(self, signal):
        exchange = signal['exchange']
        symbol = signal['symbol']
        amount = signal['amount']

        # 1. Проверка rate limit
        wait_time = await rate_limiter.acquire(exchange, 'order')
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        # 2. Проверка и резервирование баланса
        available, error = await balance_manager.check_balance_availability(
            exchange=exchange,
            symbol='USDT',
            amount=amount * signal['price']
        )

        if not available:
            logger.warning(f"Недостаточно средств: {error}")
            return None

        reservation_id = await balance_manager.reserve_balance(
            exchange=exchange,
            symbol='USDT',
            amount=amount * signal['price'],
            purpose=f"order_{signal['id']}"
        )

        try:
            # 3. Создание ордера
            order = await self.exchange_client.create_order(
                symbol=symbol,
                side=signal['direction'],
                amount=amount,
                price=signal['price']
            )

            # 4. Освобождение резерва
            await balance_manager.release_reservation(reservation_id)

            return order

        except Exception as e:
            # Откат резервирования при ошибке
            await balance_manager.release_reservation(reservation_id)

            # Сообщение об ошибке в монитор
            await process_monitor.report_error(
                'trading_engine',
                f"Order creation failed: {e}",
                is_critical=False
            )
            raise
```

---

## 📖 API Reference

### WorkerCoordinator API

```python
class WorkerCoordinator:
    async def register_worker(
        self,
        worker_type: str,
        worker_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Регистрация нового воркера

        Args:
            worker_type: Тип воркера (ml_manager, trading_engine, etc)
            worker_id: ID воркера (генерируется автоматически если не указан)
            metadata: Дополнительные данные о воркере

        Returns:
            worker_id если успешно, None если воркер такого типа уже существует
        """

    async def heartbeat(
        self,
        worker_id: str,
        status: str = 'running',
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка heartbeat от воркера

        Args:
            worker_id: ID воркера
            status: Текущий статус (running, idle, busy, error)
            metadata: Дополнительные данные о состоянии

        Returns:
            True если успешно, False если воркер не найден
        """

    async def unregister_worker(self, worker_id: str) -> bool:
        """
        Снятие воркера с регистрации

        Args:
            worker_id: ID воркера

        Returns:
            True если успешно снят с регистрации
        """

    def get_worker_stats(self) -> Dict[str, Any]:
        """
        Получение статистики по воркерам

        Returns:
            Словарь со статистикой
        """
```

### SignalDeduplicator API

```python
class SignalDeduplicator:
    async def check_and_register_signal(
        self,
        signal_data: Dict[str, Any]
    ) -> bool:
        """
        Проверка сигнала на уникальность и регистрация

        Args:
            signal_data: Данные сигнала (symbol, direction, strategy, etc)

        Returns:
            True если сигнал уникален, False если дубликат
        """

    async def get_recent_signals(
        self,
        minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Получение недавних сигналов

        Args:
            minutes: Временное окно в минутах

        Returns:
            Список недавних сигналов
        """

    def get_stats(self) -> Dict[str, int]:
        """
        Получение статистики дедупликации

        Returns:
            Словарь со статистикой (total_checks, duplicates_found, etc)
        """
```

### RateLimiter API

```python
class RateLimiter:
    async def acquire(
        self,
        exchange: str,
        endpoint: str = 'default',
        weight: Optional[int] = None
    ) -> float:
        """
        Запрос разрешения на выполнение API запроса

        Args:
            exchange: Название биржи
            endpoint: Тип endpoint'а (market_data, order, account)
            weight: Вес запроса (по умолчанию из конфигурации)

        Returns:
            Время ожидания в секундах (0 если можно выполнять сразу)
        """

    async def get_current_usage(
        self,
        exchange: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получение текущего использования лимитов

        Args:
            exchange: Название биржи

        Returns:
            Словарь с использованием по endpoint'ам
        """

    def get_stats(self, exchange: str) -> Dict[str, Dict[str, int]]:
        """
        Получение статистики по запросам

        Args:
            exchange: Название биржи

        Returns:
            Статистика по endpoint'ам
        """
```

### BalanceManager API

```python
class BalanceManager:
    async def update_balance(
        self,
        exchange: str,
        symbol: str,
        total: Decimal,
        available: Decimal,
        locked: Decimal
    ) -> bool:
        """
        Обновление баланса

        Args:
            exchange: Название биржи
            symbol: Символ валюты (USDT, BTC, etc)
            total: Общий баланс
            available: Доступный баланс
            locked: Заблокированный баланс

        Returns:
            True если успешно обновлено
        """

    async def check_balance_availability(
        self,
        exchange: str,
        symbol: str,
        amount: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверка доступности средств

        Args:
            exchange: Название биржи
            symbol: Символ валюты
            amount: Требуемая сумма

        Returns:
            (доступно, сообщение об ошибке если недоступно)
        """

    async def reserve_balance(
        self,
        exchange: str,
        symbol: str,
        amount: Decimal,
        purpose: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Резервирование средств

        Args:
            exchange: Название биржи
            symbol: Символ валюты
            amount: Сумма для резервирования
            purpose: Цель резервирования
            metadata: Дополнительные данные

        Returns:
            reservation_id если успешно, None если недостаточно средств
        """

    async def release_reservation(
        self,
        reservation_id: str
    ) -> bool:
        """
        Освобождение резервирования

        Args:
            reservation_id: ID резервирования

        Returns:
            True если успешно освобождено
        """
```

### ProcessMonitor API

```python
class ProcessMonitor:
    async def register_component(
        self,
        component_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Регистрация компонента для мониторинга

        Args:
            component_name: Имя компонента
            metadata: Дополнительные данные

        Returns:
            True если успешно зарегистрирован
        """

    async def heartbeat(
        self,
        component_name: str,
        status: str = 'healthy',
        active_tasks: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка heartbeat от компонента

        Args:
            component_name: Имя компонента
            status: Статус (healthy, degraded, unhealthy)
            active_tasks: Количество активных задач
            metadata: Дополнительные метрики

        Returns:
            True если heartbeat принят
        """

    async def report_error(
        self,
        component_name: str,
        error: str,
        is_critical: bool = False
    ) -> None:
        """
        Сообщение об ошибке

        Args:
            component_name: Имя компонента
            error: Описание ошибки
            is_critical: Критическая ли ошибка
        """

    def get_component_health(
        self,
        component_name: str
    ) -> Dict[str, Any]:
        """
        Получение состояния компонента

        Args:
            component_name: Имя компонента

        Returns:
            Словарь с информацией о здоровье компонента
        """
```

---

## 🔍 Решение проблем

### Проблема: WorkerCoordinator heartbeat error

**Симптом:**

```
TypeError: heartbeat() got an unexpected keyword argument 'active_tasks'
```

**Решение:**

```python
# Исправить сигнатуру метода в worker_coordinator.py
async def heartbeat(
    self,
    worker_id: str,
    status: str = 'running',
    active_tasks: int = 0,  # Добавить этот параметр
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
```

### Проблема: Redis connection refused

**Симптом:**

```
Error 111 connecting to localhost:6379. Connection refused.
```

**Решение:**

1. Установить и запустить Redis:

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis
```

2. Или использовать локальный кеш (fallback):

```python
# Система автоматически переключится на локальный кеш
# Проверить в логах:
"Используется локальный кеш вместо Redis"
```

### Проблема: RateLimiter pipeline error

**Симптом:**

```
TypeError: '>=' not supported between instances of 'Pipeline' and 'int'
```

**Решение:**

```python
# В rate_limiter.py исправить:
# Было:
if pipe.zcard(key) >= limit:

# Стало:
count = await pipe.zcard(key)
if count >= limit:
```

### Проблема: Duplicate ML processes

**Симптом:**

```
Multiple ML Manager instances running
Database constraint violations
```

**Решение:**

1. Остановить все процессы:

```bash
pkill -f "python.*unified_launcher"
```

2. Очистить locks:

```sql
DELETE FROM worker_registry WHERE worker_type = 'ml_manager';
```

3. Перезапустить с проверкой:

```bash
python3 unified_launcher.py --mode=ml
```

### Проблема: Insufficient balance errors

**Симптом:**

```
API Error Code: 110007 - Insufficient balance
```

**Решение:**

1. Проверить актуальность балансов:

```python
# Принудительное обновление
await balance_manager.force_update_all_balances()
```

2. Увеличить интервал обновления:

```env
BALANCE_UPDATE_INTERVAL=10  # Обновлять каждые 10 секунд
```

3. Добавить safety margin:

```python
# При проверке доступности
required_amount = order_amount * Decimal('1.02')  # +2% запас
```

---

## 📊 Мониторинг и метрики

### Dashboards

#### Grafana Dashboard

Доступ: <http://localhost:3000>

**Панели:**

- Worker Status - состояние всех воркеров
- Signal Deduplication Rate - процент дубликатов
- API Rate Limits - использование лимитов
- Balance Reservations - активные резервирования
- System Health - общее состояние системы

#### Prometheus Metrics

Доступ: <http://localhost:9090>

**Метрики:**

```
# Воркеры
worker_coordinator_active_workers{type="ml_manager"} 1
worker_coordinator_heartbeat_age_seconds{worker_id="..."} 15

# Сигналы
signal_deduplicator_total_checks 1523
signal_deduplicator_duplicates_found 234
signal_deduplicator_unique_signals 1289

# Rate Limits
rate_limiter_requests_total{exchange="bybit", endpoint="order"} 456
rate_limiter_blocked_requests{exchange="bybit"} 12

# Балансы
balance_manager_total_balance{exchange="bybit", symbol="USDT"} 10000
balance_manager_reserved_balance{exchange="bybit", symbol="USDT"} 1500

# Мониторинг
process_monitor_component_health{name="trading_engine"} 1
process_monitor_errors_total{component="ml_manager"} 5
```

### Логирование

#### Структура логов

```
data/logs/
├── bot_trading_YYYYMMDD.log      # Основной лог
├── ml_manager_YYYYMMDD.log       # ML компоненты
├── trading_engine_YYYYMMDD.log   # Торговая логика
├── system_monitor_YYYYMMDD.log   # Мониторинг
└── errors_YYYYMMDD.log          # Только ошибки
```

#### Просмотр логов

```bash
# Следить за всеми логами
tail -f data/logs/bot_trading_$(date +%Y%m%d).log

# Только ошибки
tail -f data/logs/errors_$(date +%Y%m%d).log | grep ERROR

# ML предсказания
tail -f data/logs/ml_manager_$(date +%Y%m%d).log | grep "returns_15m"

# Дубликаты сигналов
grep "Дубликат сигнала" data/logs/bot_trading_$(date +%Y%m%d).log | wc -l
```

### Алерты

#### Email алерты

```python
# config/alerts.yaml
alerts:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    from_email: bot@example.com
    to_emails:
      - admin@example.com
    triggers:
      - worker_offline
      - high_error_rate
      - low_balance
```

#### Telegram алерты

```python
# config/alerts.yaml
alerts:
  telegram:
    enabled: true
    bot_token: YOUR_BOT_TOKEN
    chat_id: YOUR_CHAT_ID
    triggers:
      - critical_error
      - worker_restart
      - rate_limit_exceeded
```

### Health Checks

#### HTTP Endpoint

```bash
# Проверка здоровья системы
curl http://localhost:8080/health

# Ответ:
{
  "status": "healthy",
  "components": {
    "ml_manager": "healthy",
    "trading_engine": "healthy",
    "database": "healthy",
    "redis": "degraded"
  },
  "uptime": 3600,
  "version": "3.0.0"
}
```

#### CLI команда

```bash
# Проверка статуса
python3 unified_launcher.py --status

# Вывод:
✅ ML Manager: Running (PID: 12345)
✅ Trading Engine: Running (PID: 12346)
✅ API Server: Running (PID: 12347)
⚠️  Redis: Not connected (using local cache)
✅ PostgreSQL: Connected (port 5555)
```

---

## 🎯 Лучшие практики

### 1. Всегда используйте WorkerCoordinator

```python
# ❌ Плохо
class MLManager:
    def __init__(self):
        self.start()  # Может запустить дубликаты

# ✅ Хорошо
class MLManager:
    async def initialize(self):
        self.worker_id = await worker_coordinator.register_worker('ml_manager')
        if not self.worker_id:
            raise RuntimeError("ML Manager already running")
```

### 2. Проверяйте сигналы на дубликаты

```python
# ❌ Плохо
signal = generate_signal()
await process_signal(signal)  # Может обработать дубликат

# ✅ Хорошо
signal = generate_signal()
if await signal_deduplicator.check_and_register_signal(signal):
    await process_signal(signal)
```

### 3. Соблюдайте rate limits

```python
# ❌ Плохо
for order in orders:
    await create_order(order)  # Может превысить лимит

# ✅ Хорошо
for order in orders:
    wait_time = await rate_limiter.acquire('bybit', 'order')
    if wait_time > 0:
        await asyncio.sleep(wait_time)
    await create_order(order)
```

### 4. Резервируйте балансы

```python
# ❌ Плохо
if balance >= amount:
    await create_order(amount)  # Баланс может измениться

# ✅ Хорошо
reservation_id = await balance_manager.reserve_balance('bybit', 'USDT', amount)
if reservation_id:
    try:
        await create_order(amount)
    finally:
        await balance_manager.release_reservation(reservation_id)
```

### 5. Отправляйте heartbeats

```python
# ❌ Плохо
while True:
    await process_data()  # Монитор не знает о состоянии

# ✅ Хорошо
while True:
    await process_data()
    await process_monitor.heartbeat('component_name', status='healthy')
    await asyncio.sleep(30)
```

---

## 📞 Поддержка

### Контакты

- **Email**: <support@botai.tech>
- **Telegram**: @botai_support
- **GitHub Issues**: <https://github.com/your-org/BOT_AI_V3/issues>

### FAQ

**Q: Как часто обновляются балансы?**
A: По умолчанию каждые 30 секунд, настраивается через BALANCE_UPDATE_INTERVAL.

**Q: Что делать если Redis недоступен?**
A: Система автоматически переключится на локальный кеш. Функциональность сохранится, но без распределенности.

**Q: Как изменить rate limits?**
A: Отредактировать EXCHANGE_LIMITS в core/system/rate_limiter.py или передать через конфигурацию.

**Q: Можно ли запустить несколько Trading Engine?**
A: Да, но только с разными конфигурациями (разные биржи или символы).

---

## 📈 Roadmap

### v3.1 (Q1 2025)

- [ ] Распределенная координация через Kubernetes
- [ ] Автоматическое масштабирование воркеров
- [ ] ML-based rate limit prediction

### v3.2 (Q2 2025)

- [ ] Multi-exchange балансировка
- [ ] Расширенная система алертов
- [ ] WebSocket мониторинг в реальном времени

### v3.3 (Q3 2025)

- [ ] Автоматическое восстановление после сбоев
- [ ] Blockchain интеграция для аудита
- [ ] AI-driven оптимизация параметров

---

## 📄 Лицензия

Copyright (c) 2025 BOT_AI Team

Лицензия: Proprietary
Использование только с письменного разрешения.

---

## 🙏 Благодарности

Спасибо всем участникам проекта BOT_AI_V3 за вклад в развитие системы.

Особая благодарность:

- Команде разработки ML моделей
- QA инженерам за тестирование
- DevOps команде за инфраструктуру
- Сообществу за обратную связь

---

*Документация актуальна на: Январь 2025*
*Версия системы: 3.0.0*
*Последнее обновление: 14.01.2025*
