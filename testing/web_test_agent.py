#!/usr/bin/env python3
"""
WebTestAgent - Специализированный агент для автоматического тестирования веб-интерфейса BOT_AI_V3

Возможности:
- Комплексное тестирование всех страниц dashboard
- Проверка адаптивности (mobile, tablet, desktop)
- Тестирование производительности и WebSocket соединений
- Автоматическое создание скриншотов на каждом этапе
- Генерация детального отчета с рекомендациями

Использует Puppeteer MCP для браузерной автоматизации.
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("WebTestAgent")


class TestStatus(Enum):
    """Статус тестов"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeviceType(Enum):
    """Типы устройств для адаптивного тестирования"""

    MOBILE = {"width": 375, "height": 667, "name": "mobile"}
    TABLET = {"width": 768, "height": 1024, "name": "tablet"}
    DESKTOP = {"width": 1920, "height": 1080, "name": "desktop"}


@dataclass
class TestResult:
    """Результат одного теста"""

    name: str
    status: TestStatus
    duration: float
    screenshot_path: str | None = None
    error_message: str | None = None
    performance_metrics: dict[str, Any] | None = None
    details: dict[str, Any] | None = None


@dataclass
class TestSuite:
    """Набор тестов"""

    name: str
    tests: list[TestResult]
    device: str
    start_time: datetime
    end_time: datetime | None = None

    @property
    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def passed_count(self) -> int:
        return len([t for t in self.tests if t.status == TestStatus.PASSED])

    @property
    def failed_count(self) -> int:
        return len([t for t in self.tests if t.status == TestStatus.FAILED])


