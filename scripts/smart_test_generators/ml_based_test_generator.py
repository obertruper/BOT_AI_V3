#!/usr/bin/env python3
"""
Умный генератор тестов на основе машинного обучения для BOT_AI_V3
Анализирует паттерны кода и генерирует соответствующие тесты
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent


class CodePatternType(Enum):
    """Типы паттернов кода"""

    ASYNC_FUNCTION = "async_function"
    DATABASE_OPERATION = "database_operation"
    API_ENDPOINT = "api_endpoint"
    ML_PREDICTION = "ml_prediction"
    TRADING_LOGIC = "trading_logic"
    EXCHANGE_OPERATION = "exchange_operation"
    WEB_SOCKET_HANDLER = "websocket_handler"
    VALIDATION_FUNCTION = "validation_function"
    UTILITY_FUNCTION = "utility_function"
    CLASS_METHOD = "class_method"
    STATIC_METHOD = "static_method"
    PROPERTY_METHOD = "property_method"


@dataclass
class CodePattern:
    """Паттерн кода"""

    pattern_type: CodePatternType
    confidence: float
    characteristics: dict[str, Any]
    test_strategies: list[str]


@dataclass
class TestCase:
    """Тестовый случай"""

    name: str
    code: str
    description: str
    test_type: str  # unit, integration, e2e
    priority: int  # 1-5
    dependencies: list[str]


class CodePatternAnalyzer:
    """
    Анализатор паттернов кода для определения типов функций
    """

    def __init__(self):
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> dict[CodePatternType, dict]:
        """Инициализирует паттерны поиска"""
        return {
            CodePatternType.ASYNC_FUNCTION: {
                "keywords": ["async", "await", "asyncio"],
                "imports": ["asyncio", "aiohttp", "asyncpg"],
                "decorators": ["@asyncio.coroutine"],
            },
            CodePatternType.DATABASE_OPERATION: {
                "keywords": ["SELECT", "INSERT", "UPDATE", "DELETE", "query", "execute", "fetch"],
                "imports": ["psycopg2", "asyncpg", "sqlalchemy", "database"],
                "functions": ["connect", "cursor", "execute", "fetchall", "commit"],
            },
            CodePatternType.API_ENDPOINT: {
                "decorators": ["@app.route", "@router.get", "@router.post", "@api.route"],
                "keywords": ["request", "response", "json", "status_code"],
                "imports": ["fastapi", "flask", "tornado", "starlette"],
            },
            CodePatternType.ML_PREDICTION: {
                "keywords": ["predict", "model", "inference", "features", "prediction"],
                "imports": ["torch", "tensorflow", "sklearn", "numpy", "pandas"],
                "functions": ["fit", "predict", "transform", "score"],
            },
            CodePatternType.TRADING_LOGIC: {
                "keywords": ["order", "trade", "position", "signal", "strategy", "portfolio"],
                "imports": ["trading", "strategies", "exchanges"],
                "functions": ["buy", "sell", "close_position", "calculate_pnl"],
            },
            CodePatternType.EXCHANGE_OPERATION: {
                "keywords": ["exchange", "ticker", "orderbook", "balance", "symbol"],
                "imports": ["exchanges", "bybit", "binance", "okx"],
                "functions": ["get_balance", "place_order", "cancel_order"],
            },
            CodePatternType.WEB_SOCKET_HANDLER: {
                "keywords": ["websocket", "connect", "disconnect", "message", "stream"],
                "imports": ["websockets", "socket.io", "tornado.websocket"],
                "decorators": ["@websocket.route"],
            },
        }

    def analyze_function(self, func_info: dict) -> list[CodePattern]:
        """Анализирует функцию и определяет её паттерны"""
        patterns = []

        for pattern_type, pattern_config in self.patterns.items():
            confidence = self._calculate_pattern_confidence(func_info, pattern_config)

            if confidence > 0.3:  # Пороговое значение
                characteristics = self._extract_characteristics(func_info, pattern_type)
                test_strategies = self._get_test_strategies(pattern_type, characteristics)

                patterns.append(
                    CodePattern(
                        pattern_type=pattern_type,
                        confidence=confidence,
                        characteristics=characteristics,
                        test_strategies=test_strategies,
                    )
                )

        return sorted(patterns, key=lambda p: p.confidence, reverse=True)

    def _calculate_pattern_confidence(self, func_info: dict, pattern_config: dict) -> float:
        """Вычисляет уверенность в том, что функция соответствует паттерну"""
        confidence = 0.0
        total_checks = 0

        # Проверяем ключевые слова
        if "keywords" in pattern_config:
            func_code = func_info.get("code", "") + " " + func_info.get("name", "")
            for keyword in pattern_config["keywords"]:
                total_checks += 1
                if keyword.lower() in func_code.lower():
                    confidence += 0.3

        # Проверяем импорты
        if "imports" in pattern_config:
            file_imports = func_info.get("file_imports", [])
            for import_pattern in pattern_config["imports"]:
                total_checks += 1
                if any(import_pattern in imp for imp in file_imports):
                    confidence += 0.4

        # Проверяем декораторы
        if "decorators" in pattern_config:
            func_decorators = func_info.get("decorators", [])
            for decorator_pattern in pattern_config["decorators"]:
                total_checks += 1
                if any(decorator_pattern in dec for dec in func_decorators):
                    confidence += 0.5

        # Проверяем имена функций
        if "functions" in pattern_config:
            func_calls = func_info.get("function_calls", [])
            for func_pattern in pattern_config["functions"]:
                total_checks += 1
                if any(func_pattern in call for call in func_calls):
                    confidence += 0.2

        return min(confidence, 1.0)

    def _extract_characteristics(
        self, func_info: dict, pattern_type: CodePatternType
    ) -> dict[str, Any]:
        """Извлекает характеристики функции для конкретного паттерна"""
        characteristics = {
            "name": func_info.get("name", ""),
            "args": func_info.get("args", []),
            "return_type": func_info.get("return_type", "Any"),
            "is_async": func_info.get("is_async", False),
            "decorators": func_info.get("decorators", []),
            "complexity": self._estimate_complexity(func_info),
        }

        # Специфичные характеристики для разных типов
        if pattern_type == CodePatternType.DATABASE_OPERATION:
            characteristics.update(
                {
                    "has_transaction": "transaction" in func_info.get("code", "").lower(),
                    "query_type": self._detect_query_type(func_info),
                    "has_pagination": any(
                        arg in ["limit", "offset", "page"] for arg in characteristics["args"]
                    ),
                }
            )

        elif pattern_type == CodePatternType.API_ENDPOINT:
            characteristics.update(
                {
                    "http_method": self._detect_http_method(func_info),
                    "has_auth": "auth" in func_info.get("code", "").lower(),
                    "returns_json": "json" in func_info.get("code", "").lower(),
                }
            )

        elif pattern_type == CodePatternType.ML_PREDICTION:
            characteristics.update(
                {
                    "model_type": self._detect_model_type(func_info),
                    "has_preprocessing": "preprocess" in func_info.get("code", "").lower(),
                    "batch_processing": "batch" in func_info.get("code", "").lower(),
                }
            )

        return characteristics

    def _get_test_strategies(
        self, pattern_type: CodePatternType, characteristics: dict
    ) -> list[str]:
        """Определяет стратегии тестирования для паттерна"""
        strategies = {
            CodePatternType.ASYNC_FUNCTION: [
                "test_async_execution",
                "test_timeout_handling",
                "test_cancellation",
                "test_concurrent_calls",
            ],
            CodePatternType.DATABASE_OPERATION: [
                "test_successful_operation",
                "test_connection_error",
                "test_transaction_rollback",
                "test_data_validation",
                "test_sql_injection_protection",
            ],
            CodePatternType.API_ENDPOINT: [
                "test_valid_request",
                "test_invalid_input",
                "test_authentication",
                "test_rate_limiting",
                "test_error_responses",
            ],
            CodePatternType.ML_PREDICTION: [
                "test_prediction_accuracy",
                "test_input_validation",
                "test_model_loading",
                "test_batch_processing",
                "test_performance_benchmarks",
            ],
            CodePatternType.TRADING_LOGIC: [
                "test_signal_generation",
                "test_risk_management",
                "test_position_sizing",
                "test_pnl_calculation",
                "test_edge_cases",
            ],
        }

        return strategies.get(pattern_type, ["test_basic_functionality"])

    def _estimate_complexity(self, func_info: dict) -> int:
        """Оценивает сложность функции"""
        code = func_info.get("code", "")

        complexity = 1  # Базовая сложность

        # Увеличиваем за условные конструкции
        complexity += code.count("if ")
        complexity += code.count("elif ")
        complexity += code.count("for ")
        complexity += code.count("while ")
        complexity += code.count("try:")
        complexity += code.count("except")

        return min(complexity, 10)  # Ограничиваем максимальной сложностью

    def _detect_query_type(self, func_info: dict) -> str:
        """Определяет тип SQL запроса"""
        code = func_info.get("code", "").upper()

        if "SELECT" in code:
            return "SELECT"
        elif "INSERT" in code:
            return "INSERT"
        elif "UPDATE" in code:
            return "UPDATE"
        elif "DELETE" in code:
            return "DELETE"
        else:
            return "UNKNOWN"

    def _detect_http_method(self, func_info: dict) -> str:
        """Определяет HTTP метод"""
        decorators = " ".join(func_info.get("decorators", []))

        if "get" in decorators.lower():
            return "GET"
        elif "post" in decorators.lower():
            return "POST"
        elif "put" in decorators.lower():
            return "PUT"
        elif "delete" in decorators.lower():
            return "DELETE"
        else:
            return "GET"  # По умолчанию

    def _detect_model_type(self, func_info: dict) -> str:
        """Определяет тип ML модели"""
        code = func_info.get("code", "").lower()

        if "torch" in code or "pytorch" in code:
            return "PyTorch"
        elif "tensorflow" in code or "keras" in code:
            return "TensorFlow"
        elif "sklearn" in code:
            return "Scikit-learn"
        else:
            return "Unknown"


class TestTemplateLibrary:
    """
    Библиотека шаблонов тестов
    """

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> dict[str, str]:
        """Загружает шаблоны тестов"""
        return {
            "async_function": '''
async def test_{function_name}():
    """Тест для асинхронной функции {function_name}"""
    # Arrange
    {setup_code}
    
    # Act
    result = await {module_path}.{function_name}({parameters})
    
    # Assert
    assert result is not None
    {assertions}

@pytest.mark.asyncio
async def test_{function_name}_timeout():
    """Тест таймаута для {function_name}"""
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            {module_path}.{function_name}({parameters}),
            timeout=0.001
        )
''',
            "database_operation": '''
@pytest.mark.asyncio
async def test_{function_name}():
    """Тест для операции с БД {function_name}"""
    # Arrange
    async with get_test_db_connection() as conn:
        {setup_data}
        
        # Act
        result = await {module_path}.{function_name}(conn, {parameters})
        
        # Assert
        assert result is not None
        {assertions}
        
        # Cleanup выполняется автоматически через rollback

@pytest.mark.asyncio
async def test_{function_name}_connection_error():
    """Тест обработки ошибки подключения к БД"""
    with pytest.raises(ConnectionError):
        await {module_path}.{function_name}(None, {parameters})
''',
            "api_endpoint": '''
@pytest.mark.asyncio
async def test_{function_name}_success(client):
    """Тест успешного API запроса {function_name}"""
    # Arrange
    request_data = {request_data}
    
    # Act
    response = await client.{http_method.lower()}("{endpoint}", json=request_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    {assertions}

@pytest.mark.asyncio
async def test_{function_name}_invalid_input(client):
    """Тест API с невалидными данными"""
    # Act
    response = await client.{http_method.lower()}("{endpoint}", json={{}})
    
    # Assert
    assert response.status_code == 400
''',
            "ml_prediction": '''
def test_{function_name}_prediction():
    """Тест ML предсказания {function_name}"""
    # Arrange
    test_features = {test_features}
    expected_shape = {expected_shape}
    
    # Act
    prediction = {module_path}.{function_name}(test_features)
    
    # Assert
    assert prediction is not None
    assert prediction.shape == expected_shape
    assert not torch.isnan(prediction).any()

def test_{function_name}_batch_processing():
    """Тест батчевой обработки"""
    # Arrange
    batch_features = {batch_features}
    
    # Act
    predictions = {module_path}.{function_name}(batch_features)
    
    # Assert
    assert len(predictions) == len(batch_features)
''',
            "trading_logic": '''
@pytest.mark.asyncio
async def test_{function_name}_signal_generation():
    """Тест генерации торгового сигнала {function_name}"""
    # Arrange
    market_data = create_test_market_data()
    
    # Act
    signal = await {module_path}.{function_name}(market_data)
    
    # Assert
    assert signal in ['BUY', 'SELL', 'HOLD']
    assert signal.confidence >= 0.0
    assert signal.confidence <= 1.0

@pytest.mark.asyncio
async def test_{function_name}_risk_management():
    """Тест риск-менеджмента"""
    # Arrange
    high_risk_data = create_high_risk_scenario()
    
    # Act
    signal = await {module_path}.{function_name}(high_risk_data)
    
    # Assert
    assert signal == 'HOLD'  # В высокорисковой ситуации должны держать позицию
''',
        }

    def get_template(self, template_name: str) -> str:
        """Получает шаблон по имени"""
        return self.templates.get(template_name, self.templates["async_function"])

    def customize_template(self, template_name: str, customizations: dict[str, str]) -> str:
        """Кастомизирует шаблон"""
        template = self.get_template(template_name)

        for placeholder, value in customizations.items():
            template = template.replace(f"{{{placeholder}}}", str(value))

        return template


class MLBasedTestGenerator:
    """
    Генератор тестов на основе машинного обучения
    Анализирует паттерны кода и генерирует соответствующие тесты
    """

    def __init__(self):
        self.pattern_analyzer = CodePatternAnalyzer()
        self.test_templates = TestTemplateLibrary()
        self.generated_tests = {}

    def generate_tests_for_function(self, func_info: dict) -> list[TestCase]:
        """Генерирует тесты для функции на основе её анализа"""

        # Анализируем паттерны функции
        patterns = self.pattern_analyzer.analyze_function(func_info)

        if not patterns:
            # Если паттерны не найдены, генерируем базовый тест
            return [self._generate_basic_test(func_info)]

        test_cases = []

        # Генерируем тесты по каждому паттерну
        for pattern in patterns:
            if pattern.confidence > 0.5:  # Только высокоуверенные паттерны
                pattern_tests = self._generate_pattern_tests(func_info, pattern)
                test_cases.extend(pattern_tests)

        return test_cases

    def _generate_pattern_tests(self, func_info: dict, pattern: CodePattern) -> list[TestCase]:
        """Генерирует тесты для конкретного паттерна"""
        test_cases = []

        if pattern.pattern_type == CodePatternType.ASYNC_FUNCTION:
            test_cases.extend(self._generate_async_tests(func_info, pattern))
        elif pattern.pattern_type == CodePatternType.DATABASE_OPERATION:
            test_cases.extend(self._generate_db_tests(func_info, pattern))
        elif pattern.pattern_type == CodePatternType.API_ENDPOINT:
            test_cases.extend(self._generate_api_tests(func_info, pattern))
        elif pattern.pattern_type == CodePatternType.ML_PREDICTION:
            test_cases.extend(self._generate_ml_tests(func_info, pattern))
        elif pattern.pattern_type == CodePatternType.TRADING_LOGIC:
            test_cases.extend(self._generate_trading_tests(func_info, pattern))
        else:
            test_cases.append(self._generate_basic_test(func_info))

        return test_cases

    def _generate_async_tests(self, func_info: dict, pattern: CodePattern) -> list[TestCase]:
        """Генерирует тесты для async функций"""
        tests = []

        # Базовый тест
        template = self.test_templates.get_template("async_function")
        test_code = self._fill_template(template, func_info, pattern)

        tests.append(
            TestCase(
                name=f"test_{func_info['name']}_async",
                code=test_code,
                description=f"Тест асинхронной функции {func_info['name']}",
                test_type="unit",
                priority=3,
                dependencies=["pytest-asyncio"],
            )
        )

        return tests

    def _generate_db_tests(self, func_info: dict, pattern: CodePattern) -> list[TestCase]:
        """Генерирует тесты для операций с БД"""
        tests = []

        template = self.test_templates.get_template("database_operation")
        test_code = self._fill_template(template, func_info, pattern)

        tests.append(
            TestCase(
                name=f"test_{func_info['name']}_db_operation",
                code=test_code,
                description=f"Тест операции с БД {func_info['name']}",
                test_type="integration",
                priority=4,
                dependencies=["pytest-asyncio", "asyncpg"],
            )
        )

        return tests

    def _generate_api_tests(self, func_info: dict, pattern: CodePattern) -> list[TestCase]:
        """Генерирует тесты для API endpoints"""
        tests = []

        template = self.test_templates.get_template("api_endpoint")
        test_code = self._fill_template(template, func_info, pattern)

        tests.append(
            TestCase(
                name=f"test_{func_info['name']}_api_endpoint",
                code=test_code,
                description=f"Тест API endpoint {func_info['name']}",
                test_type="integration",
                priority=4,
                dependencies=["httpx", "pytest-asyncio"],
            )
        )

        return tests

    def _generate_ml_tests(self, func_info: dict, pattern: CodePattern) -> list[TestCase]:
        """Генерирует тесты для ML функций"""
        tests = []

        template = self.test_templates.get_template("ml_prediction")
        test_code = self._fill_template(template, func_info, pattern)

        tests.append(
            TestCase(
                name=f"test_{func_info['name']}_ml_prediction",
                code=test_code,
                description=f"Тест ML предсказания {func_info['name']}",
                test_type="unit",
                priority=5,
                dependencies=["torch", "numpy"],
            )
        )

        return tests

    def _generate_trading_tests(self, func_info: dict, pattern: CodePattern) -> list[TestCase]:
        """Генерирует тесты для торговой логики"""
        tests = []

        template = self.test_templates.get_template("trading_logic")
        test_code = self._fill_template(template, func_info, pattern)

        tests.append(
            TestCase(
                name=f"test_{func_info['name']}_trading_logic",
                code=test_code,
                description=f"Тест торговой логики {func_info['name']}",
                test_type="unit",
                priority=5,
                dependencies=["pytest-asyncio"],
            )
        )

        return tests

    def _generate_basic_test(self, func_info: dict) -> TestCase:
        """Генерирует базовый тест для функции"""
        test_code = f'''
def test_{func_info["name"]}_basic():
    """Базовый тест для {func_info["name"]}"""
    # TODO: Реализовать тест
    assert True  # Заглушка
'''

        return TestCase(
            name=f"test_{func_info['name']}_basic",
            code=test_code,
            description=f"Базовый тест для {func_info['name']}",
            test_type="unit",
            priority=1,
            dependencies=[],
        )

    def _fill_template(self, template: str, func_info: dict, pattern: CodePattern) -> str:
        """Заполняет шаблон конкретными данными"""
        replacements = {
            "function_name": func_info["name"],
            "module_path": func_info.get("module", "module"),
            "parameters": self._generate_test_parameters(func_info),
            "setup_code": self._generate_setup_code(func_info, pattern),
            "assertions": self._generate_assertions(func_info, pattern),
            "expected_behavior": pattern.characteristics.get("expected_behavior", "success"),
            "timeout": pattern.characteristics.get("timeout", 30),
            "http_method": pattern.characteristics.get("http_method", "GET"),
            "endpoint": f"/{func_info['name']}",
            "request_data": self._generate_request_data(func_info),
            "test_features": self._generate_test_features(func_info),
            "expected_shape": self._generate_expected_shape(func_info),
            "batch_features": self._generate_batch_features(func_info),
        }

        filled_template = template
        for key, value in replacements.items():
            filled_template = filled_template.replace(f"{{{key}}}", str(value))

        return filled_template

    def _generate_test_parameters(self, func_info: dict) -> str:
        """Генерирует параметры для теста"""
        args = func_info.get("args", [])

        if not args:
            return ""

        # Генерируем тестовые значения на основе имён аргументов
        test_params = []
        for arg in args:
            if arg in ["self", "cls"]:
                continue
            elif "id" in arg.lower():
                test_params.append(f"{arg}=1")
            elif "name" in arg.lower():
                test_params.append(f'{arg}="test"')
            elif "amount" in arg.lower() or "price" in arg.lower():
                test_params.append(f"{arg}=100.0")
            elif "symbol" in arg.lower():
                test_params.append(f'{arg}="BTCUSDT"')
            else:
                test_params.append(f"{arg}=None")

        return ", ".join(test_params)

    def _generate_setup_code(self, func_info: dict, pattern: CodePattern) -> str:
        """Генерирует код настройки теста"""
        if pattern.pattern_type == CodePatternType.DATABASE_OPERATION:
            return "# Подготовка тестовых данных в БД"
        elif pattern.pattern_type == CodePatternType.ML_PREDICTION:
            return "# Загрузка тестовой модели"
        else:
            return "# Настройка теста"

    def _generate_assertions(self, func_info: dict, pattern: CodePattern) -> str:
        """Генерирует утверждения для теста"""
        base_assertions = ["assert result is not None"]

        if pattern.pattern_type == CodePatternType.DATABASE_OPERATION:
            if "SELECT" in pattern.characteristics.get("query_type", ""):
                base_assertions.append("assert len(result) >= 0")
            else:
                base_assertions.append("assert result > 0")

        elif pattern.pattern_type == CodePatternType.API_ENDPOINT:
            base_assertions.extend(
                ["assert 'status' in result", "assert result['status'] == 'success'"]
            )

        elif pattern.pattern_type == CodePatternType.ML_PREDICTION:
            base_assertions.extend(
                ["assert hasattr(result, 'shape')", "assert not torch.isnan(result).any()"]
            )

        return "\n    ".join(base_assertions)

    def _generate_request_data(self, func_info: dict) -> str:
        """Генерирует данные запроса для API тестов"""
        return '{"test": "data"}'

    def _generate_test_features(self, func_info: dict) -> str:
        """Генерирует тестовые признаки для ML"""
        return "torch.randn(1, 240)"  # Для BOT_AI_V3 используем 240 признаков

    def _generate_expected_shape(self, func_info: dict) -> str:
        """Генерирует ожидаемую форму для ML"""
        return "(1, 1)"

    def _generate_batch_features(self, func_info: dict) -> str:
        """Генерирует батч признаков для ML"""
        return "torch.randn(32, 240)"


def main():
    """Главная функция для демонстрации"""
    # Пример использования
    generator = MLBasedTestGenerator()

    # Тестовая функция
    test_func_info = {
        "name": "predict_price_movement",
        "args": ["features", "model"],
        "return_type": "torch.Tensor",
        "is_async": True,
        "decorators": [],
        "code": '''
async def predict_price_movement(features, model):
    """Предсказывает движение цены"""
    features = torch.tensor(features)
    prediction = model.predict(features)
    return prediction
        ''',
        "file_imports": ["torch", "ml.logic"],
        "function_calls": ["predict", "tensor"],
    }

    test_cases = generator.generate_tests_for_function(test_func_info)

    print("🧪 Сгенерированные тесты:")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case.name}")
        print(f"   Тип: {test_case.test_type}")
        print(f"   Приоритет: {test_case.priority}")
        print(f"   Описание: {test_case.description}")
        print(f"   Код:\n{test_case.code}")


if __name__ == "__main__":
    main()
