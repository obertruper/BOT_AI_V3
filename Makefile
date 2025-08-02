# BOT_AI_V3 Makefile
.PHONY: help test test-all test-unit test-ml test-integration test-performance test-coverage test-quick test-watch test-chain clean install dev-install lint format check

# По умолчанию показываем help
.DEFAULT_GOAL := help

# Переменные
PYTHON := python3
PIP := pip3
PYTEST := pytest
BLACK := black
RUFF := ruff
MYPY := mypy

help: ## Показать это сообщение помощи
	@echo "BOT_AI_V3 - Команды разработки"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ==================== Установка ====================

install: ## Установить зависимости проекта
	$(PIP) install -r requirements.txt

dev-install: ## Установить зависимости для разработки
	$(PIP) install -e ".[dev]"
	pre-commit install

# ==================== Тестирование ====================

test: test-unit ## Запустить unit тесты (по умолчанию)

test-all: ## Запустить все тесты
	$(PYTEST) tests/ -v

test-unit: ## Запустить unit тесты
	$(PYTEST) tests/unit/ -m "unit" -v

test-ml: ## Запустить ML тесты
	$(PYTEST) tests/unit/ml/ -m "ml" -v --durations=10

test-integration: ## Запустить интеграционные тесты
	$(PYTEST) tests/integration/ -m "integration" -v

test-performance: ## Запустить performance тесты
	$(PYTEST) tests/performance/ -m "performance" -v

test-coverage: ## Запустить тесты с отчетом покрытия
	$(PYTEST) tests/ --cov=. --cov-report=html --cov-report=term

test-quick: ## Быстрые тесты (без slow маркера)
	$(PYTEST) tests/unit/ -m "not slow" -v --tb=short

test-smoke: ## Smoke тесты для CI
	$(PYTEST) tests/ -m "smoke" -v --tb=short

test-failed: ## Перезапустить только проваленные тесты
	$(PYTEST) tests/ --lf -v

test-watch: ## Запустить тесты в режиме watch (требует pytest-watch)
	ptw tests/ -- -x --tb=short

test-chain: ## Запустить цепочку тестов
	@echo "🔗 Запуск цепочки тестов..."
	@$(MAKE) test-unit && \
	$(MAKE) test-ml && \
	$(MAKE) test-integration && \
	echo "✅ Все тесты в цепочке пройдены успешно!"

test-parallel: ## Запустить тесты параллельно (требует pytest-xdist)
	$(PYTEST) tests/ -n auto -v

# ==================== ML специфичные тесты ====================

test-ml-models: ## Тестировать ML модели
	$(PYTEST) tests/unit/ml/test_patchtst_model.py tests/unit/ml/test_feature_engineering.py -v

test-ml-pipeline: ## Тестировать ML pipeline
	$(PYTEST) tests/unit/ml/test_ml_manager.py tests/unit/ml/test_ml_signal_processor.py -v

test-ml-integration: ## Интеграционный тест ML
	$(PYTHON) scripts/test_ml_integration.py

# ==================== Качество кода ====================

lint: ## Проверить код линтерами
	$(RUFF) check .
	$(MYPY) . --ignore-missing-imports

format: ## Форматировать код
	$(BLACK) .
	$(RUFF) check --fix .

check: lint test-quick ## Быстрая проверка перед коммитом

# ==================== База данных ====================

db-test: ## Запустить тесты БД
	$(PYTEST) tests/unit/database/ -v

db-migrate-test: ## Тестировать миграции
	alembic upgrade head
	alembic downgrade -1
	alembic upgrade head

# ==================== Очистка ====================

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage*" -delete

clean-all: clean ## Полная очистка включая логи
	rm -rf data/logs/*
	rm -rf data/cache/*
	rm -rf data/temp/*

# ==================== Запуск приложения ====================

run: ## Запустить торговый движок
	$(PYTHON) main.py

run-web: ## Запустить веб-интерфейс
	$(PYTHON) web/launcher.py --reload --debug

run-all: ## Запустить все компоненты
	./start_all.sh

# ==================== Docker ====================

docker-build: ## Собрать Docker образ
	docker build -t bot-trading-v3:latest .

docker-run: ## Запустить в Docker
	docker-compose up -d

docker-test: ## Запустить тесты в Docker
	docker-compose run --rm app pytest tests/

# ==================== Документация ====================

docs: ## Сгенерировать документацию
	cd docs && sphinx-build -b html . _build/html

docs-serve: ## Запустить сервер документации
	cd docs/_build/html && python -m http.server 8080

# ==================== Утилиты ====================

show-todo: ## Показать TODO в коде
	@grep -r "TODO\|FIXME\|XXX" --include="*.py" . | grep -v ".git"

count-lines: ## Подсчитать строки кода
	@find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" | xargs wc -l | tail -1

deps-tree: ## Показать дерево зависимостей
	pipdeptree

security-check: ## Проверка безопасности зависимостей
	safety check
	bandit -r . -f json -o bandit-report.json

# ==================== Релиз ====================

version: ## Показать текущую версию
	@cat VERSION

bump-patch: ## Увеличить patch версию
	bumpversion patch

bump-minor: ## Увеличить minor версию
	bumpversion minor

bump-major: ## Увеличить major версию
	bumpversion major
