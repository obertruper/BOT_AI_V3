#!/usr/bin/env python3
"""
Единая точка входа для запуска всей системы BOT_AI_V3

Управляет всеми компонентами:
- Core System (торговый движок + ML)
- Web API (FastAPI)
- Frontend (React/Vite)
- Мониторинг и health checks
"""

import argparse
import asyncio
import os
import signal
import socket
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psutil
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from core.system.health_monitor import HealthMonitor
from core.system.process_manager import ProcessManager

# Настройка логирования
logger = setup_logger("unified_launcher")


def is_port_in_use(port: int, host: str = "localhost") -> bool:
    """Проверка, используется ли порт"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_processes_using_port(port: int) -> list[dict[str, Any]]:
    """Поиск процессов, использующих указанный порт"""
    processes = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            for conn in proc.net_connections():
                if conn.laddr and conn.laddr.port == port:
                    processes.append(
                        {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cmdline": (
                                " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""
                            ),
                            "status": proc.status(),
                        }
                    )
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return processes


def kill_processes_on_port(port: int, force: bool = False) -> list[int]:
    """Завершение процессов, использующих порт"""
    killed_pids = []
    processes = find_processes_using_port(port)

    for proc_info in processes:
        pid = proc_info["pid"]
        try:
            proc = psutil.Process(pid)

            # Не убиваем системные процессы
            if proc_info["name"] in ["System", "kernel_task", "launchd"]:
                continue

            # Сначала пробуем graceful shutdown
            if not force:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                    killed_pids.append(pid)
                    logger.info(f"✅ Процесс {proc_info['name']} (PID: {pid}) корректно завершен")
                except psutil.TimeoutExpired:
                    # Если не завершился, убиваем принудительно
                    proc.kill()
                    killed_pids.append(pid)
                    logger.warning(
                        f"⚠️ Процесс {proc_info['name']} (PID: {pid}) принудительно завершен"
                    )
            else:
                proc.kill()
                killed_pids.append(pid)
                logger.warning(f"⚠️ Процесс {proc_info['name']} (PID: {pid}) принудительно завершен")

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.debug(f"Не удалось завершить процесс {pid}: {e}")

    return killed_pids


class LaunchMode(Enum):
    """Режимы запуска системы"""

    FULL = "full"  # Все компоненты
    CORE = "core"  # Только торговля
    DEV = "dev"  # Режим разработки
    API = "api"  # Только API + Frontend
    ML = "ml"  # Core + ML без frontend


class UnifiedLauncher:
    """
    Главный лаунчер для управления всеми компонентами системы
    """

    def __init__(self, mode: LaunchMode = LaunchMode.FULL):
        self.mode = mode
        self.config_manager = ConfigManager()
        self.process_manager = ProcessManager()
        self.health_monitor = HealthMonitor()

        # Загружаем конфигурацию
        self.config = self.config_manager.get_config()
        self.unified_config = self.config.get("unified_system", {})

        # Состояние системы
        self.is_running = False
        self.startup_time: datetime | None = None
        self.shutdown_event = asyncio.Event()

        # Компоненты для запуска
        self.components_config = self._get_components_config()

        # PID файлы
        self.pid_dir = Path("logs/pids")
        self.pid_dir.mkdir(parents=True, exist_ok=True)

    def _get_components_config(self) -> dict[str, dict[str, Any]]:
        """Получение конфигурации компонентов в зависимости от режима"""
        base_config = self.unified_config.get("components", {}) if self.unified_config else {}

        # Конфигурация по умолчанию
        default_config = {
            "core": {
                "enabled": False,  # Core будет встроен в API процесс (EMBED_CORE)
                "command": "venv/bin/python main.py",
                "name": "Core System",
                "auto_restart": True,
                "health_check_endpoint": None,
                "startup_delay": 0,
                "env": {
                    "UNIFIED_MODE": "true",
                    "PYTHONPATH": str(Path(__file__).parent),
                },
            },
            "ml": {
                "enabled": True,
                "command": None,  # ML интегрирован в Core
                "name": "ML System",
                "auto_restart": True,
                "health_check_endpoint": None,
                "startup_delay": 0,
                "integrated_with": "core",
            },
            "api": {
                "enabled": True,
                "command": "venv/bin/python web/launcher.py",
                "name": "Web API",
                "port": 8083,
                "auto_restart": True,
                "health_check_endpoint": "http://localhost:8083/api/health",
                "startup_delay": 3,
                "env": {
                    "UNIFIED_MODE": "true",
                    "PYTHONPATH": str(Path(__file__).parent),
                    "PATH": f"{Path(__file__).parent}/venv/bin:" + os.environ.get("PATH", ""),
                    "EMBED_CORE": "true",  # Встраиваем Core в веб-процесс для боевого режима
                },
            },
            "frontend": {
                "enabled": True,
                "command": "CHOKIDAR_USEPOLLING=true npm run dev -- --host",
                "name": "Frontend",
                "port": 5173,
                "auto_restart": False,
                "health_check_endpoint": "http://localhost:5173",
                "startup_delay": 5,
                "cwd": "web/frontend",
                "env": {"VITE_API_URL": "http://localhost:8083"},
            },
        }

        # Объединяем с конфигурацией из файла
        for comp_name, comp_config in default_config.items():
            if comp_name in base_config:
                comp_config.update(base_config[comp_name])
            default_config[comp_name] = comp_config

        # Фильтруем компоненты в зависимости от режима
        if self.mode == LaunchMode.CORE:
            default_config["api"]["enabled"] = False
            default_config["frontend"]["enabled"] = False
        elif self.mode == LaunchMode.API:
            default_config["core"]["enabled"] = False
            default_config["ml"]["enabled"] = False
        elif self.mode == LaunchMode.ML:
            default_config["frontend"]["enabled"] = False
        elif self.mode == LaunchMode.DEV:
            # В dev режиме отключаем auto_restart
            for comp in default_config.values():
                comp["auto_restart"] = False

        return default_config

    async def initialize(self):
        """Инициализация системы"""
        logger.info("=" * 80)
        logger.info("🚀 BOT_AI_V3 - Единая система запуска")
        logger.info(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🎯 Режим: {self.mode.value}")
        logger.info("=" * 80)

        # Проверяем критические зависимости
        await self._check_dependencies()

        # Инициализируем компоненты
        await self.process_manager.initialize()
        await self.health_monitor.initialize(self.components_config)

        self.startup_time = datetime.now()
        logger.info("✅ Система инициализирована")

    async def _check_dependencies(self):
        """Проверка критических зависимостей"""
        logger.info("🔍 Проверка зависимостей...")

        # Проверка и освобождение портов
        await self._check_and_free_ports()

        # Проверка PostgreSQL
        try:
            import asyncpg

            conn = await asyncpg.connect(
                host=os.getenv("PGHOST", "localhost"),
                port=int(os.getenv("PGPORT", "5555")),
                user=os.getenv("PGUSER"),
                password=os.getenv("PGPASSWORD"),
                database=os.getenv("PGDATABASE"),
            )
            await conn.close()
            logger.info("✅ PostgreSQL доступен")
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL недоступен: {e}")

        # Проверка Node.js для frontend
        if self.components_config["frontend"]["enabled"]:
            try:
                result = subprocess.run(["node", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"✅ Node.js {result.stdout.strip()}")
                else:
                    raise Exception("Node.js не найден")
            except Exception as e:
                logger.error(f"❌ Node.js не установлен: {e}")
                self.components_config["frontend"]["enabled"] = False

        # Проверка ML модели
        ml_model_path = Path("models/saved/best_model_20250728_215703.pth")
        if ml_model_path.exists():
            logger.info("✅ ML модель найдена")
        else:
            logger.warning("⚠️ ML модель не найдена")
            if self.mode == LaunchMode.ML:
                logger.error("❌ ML режим требует наличия модели")
                raise FileNotFoundError("ML модель не найдена")

    async def _check_and_free_ports(self):
        """Проверка и освобождение занятых портов"""
        logger.info("🔍 Проверка портов...")

        # Собираем порты, которые нам нужны
        required_ports = []

        for comp_name, comp_config in self.components_config.items():
            if comp_config.get("enabled", False) and "port" in comp_config:
                port = comp_config["port"]
                required_ports.append((comp_name, port))

        # Проверяем каждый порт
        for comp_name, port in required_ports:
            if is_port_in_use(port):
                logger.warning(f"⚠️ Порт {port} ({comp_name}) занят")

                # Ищем процессы, использующие порт
                processes = find_processes_using_port(port)

                for proc_info in processes:
                    logger.info(f"   🔍 Процесс: {proc_info['name']} (PID: {proc_info['pid']})")
                    logger.info(f"   📝 Команда: {proc_info['cmdline'][:100]}...")

                # Определяем, нужно ли освобождать порт
                should_kill = False

                # Если это наши процессы (предыдущие запуски), освобождаем
                for proc_info in processes:
                    cmdline = proc_info["cmdline"].lower()
                    if any(
                        keyword in cmdline
                        for keyword in [
                            "main.py",
                            "web/launcher.py",
                            "npm run dev",
                            "bot_ai_v3",
                            "unified_launcher",
                            "uvicorn",
                            "vite",
                        ]
                    ):
                        should_kill = True
                        break

                if should_kill:
                    logger.info(f"🔧 Освобождение порта {port}...")
                    killed_pids = kill_processes_on_port(port)

                    if killed_pids:
                        logger.info(
                            f"✅ Порт {port} освобожден (завершено процессов: {len(killed_pids)})"
                        )

                        # Даем время процессам завершиться
                        await asyncio.sleep(2)

                        # Проверяем еще раз
                        if is_port_in_use(port):
                            logger.warning(
                                f"⚠️ Порт {port} все еще занят, принудительное освобождение..."
                            )
                            kill_processes_on_port(port, force=True)
                            await asyncio.sleep(1)
                    else:
                        logger.warning(f"⚠️ Не удалось освободить порт {port}")
                else:
                    logger.warning(f"⚠️ Порт {port} занят сторонним процессом. Возможны конфликты!")
            else:
                logger.info(f"✅ Порт {port} ({comp_name}) свободен")

    async def start(self):
        """Запуск всех компонентов"""
        logger.info("\n🔄 Запуск компонентов...")
        self.is_running = True

        # Запускаем компоненты в правильном порядке
        components_order = ["core", "api", "frontend"]  # ML интегрирован в core

        for comp_name in components_order:
            comp_config = self.components_config.get(comp_name, {})

            if not comp_config.get("enabled", False):
                continue

            if comp_config.get("integrated_with"):
                # Компонент интегрирован в другой
                logger.info(
                    f"📦 {comp_config['name']} интегрирован в {comp_config['integrated_with']}"
                )
                continue

            try:
                # Задержка перед запуском
                if comp_config.get("startup_delay", 0) > 0:
                    await asyncio.sleep(comp_config["startup_delay"])

                # Запускаем компонент
                pid = await self.process_manager.start_component(
                    name=comp_name,
                    command=comp_config["command"],
                    cwd=comp_config.get("cwd"),
                    env=comp_config.get("env", {}),
                    auto_restart=comp_config.get("auto_restart", True),
                )

                # Сохраняем PID
                pid_file = self.pid_dir / f"{comp_name}.pid"
                pid_file.write_text(str(pid))

                logger.info(f"✅ {comp_config['name']} запущен (PID: {pid})")

                # Ждем готовности компонента
                if comp_config.get("health_check_endpoint"):
                    await self._wait_for_component(comp_name, comp_config["health_check_endpoint"])

            except Exception as e:
                logger.error(f"❌ Ошибка запуска {comp_config['name']}: {e}")
                if self.mode != LaunchMode.DEV:
                    raise

        # Запускаем мониторинг
        asyncio.create_task(self._monitor_system())

        logger.info("\n✅ Все компоненты запущены успешно")
        await self._print_system_info()

    async def _wait_for_component(self, name: str, endpoint: str, timeout: int = 30):
        """Ожидание готовности компонента"""
        import aiohttp

        logger.info(f"⏳ Ожидание готовности {name}...")
        start_time = asyncio.get_event_loop().time()

        async with aiohttp.ClientSession() as session:
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    async with session.get(endpoint, timeout=2) as resp:
                        if resp.status < 500:
                            logger.info(f"✅ {name} готов к работе")
                            return
                except:
                    pass
                await asyncio.sleep(1)

        logger.warning(f"⚠️ {name} не ответил за {timeout} секунд")

    async def _monitor_system(self):
        """Оптимизированный мониторинг состояния системы"""
        consecutive_errors = 0
        max_errors = 5

        while self.is_running:
            try:
                # Проверяем health всех компонентов
                health_status = await self.health_monitor.check_all()

                # Оптимизированная обработка нездоровых компонентов
                unhealthy_components = [
                    (comp_name, status)
                    for comp_name, status in health_status.items()
                    if not status["healthy"]
                    and self.components_config[comp_name].get("auto_restart")
                ]

                if unhealthy_components:
                    logger.warning(f"🏥 Найдено {len(unhealthy_components)} нездоровых компонентов")

                    # Ограничиваем количество одновременных перезапусков
                    for comp_name, status in unhealthy_components[:2]:  # Максимум 2 одновременно
                        error_msg = status.get("error", "Unknown error")

                        # Пропускаем временные сетевые ошибки
                        if any(
                            skip_err in error_msg
                            for skip_err in ["timeout", "connection", "broken pipe"]
                        ):
                            logger.debug(f"🔄 Пропуск временной ошибки {comp_name}: {error_msg}")
                            continue

                        logger.warning(f"🔄 Планируется перезапуск {comp_name}: {error_msg}")
                        asyncio.create_task(self._safe_restart_component(comp_name))

                # Сбор метрик с оптимизированной частотой
                metrics = await self._collect_metrics()

                # Алерты только для критических значений
                if metrics["memory_percent"] > 85:
                    logger.warning(
                        f"⚠️ Критическое использование памяти: {metrics['memory_percent']:.1f}%"
                    )
                elif metrics["cpu_percent"] > 90:
                    logger.warning(
                        f"⚠️ Критическое использование CPU: {metrics['cpu_percent']:.1f}%"
                    )

                # Сброс счетчика ошибок при успешной итерации
                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    logger.warning(f"Ошибка мониторинга #{consecutive_errors}: {e}")
                elif consecutive_errors == max_errors:
                    logger.error(f"Критическое количество ошибок мониторинга: {consecutive_errors}")
                    # Увеличиваем интервал проверки при частых ошибках
                    await asyncio.sleep(60)
                    continue

            # Адаптивный интервал проверки
            if consecutive_errors > 0:
                sleep_time = min(60, 30 + consecutive_errors * 10)
            else:
                sleep_time = 30

            await asyncio.sleep(sleep_time)

    async def _safe_restart_component(self, comp_name: str):
        """Безопасный перезапуск компонента с защитой от частых перезапусков"""
        try:
            # Проверяем, не перезапускался ли компонент недавно
            proc_info = self.process_manager.get_process_info(comp_name)
            if proc_info and proc_info.get("restart_count", 0) >= 3:
                logger.warning(f"⏸️ Пропуск перезапуска {comp_name} - слишком много попыток")
                return

            # Проверяем, зарегистрирован ли компонент
            if comp_name not in self.process_manager.processes:
                logger.warning(f"⚠️ Компонент {comp_name} не зарегистрирован, попытка запуска")
                # Если это API, пытаемся запустить через subprocess
                if comp_name == "api" and "components" in self.config and comp_name in self.config["components"]:
                    comp_config = self.config["components"][comp_name]
                    if comp_config.get("enabled", False):
                        await self.process_manager.start_component(
                            name=comp_name,
                            command=comp_config.get("command"),
                            cwd=comp_config.get("cwd"),
                            env=comp_config.get("env", {}),
                            auto_restart=comp_config.get("auto_restart", True),
                        )
                        logger.info(f"✅ Компонент {comp_name} запущен")
                return

            await self.process_manager.restart_component(comp_name)
            logger.info(f"✅ Компонент {comp_name} успешно перезапущен")

        except Exception as e:
            logger.error(f"❌ Ошибка перезапуска {comp_name}: {e}")

    async def _collect_metrics(self) -> dict[str, float]:
        """Сбор системных метрик"""
        # Используем SSD путь для мониторинга диска, так как данные теперь там
        disk_path = "/mnt/SSD" if os.path.exists("/mnt/SSD") else "/"
        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage(disk_path).percent,
            "active_processes": len(self.process_manager.processes),
            "uptime_hours": (datetime.now() - self.startup_time).total_seconds() / 3600,
        }
        return metrics

    async def _print_system_info(self):
        """Вывод информации о системе"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 ИНФОРМАЦИЯ О СИСТЕМЕ")
        logger.info("=" * 60)

        # Компоненты
        logger.info("\n🔧 Активные компоненты:")
        for comp_name, comp_config in self.components_config.items():
            if comp_config.get("enabled"):
                # 🛡️ ИСПРАВЛЕНО: ML система интегрирована в Core System
                if comp_name == "ml":
                    # ML система работает если Core System работает
                    core_running = "core" in self.process_manager.processes
                    status = "✅ Запущен" if core_running else "❌ Остановлен"
                else:
                    # Для остальных компонентов проверяем наличие отдельного процесса
                    status = (
                        "✅ Запущен"
                        if comp_name in self.process_manager.processes
                        else "❌ Остановлен"
                    )
                logger.info(f"  {comp_config['name']}: {status}")

        # URL-адреса
        logger.info("\n🌐 Доступные сервисы:")
        if self.components_config["frontend"]["enabled"]:
            logger.info("  Dashboard: http://localhost:5173")
        if self.components_config["api"]["enabled"]:
            logger.info("  API: http://localhost:8083")
            logger.info("  API Docs: http://localhost:8083/api/docs")

        # Системные метрики
        metrics = await self._collect_metrics()
        logger.info("\n💻 Системные метрики:")
        logger.info(f"  CPU: {metrics['cpu_percent']:.1f}%")
        logger.info(f"  Память: {metrics['memory_percent']:.1f}%")
        logger.info(f"  Диск: {metrics['disk_usage']:.1f}%")

        logger.info("\n" + "=" * 60)

    async def run(self):
        """Основной цикл работы"""
        logger.info("\n✅ Система готова к работе")
        logger.info("🛑 Для остановки нажмите Ctrl+C")

        # Ожидаем сигнал остановки
        await self.shutdown_event.wait()

    async def stop(self):
        """Остановка всех компонентов"""
        logger.info("\n🛑 Получен сигнал остановки...")
        self.is_running = False

        # Останавливаем мониторинг
        await self.health_monitor.stop()

        # Останавливаем все процессы
        await self.process_manager.stop_all()

        # Очищаем PID файлы
        for pid_file in self.pid_dir.glob("*.pid"):
            pid_file.unlink()

        logger.info("✅ Все компоненты остановлены")
        logger.info("👋 BOT_AI_V3 завершил работу")

    def handle_signal(self, sig, frame):
        """Обработчик системных сигналов"""
        logger.info(f"\n📡 Получен сигнал {sig}")
        self.shutdown_event.set()


