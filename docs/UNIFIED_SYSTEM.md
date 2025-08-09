# 🚀 Единая система запуска BOT_AI_V3

## Обзор

Единая система запуска обеспечивает централизованное управление всеми компонентами BOT_AI_V3 из одной точки входа. Это решение объединяет торговый движок, ML систему, Web API и Frontend в единую управляемую систему.

## Архитектура

```
unified_launcher.py
    ├── ProcessManager          # Управление процессами
    │   ├── Core Process       # Торговый движок + ML
    │   ├── API Process        # FastAPI сервер
    │   └── Frontend Process   # React/Vite приложение
    │
    ├── HealthMonitor          # Мониторинг здоровья
    │   ├── HTTP checks        # Проверка endpoints
    │   ├── Process checks     # Проверка процессов
    │   └── Resource metrics   # Метрики ресурсов
    │
    └── ConfigManager          # Единая конфигурация
        └── unified_system     # Настройки из system.yaml
```

## Быстрый старт

### 1. Простейший запуск

```bash
./start_all.sh
# Выберите пункт 0 для запуска единой системы
```

### 2. Прямой запуск

```bash
# Полная система с ML
python unified_launcher.py

# Только торговля без frontend
python unified_launcher.py --mode=core

# Только API и frontend
python unified_launcher.py --mode=api

# Режим разработки (без автоперезапуска)
python unified_launcher.py --mode=dev
```

### 3. Управление системой

```bash
# Проверить статус
python unified_launcher.py --status

# Следить за логами
python unified_launcher.py --logs
```

## Режимы работы

### FULL (по умолчанию)

- ✅ Core System (торговый движок)
- ✅ ML System (генерация сигналов)
- ✅ Web API (REST/WebSocket)
- ✅ Frontend (React Dashboard)

### CORE

- ✅ Core System
- ✅ ML System
- ❌ Web API
- ❌ Frontend

### API

- ❌ Core System
- ❌ ML System
- ✅ Web API
- ✅ Frontend

### ML

- ✅ Core System
- ✅ ML System
- ✅ Web API
- ❌ Frontend

### DEV

- Все компоненты как в FULL
- Отключен автоперезапуск
- Расширенное логирование

## Конфигурация

Настройки единой системы находятся в `config/system.yaml`:

```yaml
unified_system:
  enabled: true

  components:
    core:
      enabled: true
      auto_restart: true
      health_check_interval: 30

    ml:
      enabled: true
      integrated_with: core  # ML встроен в Core

    api:
      enabled: true
      port: 8080
      auto_restart: true
      health_check_endpoint: "http://localhost:8080/api/health"

    frontend:
      enabled: true
      port: 5173
      auto_restart: false
```

## Возможности

### 🔄 Автоматический перезапуск

- Компоненты автоматически перезапускаются при сбоях
- Настраиваемое количество попыток (по умолчанию 5)
- Задержка между перезапусками

### 📊 Мониторинг здоровья

- HTTP health checks для API endpoints
- Process-based проверки для всех компонентов
- Мониторинг использования ресурсов (CPU, память)

### 📝 Централизованное логирование

- Все логи в директории `logs/`
- Отдельные логи для каждого процесса в `logs/processes/`
- Агрегированный просмотр через `--logs`

### 🛡️ Graceful Shutdown

- Корректная остановка всех компонентов по Ctrl+C
- Сохранение состояния перед остановкой
- Правильный порядок остановки

## Мониторинг

### Проверка статуса

```bash
$ python unified_launcher.py --status

📊 Статус системы BOT_AI_V3
============================================================

✅ CORE
  PID: 12345
  Статус: running
  CPU: 15.2%
  Память: 256.3 MB
  Uptime: 2:15:30

✅ API
  PID: 12346
  Статус: running
  CPU: 5.1%
  Память: 128.5 MB
  Uptime: 2:15:25

✅ FRONTEND
  PID: 12347
  Статус: running
  CPU: 2.3%
  Память: 98.2 MB
  Uptime: 2:15:20
```

### Health Endpoints

- **API Health**: <http://localhost:8080/api/health>
- **Frontend**: <http://localhost:5173>
- **API Docs**: <http://localhost:8080/api/docs>

## Устранение неполадок

### Система не запускается

1. Проверьте виртуальное окружение:

   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Проверьте PostgreSQL:

   ```bash
   psql -p 5555 -U obertruper -d bot_trading_v3
   ```

3. Проверьте наличие ML модели:

   ```bash
   ls models/saved/best_model_*.pth
   ```

### Компонент постоянно перезапускается

1. Проверьте логи компонента:

   ```bash
   tail -f logs/processes/{component}_stderr.log
   ```

2. Отключите автоперезапуск в `system.yaml`

3. Запустите в режиме разработки:

   ```bash
   python unified_launcher.py --mode=dev
   ```

### Frontend не доступен

1. Проверьте установку Node.js:

   ```bash
   node --version
   npm --version
   ```

2. Установите зависимости frontend:

   ```bash
   cd web/frontend
   npm install
   ```

## Сравнение с предыдущими методами

| Функция | start_all.sh (старый) | integrated_start.py | unified_launcher.py |
|---------|---------------------|-------------------|-------------------|
| Управление процессами | Bash скрипты | Один процесс | ProcessManager |
| Автоперезапуск | ❌ | ❌ | ✅ |
| Health monitoring | ❌ | Частично | ✅ |
| Разные режимы | Меню выбора | ❌ | CLI аргументы |
| Логирование | Разрозненное | Объединенное | Структурированное |
| Graceful shutdown | Частично | ✅ | ✅ |

## Рекомендации

1. **Используйте unified_launcher.py** для production окружения
2. **Режим DEV** для разработки и отладки
3. **Мониторьте логи** регулярно через `--logs`
4. **Настройте автоперезапуск** в зависимости от стабильности
5. **Проверяйте health endpoints** для мониторинга

## Дальнейшее развитие

- [ ] Интеграция с systemd для автозапуска
- [ ] Web UI для управления системой
- [ ] Метрики в Prometheus/Grafana
- [ ] Уведомления о сбоях в Telegram
- [ ] Автоматическое восстановление данных
