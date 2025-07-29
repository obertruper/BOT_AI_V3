"""
Интерфейс для взаимодействия с AI моделями через браузер
Использует Playwright MCP для автоматизации с поддержкой Grok 4 и OpenAI 3 Pro
"""
import asyncio
import json
import ast
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import subprocess
from pathlib import Path
import re
from datetime import datetime

from .claude_code_sdk import ClaudeCodeSDK, ClaudeCodeOptions, ThinkingMode


@dataclass
class AIModelConfig:
    """Конфигурация для AI модели"""
    name: str
    url: str
    selectors: Dict[str, str]
    file_upload_method: str = "button"  # "button", "drag_drop", "input"
    file_selectors: Dict[str, str] = field(default_factory=dict)
    wait_selectors: List[str] = field(default_factory=list)
    wait_time: int = 5000
    max_retries: int = 3


class BrowserAIInterface:
    """Интерфейс для работы с AI через браузер используя Playwright MCP"""
    
    def __init__(self):
        self.claude_sdk = ClaudeCodeSDK()
        self.models = self._setup_models()
        
    def _setup_models(self) -> Dict[str, AIModelConfig]:
        """Настройка конфигураций для различных AI моделей"""
        return {
            "grok4": AIModelConfig(
                name="Grok 4",
                url="https://x.ai/",
                selectors={
                    "input": "textarea[placeholder*='Ask'], textarea[placeholder*='Message'], div[contenteditable='true']",
                    "send_button": "button[aria-label*='Send'], button[type='submit'], svg[data-testid='send']",
                    "response": "div[data-testid='message'], div.message-content, div.response",
                    "loading": "div[data-testid='loading'], .loading, .thinking"
                },
                file_upload_method="button",
                file_selectors={
                    "attach_button": "button[aria-label*='Attach'], button[title*='Attach'], input[type='file']",
                    "file_input": "input[type='file']",
                    "drop_zone": "div[data-testid='drop-zone'], .file-drop"
                },
                wait_selectors=["div[data-testid='typing']", ".ai-thinking", ".generating"],
                wait_time=10000
            ),
            "openai_pro": AIModelConfig(
                name="OpenAI 3 Pro",
                url="https://chat.openai.com",
                selectors={
                    "input": "textarea[placeholder*='Message'], div[contenteditable='true']",
                    "send_button": "button[data-testid='send-button'], button[aria-label*='Send']",
                    "response": "div.markdown, div[data-message-author-role='assistant'], .message-content",
                    "loading": "div[data-testid='loading'], .result-thinking"
                },
                file_upload_method="button", 
                file_selectors={
                    "attach_button": "button[aria-label*='Attach'], button[data-testid='attach']",
                    "file_input": "input[type='file']",
                    "drop_zone": "div[data-testid='file-upload-dropzone']"
                },
                wait_selectors=["div.result-thinking", ".typing-indicator"],
                wait_time=15000
            ),
            "claude_web": AIModelConfig(
                name="Claude Web",
                url="https://claude.ai",
                selectors={
                    "input": "div[contenteditable='true'], textarea",
                    "send_button": "button[aria-label*='Send'], button[type='submit']",
                    "response": "div.prose, div[data-testid='message'], .message-content",
                    "loading": "div.animate-pulse, .thinking"
                },
                file_upload_method="button",
                file_selectors={
                    "attach_button": "button[title*='Attach'], button[aria-label*='Attach']",
                    "file_input": "input[type='file']",
                    "drop_zone": "div[data-testid='file-drop']"
                },
                wait_selectors=["div.thinking", ".generating-response"],
                wait_time=12000
            )
        }
    
    async def query_model_via_browser(
        self, 
        model_name: str, 
        prompt: str, 
        file_paths: List[str] = None,
        use_existing_tab: bool = True
    ) -> str:
        """Отправить запрос к AI модели через браузер используя Playwright MCP"""
        if model_name not in self.models:
            raise ValueError(f"Неизвестная модель: {model_name}")
            
        model_config = self.models[model_name]
        
        # Создаем задачу для Playwright MCP
        playwright_task = self._build_playwright_task(model_config, prompt, file_paths, use_existing_tab)
        
        # Выполняем через Claude Code SDK
        options = ClaudeCodeOptions(
            model="claude-3-5-haiku-20241022",
            allowed_tools=[
                "mcp__playwright__browser_navigate",
                "mcp__playwright__browser_snapshot",
                "mcp__playwright__browser_click", 
                "mcp__playwright__browser_type",
                "mcp__playwright__browser_file_upload",
                "mcp__playwright__browser_wait_for",
                "mcp__playwright__browser_tab_list",
                "mcp__playwright__browser_tab_select"
            ],
            thinking_mode=ThinkingMode.THINK,
            max_turns=20,
            timeout=60000
        )
        
        result = await self.claude_sdk.query(playwright_task, options, f"browser_ai_{model_name}")
        return self._extract_ai_response(result)
    
    def _build_playwright_task(
        self, 
        model_config: AIModelConfig, 
        prompt: str, 
        file_paths: List[str] = None,
        use_existing_tab: bool = True
    ) -> str:
        """Построить задачу для Playwright MCP"""
        
        task_parts = [
            f"Автоматизируйте взаимодействие с {model_config.name} используя Playwright MCP:",
            "",
            "1. ПРОВЕРКА БРАУЗЕРА:",
            "   - Выполните browser_tab_list чтобы увидеть открытые вкладки"
        ]
        
        if use_existing_tab:
            task_parts.extend([
                f"   - Найдите вкладку с {model_config.url} или содержащую {model_config.name}",
                f"   - Если есть - выберите её с browser_tab_select",
                f"   - Если нет - откройте новую с browser_navigate на {model_config.url}"
            ])
        else:
            task_parts.append(f"   - Откройте новую вкладку: browser_navigate {model_config.url}")
        
        task_parts.extend([
            "",
            "2. СНИМОК ЭКРАНА:",
            "   - Сделайте browser_snapshot для понимания интерфейса",
            "   - Найдите элементы для взаимодействия",
            ""
        ])
        
        # Загрузка файлов если необходимо
        if file_paths:
            task_parts.extend([
                "3. ЗАГРУЗКА ФАЙЛОВ:",
                f"   - Найдите кнопку загрузки: {model_config.file_selectors.get('attach_button', 'button[aria-label*=\"Attach\"]')}",
                f"   - Нажмите на неё: browser_click",
                f"   - Загрузите файлы: browser_file_upload с файлами {file_paths}",
                "   - Дождитесь завершения загрузки",
                ""
            ])
            
        task_parts.extend([
            f"{'4' if file_paths else '3'}. ОТПРАВКА ЗАПРОСА:",
            f"   - Найдите поле ввода: {model_config.selectors['input']}",
            f"   - Введите текст: browser_type с текстом \"{prompt}\"",
            f"   - Найдите кнопку отправки: {model_config.selectors['send_button']}",
            f"   - Нажмите её: browser_click",
            "",
            f"{'5' if file_paths else '4'}. ОЖИДАНИЕ ОТВЕТА:",
            f"   - Дождитесь исчезновения индикаторов загрузки:"
        ])
        
        for wait_selector in model_config.wait_selectors:
            task_parts.append(f"     * browser_wait_for текст \"{wait_selector}\" исчез")
        
        task_parts.extend([
            f"   - Дождитесь появления ответа в: {model_config.selectors['response']}",
            f"   - Подождите {model_config.wait_time}ms для полного формирования ответа",
            "",
            f"{'6' if file_paths else '5'}. ИЗВЛЕЧЕНИЕ РЕЗУЛЬТАТА:",
            f"   - Сделайте снимок экрана для проверки",
            f"   - Извлеките текст ответа из {model_config.selectors['response']}",
            f"   - Верните ТОЛЬКО содержимое ответа AI (без интерфейсных элементов)",
            "",
            "ВАЖНЫЕ ПРАВИЛА:",
            "- Если элемент не найден, попробуйте альтернативные селекторы",
            "- При ошибках авторизации - сообщите об этом",
            "- Дождитесь ПОЛНОГО формирования ответа перед извлечением",
            "- Игнорируйте элементы интерфейса, кнопки, навигацию",
            "- Возвращайте только текст ответа от AI модели"
        ])
        
        return "\n".join(task_parts)
        
    def _extract_ai_response(self, claude_response: str) -> str:
        """Извлечь ответ AI из результата Claude"""
        lines = claude_response.split('\n')
        
        # Ищем маркеры начала ответа AI
        response_markers = [
            'ответ ai:', 'ai response:', 'response from', 'извлеченный текст:',
            'результат:', 'ответ модели:', 'содержимое ответа:'
        ]
        
        response_start = -1
        for i, line in enumerate(lines):
            if any(marker in line.lower() for marker in response_markers):
                response_start = i + 1
                break
        
        if response_start >= 0:
            return '\n'.join(lines[response_start:]).strip()
        
        # Если маркер не найден, ищем последний блок с кавычками или отступами
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line and not line.startswith(('✓', '•', '-', '*', 'browser_')):
                # Нашли последний содержательный блок
                return '\n'.join(lines[max(0, i-10):i+1]).strip()
        
        return claude_response.strip()
    
    async def compare_models(
        self, 
        prompt: str, 
        models: List[str], 
        file_paths: List[str] = None
    ) -> Dict[str, str]:
        """Сравнить ответы от нескольких моделей"""
        results = {}
        
        # Параллельная отправка запросов
        tasks = []
        for model in models:
            task = self.query_model_via_browser(model, prompt, file_paths)
            tasks.append((model, task))
        
        # Ждем все ответы
        for model, task in tasks:
            try:
                response = await task
                results[model] = {
                    "status": "success",
                    "response": response,
                    "error": None
                }
            except Exception as e:
                results[model] = {
                    "status": "error", 
                    "response": None,
                    "error": str(e)
                }
                
        return results
    
    def analyze_complexity(self, prompt: str, file_paths: List[str] = None) -> Tuple[int, str]:
        """Анализ сложности задачи (1-10) и обоснование"""
        
        complexity_score = 1
        reasons = []
        
        # Анализ текста запроса
        prompt_lower = prompt.lower()
        
        # Ключевые слова высокой сложности
        complex_keywords = [
            'архитектура', 'оптимизация', 'безопасность', 'производительность',
            'алгоритм', 'стратегия', 'бэктестинг', 'машинное обучение',
            'анализируй', 'исследуй', 'сравни', 'оцени'
        ]
        
        for keyword in complex_keywords:
            if keyword in prompt_lower:
                complexity_score += 1
                reasons.append(f"Содержит сложное ключевое слово: {keyword}")
        
        # Анализ файлов
        if file_paths:
            complexity_score += len(file_paths)
            reasons.append(f"Прикреплено файлов: {len(file_paths)}")
            
            # Анализ содержимого Python файлов
            python_files = [f for f in file_paths if f.endswith('.py')]
            for py_file in python_files[:3]:  # Анализируем первые 3 файла
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Считаем функции, классы, строки
                    try:
                        tree = ast.parse(content)
                        functions = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
                        classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
                        lines = len(content.split('\n'))
                        
                        if lines > 100:
                            complexity_score += 2
                            reasons.append(f"{py_file}: {lines} строк кода")
                        if functions > 5:
                            complexity_score += 1
                            reasons.append(f"{py_file}: {functions} функций")
                        if classes > 2:
                            complexity_score += 1
                            reasons.append(f"{py_file}: {classes} классов")
                            
                    except SyntaxError:
                        complexity_score += 1
                        reasons.append(f"{py_file}: синтаксические ошибки требуют анализа")
                        
                except Exception:
                    pass
        
        # Длина запроса
        if len(prompt) > 500:
            complexity_score += 1
            reasons.append("Длинный запрос (>500 символов)")
        
        # Множественные вопросы
        question_marks = prompt.count('?')
        if question_marks > 2:
            complexity_score += 1
            reasons.append(f"Множественные вопросы ({question_marks} шт.)")
        
        # Ограничиваем максимальный балл
        complexity_score = min(complexity_score, 10)
        
        reasoning = "; ".join(reasons) if reasons else "Простая задача"
        
        return complexity_score, reasoning
    
    def should_cross_verify(self, prompt: str, file_paths: List[str] = None) -> bool:
        """Определить нужна ли кросс-проверка"""
        
        # Явный триггер
        if "!кросс!" in prompt.lower():
            return True
        
        # По сложности задачи
        complexity, _ = self.analyze_complexity(prompt, file_paths)
        if complexity >= 6:
            return True
            
        # Критичные директории
        if file_paths:
            critical_paths = ['trading/', 'strategies/', 'security/', 'ai_agents/']
            for file_path in file_paths:
                if any(critical in file_path for critical in critical_paths):
                    return True
        
        # Ключевые слова требующие проверки
        verification_keywords = [
            'безопасность', 'уязвимость', 'оптимизация', 'производительность',
            'финансы', 'торговля', 'risk', 'стратегия', 'бэктестинг'
        ]
        
        prompt_lower = prompt.lower()
        for keyword in verification_keywords:
            if keyword in prompt_lower:
                return True
        
        return False


