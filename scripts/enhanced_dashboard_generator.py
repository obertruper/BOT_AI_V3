#!/usr/bin/env python3
"""
🎨 Enhanced Dashboard Generator for BOT_AI_V3
Генерирует интерактивный HTML дашборд с подробными деталями для каждого компонента
"""

from datetime import datetime


class EnhancedDashboardGenerator:
    """Генератор улучшенного интерактивного дашборда"""

    def __init__(self):
        self.component_descriptions = {
            "unit_tests": {
                "description": "Базовые unit тесты для проверки отдельных функций и методов системы",
                "checks": [
                    "Тест простых функций",
                    "Валидация входных данных",
                    "Проверка возвращаемых значений",
                ],
                "importance": "🔥 Критично",
            },
            "database_tests": {
                "description": "Тестирование подключения и операций с PostgreSQL базой данных",
                "checks": [
                    "Подключение к PostgreSQL:5555",
                    "CRUD операции",
                    "Миграции базы данных",
                ],
                "importance": "🔥 Критично",
            },
            "trading_tests": {
                "description": "Проверка торговых алгоритмов и обработки рыночных сигналов",
                "checks": ["Генерация торговых сигналов", "Обработка ордеров", "Расчет PnL"],
                "importance": "🔥 Критично",
            },
            "ml_tests": {
                "description": "Тестирование ML компонентов и предсказательных моделей",
                "checks": ["Загрузка модели", "Обработка признаков", "Генерация предсказаний"],
                "importance": "⚡ Высоко",
            },
            "integration_tests": {
                "description": "Комплексное тестирование взаимодействия между компонентами системы",
                "checks": ["API интеграция", "End-to-end workflows", "Межсервисное взаимодействие"],
                "importance": "⚡ Высоко",
            },
            "performance_tests": {
                "description": "Тестирование производительности и нагрузочные тесты",
                "checks": [
                    "Время отклика < 50ms",
                    "Пропускная способность",
                    "Использование памяти",
                ],
                "importance": "📊 Средне",
            },
            "code_quality": {
                "description": "Проверка качества кода с помощью статических анализаторов",
                "checks": ["Ruff статический анализ", "Проверка стиля кода", "Обнаружение ошибок"],
                "importance": "📊 Средне",
            },
            "type_check": {
                "description": "Проверка типов Python с помощью MyPy",
                "checks": ["Статическая типизация", "Проверка аннотаций", "Совместимость типов"],
                "importance": "📊 Средне",
            },
            "coverage_report": {
                "description": "Анализ покрытия кода тестами для оценки качества тестирования",
                "checks": [
                    "Измерение покрытия",
                    "Генерация отчетов",
                    "Выявление непротестированного кода",
                ],
                "importance": "📊 Средне",
            },
            "security_check": {
                "description": "Проверка безопасности кода и поиск утечек секретных данных",
                "checks": ["Поиск API ключей", "Обнаружение паролей", "Проверка секретов в коде"],
                "importance": "🛡️ Безопасность",
            },
            "code_usage_analyzer_tests": {
                "description": "Тестирование системы анализа использования кода и поиска неиспользуемых файлов",
                "checks": [
                    "Сканирование Python файлов",
                    "AST анализ импортов",
                    "Построение графа зависимостей",
                    "Детекция неиспользуемых файлов",
                ],
                "importance": "🔍 Анализ",
            },
            "code_analyzer_validation_tests": {
                "description": "Валидация точности анализатора кода и проверка на ложные срабатывания",
                "checks": [
                    "Проверка точности на реальном проекте",
                    "Тесты производительности",
                    "Валидация результатов",
                    "Предотвращение ложных срабатываний",
                ],
                "importance": "✅ Валидация",
            },
            "code_analysis_report": {
                "description": "Полный анализ использования кода с генерацией отчетов о неиспользуемых файлах",
                "checks": [
                    "Анализ 520+ Python файлов",
                    "Выявление неиспользуемых файлов",
                    "HTML и JSON отчеты",
                    "Анализ устаревших файлов",
                ],
                "importance": "📊 Отчетность",
            },
            "feature_engineering_tests": {
                "description": "Тестирование системы инжиниринга признаков для ML модели",
                "checks": [
                    "Генерация 240+ признаков",
                    "Валидация технических индикаторов",
                    "Проверка качества данных",
                ],
                "importance": "⚡ Высоко",
            },
            "exchanges_tests": {
                "description": "Тестирование интеграции с 7 криптовалютными биржами",
                "checks": [
                    "API подключения",
                    "WebSocket потоки",
                    "Обработка ордеров",
                    "Управление балансами",
                ],
                "importance": "🔥 Критично",
            },
            "web_api_tests": {
                "description": "Тестирование REST API и веб-интерфейса",
                "checks": [
                    "HTTP endpoints",
                    "Аутентификация",
                    "Валидация данных",
                    "Производительность API",
                ],
                "importance": "⚡ Высоко",
            },
            "core_orchestrator_tests": {
                "description": "Тестирование системного оркестратора и координации компонентов",
                "checks": [
                    "Запуск процессов",
                    "Межкомпонентное взаимодействие",
                    "Обработка ошибок",
                ],
                "importance": "🔥 Критично",
            },
            "trading_engine_tests": {
                "description": "Комплексное тестирование торгового движка",
                "checks": [
                    "Обработка сигналов",
                    "Управление ордерами",
                    "Расчет PnL",
                    "Риск-менеджмент",
                ],
                "importance": "🔥 Критично",
            },
            "ml_manager_tests": {
                "description": "Тестирование ML менеджера и модели UnifiedPatchTST",
                "checks": ["Загрузка модели", "GPU инициализация", "Обработка предсказаний"],
                "importance": "⚡ Высоко",
            },
            "core_system_tests": {
                "description": "Тестирование базовых системных компонентов",
                "checks": ["Системные утилиты", "Конфигурация", "Логирование"],
                "importance": "📊 Средне",
            },
            "main_application_tests": {
                "description": "Тестирование главного приложения и точки входа",
                "checks": ["Инициализация приложения", "Загрузка конфигурации", "Запуск сервисов"],
                "importance": "🔥 Критично",
            },
            "unified_launcher_tests": {
                "description": "Тестирование единого лаунчера системы",
                "checks": ["Запуск всех компонентов", "Мониторинг процессов", "Graceful shutdown"],
                "importance": "🔥 Критично",
            },
            "ml_prediction_logger_tests": {
                "description": "Тестирование детального логирования ML предсказаний",
                "checks": [
                    "Форматирование таблиц",
                    "Сохранение в БД",
                    "Дедупликация",
                    "Статистика",
                ],
                "importance": "📊 Средне",
            },
            "ml_manager_enhanced_tests": {
                "description": "Расширенные тесты ML менеджера с новым логированием",
                "checks": ["Улучшенное логирование", "GPU мониторинг", "Производительность"],
                "importance": "⚡ Высоко",
            },
        }

    def generate_interactive_dashboard(
        self, stats: dict, components: dict, results: dict = None
    ) -> str:
        """Генерирует интерактивный HTML дашборд"""

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOT_AI_V3 Interactive Test Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }}
        h1 {{
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #666;
            font-size: 1.2em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s;
            cursor: pointer;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-icon {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #999;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .components {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .component-item {{
            display: flex;
            flex-direction: column;
            margin-bottom: 15px;
            border: 1px solid #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
            transition: all 0.3s;
        }}
        .component-item:hover {{
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .component-header {{
            display: flex;
            align-items: center;
            padding: 15px;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .component-header:hover {{
            background: #f8f9fa;
        }}
        .component-icon {{
            font-size: 1.5em;
            margin-right: 15px;
        }}
        .component-name {{
            flex: 1;
            font-weight: 500;
            color: #333;
        }}
        .component-status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
            margin-right: 10px;
        }}
        .expand-icon {{
            font-size: 1.2em;
            color: #999;
            transition: transform 0.3s;
        }}
        .expand-icon.expanded {{
            transform: rotate(180deg);
        }}
        .status-success {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-partial {{
            background: #fff3cd;
            color: #856404;
        }}
        .status-pending {{
            background: #e2e3e5;
            color: #6c757d;
        }}
        .component-details {{
            display: none;
            padding: 25px;
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }}
        .component-details.expanded {{
            display: block;
            animation: slideDown 0.3s ease-out;
        }}
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .component-description {{
            color: #495057;
            margin-bottom: 20px;
            line-height: 1.6;
            font-size: 1.05em;
        }}
        .importance-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 600;
            margin-bottom: 15px;
        }}
        .importance-critical {{ background: #ffe6e6; color: #d73527; }}
        .importance-high {{ background: #fff3cd; color: #856404; }}
        .importance-medium {{ background: #e7f3ff; color: #0066cc; }}
        .importance-security {{ background: #e6f7ff; color: #1890ff; }}
        .importance-analysis {{ background: #f0f9ff; color: #0284c7; }}
        .importance-validation {{ background: #ecfdf5; color: #059669; }}
        .importance-reporting {{ background: #fef3f2; color: #dc2626; }}
        .checks-list {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .checks-title {{
            font-weight: 600;
            color: #374151;
            margin-bottom: 10px;
        }}
        .check-item {{
            display: flex;
            align-items: center;
            padding: 5px 0;
            color: #6b7280;
        }}
        .check-item::before {{
            content: "✓";
            color: #10b981;
            font-weight: bold;
            margin-right: 8px;
        }}
        .component-output {{
            background: #1a202c;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.85em;
            line-height: 1.4;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            margin-top: 15px;
        }}
        .output-header {{
            color: #a0aec0;
            font-size: 0.8em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .coverage-bar {{
            width: 100%;
            height: 40px;
            background: #f0f0f0;
            border-radius: 20px;
            overflow: hidden;
            margin-top: 30px;
            position: relative;
        }}
        .coverage-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981, #059669);
            transition: width 2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.1em;
        }}
        .timestamp {{
            text-align: center;
            color: #999;
            margin-top: 30px;
            font-size: 0.9em;
        }}
        .legend {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .legend h3 {{
            color: #333;
            margin-bottom: 15px;
        }}
        .legend-item {{
            display: inline-flex;
            align-items: center;
            margin-right: 25px;
            margin-bottom: 10px;
        }}
        .legend-icon {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            margin-right: 10px;
        }}
        .legend-success {{ background: #10b981; }}
        .legend-failed {{ background: #dc2626; }}
        .legend-partial {{ background: #f59e0b; }}
        .legend-pending {{ background: #6b7280; }}
        .filter-buttons {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .filter-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            margin: 0 5px;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .filter-btn:hover {{
            background: #5a67d8;
        }}
        .filter-btn.active {{
            background: #4c51bf;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 BOT_AI_V3 Interactive Test Dashboard</h1>
            <div class="subtitle">Comprehensive Testing & Code Analysis • Click components to expand details</div>
        </div>

        <div class="legend">
            <h3>📊 Status Legend & Quick Actions</h3>
            <div class="legend-item">
                <div class="legend-icon legend-success"></div>
                <span>Success - All tests passed</span>
            </div>
            <div class="legend-item">
                <div class="legend-icon legend-partial"></div>
                <span>Partial - Some tests failed</span>
            </div>
            <div class="legend-item">
                <div class="legend-icon legend-failed"></div>
                <span>Failed - Major issues found</span>
            </div>
            <div class="legend-item">
                <div class="legend-icon legend-pending"></div>
                <span>Pending - Not executed</span>
            </div>

            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterComponents('all')">Show All</button>
                <button class="filter-btn" onclick="filterComponents('success')">Success Only</button>
                <button class="filter-btn" onclick="filterComponents('issues')">Issues Only</button>
                <button class="filter-btn" onclick="expandAll()">Expand All</button>
                <button class="filter-btn" onclick="collapseAll()">Collapse All</button>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card" onclick="showOverallStats()">
                <div class="stat-icon">📋</div>
                <div class="stat-value">{stats["total_tests"]}</div>
                <div class="stat-label">Total Tests</div>
            </div>

            <div class="stat-card" onclick="filterComponents('success')">
                <div class="stat-icon">✅</div>
                <div class="stat-value">{stats["passed_tests"]}</div>
                <div class="stat-label">Passed Tests</div>
            </div>

            <div class="stat-card" onclick="filterComponents('issues')">
                <div class="stat-icon">❌</div>
                <div class="stat-value">{stats["failed_tests"]}</div>
                <div class="stat-label">Failed Tests</div>
            </div>

            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-value">{stats["coverage_percent"]:.1f}%</div>
                <div class="stat-label">Code Coverage</div>
            </div>

            <div class="stat-card">
                <div class="stat-icon">⏱️</div>
                <div class="stat-value">{stats["execution_time"]:.1f}s</div>
                <div class="stat-label">Execution Time</div>
            </div>

            <div class="stat-card">
                <div class="stat-icon">🎯</div>
                <div class="stat-value">{len([c for c in components.values() if c["status"] == "success"])}/{len(components)}</div>
                <div class="stat-label">Components Passed</div>
            </div>
        </div>

        <div class="components">
            <h2 style="margin-bottom: 20px; color: #333;">🔍 Test Components Details • Click to Expand</h2>
            {self._generate_interactive_components(components, results or {{}})}

            <div class="coverage-bar">
                <div class="coverage-fill" style="width: {stats["coverage_percent"]}%">
                    {stats["coverage_percent"]:.1f}% Code Coverage
                </div>
            </div>
        </div>

        <div class="timestamp">
            Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} • Interactive Dashboard v2.0 • BOT_AI_V3
        </div>
    </div>

    <script>
        let expandedComponents = new Set();

        function toggleComponent(componentId) {{
            const details = document.getElementById('details-' + componentId);
            const icon = document.getElementById('icon-' + componentId);

            if (details.classList.contains('expanded')) {{
                details.classList.remove('expanded');
                icon.classList.remove('expanded');
                expandedComponents.delete(componentId);
            }} else {{
                details.classList.add('expanded');
                icon.classList.add('expanded');
                expandedComponents.add(componentId);
            }}
        }}

        function filterComponents(filter) {{
            const components = document.querySelectorAll('.component-item');
            const buttons = document.querySelectorAll('.filter-btn');

            // Update active button
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            components.forEach(comp => {{
                const statusEl = comp.querySelector('.component-status');
                const statusText = statusEl.textContent.toLowerCase();

                let show = false;
                if (filter === 'all') {{
                    show = true;
                }} else if (filter === 'success' && statusText.includes('success')) {{
                    show = true;
                }} else if (filter === 'issues' && (statusText.includes('failed') || statusText.includes('partial'))) {{
                    show = true;
                }}

                comp.style.display = show ? 'flex' : 'none';
            }});
        }}

        function expandAll() {{
            const components = document.querySelectorAll('.component-item');
            components.forEach(comp => {{
                if (comp.style.display !== 'none') {{
                    const componentId = comp.id.replace('component-', '');
                    const details = document.getElementById('details-' + componentId);
                    const icon = document.getElementById('icon-' + componentId);

                    if (!details.classList.contains('expanded')) {{
                        details.classList.add('expanded');
                        icon.classList.add('expanded');
                        expandedComponents.add(componentId);
                    }}
                }}
            }});
        }}

        function collapseAll() {{
            const components = document.querySelectorAll('.component-item');
            components.forEach(comp => {{
                const componentId = comp.id.replace('component-', '');
                const details = document.getElementById('details-' + componentId);
                const icon = document.getElementById('icon-' + componentId);

                if (details.classList.contains('expanded')) {{
                    details.classList.remove('expanded');
                    icon.classList.remove('expanded');
                    expandedComponents.delete(componentId);
                }}
            }});
        }}

        function showOverallStats() {{
            const successRate = ({stats["passed_tests"]} / Math.max({stats["total_tests"]}, 1) * 100).toFixed(1);
            const failureRate = ({stats["failed_tests"]} / Math.max({stats["total_tests"]}, 1) * 100).toFixed(1);
            const componentsSuccessRate = ({len([c for c in components.values() if c["status"] == "success"])} / {len(components)} * 100).toFixed(1);

            alert(`📊 BOT_AI_V3 Testing Overview\\n\\n` +
                  `✅ Tests Passed: {stats["passed_tests"]} (${successRate}%)\\n` +
                  `❌ Tests Failed: {stats["failed_tests"]} (${failureRate}%)\\n` +
                  `📋 Total Tests: {stats["total_tests"]}\\n\\n` +
                  `🎯 Component Success Rate: ${componentsSuccessRate}%\\n` +
                  `📊 Code Coverage: {stats["coverage_percent"]:.1f}%\\n` +
                  `⏱️ Total Execution Time: {stats["execution_time"]:.2f}s\\n\\n` +
                  `💡 Quick Actions:\\n` +
                  `• Click "Issues Only" to focus on failures\\n` +
                  `• Expand components for detailed information\\n` +
                  `• Check output logs for debugging`);
        }}

        // Auto-expand first failed/partial component
        document.addEventListener('DOMContentLoaded', function() {{
            const issueComponent = document.querySelector('.status-failed, .status-partial');
            if (issueComponent) {{
                const componentItem = issueComponent.closest('.component-item');
                const componentId = componentItem.id.replace('component-', '');
                setTimeout(() => toggleComponent(componentId), 1000);
            }}
        }});

        // Add search functionality
        function searchComponents(query) {{
            const components = document.querySelectorAll('.component-item');
            const searchQuery = query.toLowerCase();

            components.forEach(comp => {{
                const name = comp.querySelector('.component-name').textContent.toLowerCase();
                const description = comp.querySelector('.component-description')?.textContent.toLowerCase() || '';

                if (name.includes(searchQuery) || description.includes(searchQuery)) {{
                    comp.style.display = 'flex';
                }} else {{
                    comp.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
        """

    def _generate_interactive_components(self, components: dict, results: dict) -> str:
        """Генерирует интерактивные компоненты с деталями"""
        html_components = []

        for key, component in components.items():
            component_info = self.component_descriptions.get(key, {})
            description = component_info.get("description", "Описание компонента не доступно")
            checks = component_info.get("checks", [])
            importance = component_info.get("importance", "📊 Средне")

            # Определяем класс важности
            importance_class = self._get_importance_class(importance)

            # Получаем детали результата
            result_details = results.get(key, {})
            output = result_details.get("output", "Вывод не доступен")
            error = result_details.get("error", "")

            # Объединяем output и error
            full_output = f"{output}\n{error}".strip() if error else output

            html_components.append(
                f"""
            <div class="component-item" id="component-{key}">
                <div class="component-header" onclick="toggleComponent('{key}')">
                    <div class="component-icon">{component["icon"]}</div>
                    <div class="component-name">{component["name"]}</div>
                    <div class="component-status status-{component["status"]}">{component["status"].upper()}</div>
                    <div class="expand-icon" id="icon-{key}">▼</div>
                </div>

                <div class="component-details" id="details-{key}">
                    <div class="importance-badge {importance_class}">{importance}</div>

                    <div class="component-description">{description}</div>

                    <div class="checks-list">
                        <div class="checks-title">🔍 Что проверяется:</div>
                        {"".join(f'<div class="check-item">{check}</div>' for check in checks)}
                    </div>

                    <div class="component-output">
                        <div class="output-header">📄 Вывод выполнения:</div>
                        {self._format_output_for_html(full_output)}
                    </div>
                </div>
            </div>
            """
            )

        return "".join(html_components)

    def _get_importance_class(self, importance: str) -> str:
        """Определяет CSS класс для значка важности"""
        if "Критично" in importance:
            return "importance-critical"
        elif "Высоко" in importance:
            return "importance-high"
        elif "Средне" in importance:
            return "importance-medium"
        elif "Безопасность" in importance:
            return "importance-security"
        elif "Анализ" in importance:
            return "importance-analysis"
        elif "Валидация" in importance:
            return "importance-validation"
        elif "Отчетность" in importance:
            return "importance-reporting"
        else:
            return "importance-medium"

    def _format_output_for_html(self, output: str) -> str:
        """Форматирует вывод для HTML"""
        if not output:
            return "Вывод отсутствует"

        # Ограничиваем длину для отображения
        if len(output) > 2000:
            output = output[:2000] + "\n... (вывод обрезан)"

        # Экранируем HTML символы
        import html

        return html.escape(output)


# Функция интеграции с основным оркестратором
def integrate_enhanced_dashboard():
    """Интегрирует улучшенный дашборд в основной оркестратор"""
    generator = EnhancedDashboardGenerator()
    return generator
