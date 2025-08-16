#!/usr/bin/env python3
"""
Шаблоны workflow для различных типов задач кросс-верификации

Автор: BOT Trading v3 Team
"""

from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Типы задач для кросс-верификации"""

    STRATEGY_DEVELOPMENT = "strategy_development"
    ARCHITECTURE_REVIEW = "architecture_review"
    CODE_REVIEW = "code_review"
    RISK_MANAGEMENT = "risk_management"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    DOCUMENTATION = "documentation"
    ALGORITHM_DESIGN = "algorithm_design"
    MARKET_ANALYSIS = "market_analysis"


@dataclass
class WorkflowTemplate:
    """Шаблон workflow для определенного типа задач"""

    name: str
    task_type: TaskType
    description: str
    prompt_template: str
    ai_systems: list[str]
    max_iterations: int
    specific_config: dict
    follow_up_questions: list[str]


class WorkflowTemplates:
    """Коллекция шаблонов workflow"""

    @staticmethod
    def get_strategy_development_template() -> WorkflowTemplate:
        """Шаблон для разработки торговых стратегий"""
        return WorkflowTemplate(
            name="Разработка торговой стратегии",
            task_type=TaskType.STRATEGY_DEVELOPMENT,
            description="Кросс-верификация новых торговых стратегий",
            prompt_template="""
Ты эксперт по разработке торговых стратегий для криптовалютного рынка.

ЗАДАЧА: {task_description}

Контекст:
- Торговый бот BOT Trading v3
- Целевой рынок: Криптовалюты (Bitcoin, Ethereum, основные альткоины)
- Горизонт торговли: {timeframe}
- Целевая доходность: {target_return}% в месяц
- Максимальная просадка: {max_drawdown}%

Требуется разработать:
1. **Архитектуру стратегии** - структура классов и модулей
2. **Торговые сигналы** - логика входа и выхода
3. **Управление рисками** - stop-loss, take-profit, размер позиций
4. **Параметры и настройки** - оптимальные значения для индикаторов
5. **Бэктестинг** - структура для валидации стратегии

Детали задачи:
{task_content}

Отвечай максимально подробно, с конкретными формулами, кодом и примерами.
            """,
            ai_systems=["chatgpt", "grok", "claude"],
            max_iterations=4,
            specific_config={
                "include_backtesting": True,
                "include_code_examples": True,
                "focus_on_crypto": True,
            },
            follow_up_questions=[
                "Какие риски не учтены в этой стратегии?",
                "Как адаптировать стратегию для разных рыночных условий?",
                "Какие дополнительные индикаторы улучшат производительность?",
                "Как оптимизировать параметры для разных криптовалют?",
            ],
        )

    @staticmethod
    def get_architecture_review_template() -> WorkflowTemplate:
        """Шаблон для ревью архитектуры"""
        return WorkflowTemplate(
            name="Ревью архитектуры системы",
            task_type=TaskType.ARCHITECTURE_REVIEW,
            description="Анализ и улучшение архитектуры торгового бота",
            prompt_template="""
Ты архитектор программных систем, эксперт по высокопроизводительным торговым системам.

ЗАДАЧА: {task_description}

Контекст системы:
- Проект: BOT Trading v3
- Технологии: Python 3.11+, asyncio, PostgreSQL, Redis
- Архитектура: Модульная, микросервисная
- Нагрузка: {expected_load} запросов/сек
- Биржи: {exchange_count} бирж одновременно

Требуется проанализировать:
1. **Масштабируемость** - способность выдерживать нагрузку
2. **Надежность** - отказоустойчивость и восстановление
3. **Производительность** - латентность и пропускная способность
4. **Безопасность** - защита API ключей и данных
5. **Maintainability** - простота поддержки и развития

Архитектура для анализа:
{task_content}