class SmartCrossVerifier:
    """Умная система кросс-проверки ответов от множественных AI"""
    
    def __init__(self):
        self.browser_interface = BrowserAIInterface()
        self.claude_sdk = ClaudeCodeSDK()
        
    async def intelligent_query(
        self, 
        prompt: str, 
        file_paths: List[str] = None,
        force_cross_verify: bool = False
    ) -> Dict[str, Any]:
        """Интеллектуальный запрос с автоматическим решением о кросс-проверке"""
        
        # Анализируем нужна ли кросс-проверка
        complexity, complexity_reason = self.browser_interface.analyze_complexity(prompt, file_paths)
        needs_verification = force_cross_verify or self.browser_interface.should_cross_verify(prompt, file_paths)
        
        result = {
            "query": prompt,
            "file_paths": file_paths or [],
            "complexity_score": complexity,
            "complexity_reason": complexity_reason,
            "verification_used": needs_verification,
            "timestamp": datetime.now().isoformat()
        }
        
        if needs_verification:
            # Кросс-проверка через Grok 4 и OpenAI 3 Pro
            verification_result = await self._cross_verify_response(prompt, file_paths)
            result.update(verification_result)
        else:
            # Обычный ответ через Claude
            simple_response = await self._simple_claude_response(prompt, file_paths)
            result.update({
                "response": simple_response,
                "confidence_score": 0.8,  # Базовая уверенность для Claude
                "models_used": ["claude_code_sdk"],
                "analysis": {"summary": "Простая задача, кросс-проверка не требуется"}
            })
        
        return result
    
    async def _cross_verify_response(
        self, 
        prompt: str, 
        file_paths: List[str] = None
    ) -> Dict[str, Any]:
        """Выполнить кросс-проверку через Grok 4 и OpenAI 3 Pro"""
        
        models = ["grok4", "openai_pro"]
        
        # Отправляем запросы параллельно
        model_responses = await self.browser_interface.compare_models(prompt, models, file_paths)
        
        # Анализируем согласованность ответов
        analysis = await self._analyze_response_consistency(model_responses, prompt)
        
        # Генерируем итоговый ответ
        final_response = await self._generate_consensus_response(model_responses, analysis, prompt)
        
        return {
            "response": final_response,
            "confidence_score": analysis.get("consistency_score", 0.5),
            "models_used": models,
            "model_responses": model_responses,
            "analysis": analysis
        }
    
    async def _simple_claude_response(self, prompt: str, file_paths: List[str] = None) -> str:
        """Простой ответ через Claude Code SDK"""
        
        # Добавляем информацию о файлах в промпт если есть
        enhanced_prompt = prompt
        if file_paths:
            enhanced_prompt += f"\n\nПрикрепленные файлы для анализа: {', '.join(file_paths)}"
        
        options = ClaudeCodeOptions(
            thinking_mode=ThinkingMode.NORMAL,
            max_turns=5
        )
        
        return await self.claude_sdk.query(enhanced_prompt, options, "simple_query")
    
    async def _analyze_response_consistency(
        self, 
        model_responses: Dict[str, Dict[str, Any]], 
        original_query: str
    ) -> Dict[str, Any]:
        """Анализ согласованности ответов от разных AI"""
        
        successful_responses = {}
        for model, data in model_responses.items():
            if data["status"] == "success" and data["response"]:
                successful_responses[model] = data["response"]
        
        if len(successful_responses) < 2:
            return {
                "consistency_score": 0.0,
                "agreement_level": "insufficient_data",
                "summary": "Недостаточно успешных ответов для анализа",
                "key_agreements": [],
                "key_differences": [],
                "recommendations": ["Попробуйте повторить запрос", "Проверьте доступность AI сервисов"]
            }
        
        # Анализируем через Claude
        analysis_prompt = f"""
        Проанализируйте согласованность ответов от разных AI моделей на вопрос: "{original_query}"
        
        Ответы для анализа:
        {json.dumps(successful_responses, ensure_ascii=False, indent=2)}
        
        Выполните детальный анализ:
        
        1. Оцените согласованность ключевых фактов (0.0-1.0):
           - 1.0 = полное согласие по всем важным моментам
           - 0.8-0.9 = согласие по основным моментам, мелкие различия
           - 0.6-0.7 = согласие по большинству вопросов, есть расхождения
           - 0.4-0.5 = существенные различия, но общее направление схожее
           - 0.0-0.3 = кардинальные расхождения
        
        2. Определите уровень согласия:
           - "high" = модели дают практически идентичные ответы
           - "medium" = модели согласны в основном, есть дополнения
           - "low" = модели дают разные подходы к решению
           - "conflict" = модели противоречат друг другу
        
        3. Найдите ключевые точки согласия и расхождения
        
        4. Дайте рекомендации по использованию результатов
        
        Верните ответ СТРОГО в JSON формате:
        {{
            "consistency_score": float,
            "agreement_level": str,
            "key_agreements": [str],
            "key_differences": [str],
            "summary": str,
            "recommendations": [str]
        }}
        """
        
        analysis_options = ClaudeCodeOptions(
            thinking_mode=ThinkingMode.THINK_HARD,
            max_turns=3
        )
        
        analysis_response = await self.claude_sdk.query(
            analysis_prompt,
            analysis_options,
            "response_analyzer"
        )
        
        try:
            # Извлекаем JSON из ответа
            json_match = re.search(r'\{.*\}', analysis_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"Ошибка парсинга анализа: {e}")
        
        # Fallback анализ
        return {
            "consistency_score": 0.5,
            "agreement_level": "unknown",
            "summary": "Автоматический анализ не удался",
            "key_agreements": [],
            "key_differences": [],
            "recommendations": ["Проверьте ответы вручную"]
        }
    
    async def _generate_consensus_response(
        self, 
        model_responses: Dict[str, Dict[str, Any]], 
        analysis: Dict[str, Any], 
        original_query: str
    ) -> str:
        """Генерация итогового консенсусного ответа"""
        
        successful_responses = {}
        for model, data in model_responses.items():
            if data["status"] == "success" and data["response"]:
                successful_responses[model] = data["response"]
        
        if not successful_responses:
            return "❌ Не удалось получить ответы от AI моделей. Проверьте подключение и попробуйте снова."
        
        consensus_prompt = f"""
        На основе ответов от различных AI моделей создайте итоговый консенсусный ответ на вопрос: "{original_query}"
        
        Ответы моделей:
        {json.dumps(successful_responses, ensure_ascii=False, indent=2)}
        
        Анализ согласованности:
        {json.dumps(analysis, ensure_ascii=False, indent=2)}
        
        Создайте итоговый ответ который:
        1. Объединяет лучшие элементы из всех ответов
        2. Выделяет области согласия между моделями  
        3. Указывает на разногласия там где они есть
        4. Предоставляет сбалансированный и объективный взгляд
        5. Включает оценку уверенности в различных утверждениях
        
        Используйте следующую структуру:
        
        ## Консенсусный ответ
        [Основной ответ, объединяющий лучшие части]
        
        ## Уровень согласия моделей: {analysis.get('agreement_level', 'unknown')}
        ## Оценка надежности: {analysis.get('consistency_score', 0.5):.1f}/1.0
        
        {"## Области согласия:" if analysis.get('key_agreements') else ""}
        {chr(10).join(f"- {agreement}" for agreement in analysis.get('key_agreements', []))}
        
        {"## Области разногласий:" if analysis.get('key_differences') else ""}
        {chr(10).join(f"- {difference}" for difference in analysis.get('key_differences', []))}
        
        ## Рекомендации:
        {chr(10).join(f"- {rec}" for rec in analysis.get('recommendations', ['Используйте результат с осторожностью']))}
        """
        
        consensus_options = ClaudeCodeOptions(
            thinking_mode=ThinkingMode.THINK_HARDER,
            max_turns=5
        )
        
        return await self.claude_sdk.query(consensus_prompt, consensus_options, "consensus_generator")
    
    async def research_with_verification(
        self, 
        topic: str, 
        include_sources: bool = True,
        force_verification: bool = True
    ) -> Dict[str, Any]:
        """Исследование темы с обязательной верификацией"""
        
        research_query = f"""
        Проведите comprehensive исследование темы: {topic}
        
        Предоставьте:
        1. Ключевые концепции и определения
        2. Текущее состояние области
        3. Последние разработки и тренды (2024-2025)
        4. Практические применения и кейсы
        5. Потенциальные проблемы и ограничения
        6. Перспективы развития
        {'7. Надежные источники и ссылки для дополнительного изучения' if include_sources else ''}
        
        Фокус на актуальной и проверенной информации.
        """
        
        return await self.intelligent_query(research_query, force_cross_verify=force_verification)