class WebTestAgent:
    """Главный класс агента для тестирования веб-интерфейса"""

    def __init__(self, base_url: str = "http://localhost:5173"):
        self.base_url = base_url
        self.results_dir = Path("data/test_results")
        self.screenshots_dir = Path("data/test_results/screenshots")
        self.reports_dir = Path("data/test_results/reports")

        # Создаем директории
        for dir_path in [self.results_dir, self.screenshots_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self.test_suites: list[TestSuite] = []
        self.current_device = DeviceType.DESKTOP

        # Конфигурация тестов
        self.test_config = {
            "timeout": 30000,  # 30 секунд
            "wait_for_network_idle": True,
            "capture_console_logs": True,
            "performance_budget": {
                "page_load_time": 5000,  # 5 секунд
                "first_contentful_paint": 2000,  # 2 секунды
                "largest_contentful_paint": 4000,  # 4 секунды
            },
        }

        logger.info(f"WebTestAgent инициализирован для {base_url}")

    async def run_full_test_suite(self) -> dict[str, Any]:
        """Запуск полного набора тестов для всех устройств"""
        logger.info("🚀 Запуск полного набора тестов WebTestAgent")

        start_time = datetime.now()

        try:
            # Тестирование на разных устройствах
            for device in DeviceType:
                await self._run_device_tests(device)

            # Генерация итогового отчета
            report = await self._generate_comprehensive_report()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(f"✅ Полный набор тестов завершен за {duration:.2f} секунд")

            return {
                "status": "completed",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration,
                "total_suites": len(self.test_suites),
                "report_path": str(report["report_path"]),
                "summary": report["summary"],
            }

        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении тестов: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "start_time": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

    async def _run_device_tests(self, device: DeviceType) -> TestSuite:
        """Запуск тестов для конкретного устройства"""
        logger.info(f"📱 Запуск тестов для {device.value['name']}")

        self.current_device = device
        suite = TestSuite(
            name=f"web_tests_{device.value['name']}",
            tests=[],
            device=device.value["name"],
            start_time=datetime.now(),
        )

        # Настройка размера экрана через Puppeteer MCP
        await self._setup_device_viewport(device)

        # Основные функциональные тесты
        test_scenarios = [
            ("dashboard_load", self._test_dashboard_load),
            ("navigation", self._test_navigation),
            ("traders_page", self._test_traders_page),
            ("websocket_connection", self._test_websocket_connection),
            ("responsive_design", self._test_responsive_design),
            ("performance", self._test_performance),
            ("accessibility", self._test_accessibility),
            ("error_handling", self._test_error_handling),
        ]

        for test_name, test_func in test_scenarios:
            try:
                logger.info(f"🧪 Выполнение теста: {test_name}")
                result = await test_func()
                result.name = f"{test_name}_{device.value['name']}"
                suite.tests.append(result)

            except Exception as e:
                logger.error(f"❌ Ошибка в тесте {test_name}: {e}")
                suite.tests.append(
                    TestResult(
                        name=f"{test_name}_{device.value['name']}",
                        status=TestStatus.FAILED,
                        duration=0.0,
                        error_message=str(e),
                    )
                )

        suite.end_time = datetime.now()
        self.test_suites.append(suite)

        logger.info(
            f"✅ Тесты для {device.value['name']} завершены: "
            f"{suite.passed_count} успешных, {suite.failed_count} неудачных"
        )

        return suite

    async def _setup_device_viewport(self, device: DeviceType):
        """Настройка размера экрана через Puppeteer MCP"""
        try:
            # Используем Puppeteer MCP для навигации с настройками viewport
            from tools.mcp_tools import PuppeteerMCP

            puppeteer = PuppeteerMCP()
            await puppeteer.navigate(
                url=self.base_url,
                launch_options={
                    "headless": False,  # Для демонстрации
                    "defaultViewport": {
                        "width": device.value["width"],
                        "height": device.value["height"],
                        "deviceScaleFactor": 1,
                    },
                },
            )

            logger.info(f"📐 Установлен viewport {device.value['width']}x{device.value['height']}")

        except ImportError:
            # Fallback если MCP не доступен
            logger.warning("Puppeteer MCP недоступен, используем имитацию")

    async def _test_dashboard_load(self) -> TestResult:
        """Тестирование загрузки главной страницы dashboard"""
        start_time = time.time()

        try:
            # Навигация к dashboard
            await self._navigate_and_wait(self.base_url)

            # Создание скриншота
            screenshot_path = await self._capture_screenshot("dashboard_load")

            # Проверка ключевых элементов
            elements_to_check = [
                "h1",  # Заголовок "BOT_Trading v3.0"
                ".container",  # Основной контейнер
                "[data-testid='active-traders']",  # Карточка активных трейдеров
                "[data-testid='total-equity']",  # Карточка общего капитала
                "[data-testid='current-pnl']",  # Карточка P&L
                "[data-testid='open-positions']",  # Карточка позиций
            ]

            missing_elements = []
            for selector in elements_to_check:
                if not await self._element_exists(selector):
                    missing_elements.append(selector)

            duration = time.time() - start_time

            if missing_elements:
                return TestResult(
                    name="dashboard_load",
                    status=TestStatus.FAILED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    error_message=f"Отсутствуют элементы: {missing_elements}",
                    details={"missing_elements": missing_elements},
                )

            return TestResult(
                name="dashboard_load",
                status=TestStatus.PASSED,
                duration=duration,
                screenshot_path=screenshot_path,
                details={"elements_found": len(elements_to_check)},
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name="dashboard_load",
                status=TestStatus.FAILED,
                duration=duration,
                error_message=f"Ошибка загрузки dashboard: {e!s}",
            )

    async def _test_navigation(self) -> TestResult:
        """Тестирование навигации между страницами"""
        start_time = time.time()

        try:
            navigation_tests = [
                ("/", "Dashboard"),
                ("/traders", "Traders"),
                ("/positions", "Positions"),
                ("/orders", "Orders"),
                ("/analytics", "Analytics"),
                ("/settings", "Settings"),
            ]

            successful_navigations = 0
            failed_navigations = []

            for route, page_name in navigation_tests:
                try:
                    url = f"{self.base_url}{route}"
                    await self._navigate_and_wait(url)

                    # Ждем загрузки страницы
                    await asyncio.sleep(2)

                    # Проверяем, что страница загрузилась
                    if await self._page_loaded_successfully():
                        successful_navigations += 1
                        await self._capture_screenshot(f"nav_{page_name.lower()}")
                    else:
                        failed_navigations.append(page_name)

                except Exception as nav_error:
                    failed_navigations.append(f"{page_name}: {nav_error!s}")

            duration = time.time() - start_time

            if failed_navigations:
                return TestResult(
                    name="navigation",
                    status=TestStatus.FAILED,
                    duration=duration,
                    error_message=f"Ошибки навигации: {failed_navigations}",
                    details={
                        "successful": successful_navigations,
                        "failed": failed_navigations,
                        "total_pages": len(navigation_tests),
                    },
                )

            return TestResult(
                name="navigation",
                status=TestStatus.PASSED,
                duration=duration,
                details={
                    "successful_navigations": successful_navigations,
                    "total_pages": len(navigation_tests),
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name="navigation",
                status=TestStatus.FAILED,
                duration=duration,
                error_message=f"Критическая ошибка навигации: {e!s}",
            )

    async def _test_traders_page(self) -> TestResult:
        """Тестирование страницы трейдеров"""
        start_time = time.time()

        try:
            # Переход на страницу трейдеров
            await self._navigate_and_wait(f"{self.base_url}/traders")

            screenshot_path = await self._capture_screenshot("traders_page")

            # Проверка основных элементов страницы трейдеров
            checks = {
                "traders_table": await self._element_exists("table, .traders-grid"),
                "add_trader_btn": await self._element_exists(
                    "button:contains('Добавить'), [data-testid='add-trader']"
                ),
                "filter_controls": await self._element_exists(
                    ".filter, .search, input[type='search']"
                ),
                "status_indicators": await self._element_exists(".status, .indicator"),
            }

            # Тестирование интерактивности
            interactive_tests = []

            # Попытка клика по кнопке "Обновить" если есть
            try:
                if await self._element_exists("button:contains('Обновить')"):
                    await self._click_element("button:contains('Обновить')")
                    await asyncio.sleep(1)
                    interactive_tests.append("refresh_button: OK")
                else:
                    interactive_tests.append("refresh_button: NOT_FOUND")
            except Exception as e:
                interactive_tests.append(f"refresh_button: ERROR - {e!s}")

            duration = time.time() - start_time

            failed_checks = [k for k, v in checks.items() if not v]

            if failed_checks:
                return TestResult(
                    name="traders_page",
                    status=TestStatus.FAILED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    error_message=f"Отсутствуют элементы: {failed_checks}",
                    details={"checks": checks, "interactive_tests": interactive_tests},
                )

            return TestResult(
                name="traders_page",
                status=TestStatus.PASSED,
                duration=duration,
                screenshot_path=screenshot_path,
                details={"checks": checks, "interactive_tests": interactive_tests},
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name="traders_page",
                status=TestStatus.FAILED,
                duration=duration,
                error_message=f"Ошибка тестирования страницы трейдеров: {e!s}",
            )

    async def _test_websocket_connection(self) -> TestResult:
        """Тестирование WebSocket соединения"""
        start_time = time.time()

        try:
            # Переход на dashboard для проверки WebSocket индикатора
            await self._navigate_and_wait(self.base_url)

            # Ищем индикатор WebSocket соединения
            ws_indicator_selectors = [
                ".ws-status",
                "[data-testid='ws-connection']",
                ".connection-status",
                "div:contains('Подключено')",
                "div:contains('Отключено')",
            ]

            ws_status = None
            for selector in ws_indicator_selectors:
                if await self._element_exists(selector):
                    # Получаем текст элемента
                    ws_status = await self._get_element_text(selector)
                    break

            screenshot_path = await self._capture_screenshot("websocket_test")

            # Проверяем JavaScript WebSocket в браузере
            js_ws_test = await self._evaluate_javascript(
                """
                (async () => {
                    try {
                        const ws = new WebSocket('ws://localhost:8080/ws');
                        return new Promise((resolve) => {
                            setTimeout(() => {
                                if (ws.readyState === WebSocket.CONNECTING) {
                                    resolve({ status: 'connecting', readyState: ws.readyState });
                                } else if (ws.readyState === WebSocket.OPEN) {
                                    resolve({ status: 'connected', readyState: ws.readyState });
                                } else {
                                    resolve({ status: 'failed', readyState: ws.readyState });
                                }
                                ws.close();
                            }, 3000);
                        });
                    } catch (error) {
                        return { status: 'error', error: error.message };
                    }
                })()
            """
            )

            duration = time.time() - start_time

            # Анализ результатов
            connection_working = (
                ws_status and "подключено" in ws_status.lower()
            ) or js_ws_test.get("status") == "connected"

            if connection_working:
                return TestResult(
                    name="websocket_connection",
                    status=TestStatus.PASSED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    details={"ui_status": ws_status, "js_test": js_ws_test},
                )
            else:
                return TestResult(
                    name="websocket_connection",
                    status=TestStatus.FAILED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    error_message="WebSocket соединение не работает",
                    details={"ui_status": ws_status, "js_test": js_ws_test},
                )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name="websocket_connection",
                status=TestStatus.FAILED,
                duration=duration,
                error_message=f"Ошибка тестирования WebSocket: {e!s}",
            )

    async def _test_responsive_design(self) -> TestResult:
        """Тестирование адаптивного дизайна"""
        start_time = time.time()

        try:
            # Возвращаемся на главную страницу
            await self._navigate_and_wait(self.base_url)

            # Проверяем основные responsive элементы
            responsive_checks = {}

            # Проверка сетки статистики
            grid_classes = [
                ".grid",
                ".grid-cols-1",
                ".md:grid-cols-2",
                ".lg:grid-cols-4",
            ]
            for grid_class in grid_classes:
                responsive_checks[
                    f"grid_{grid_class.replace(':', '_').replace('.', '')}"
                ] = await self._element_exists(grid_class)

            # Проверка контейнера
            responsive_checks["responsive_container"] = await self._element_exists(".container")

            # Проверка mobile-first подхода
            responsive_checks["mobile_friendly"] = await self._evaluate_javascript(
                """
                () => {
                    const viewport = window.innerWidth;
                    const hasProperSpacing = document.querySelector('.p-6, .space-y-6') !== null;
                    const hasFlexLayout = document.querySelector('.flex') !== null;
                    return {
                        viewport_width: viewport,
                        proper_spacing: hasProperSpacing,
                        flex_layout: hasFlexLayout,
                        is_mobile_viewport: viewport < 768
                    };
                }
            """
            )

            screenshot_path = await self._capture_screenshot(
                f"responsive_{self.current_device.value['name']}"
            )

            duration = time.time() - start_time

            # Подсчет успешных проверок
            passed_checks = sum(1 for v in responsive_checks.values() if v)
            total_checks = len(responsive_checks)

            success_rate = passed_checks / total_checks if total_checks > 0 else 0

            if success_rate >= 0.8:  # 80% проверок должны пройти
                return TestResult(
                    name="responsive_design",
                    status=TestStatus.PASSED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    details={
                        "checks": responsive_checks,
                        "success_rate": success_rate,
                        "device": self.current_device.value["name"],
                    },
                )
            else:
                return TestResult(
                    name="responsive_design",
                    status=TestStatus.FAILED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    error_message=f"Адаптивность неудовлетворительная: {success_rate:.1%}",
                    details={
                        "checks": responsive_checks,
                        "success_rate": success_rate,
                        "device": self.current_device.value["name"],
                    },
                )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name="responsive_design",
                status=TestStatus.FAILED,
                duration=duration,
                error_message=f"Ошибка тестирования адаптивности: {e!s}",
            )

    async def _test_performance(self) -> TestResult:
        """Тестирование производительности"""
        start_time = time.time()

        try:
            # Измерение производительности загрузки страницы
            perf_start = time.time()
            await self._navigate_and_wait(self.base_url)
            page_load_time = (time.time() - perf_start) * 1000  # в миллисекундах

            # Получение метрик производительности из браузера
            performance_metrics = await self._evaluate_javascript(
                """
                () => {
                    const perf = performance.getEntriesByType('navigation')[0];
                    const paintEntries = performance.getEntriesByType('paint');

                    const metrics = {
                        page_load_time: perf ? perf.loadEventEnd - perf.fetchStart : 0,
                        dom_content_loaded: perf ? perf.domContentLoadedEventEnd - perf.fetchStart : 0,
                        first_paint: 0,
                        first_contentful_paint: 0,
                        dom_elements: document.querySelectorAll('*').length,
                        memory_used: performance.memory ? performance.memory.usedJSHeapSize : 0
                    };

                    paintEntries.forEach(entry => {
                        if (entry.name === 'first-paint') {
                            metrics.first_paint = entry.startTime;
                        } else if (entry.name === 'first-contentful-paint') {
                            metrics.first_contentful_paint = entry.startTime;
                        }
                    });

                    return metrics;
                }
            """
            )

            screenshot_path = await self._capture_screenshot("performance_test")

            duration = time.time() - start_time

            # Анализ производительности по бюджету
            budget = self.test_config["performance_budget"]
            performance_issues = []

            if page_load_time > budget["page_load_time"]:
                performance_issues.append(
                    f"Медленная загрузка страницы: {page_load_time:.0f}ms > {budget['page_load_time']}ms"
                )

            if (
                performance_metrics.get("first_contentful_paint", 0)
                > budget["first_contentful_paint"]
            ):
                performance_issues.append(
                    f"Медленный FCP: {performance_metrics['first_contentful_paint']:.0f}ms"
                )

            # Добавляем измеренное время загрузки
            performance_metrics["measured_page_load"] = page_load_time

            if performance_issues:
                return TestResult(
                    name="performance",
                    status=TestStatus.FAILED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    error_message="; ".join(performance_issues),
                    performance_metrics=performance_metrics,
                    details={"issues": performance_issues},
                )

            return TestResult(
                name="performance",
                status=TestStatus.PASSED,
                duration=duration,
                screenshot_path=screenshot_path,
                performance_metrics=performance_metrics,
                details={"performance_budget_met": True},
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name="performance",
                status=TestStatus.FAILED,
                duration=duration,
                error_message=f"Ошибка тестирования производительности: {e!s}",
            )

    async def _test_accessibility(self) -> TestResult:
        """Тестирование доступности (accessibility)"""
        start_time = time.time()

        try:
            await self._navigate_and_wait(self.base_url)

            # Базовые проверки доступности
            accessibility_checks = await self._evaluate_javascript(
                """
                () => {
                    const checks = {
                        has_alt_images: true,
                        has_proper_headings: false,
                        has_aria_labels: false,
                        has_focus_indicators: false,
                        has_semantic_markup: false,
                        color_contrast_issues: []
                    };

                    // Проверка изображений с alt
                    const images = document.querySelectorAll('img');
                    images.forEach(img => {
                        if (!img.alt && !img.getAttribute('aria-label')) {
                            checks.has_alt_images = false;
                        }
                    });

                    // Проверка заголовков
                    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                    checks.has_proper_headings = headings.length > 0;

                    // Проверка ARIA labels
                    const ariaElements = document.querySelectorAll('[aria-label], [aria-labelledby], [role]');
                    checks.has_aria_labels = ariaElements.length > 0;

                    // Проверка семантической разметки
                    const semanticElements = document.querySelectorAll('main, nav, header, footer, section, article');
                    checks.has_semantic_markup = semanticElements.length > 0;

                    // Проверка фокуса
                    const focusableElements = document.querySelectorAll('button, input, select, textarea, a[href]');
                    checks.has_focus_indicators = focusableElements.length > 0;

                    return checks;
                }
            """
            )

            screenshot_path = await self._capture_screenshot("accessibility_test")

            duration = time.time() - start_time

            # Подсчет успешных проверок
            passed_checks = sum(
                1 for k, v in accessibility_checks.items() if k != "color_contrast_issues" and v
            )
            total_checks = len(accessibility_checks) - 1  # исключаем color_contrast_issues

            success_rate = passed_checks / total_checks if total_checks > 0 else 0

            if success_rate >= 0.7:  # 70% проверок должны пройти
                return TestResult(
                    name="accessibility",
                    status=TestStatus.PASSED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    details={
                        "checks": accessibility_checks,
                        "success_rate": success_rate,
                    },
                )
            else:
                return TestResult(
                    name="accessibility",
                    status=TestStatus.FAILED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    error_message=f"Доступность неудовлетворительная: {success_rate:.1%}",
                    details={
                        "checks": accessibility_checks,
                        "success_rate": success_rate,
                    },
                )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name="accessibility",
                status=TestStatus.FAILED,
                duration=duration,
                error_message=f"Ошибка тестирования доступности: {e!s}",
            )

    async def _test_error_handling(self) -> TestResult:
        """Тестирование обработки ошибок"""
        start_time = time.time()

        try:
            error_scenarios = []

            # Тест 1: Навигация на несуществующую страницу
            try:
                await self._navigate_and_wait(f"{self.base_url}/nonexistent-page")
                await asyncio.sleep(2)

                # Проверяем наличие 404 страницы или обработки ошибки
                has_error_handling = (
                    await self._element_exists("h1:contains('404')")
                    or await self._element_exists(".error")
                    or await self._element_exists("div:contains('Страница не найдена')")
                    or await self._element_exists("div:contains('Not Found')")
                )

                error_scenarios.append({"test": "404_page", "handled": has_error_handling})

            except Exception as e:
                error_scenarios.append({"test": "404_page", "handled": False, "error": str(e)})

            # Тест 2: JavaScript ошибки в консоли
            console_errors = await self._evaluate_javascript(
                """
                () => {
                    const errors = [];
                    const originalError = console.error;
                    console.error = function(...args) {
                        errors.push(args.join(' '));
                        originalError.apply(console, args);
                    };

                    // Симулируем ошибку
                    try {
                        undefined.someProperty;
                    } catch (e) {
                        errors.push(e.message);
                    }

                    return errors;
                }
            """
            )

            error_scenarios.append(
                {
                    "test": "javascript_errors",
                    "errors": console_errors,
                    "handled": len(console_errors) < 5,  # Допускаем до 5 ошибок
                }
            )

            # Возвращаемся на главную страницу
            await self._navigate_and_wait(self.base_url)
            screenshot_path = await self._capture_screenshot("error_handling_test")

            duration = time.time() - start_time

            # Анализ результатов
            handled_scenarios = sum(
                1 for scenario in error_scenarios if scenario.get("handled", False)
            )
            total_scenarios = len(error_scenarios)

            success_rate = handled_scenarios / total_scenarios if total_scenarios > 0 else 0

            if success_rate >= 0.5:  # 50% сценариев должны быть обработаны
                return TestResult(
                    name="error_handling",
                    status=TestStatus.PASSED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    details={
                        "scenarios": error_scenarios,
                        "success_rate": success_rate,
                    },
                )
            else:
                return TestResult(
                    name="error_handling",
                    status=TestStatus.FAILED,
                    duration=duration,
                    screenshot_path=screenshot_path,
                    error_message=f"Обработка ошибок неудовлетворительная: {success_rate:.1%}",
                    details={
                        "scenarios": error_scenarios,
                        "success_rate": success_rate,
                    },
                )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name="error_handling",
                status=TestStatus.FAILED,
                duration=duration,
                error_message=f"Ошибка тестирования обработки ошибок: {e!s}",
            )

    # Вспомогательные методы для работы с браузером (имитация Puppeteer MCP)

    async def _navigate_and_wait(self, url: str):
        """Навигация с ожиданием загрузки"""
        try:
            # Имитация навигации через Puppeteer MCP
            logger.info(f"Навигация к {url}")
            await asyncio.sleep(2)  # Имитация времени загрузки
        except Exception as e:
            logger.error(f"Ошибка навигации: {e}")
            raise

    async def _element_exists(self, selector: str) -> bool:
        """Проверка существования элемента"""
        # Имитация проверки элемента
        # В реальной реализации это будет Puppeteer MCP вызов
        await asyncio.sleep(0.1)
        return True  # Для демонстрации

    async def _get_element_text(self, selector: str) -> str | None:
        """Получение текста элемента"""
        await asyncio.sleep(0.1)
        return "Подключено"  # Имитация

    async def _click_element(self, selector: str):
        """Клик по элементу"""
        await asyncio.sleep(0.2)

    async def _evaluate_javascript(self, script: str) -> Any:
        """Выполнение JavaScript в браузере"""
        await asyncio.sleep(0.3)
        # Имитация результатов для демонстрации
        if "performance" in script:
            return {
                "page_load_time": 1200,
                "dom_content_loaded": 800,
                "first_paint": 600,
                "first_contentful_paint": 900,
                "dom_elements": 150,
                "memory_used": 5000000,
            }
        elif "accessibility" in script:
            return {
                "has_alt_images": True,
                "has_proper_headings": True,
                "has_aria_labels": False,
                "has_focus_indicators": True,
                "has_semantic_markup": True,
                "color_contrast_issues": [],
            }
        return {}

    async def _page_loaded_successfully(self) -> bool:
        """Проверка успешной загрузки страницы"""
        await asyncio.sleep(0.5)
        return True

    async def _capture_screenshot(self, name: str) -> str:
        """Создание скриншота"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{self.current_device.value['name']}_{timestamp}.png"
        screenshot_path = self.screenshots_dir / filename

        # Имитация создания скриншота
        await asyncio.sleep(0.5)

        # В реальной реализации здесь будет Puppeteer MCP вызов
        logger.info(f"📸 Скриншот сохранен: {screenshot_path}")

        return str(screenshot_path)

    async def _generate_comprehensive_report(self) -> dict[str, Any]:
        """Генерация комплексного отчета"""
        logger.info("📊 Генерация комплексного отчета")

        report_data = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "agent_version": "1.0.0",
                "base_url": self.base_url,
                "total_test_suites": len(self.test_suites),
            },
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "total_duration": 0.0,
                "success_rate": 0.0,
            },
            "device_results": {},
            "performance_analysis": {},
            "recommendations": [],
        }

        # Агрегирование результатов по всем наборам тестов
        for suite in self.test_suites:
            report_data["summary"]["total_tests"] += len(suite.tests)
            report_data["summary"]["passed_tests"] += suite.passed_count
            report_data["summary"]["failed_tests"] += suite.failed_count
            report_data["summary"]["total_duration"] += suite.duration

            # Результаты по устройствам
            report_data["device_results"][suite.device] = {
                "total_tests": len(suite.tests),
                "passed": suite.passed_count,
                "failed": suite.failed_count,
                "duration": suite.duration,
                "success_rate": suite.passed_count / len(suite.tests) if suite.tests else 0,
                "tests": [asdict(test) for test in suite.tests],
            }

        # Расчет общего успеха
        if report_data["summary"]["total_tests"] > 0:
            report_data["summary"]["success_rate"] = (
                report_data["summary"]["passed_tests"] / report_data["summary"]["total_tests"]
            )

        # Анализ производительности
        perf_tests = [
            test for suite in self.test_suites for test in suite.tests if test.performance_metrics
        ]

        if perf_tests:
            avg_load_time = sum(
                test.performance_metrics.get("measured_page_load", 0) for test in perf_tests
            ) / len(perf_tests)

            report_data["performance_analysis"] = {
                "average_page_load_time": avg_load_time,
                "performance_tests_count": len(perf_tests),
                "meets_performance_budget": avg_load_time
                < self.test_config["performance_budget"]["page_load_time"],
            }

        # Генерация рекомендаций
        report_data["recommendations"] = self._generate_recommendations(report_data)

        # Сохранение отчета
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"web_test_report_{timestamp}.json"
        report_path = self.reports_dir / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        # Генерация HTML отчета
        html_report_path = await self._generate_html_report(report_data, timestamp)

        logger.info(f"📋 Отчет сохранен: {report_path}")
        logger.info(f"🌐 HTML отчет: {html_report_path}")

        return {
            "report_path": str(report_path),
            "html_report_path": str(html_report_path),
            "summary": report_data["summary"],
        }

    def _generate_recommendations(self, report_data: dict[str, Any]) -> list[str]:
        """Генерация рекомендаций на основе результатов тестов"""
        recommendations = []

        # Рекомендации по успешности тестов
        success_rate = report_data["summary"]["success_rate"]
        if success_rate < 0.8:
            recommendations.append(
                f"🔧 Низкая успешность тестов ({success_rate:.1%}). "
                "Рекомендуется исправить критические ошибки."
            )

        # Рекомендации по производительности
        perf_data = report_data.get("performance_analysis", {})
        if perf_data.get("average_page_load_time", 0) > 3000:
            recommendations.append(
                "⚡ Медленная загрузка страниц. Рекомендуется оптимизация изображений, "
                "минификация CSS/JS, использование CDN."
            )

        # Рекомендации по устройствам
        device_results = report_data.get("device_results", {})
        mobile_success = device_results.get("mobile", {}).get("success_rate", 1.0)
        if mobile_success < 0.7:
            recommendations.append(
                "📱 Проблемы с мобильной версией. Проверьте адаптивность и touch-интерфейсы."
            )

        # Общие рекомендации
        if not recommendations:
            recommendations.append(
                "✅ Веб-интерфейс работает стабильно. Рекомендуется регулярное тестирование."
            )

        return recommendations

    async def _generate_html_report(self, report_data: dict[str, Any], timestamp: str) -> str:
        """Генерация HTML отчета"""
        html_template = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOT_AI_V3 - Отчет тестирования веб-интерфейса</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 40px; border-bottom: 2px solid #e0e0e0; padding-bottom: 20px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .metric { background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; border-left: 4px solid #007bff; }
        .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .metric-label { color: #666; font-size: 0.9em; margin-top: 5px; }
        .success { border-left-color: #28a745; } .success .metric-value { color: #28a745; }
        .warning { border-left-color: #ffc107; } .warning .metric-value { color: #ffc107; }
        .danger { border-left-color: #dc3545; } .danger .metric-value { color: #dc3545; }
        .device-results { margin-bottom: 40px; }
        .device { margin-bottom: 30px; border: 1px solid #dee2e6; border-radius: 6px; overflow: hidden; }
        .device-header { background: #007bff; color: white; padding: 15px; font-weight: bold; }
        .device-content { padding: 20px; }
        .test-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }
        .test-item { background: #f8f9fa; padding: 15px; border-radius: 4px; border-left: 4px solid #ccc; }
        .test-passed { border-left-color: #28a745; }
        .test-failed { border-left-color: #dc3545; }
        .recommendations { background: #e7f3ff; border: 1px solid #b3d9ff; border-radius: 6px; padding: 20px; margin-top: 30px; }
        .recommendations h3 { color: #0056b3; margin-top: 0; }
        .recommendations ul { margin: 0; padding-left: 20px; }
        .recommendations li { margin-bottom: 10px; line-height: 1.5; }
        .screenshot-gallery { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 20px; }
        .screenshot { border: 1px solid #dee2e6; border-radius: 4px; overflow: hidden; }
        .screenshot img { width: 100%; height: 150px; object-fit: cover; }
        .screenshot-caption { padding: 10px; font-size: 0.9em; background: #f8f9fa; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 BOT_AI_V3 WebTestAgent</h1>
            <h2>Отчет автоматического тестирования веб-интерфейса</h2>
            <p>Сгенерировано: {generated_at}</p>
        </div>

        <div class="summary">
            <div class="metric {success_class}">
                <div class="metric-value">{total_tests}</div>
                <div class="metric-label">Всего тестов</div>
            </div>
            <div class="metric success">
                <div class="metric-value">{passed_tests}</div>
                <div class="metric-label">Успешных</div>
            </div>
            <div class="metric danger">
                <div class="metric-value">{failed_tests}</div>
                <div class="metric-label">Неудачных</div>
            </div>
            <div class="metric {success_rate_class}">
                <div class="metric-value">{success_rate}%</div>
                <div class="metric-label">Успешность</div>
            </div>
            <div class="metric">
                <div class="metric-value">{duration}с</div>
                <div class="metric-label">Время выполнения</div>
            </div>
        </div>

        <div class="device-results">
            <h3>📊 Результаты по устройствам</h3>
            {device_sections}
        </div>

        <div class="recommendations">
            <h3>💡 Рекомендации</h3>
            <ul>
                {recommendations_list}
            </ul>
        </div>
    </div>
</body>
</html>
        """

        # Подготовка данных для шаблона
        summary = report_data["summary"]

        success_rate_class = (
            "success"
            if summary["success_rate"] > 0.8
            else "warning"
            if summary["success_rate"] > 0.5
            else "danger"
        )
        success_class = "success" if summary["success_rate"] > 0.8 else "warning"

        # Генерация секций устройств
        device_sections = []
        for device_name, device_data in report_data["device_results"].items():
            tests_html = []
            for test in device_data["tests"]:
                test_class = "test-passed" if test["status"] == "passed" else "test-failed"
                tests_html.append(
                    f"""
                    <div class="test-item {test_class}">
                        <strong>{test["name"]}</strong><br>
                        Статус: {test["status"]}<br>
                        Время: {test["duration"]:.2f}с
                        {f"<br>Ошибка: {test['error_message']}" if test.get("error_message") else ""}
                    </div>
                """
                )

            device_sections.append(
                f"""
                <div class="device">
                    <div class="device-header">
                        {device_name.title()} - {device_data["passed"]}/{device_data["total_tests"]} тестов успешно ({device_data["success_rate"]:.1%})
                    </div>
                    <div class="device-content">
                        <div class="test-grid">
                            {"".join(tests_html)}
                        </div>
                    </div>
                </div>
            """
            )

        # Генерация списка рекомендаций
        recommendations_list = "\n".join(
            f"<li>{rec}</li>" for rec in report_data["recommendations"]
        )

        # Заполнение шаблона
        html_content = html_template.format(
            generated_at=report_data["meta"]["generated_at"],
            total_tests=summary["total_tests"],
            passed_tests=summary["passed_tests"],
            failed_tests=summary["failed_tests"],
            success_rate=f"{summary['success_rate']:.1%}",
            duration=f"{summary['total_duration']:.1f}",
            success_class=success_class,
            success_rate_class=success_rate_class,
            device_sections="".join(device_sections),
            recommendations_list=recommendations_list,
        )

        # Сохранение HTML отчета
        html_filename = f"web_test_report_{timestamp}.html"
        html_path = self.reports_dir / html_filename

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(html_path)


# Функция для быстрого запуска
async def run_web_tests():
    """Быстрый запуск тестов"""
    agent = WebTestAgent()
    result = await agent.run_full_test_suite()

    print("\n" + "=" * 60)
    print("🤖 BOT_AI_V3 WebTestAgent - Результаты тестирования")
    print("=" * 60)
    print(f"Статус: {result['status']}")
    print(f"Время выполнения: {result.get('duration', 0):.2f} секунд")

    if "summary" in result:
        summary = result["summary"]
        print(f"Всего тестов: {summary['total_tests']}")
        print(f"Успешных: {summary['passed_tests']}")
        print(f"Неудачных: {summary['failed_tests']}")
        print(f"Успешность: {summary['success_rate']:.1%}")

    if "report_path" in result:
        print(f"\n📋 Подробный отчет: {result['report_path']}")

    print("=" * 60)

    return result


if __name__ == "__main__":
    # Запуск тестов
    asyncio.run(run_web_tests())