Дай конкретные рекомендации по улучшению каждого аспекта.
            """,
            ai_systems=["chatgpt", "grok", "claude"],
            max_iterations=3,
            specific_config={
                "focus_on_performance": True,
                "include_diagrams": True,
                "consider_scalability": True,
            },
            follow_up_questions=[
                "Какие узкие места могут возникнуть при росте нагрузки?",
                "Как обеспечить zero-downtime deployment?",
                "Какие метрики важно мониторить?",
                "Как оптимизировать для низкой латентности?",
            ],
        )

    @staticmethod
    def get_risk_management_template() -> WorkflowTemplate:
        """Шаблон для системы управления рисками"""
        return WorkflowTemplate(
            name="Система управления рисками",
            task_type=TaskType.RISK_MANAGEMENT,
            description="Разработка и анализ системы риск-менеджмента",
            prompt_template="""
Ты эксперт по риск-менеджменту в алготрейдинге и количественных финансах.

ЗАДАЧА: {task_description}

Контекст торговли:
- Рынок: Криптовалюты (высокая волатильность)
- Капитал: {capital_size}
- Максимальный риск на сделку: {max_risk_per_trade}%
- Целевая доходность: {target_return}% в месяц
- Допустимая просадка: {max_drawdown}%

Требуется разработать:
1. **Position Sizing** - расчет размера позиций (Kelly, Fixed %, Volatility-based)
2. **Stop Loss системы** - фиксированные, динамические, trailing stops
3. **Take Profit стратегии** - частичное закрытие, масштабирование
4. **Portfolio Risk** - корреляции, концентрация, диверсификация
5. **Risk Metrics** - VaR, Sharpe, Sortino, Maximum Drawdown

Детали задачи:
{task_content}

Предоставь математические формулы, алгоритмы и примеры реализации.
            """,
            ai_systems=["chatgpt", "grok", "claude"],
            max_iterations=4,
            specific_config={
                "include_formulas": True,
                "focus_on_crypto_specifics": True,
                "include_backtesting_metrics": True,
            },
            follow_up_questions=[
                "Как адаптировать риск-менеджмент для разных волатильностей?",
                "Какие дополнительные риски специфичны для крипто?",
                "Как оптимизировать risk-reward соотношения?",
                "Какие early warning системы нужны?",
            ],
        )

    @staticmethod
    def get_code_review_template() -> WorkflowTemplate:
        """Шаблон для ревью кода"""
        return WorkflowTemplate(
            name="Ревью кода",
            task_type=TaskType.CODE_REVIEW,
            description="Анализ качества кода и предложения улучшений",
            prompt_template="""
Ты senior разработчик Python, эксперт по code review и best practices.

ЗАДАЧА: {task_description}

Контекст проекта:
- Язык: Python 3.11+
- Стиль: PEP 8, type hints обязательны
- Тестирование: pytest, coverage >90%
- Производительность: Критична для HFT
- Асинхронность: asyncio/aiohttp

Критерии ревью:
1. **Качество кода** - читаемость, структура, naming conventions
2. **Производительность** - оптимизация алгоритмов, memory usage
3. **Безопасность** - уязвимости, валидация данных
4. **Тестируемость** - покрытие тестами, mock-friendly design
5. **Maintainability** - модульность, documentation, SOLID principles

Код для ревью:
{task_content}

Дай детальный анализ с конкретными примерами улучшений.
            """,
            ai_systems=["chatgpt", "grok", "claude"],
            max_iterations=2,
            specific_config={
                "include_performance_tips": True,
                "check_security": True,
                "suggest_tests": True,
            },
            follow_up_questions=[
                "Какие потенциальные баги могут возникнуть?",
                "Как улучшить производительность этого кода?",
                "Какие тесты нужно добавить?",
                "Как сделать код более maintainable?",
            ],
        )

    @staticmethod
    def get_performance_optimization_template() -> WorkflowTemplate:
        """Шаблон для оптимизации производительности"""
        return WorkflowTemplate(
            name="Оптимизация производительности",
            task_type=TaskType.PERFORMANCE_OPTIMIZATION,
            description="Анализ и улучшение производительности системы",
            prompt_template="""
Ты эксперт по оптимизации производительности высоконагруженных систем.

ЗАДАЧА: {task_description}