class TerminalAICommands:
    """Команды для работы с AI из терминала с поддержкой кросс-проверки"""
    
    def __init__(self):
        self.browser_interface = BrowserAIInterface()
        self.cross_verifier = SmartCrossVerifier()
        
    async def ask_multiple_models(
        self, 
        question: str, 
        models: Optional[List[str]] = None,
        file_paths: Optional[List[str]] = None
    ):
        """Задать вопрос нескольким моделям"""
        if models is None:
            models = ["grok4", "openai_pro", "claude_web"]
            
        print(f"📡 Отправляю запрос к моделям: {', '.join(models)}")
        print(f"❓ Вопрос: {question}")
        if file_paths:
            print(f"📎 Файлы: {', '.join(file_paths)}")
        print()
        
        results = await self.browser_interface.compare_models(question, models, file_paths)
        
        for model, data in results.items():
            print(f"\n{'='*60}")
            print(f"🤖 Ответ от {data.get('name', model)}:")
            print(f"{'='*60}")
            
            if data["status"] == "success":
                print(data["response"])
            else:
                print(f"❌ Ошибка: {data['error']}")
            print()
            
    async def intelligent_ask(
        self, 
        question: str, 
        file_paths: Optional[List[str]] = None,
        force_cross_verify: bool = False
    ):
        """Интеллектуальный запрос с автоматической кросс-проверкой"""
        
        print(f"🧠 Анализирую сложность запроса...")
        
        result = await self.cross_verifier.intelligent_query(
            question, 
            file_paths, 
            force_cross_verify
        )
        
        print(f"📊 Сложность: {result['complexity_score']}/10 ({result['complexity_reason']})")
        print(f"🔍 Кросс-проверка: {'Да' if result['verification_used'] else 'Нет'}")
        print(f"🎯 Уверенность: {result['confidence_score']:.1f}/1.0")
        print(f"🤖 Модели: {', '.join(result['models_used'])}")
        print()
        
        if result['verification_used']:
            print("📋 Анализ согласованности:")
            analysis = result.get('analysis', {})
            print(f"   Уровень согласия: {analysis.get('agreement_level', 'unknown')}")
            if analysis.get('key_agreements'):
                print("   ✅ Области согласия:")
                for agreement in analysis['key_agreements']:
                    print(f"      • {agreement}")
            if analysis.get('key_differences'):
                print("   ⚠️ Области разногласий:")
                for difference in analysis['key_differences']:
                    print(f"      • {difference}")
            print()
        
        print("💬 Итоговый ответ:")
        print("-" * 60)
        print(result['response'])
        
    async def research_topic(self, topic: str, verification: bool = True):
        """Исследовать тему используя кросс-проверку"""
        
        print(f"🔬 Исследую тему: {topic}")
        print(f"🔍 Верификация: {'Включена' if verification else 'Отключена'}")
        
        if verification:
            result = await self.cross_verifier.research_with_verification(topic)
            
            print(f"📊 Результаты исследования:")
            print(f"   Сложность: {result['complexity_score']}/10")
            print(f"   Уверенность: {result['confidence_score']:.1f}/1.0")
            print(f"   Модели: {', '.join(result['models_used'])}")
            print()
            
            print("📖 Итоговый отчет:")
            print("=" * 80)
            print(result['response'])
        else:
            # Простое исследование через одну модель
            research_prompt = f"""
            Исследуйте тему: {topic}
            
            Предоставьте:
            1. Ключевые концепции и определения
            2. Последние разработки и тренды
            3. Практические применения
            4. Источники для дальнейшего изучения
            """
            
            response = await self.browser_interface.query_model_via_browser("claude_web", research_prompt)
            print("📖 Результат исследования:")
            print("=" * 80)
            print(response)


