#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

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
        self.startup_time: Optional[datetime] = None
        self.shutdown_event = asyncio.Event()

        # Компоненты для запуска
        self.components_config = self._get_components_config()

        # PID файлы
        self.pid_dir = Path("logs/pids")
        self.pid_dir.mkdir(parents=True, exist_ok=True)

    def _get_components_config(self) -> Dict[str, Dict[str, Any]]:
        """Получение конфигурации компонентов в зависимости от режима"""
        base_config = self.unified_config.get("components", {})

        # Конфигурация по умолчанию
        default_config = {
            "core": {
                "enabled": True,
                "command": f"{sys.executable} main.py",
                "name": "Core System",
                "auto_restart": True,
                "health_check_endpoint": None,
                "startup_delay": 0,
                "env": {"UNIFIED_MODE": "true"},
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
                "command": f"{sys.executable} web/launcher.py",
                "name": "Web API",
                "port": 8080,
                "auto_restart": True,
                "health_check_endpoint": "http://localhost:8080/api/health",
                "startup_delay": 3,
                "env": {
                    "UNIFIED_MODE": "true",
                    "PYTHONPATH": str(Path(__file__).parent),
                },
            },
            "frontend": {
                "enabled": True,
                "command": "npm run dev -- --host",
                "name": "Frontend",
                "port": 5173,
                "auto_restart": False,
                "health_check_endpoint": "http://localhost:5173",
                "startup_delay": 5,
                "cwd": "web/frontend",
                "env": {"VITE_API_URL": "http://localhost:8080"},
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
                result = subprocess.run(
                    ["node", "--version"], capture_output=True, text=True
                )
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
                    await self._wait_for_component(
                        comp_name, comp_config["health_check_endpoint"]
                    )

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
        """Мониторинг состояния системы"""
        while self.is_running:
            try:
                # Проверяем health всех компонентов
                health_status = await self.health_monitor.check_all()

                # Обрабатываем нездоровые компоненты
                for comp_name, status in health_status.items():
                    if not status["healthy"] and self.components_config[comp_name].get(
                        "auto_restart"
                    ):
                        logger.warning(
                            f"🔄 Перезапуск {comp_name}: {status.get('error')}"
                        )
                        await self.process_manager.restart_component(comp_name)

                # Собираем метрики
                metrics = await self._collect_metrics()
                if metrics["memory_percent"] > 80:
                    logger.warning(
                        f"⚠️ Высокое использование памяти: {metrics['memory_percent']:.1f}%"
                    )

            except Exception as e:
                logger.error(f"Ошибка мониторинга: {e}")

            # Интервал проверки
            await asyncio.sleep(30)

    async def _collect_metrics(self) -> Dict[str, float]:
        """Сбор системных метрик"""
        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
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
            logger.info("  API: http://localhost:8080")
            logger.info("  API Docs: http://localhost:8080/api/docs")

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