Контекст системы:
- Требования: Latency <{target_latency}ms, Throughput >{target_throughput} ops/sec
- Профилирование: {profiling_data}
- Bottlenecks: {current_bottlenecks}
- Hardware: {hardware_specs}

Области оптимизации:
1. **CPU оптимизация** - алгоритмы, кэширование, parallel processing
2. **Memory optimization** - memory pools, garbage collection, memory leaks
3. **I/O оптимизация** - async I/O, connection pooling, batch operations
4. **Network optimization** - compression, keep-alive, multiplexing
5. **Database optimization** - indexes, query optimization, connection pooling

Текущая реализация:
{task_content}

Предложи конкретные техники оптимизации с примерами кода.
            """,
            ai_systems=["chatgpt", "grok", "claude"],
            max_iterations=3,
            specific_config={
                "include_benchmarks": True,
                "focus_on_python": True,
                "include_profiling": True,
            },
            follow_up_questions=[
                "Какие инструменты лучше использовать для профилирования?",
                "Как измерить эффективность оптимизаций?",
                "Какие trade-offs между скоростью и памятью?",
                "Как оптимизировать для конкретного hardware?",
            ],
        )

    @staticmethod
    def get_all_templates() -> dict[TaskType, WorkflowTemplate]:
        """Получить все доступные шаблоны"""
        return {
            TaskType.STRATEGY_DEVELOPMENT: WorkflowTemplates.get_strategy_development_template(),
            TaskType.ARCHITECTURE_REVIEW: WorkflowTemplates.get_architecture_review_template(),
            TaskType.RISK_MANAGEMENT: WorkflowTemplates.get_risk_management_template(),
            TaskType.CODE_REVIEW: WorkflowTemplates.get_code_review_template(),
            TaskType.PERFORMANCE_OPTIMIZATION: WorkflowTemplates.get_performance_optimization_template(),
        }

    @staticmethod
    def format_prompt(template: WorkflowTemplate, **kwargs) -> str:
        """Форматирование промпта с параметрами"""
        # Дефолтные значения
        defaults = {
            "timeframe": "1-7 дней",
            "target_return": "15",
            "max_drawdown": "10",
            "expected_load": "1000",
            "exchange_count": "5",
            "capital_size": "$10,000",
            "max_risk_per_trade": "2",
            "target_latency": "10",
            "target_throughput": "1000",
            "profiling_data": "CPU: 80%, Memory: 60%, I/O wait: 15%",
            "current_bottlenecks": "Database queries, API rate limits",
            "hardware_specs": "8 CPU cores, 16GB RAM, SSD storage",
        }

        # Объединяем с переданными параметрами
        format_kwargs = {**defaults, **kwargs}

        return template.prompt_template.format(**format_kwargs)


# Предустановленные workflow для быстрого использования
QUICK_WORKFLOWS = {
    "scalping_strategy": {
        "description": "Разработка стратегии скальпинга",
        "template_type": TaskType.STRATEGY_DEVELOPMENT,
        "params": {
            "timeframe": "1-15 минут",
            "target_return": "5",
            "max_drawdown": "3",
        },
    },
    "arbitrage_strategy": {
        "description": "Арбитражная стратегия между биржами",
        "template_type": TaskType.STRATEGY_DEVELOPMENT,
        "params": {
            "timeframe": "Секунды-минуты",
            "target_return": "20",
            "max_drawdown": "5",
        },
    },
    "hft_architecture": {
        "description": "Архитектура для высокочастотной торговли",
        "template_type": TaskType.ARCHITECTURE_REVIEW,
        "params": {"expected_load": "10000", "target_latency": "1"},
    },
    "risk_system": {
        "description": "Comprehensive система управления рисками",
        "template_type": TaskType.RISK_MANAGEMENT,
        "params": {"capital_size": "$50,000", "max_risk_per_trade": "1"},
    },
    "trading_engine_optimization": {
        "description": "Оптимизация торгового движка",
        "template_type": TaskType.PERFORMANCE_OPTIMIZATION,
        "params": {"target_latency": "5", "target_throughput": "5000"},
    },
}
