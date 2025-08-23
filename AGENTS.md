# Repository Guidelines

## Язык проекта
- Всегда пишем и думаем на русском: задачи, код‑ревью, комментарии в коде и документация.
- Conventional Commits: тип и scope — на английском (`feat`, `fix`, `refactor`), текст — по‑русски.
  Пример: `feat(trading): добавлен лимит риска для расчёта объёма`.

## Структура проекта
- Ядро `core/`, торговые потоки `trading/`, биржи `exchanges/`, ML `ml/`, база данных `database/`, утилиты `utils/`, веб `web/`.
- Конфигурация `config/`; данные и логи — в `data/` (симлинк `logs/`).
- Тесты — `tests/` (unit, integration, performance). Документация — `docs/` (Sphinx) и `docs_v3/` (MkDocs).
- Скрипты `scripts/`; стратегии `strategies/`; управление рисками `risk_management/`.

## Сборка, тесты и разработка
- Установка: `make install` (prod) или `make dev-install` (dev + pre-commit).
- Тесты: `make test` (unit), `make test-all`, `make test-integration`, `make test-coverage` (HTML + терминал).
- Быстрая проверка: `make check` (линт + быстрые тесты). Форматирование: `make format`. Линтеры/типы: `make lint` (ruff + mypy).
- Запуск: `make run` (движок) и `make run-web` (UI). Docker: `make docker-build`, `make docker-run`.

## Стиль кода и соглашения
- Python: Black (100), Ruff (pycodestyle/pyflakes/bugbear…), isort через Ruff; MyPy (py312, мягкий режим по импортам).
- Отступы: 4 пробела. Имена: `snake_case` (функции/модули), `PascalCase` (классы), `UPPER_SNAKE_CASE` (константы).
- Импорты: first‑party — `core`, `trading`, `exchanges`, `ml`, `database`, `web`, `utils` (см. `pyproject.toml`).
- Pre‑commit применяет форматирование, линт, типизацию, markdownlint, Bandit и проверку сообщений коммитов.

## Тестирование
- PyTest; поиск: файлы `test_*.py`/`*_test.py`, классы `Test*`, функции `test_*`.
- Маркеры: `unit`, `integration`, `slow`, а также `requires_db`, `requires_redis`, `requires_exchange`.
  Пример: `pytest -m "unit and not slow"`.
- Покрытие: `make test-coverage`. Поддерживайте покрытие изменённого кода на разумном уровне.

## Коммиты и Pull Request
- Используем Conventional Commits (Commitizen). Перед коммитом — `make check`; один раз — `pre-commit install`.
- PR: краткое описание и мотивация, скриншоты UI (если есть), связанные issue; чек‑лист — тесты добавлены/обновлены, документация обновлена (`docs/` или `docs_v3/`) при изменении поведения.

## Безопасность и конфигурация
- Секреты не коммитим. Копируйте `.env.example` → `.env`. Активна проверка `detect-secrets`; есть `.secrets.baseline` и `.gitleaks.toml`.
- Безопасность зависимостей/кода: `make security-check` (Safety + Bandit). Не храните ПДн в `data/`.