async def main():
    """Основная функция"""
    # Парсинг аргументов
    parser = argparse.ArgumentParser(description="BOT_AI_V3 Unified Launcher")
    parser.add_argument(
        "--mode",
        type=str,
        choices=[mode.value for mode in LaunchMode],
        default=LaunchMode.FULL.value,
        help="Режим запуска системы",
    )
    parser.add_argument("--status", action="store_true", help="Показать статус системы")
    parser.add_argument("--logs", action="store_true", help="Следить за логами")

    args = parser.parse_args()

    # Проверка статуса
    if args.status:
        await show_status()
        return

    # Просмотр логов
    if args.logs:
        await follow_logs()
        return

    # Запуск системы
    launcher = UnifiedLauncher(mode=LaunchMode(args.mode))

    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, launcher.handle_signal)
    signal.signal(signal.SIGTERM, launcher.handle_signal)

    try:
        # Инициализация
        await launcher.initialize()

        # Запуск компонентов
        await launcher.start()

        # Основной цикл
        await launcher.run()

    except KeyboardInterrupt:
        logger.info("\n⌨️ Прерывание от пользователя")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Остановка
        await launcher.stop()


async def show_status():
    """Показать статус системы"""
    logger.info("📊 Статус системы BOT_AI_V3")
    logger.info("=" * 60)

    # Проверяем PID файлы
    pid_dir = Path("logs/pids")
    if not pid_dir.exists():
        logger.info("❌ Система не запущена")
        return

    for pid_file in pid_dir.glob("*.pid"):
        try:
            pid = int(pid_file.read_text())
            process = psutil.Process(pid)

            # Получаем информацию о процессе
            info = {
                "name": pid_file.stem,
                "pid": pid,
                "status": process.status(),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "create_time": datetime.fromtimestamp(process.create_time()),
            }

            uptime = datetime.now() - info["create_time"]

            logger.info(f"\n✅ {info['name'].upper()}")
            logger.info(f"  PID: {info['pid']}")
            logger.info(f"  Статус: {info['status']}")
            logger.info(f"  CPU: {info['cpu_percent']:.1f}%")
            logger.info(f"  Память: {info['memory_mb']:.1f} MB")
            logger.info(f"  Uptime: {uptime}")

        except (psutil.NoSuchProcess, ValueError):
            logger.info(f"\n❌ {pid_file.stem.upper()} - не запущен")
            pid_file.unlink()


async def follow_logs():
    """Следить за логами в реальном времени"""
    logger.info("📝 Просмотр логов (Ctrl+C для выхода)")
    logger.info("=" * 60)

    log_files = {
        "core": "logs/core.log",
        "api": "logs/api.log",
        "frontend": "logs/frontend.log",
        "unified": "logs/unified.log",
    }

    # Запускаем tail -f для всех логов
    import subprocess

    procs = []
    for name, log_file in log_files.items():
        if Path(log_file).exists():
            cmd = f"tail -f {log_file} | sed 's/^/[{name.upper()}] /'"
            proc = subprocess.Popen(cmd, shell=True)
            procs.append(proc)

    try:
        # Ждем прерывания
        for proc in procs:
            proc.wait()
    except KeyboardInterrupt:
        # Останавливаем все процессы
        for proc in procs:
            proc.terminate()


if __name__ == "__main__":
    # Проверка версии Python
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)

    # Запуск
    asyncio.run(main())