# CLI функции для быстрого доступа
async def ask_ai(
    question: str, 
    model: str = "grok4", 
    file_paths: List[str] = None
) -> str:
    """Быстрый вопрос к AI модели"""
    interface = BrowserAIInterface()
    response = await interface.query_model_via_browser(model, question, file_paths)
    return response


async def smart_ask(
    question: str, 
    file_paths: List[str] = None, 
    force_cross_verify: bool = False
) -> Dict[str, Any]:
    """Умный запрос с автоматической кросс-проверкой"""
    verifier = SmartCrossVerifier()
    return await verifier.intelligent_query(question, file_paths, force_cross_verify)


async def cross_verify(
    question: str, 
    models: List[str] = None, 
    file_paths: List[str] = None
) -> Dict[str, Any]:
    """Принудительная кросс-проверка ответов"""
    if models is None:
        models = ["grok4", "openai_pro"]
    
    interface = BrowserAIInterface()
    return await interface.compare_models(question, models, file_paths)


async def compare_ai(question: str, file_paths: List[str] = None):
    """Сравнить ответы от разных AI"""
    terminal = TerminalAICommands()
    await terminal.ask_multiple_models(question, file_paths=file_paths)


async def intelligent_ask(
    question: str, 
    file_paths: List[str] = None, 
    force_cross_verify: bool = False
):
    """Интеллектуальный вопрос с анализом сложности"""
    terminal = TerminalAICommands()
    await terminal.intelligent_ask(question, file_paths, force_cross_verify)


