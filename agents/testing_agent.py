#!/usr/bin/env python3
"""
TestingAgent - Система автоматического тестирования и исправления ошибок для BOT_AI_V3

Этот агент автоматически:
1. Запускает систему и мониторит запуск
2. Анализирует логи на ошибки
3. Определяет тип ошибки (порт занят, import error, connection error и т.д.)
4. Вызывает специализированных агентов для исправления
5. Автоматически исправляет распространенные проблемы

Автор: Claude Code Agent System
Версия: 1.0.0
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psutil

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/data/logs/testing_agent.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("TestingAgent")


class ErrorPattern:
    """Паттерны ошибок для автоматического распознавания"""

    PORT_OCCUPIED = [
        r"Address already in use",
        r"port \d+ is already in use",
        r"bind: address already in use",
        r"Error: listen EADDRINUSE",
        r"OSError: \[Errno 98\] Address already in use",
    ]

    IMPORT_ERRORS = [
        r"ModuleNotFoundError: No module named '([^']+)'",
        r"ImportError: cannot import name '([^']+)'",
        r"ImportError: No module named ([^\s]+)",
        r"from ([^\s]+) import.*ImportError",
    ]

    CONNECTION_ERRORS = [
        r"connection refused",
        r"Could not connect to",
        r"Connection failed",
        r"Database connection failed",
        r"Redis connection failed",
        r"WebSocket connection failed",
    ]

    DATABASE_ERRORS = [
        r"database \"([^\"]+)\" does not exist",
        r"relation \"([^\"]+)\" does not exist",
        r"column \"([^\"]+)\" does not exist",
        r"FATAL:.*database",
        r"psycopg2\.OperationalError",
    ]

    ML_ERRORS = [
        r"No module named 'torch'",
        r"CUDA.*not available",
        r"Model file not found",
        r"Feature.*not found",
        r"Checkpoint.*not found",
    ]

    PERMISSION_ERRORS = [
        r"Permission denied",
        r"PermissionError:",
        r"Access denied",
        r"Operation not permitted",
    ]


class TestingAgent:
    """Главный агент автоматического тестирования и исправления ошибок"""

    def __init__(self, project_root: str = "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3"):
        self.project_root = Path(project_root)
        self.venv_python = self.project_root / "venv/bin/python"
        self.logs_dir = self.project_root / "data/logs"
        self.processes: dict[str, subprocess.Popen] = {}
        self.error_history: list[dict] = []
        self.running = False

        # Создаем директории если их нет
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"TestingAgent инициализирован для проекта: {self.project_root}")

    async def start_system_monitoring(self, mode: str = "full") -> bool:
        """Запустить систему с мониторингом"""
        logger.info(f"Запуск системы в режиме {mode} с мониторингом...")

        # Проверяем систему перед запуском
        await self._pre_launch_checks()

        # Исправляем известные проблемы
        await self.fix_port_conflicts()

        # Запускаем систему
        success = await self._launch_system(mode)

        if success:
            # Мониторим запуск
            await self._monitor_startup()
            return True
        else:
            logger.error("Не удалось запустить систему")
            return False

    async def _pre_launch_checks(self):
        """Предварительные проверки перед запуском"""
        logger.info("Выполняем предварительные проверки...")

        # Проверка Python окружения
        if not self.venv_python.exists():
            logger.error("Виртуальное окружение не найдено")
            await self._setup_venv()

        # Проверка PostgreSQL
        await self._check_postgresql()

        # Проверка необходимых файлов
        await self._check_required_files()

        logger.info("Предварительные проверки завершены")

    async def _launch_system(self, mode: str) -> bool:
        """Запуск unified_launcher"""
        try:
            cmd = [str(self.venv_python), "unified_launcher.py", f"--mode={mode}"]

            # Запускаем в отдельном процессе
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            self.processes["unified_launcher"] = process
            logger.info(f"Система запущена с PID: {process.pid}")

            # Ждем несколько секунд и проверяем статус
            await asyncio.sleep(3)

            if process.poll() is None:
                logger.info("Система успешно запущена")
                return True
            else:
                stderr_output = process.stderr.read()
                logger.error(f"Система завершилась с ошибкой: {stderr_output}")
                await self.analyze_errors(stderr_output)
                return False

        except Exception as e:
            logger.error(f"Ошибка при запуске системы: {e}")
            return False

    async def _monitor_startup(self):
        """Мониторинг процесса запуска"""
        logger.info("Начинаем мониторинг запуска...")
        self.running = True

        # Мониторим логи в реальном времени
        log_files = [
            self.logs_dir / "system.log",
            self.logs_dir / "api.log",
            self.logs_dir / "errors.log",
        ]

        try:
            while self.running:
                # Проверяем процессы
                await self._check_processes()

                # Анализируем логи
                for log_file in log_files:
                    if log_file.exists():
                        await self._analyze_log_file(log_file)

                await asyncio.sleep(5)

        except KeyboardInterrupt:
            logger.info("Мониторинг остановлен пользователем")
        except Exception as e:
            logger.error(f"Ошибка в мониторинге: {e}")
        finally:
            self.running = False

    async def _check_processes(self):
        """Проверка состояния процессов"""
        for name, process in list(self.processes.items()):
            if process.poll() is not None:
                logger.warning(f"Процесс {name} завершился с кодом {process.returncode}")

                # Читаем ошибки
                if process.stderr:
                    error_output = process.stderr.read()
                    if error_output:
                        await self.analyze_errors(error_output)

                # Удаляем из списка активных процессов
                del self.processes[name]

    async def _analyze_log_file(self, log_file: Path):
        """Анализ отдельного лог файла"""
        try:
            with open(log_file, encoding="utf-8") as f:
                # Читаем только новые строки
                f.seek(0, 2)  # Идем в конец файла
                size = f.tell()

                if hasattr(self, f"_last_position_{log_file.name}"):
                    last_pos = getattr(self, f"_last_position_{log_file.name}")
                    if size > last_pos:
                        f.seek(last_pos)
                        new_lines = f.read()
                        await self.analyze_errors(new_lines)

                setattr(self, f"_last_position_{log_file.name}", size)

        except Exception as e:
            logger.error(f"Ошибка при анализе {log_file}: {e}")

    async def analyze_errors(self, log_content: str) -> list[dict]:
        """Анализ ошибок в логах"""
        errors_found = []

        if not log_content:
            return errors_found

        # Ищем паттерны ошибок
        error_types = {
            "port_occupied": ErrorPattern.PORT_OCCUPIED,
            "import_error": ErrorPattern.IMPORT_ERRORS,
            "connection_error": ErrorPattern.CONNECTION_ERRORS,
            "database_error": ErrorPattern.DATABASE_ERRORS,
            "ml_error": ErrorPattern.ML_ERRORS,
            "permission_error": ErrorPattern.PERMISSION_ERRORS,
        }

        for line in log_content.split("\n"):
            if not line.strip():
                continue

            for error_type, patterns in error_types.items():
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        error_info = {
                            "type": error_type,
                            "pattern": pattern,
                            "line": line.strip(),
                            "match": match.groups() if match.groups() else match.group(0),
                            "timestamp": datetime.now().isoformat(),
                        }
                        errors_found.append(error_info)
                        self.error_history.append(error_info)

                        logger.warning(f"Обнаружена ошибка типа {error_type}: {line.strip()}")

                        # Автоматическое исправление
                        await self._auto_fix_error(error_info)
                        break

        return errors_found

    async def _auto_fix_error(self, error_info: dict):
        """Автоматическое исправление ошибки"""
        error_type = error_info["type"]

        logger.info(f"Автоматическое исправление ошибки: {error_type}")

        try:
            if error_type == "port_occupied":
                await self.fix_port_conflicts()
            elif error_type == "import_error":
                await self.fix_import_errors(error_info)
            elif error_type == "connection_error":
                await self.fix_connection_errors(error_info)
            elif error_type == "database_error":
                await self.fix_database_errors(error_info)
            elif error_type == "ml_error":
                await self.fix_ml_errors(error_info)
            elif error_type == "permission_error":
                await self.fix_permission_errors(error_info)

        except Exception as e:
            logger.error(f"Не удалось автоматически исправить ошибку {error_type}: {e}")

    async def fix_port_conflicts(self):
        """Исправление конфликтов портов"""
        logger.info("Исправляем конфликты портов...")

        # Проверяем основные порты системы
        ports_to_check = [8080, 5173, 5555, 6379, 9090, 3000]

        for port in ports_to_check:
            processes = await self._find_processes_on_port(port)

            if processes:
                logger.warning(f"Порт {port} занят процессами: {processes}")

                for pid in processes:
                    try:
                        # Пытаемся корректно завершить процесс
                        process = psutil.Process(pid)
                        process_name = process.name()

                        # Не убиваем критические системные процессы
                        if process_name in ["postgres", "systemd", "init"]:
                            logger.info(f"Пропускаем системный процесс {process_name} (PID: {pid})")
                            continue

                        logger.info(
                            f"Завершаем процесс {process_name} (PID: {pid}) на порту {port}"
                        )
                        process.terminate()

                        # Ждем завершения
                        await asyncio.sleep(2)

                        if process.is_running():
                            logger.warning(f"Принудительно убиваем процесс {pid}")
                            process.kill()

                        logger.info(f"Процесс {pid} завершен, порт {port} освобожден")

                    except psutil.NoSuchProcess:
                        logger.info(f"Процесс {pid} уже завершен")
                    except psutil.AccessDenied:
                        logger.warning(f"Нет доступа для завершения процесса {pid}")
                    except Exception as e:
                        logger.error(f"Ошибка при завершении процесса {pid}: {e}")

    async def _find_processes_on_port(self, port: int) -> list[int]:
        """Найти процессы, использующие порт"""
        processes = []

        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == port and conn.pid:
                    processes.append(conn.pid)
        except Exception as e:
            logger.error(f"Ошибка при поиске процессов на порту {port}: {e}")

        return processes

    async def fix_import_errors(self, error_info: dict):
        """Исправление ошибок импорта"""
        logger.info("Исправляем ошибки импорта...")

        match = error_info.get("match")
        if not match:
            return

        missing_module = match[0] if isinstance(match, tuple) else match

        # Карта модулей и их установки
        module_install_map = {
            "passlib": "passlib[bcrypt]",
            "fastapi": "fastapi",
            "uvicorn": "uvicorn[standard]",
            "sqlalchemy": "sqlalchemy",
            "asyncpg": "asyncpg",
            "redis": "redis",
            "structlog": "structlog",
            "torch": "torch",
            "numpy": "numpy",
            "pandas": "pandas",
            "sklearn": "scikit-learn",
            "ccxt": "ccxt",
            "psutil": "psutil",
            "pydantic": "pydantic",
        }

        install_package = module_install_map.get(missing_module, missing_module)

        try:
            logger.info(f"Устанавливаем недостающий модуль: {install_package}")

            cmd = [str(self.venv_python), "-m", "pip", "install", install_package]
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if process.returncode == 0:
                logger.info(f"Модуль {install_package} успешно установлен")
            else:
                logger.error(f"Ошибка при установке {install_package}: {process.stderr}")

        except Exception as e:
            logger.error(f"Ошибка при установке модуля {install_package}: {e}")

    async def fix_connection_errors(self, error_info: dict):
        """Исправление ошибок подключения"""
        logger.info("Исправляем ошибки подключения...")

        line = error_info.get("line", "")

        if "database" in line.lower() or "postgres" in line.lower():
            await self._check_postgresql()
        elif "redis" in line.lower():
            await self._check_redis()
        elif "websocket" in line.lower():
            await self._check_websocket_endpoints()

    async def fix_database_errors(self, error_info: dict):
        """Исправление ошибок базы данных"""
        logger.info("Исправляем ошибки базы данных...")

        line = error_info.get("line", "")

        if "database" in line and "does not exist" in line:
            await self._create_database()
        elif "relation" in line and "does not exist" in line:
            await self._run_migrations()

    async def fix_ml_errors(self, error_info: dict):
        """Исправление ошибок ML"""
        logger.info("Исправляем ошибки ML...")

        line = error_info.get("line", "")

        if "torch" in line.lower():
            await self._install_pytorch()
        elif "model file not found" in line.lower():
            await self._check_ml_models()
        elif "cuda" in line.lower():
            await self._setup_cuda()

    async def fix_permission_errors(self, error_info: dict):
        """Исправление ошибок доступа"""
        logger.info("Исправляем ошибки доступа...")

        # Исправляем права доступа к критическим директориям
        dirs_to_fix = [
            self.project_root / "data/logs",
            self.project_root / "models/saved",
            self.project_root / "logs",
        ]

        for dir_path in dirs_to_fix:
            if dir_path.exists():
                try:
                    os.chmod(dir_path, 0o755)
                    for item in dir_path.rglob("*"):
                        if item.is_file():
                            os.chmod(item, 0o644)
                        else:
                            os.chmod(item, 0o755)
                    logger.info(f"Исправлены права доступа для {dir_path}")
                except Exception as e:
                    logger.error(f"Ошибка при исправлении прав {dir_path}: {e}")

    async def _check_postgresql(self):
        """Проверка PostgreSQL"""
        try:
            # Проверяем подключение к PostgreSQL на порту 5555
            cmd = [
                "psql",
                "-h",
                "localhost",
                "-p",
                "5555",
                "-U",
                "obertruper",
                "-d",
                "bot_trading_v3",
                "-c",
                "SELECT 1;",
            ]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if process.returncode == 0:
                logger.info("PostgreSQL доступен")
                return True
            else:
                logger.warning(f"PostgreSQL недоступен: {process.stderr}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при проверке PostgreSQL: {e}")
            return False

    async def _check_redis(self):
        """Проверка Redis"""
        try:
            import redis

            r = redis.Redis(host="localhost", port=6379, db=0)
            r.ping()
            logger.info("Redis доступен")
            return True
        except Exception as e:
            logger.warning(f"Redis недоступен: {e}")
            return False

    async def _check_websocket_endpoints(self):
        """Проверка WebSocket endpoints"""
        # Здесь можно добавить проверки специфичных WebSocket подключений
        logger.info("Проверяем WebSocket endpoints...")

    async def _create_database(self):
        """Создание базы данных"""
        try:
            cmd = [
                "sudo",
                "-u",
                "postgres",
                "psql",
                "-p",
                "5555",
                "-c",
                "CREATE DATABASE bot_trading_v3 OWNER obertruper;",
            ]
            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode == 0:
                logger.info("База данных bot_trading_v3 создана")
            else:
                logger.error(f"Ошибка при создании БД: {process.stderr}")

        except Exception as e:
            logger.error(f"Ошибка при создании базы данных: {e}")

    async def _run_migrations(self):
        """Запуск миграций"""
        try:
            cmd = [str(self.venv_python), "-m", "alembic", "upgrade", "head"]
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if process.returncode == 0:
                logger.info("Миграции успешно применены")
            else:
                logger.error(f"Ошибка при применении миграций: {process.stderr}")

        except Exception as e:
            logger.error(f"Ошибка при запуске миграций: {e}")

    async def _install_pytorch(self):
        """Установка PyTorch"""
        try:
            cmd = [
                str(self.venv_python),
                "-m",
                "pip",
                "install",
                "torch",
                "torchvision",
                "torchaudio",
            ]
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if process.returncode == 0:
                logger.info("PyTorch успешно установлен")
            else:
                logger.error(f"Ошибка при установке PyTorch: {process.stderr}")

        except Exception as e:
            logger.error(f"Ошибка при установке PyTorch: {e}")

    async def _check_ml_models(self):
        """Проверка ML моделей"""
        models_dir = self.project_root / "models/saved"

        if not models_dir.exists():
            logger.warning("Директория models/saved не существует")
            models_dir.mkdir(parents=True, exist_ok=True)

        required_files = ["best_model.pth", "data_scaler.pkl"]
        missing_files = []

        for file_name in required_files:
            if not (models_dir / file_name).exists():
                missing_files.append(file_name)

        if missing_files:
            logger.warning(f"Отсутствуют файлы моделей: {missing_files}")
        else:
            logger.info("Все файлы моделей присутствуют")

    async def _setup_cuda(self):
        """Настройка CUDA (если доступна)"""
        try:
            import torch

            if torch.cuda.is_available():
                logger.info(f"CUDA доступна: {torch.cuda.get_device_name(0)}")
            else:
                logger.info("CUDA недоступна, используем CPU")
        except ImportError:
            logger.warning("PyTorch не установлен")

    async def _setup_venv(self):
        """Настройка виртуального окружения"""
        logger.warning("Виртуальное окружение не найдено, создаем...")

        try:
            # Создаем venv
            cmd = [sys.executable, "-m", "venv", str(self.project_root / "venv")]
            subprocess.run(cmd, check=True, cwd=self.project_root)

            # Устанавливаем основные зависимости
            cmd = [
                str(self.venv_python),
                "-m",
                "pip",
                "install",
                "-r",
                "requirements.txt",
            ]
            subprocess.run(cmd, check=True, cwd=self.project_root)

            logger.info("Виртуальное окружение создано и настроено")

        except Exception as e:
            logger.error(f"Ошибка при создании venv: {e}")

    async def _check_required_files(self):
        """Проверка необходимых файлов"""
        required_files = [
            "main.py",
            "unified_launcher.py",
            "requirements.txt",
            ".env",
            "config/system.yaml",
        ]

        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            logger.warning(f"Отсутствуют файлы: {missing_files}")
        else:
            logger.info("Все необходимые файлы присутствуют")

    async def call_specialized_agent(self, agent_type: str, task_description: str) -> bool:
        """Вызов специализированного агента"""
        logger.info(f"Вызываем агента {agent_type} для задачи: {task_description}")

        # Здесь можно интегрироваться с существующими агентами системы
        # Например, через ai_agents/agent_manager.py

        try:
            # Пример интеграции с Task tool (если доступен)
            agent_commands = {
                "debug-specialist": self._call_debug_specialist,
                "exchange-specialist": self._call_exchange_specialist,
                "database-architect": self._call_database_architect,
                "ml-optimizer": self._call_ml_optimizer,
                "performance-tuner": self._call_performance_tuner,
            }

            if agent_type in agent_commands:
                return await agent_commands[agent_type](task_description)
            else:
                logger.warning(f"Неизвестный тип агента: {agent_type}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при вызове агента {agent_type}: {e}")
            return False

    async def _call_debug_specialist(self, task: str) -> bool:
        """Вызов debug-specialist агента"""
        logger.info(f"Debug specialist: {task}")
        # Здесь интеграция с debug_specialist
        return True

    async def _call_exchange_specialist(self, task: str) -> bool:
        """Вызов exchange-specialist агента"""
        logger.info(f"Exchange specialist: {task}")
        # Здесь интеграция с exchange_specialist
        return True

    async def _call_database_architect(self, task: str) -> bool:
        """Вызов database-architect агента"""
        logger.info(f"Database architect: {task}")
        # Здесь интеграция с database_architect
        return True

    async def _call_ml_optimizer(self, task: str) -> bool:
        """Вызов ml-optimizer агента"""
        logger.info(f"ML optimizer: {task}")
        # Здесь интеграция с ml_optimizer
        return True

    async def _call_performance_tuner(self, task: str) -> bool:
        """Вызов performance-tuner агента"""
        logger.info(f"Performance tuner: {task}")
        # Здесь интеграция с performance_tuner
        return True

    def get_error_report(self) -> dict:
        """Получить отчет об ошибках"""
        return {
            "total_errors": len(self.error_history),
            "error_types": self._count_error_types(),
            "recent_errors": self.error_history[-10:],  # Последние 10 ошибок
            "timestamp": datetime.now().isoformat(),
        }

    def _count_error_types(self) -> dict[str, int]:
        """Подсчет ошибок по типам"""
        counts = {}
        for error in self.error_history:
            error_type = error["type"]
            counts[error_type] = counts.get(error_type, 0) + 1
        return counts

    async def stop_monitoring(self):
        """Остановка мониторинга"""
        logger.info("Останавливаем мониторинг...")
        self.running = False

        # Завершаем активные процессы
        for name, process in self.processes.items():
            try:
                process.terminate()
                logger.info(f"Процесс {name} завершен")
            except Exception as e:
                logger.error(f"Ошибка при завершении процесса {name}: {e}")

        self.processes.clear()


async def main():
    """Главная функция для тестирования агента"""
    agent = TestingAgent()

    try:
        # Запускаем систему с мониторингом
        success = await agent.start_system_monitoring("core")

        if success:
            logger.info("Система запущена успешно")

            # Мониторим некоторое время
            await asyncio.sleep(30)

            # Получаем отчет
            report = agent.get_error_report()
            logger.info(f"Отчет об ошибках: {json.dumps(report, indent=2, ensure_ascii=False)}")
        else:
            logger.error("Не удалось запустить систему")

    except KeyboardInterrupt:
        logger.info("Остановка по запросу пользователя")
    finally:
        await agent.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