async def research(topic: str, verification: bool = True):
    """Исследовать тему с опциональной верификацией"""
    terminal = TerminalAICommands()
    await terminal.research_topic(topic, verification)


async def upload_and_analyze(
    file_paths: List[str], 
    analysis_query: str = "Проанализируйте эти файлы",
    models: List[str] = None
) -> Dict[str, Any]:
    """Загрузка файлов и анализ через браузерные AI"""
    if models is None:
        models = ["grok4", "openai_pro"]
    
    interface = BrowserAIInterface()
    return await interface.compare_models(analysis_query, models, file_paths)


if __name__ == "__main__":
    # Примеры использования новой системы кросс-проверки
    async def main():
        print("🚀 Демонстрация SmartCrossVerifier")
        print("=" * 60)
        
        # 1. Простой вопрос (автоматически определит нужна ли кросс-проверка)
        print("\n1️⃣ Простой вопрос:")
        await intelligent_ask("Что такое Python?")
        
        # 2. Сложный вопрос (автоматически запустит кросс-проверку)
        print("\n2️⃣ Сложный вопрос:")
        await intelligent_ask("Проанализируйте архитектуру торговых ботов и оптимизацию производительности")
        
        # 3. Принудительная кросс-проверка
        print("\n3️⃣ Принудительная кросс-проверка:")
        await intelligent_ask("!кросс! Какие лучшие практики для машинного обучения?", force_cross_verify=True)
        
        # 4. Анализ файлов (если есть файлы)
        # print("\n4️⃣ Анализ файлов:")
        # result = await upload_and_analyze(
        #     ["ai_agents/claude_code_sdk.py"], 
        #     "Проанализируйте этот код и предложите улучшения"
        # )
        
        # 5. Исследование с верификацией
        print("\n5️⃣ Исследование с верификацией:")
        await research("Применение ИИ в алгоритмической торговле 2024", verification=True)
        
        print("\n✅ Демонстрация завершена!")
        
    asyncio.run(main())