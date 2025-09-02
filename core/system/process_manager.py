#!/usr/bin/env python3
"""
Менеджер процессов для управления компонентами системы
"""

import asyncio
import os
import signal
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from core.logger import setup_logger

logger = setup_logger(__name__)


class ProcessInfo:
    """Информация о процессе"""

    def __init__(
        self,
        name: str,
        pid: int,
        command: str,
        auto_restart: bool = True,
        cwd: str | None = None,
    ):
        self.name = name
        self.pid = pid
        self.command = command
        self.auto_restart = auto_restart
        self.cwd = cwd
        self.start_time = datetime.now()
        self.restart_count = 0
        self.process: asyncio.subprocess.Process | None = None


class ProcessManager:
    """
    Менеджер для управления дочерними процессами

    Функциональность:
    - Запуск и остановка процессов
    - Мониторинг состояния
    - Автоматический перезапуск при сбоях
    - Логирование stdout/stderr
    """

    def __init__(self):
        self.processes: dict[str, ProcessInfo] = {}
        self.log_dir = Path("logs/processes")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._monitoring_tasks: dict[str, asyncio.Task] = {}
        self.is_running = False

    async def initialize(self):
        """Инициализация менеджера процессов"""
        self.is_running = True
        logger.info("✅ ProcessManager инициализирован")

    async def start_component(
        self,
        name: str,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        auto_restart: bool = True,
    ) -> int:
        """
        Запуск компонента как отдельного процесса

        Args:
            name: Имя компонента
            command: Команда для запуска
            cwd: Рабочая директория
            env: Дополнительные переменные окружения
            auto_restart: Автоматический перезапуск при сбое

        Returns:
            PID процесса
        """
        if name in self.processes:
            logger.warning(f"Компонент {name} уже запущен")
            return self.processes[name].pid

        logger.info(f"🚀 Запуск компонента {name}: {command}")

        # Подготовка окружения
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
            logger.info(f"📋 Дополнительные env переменные для {name}: {env}")

        # Подготовка рабочей директории
        if cwd:
            working_dir = Path(cwd).resolve()
            if not working_dir.exists():
                raise FileNotFoundError(f"Рабочая директория не найдена: {cwd}")
        else:
            working_dir = Path.cwd()

        # Лог-файлы для процесса
        stdout_log = self.log_dir / f"{name}_stdout.log"
        stderr_log = self.log_dir / f"{name}_stderr.log"

        try:
            # Запуск процесса
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(working_dir),
                env=process_env,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            # Сохраняем информацию о процессе
            proc_info = ProcessInfo(
                name=name,
                pid=process.pid,
                command=command,
                auto_restart=auto_restart,
                cwd=str(working_dir),
            )
            proc_info.process = process
            self.processes[name] = proc_info

            # Запускаем мониторинг процесса
            monitor_task = asyncio.create_task(self._monitor_process(name, stdout_log, stderr_log))
            self._monitoring_tasks[name] = monitor_task

            logger.info(f"✅ Компонент {name} запущен с PID {process.pid}")
            return process.pid

        except Exception as e:
            logger.error(f"❌ Ошибка запуска {name}: {e}")
            raise

    async def _monitor_process(self, name: str, stdout_log: Path, stderr_log: Path):
        """Мониторинг процесса и логирование вывода с оптимизированной обработкой"""
        proc_info = self.processes.get(name)
        if not proc_info or not proc_info.process:
            return

        process = proc_info.process
        log_buffer = []
        last_flush = datetime.now()

        # Создаем оптимизированную функцию чтения с буферизацией
        async def read_stream_optimized(stream, file, prefix):
            nonlocal log_buffer, last_flush

            try:
                async for line in stream:
                    now = datetime.now()

                    # Буферизуем логи для уменьшения I/O операций
                    log_line = (
                        f"[{now.strftime('%H:%M:%S')}] {line.decode('utf-8', errors='replace')}"
                    )
                    log_buffer.append(log_line.encode("utf-8"))

                    # Сброс буфера каждые 5 секунд или при накоплении 50 строк
                    if (now - last_flush).total_seconds() > 5 or len(log_buffer) >= 50:
                        file.write(b"".join(log_buffer))
                        file.flush()
                        log_buffer.clear()
                        last_flush = now

                    # Выводим только значимые сообщения с корректным уровнем
                    line_str = line.decode("utf-8", errors="replace").strip()
                    lower = line.lower()

                    # Явное соответствие уровням из исходной строки
                    if b" - ERROR - " in line or b"CRITICAL" in line:
                        logger.error(f"[{name}] {line_str}")
                    elif b" - WARNING - " in line:
                        logger.warning(f"[{name}] {line_str}")
                    else:
                        # Эвристики по проблемным ключевым словам
                        is_problem_connection = b"connection" in lower and (
                            b"error" in lower
                            or b"fail" in lower
                            or b"refused" in lower
                            or b"exhausted" in lower
                        )
                        is_timeout = b"timeout" in lower
                        is_benign_init = (
                            b"initialized" in lower or b"created" in lower
                        ) and b"circuit breaker" in lower

                        if (is_problem_connection or is_timeout) and not is_benign_init:
                            logger.warning(f"[{name}] {line_str}")
                        # Иначе подавляем до DEBUG, чтобы не поднимать уровень лишним INFO
                        elif b" - INFO - " in line:
                            logger.info(f"[{name}] {line_str}")
                        else:
                            logger.debug(f"[{name}] {line_str}")

            except Exception as e:
                logger.debug(f"Stream reading error for {name}: {e}")
            finally:
                # Финальный сброс буфера
                if log_buffer:
                    file.write(b"".join(log_buffer))
                    file.flush()

        # Открываем файлы для логирования с буферизацией
        try:
            with (
                open(stdout_log, "ab", buffering=8192) as stdout_file,
                open(stderr_log, "ab", buffering=8192) as stderr_file,
            ):
                # Запускаем чтение обоих потоков с timeout protection
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream_optimized(process.stdout, stdout_file, "STDOUT"),
                        read_stream_optimized(process.stderr, stderr_file, "STDERR"),
                        return_exceptions=True,
                    ),
                    timeout=None,  # Убираем общий timeout для избежания BrokenPipeError
                )
        except Exception as e:
            logger.debug(f"Process monitoring error for {name}: {e}")

        # Ждем завершения процесса с улучшенной обработкой
        try:
            return_code = await process.wait()
        except Exception as e:
            logger.debug(f"Process wait error for {name}: {e}")
            return_code = -1

        # Обрабатываем завершение с оптимизированной логикой перезапуска
        if name in self.processes:
            if return_code != 0:
                # Анализируем причину завершения
                if return_code == -1 or "BrokenPipeError" in str(return_code):
                    logger.debug(f"🔄 Компонент {name} завершился из-за pipe/timeout ошибки")
                else:
                    logger.error(f"❌ Компонент {name} завершился с кодом {return_code}")

                # Интеллектуальный перезапуск с экспоненциальной задержкой
                if proc_info.auto_restart and self.is_running:
                    proc_info.restart_count += 1
                    max_restarts = 3 if name == "core" else 5  # Меньше перезапусков для core

                    if proc_info.restart_count <= max_restarts:
                        # Экспоненциальная задержка: 2^attempt секунд (2, 4, 8, 16...)
                        delay = min(2**proc_info.restart_count, 60)  # Максимум 60 секунд

                        logger.info(
                            f"🔄 Перезапуск {name} через {delay}с (попытка {proc_info.restart_count}/{max_restarts})"
                        )
                        await asyncio.sleep(delay)

                        # Проверяем, что система все еще работает
                        if not self.is_running:
                            return

                        # Сохраняем информацию для перезапуска
                        restart_count = proc_info.restart_count
                        command = proc_info.command
                        cwd = proc_info.cwd
                        auto_restart = proc_info.auto_restart

                        # Удаляем старую информацию
                        if name in self.processes:
                            del self.processes[name]

                        # Перезапускаем с сохранением счетчика
                        try:
                            pid = await self.start_component(
                                name=name,
                                command=command,
                                cwd=cwd,
                                auto_restart=auto_restart,
                            )
                            # Восстанавливаем счетчик
                            if name in self.processes:
                                self.processes[name].restart_count = restart_count
                                logger.info(f"✅ Компонент {name} перезапущен успешно (PID: {pid})")
                        except Exception as e:
                            logger.error(f"❌ Ошибка перезапуска {name}: {e}")
                            # Увеличиваем задержку при ошибке перезапуска
                            await asyncio.sleep(30)
                    else:
                        logger.error(f"❌ Превышен лимит перезапусков для {name} ({max_restarts})")
                        if name in self.processes:
                            del self.processes[name]
            else:
                logger.info(f"✅ Компонент {name} завершился успешно")
                if name in self.processes:
                    del self.processes[name]

    async def stop_component(self, name: str, timeout: float = 10.0):
        """
        Остановка компонента

        Args:
            name: Имя компонента
            timeout: Таймаут ожидания завершения
        """
        if name not in self.processes:
            logger.warning(f"Компонент {name} не найден")
            return

        proc_info = self.processes[name]
        process = proc_info.process

        if not process or process.returncode is not None:
            logger.info(f"Компонент {name} уже остановлен")
            del self.processes[name]
            return

        logger.info(f"⏸️ Остановка компонента {name}...")

        try:
            # Сначала пробуем graceful shutdown
            if os.name != "nt":
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()

            # Ждем завершения
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
                logger.info(f"✅ Компонент {name} остановлен")
            except TimeoutError:
                # Принудительное завершение
                logger.warning(f"⚠️ Принудительная остановка {name}")
                if os.name != "nt":
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
                await process.wait()

        except Exception as e:
            logger.error(f"Ошибка остановки {name}: {e}")
        finally:
            # Удаляем из списка процессов
            if name in self.processes:
                del self.processes[name]

            # Отменяем задачу мониторинга
            if name in self._monitoring_tasks:
                self._monitoring_tasks[name].cancel()
                try:
                    del self._monitoring_tasks[name]
                except KeyError:
                    pass  # Уже удалено

    async def restart_component(self, name: str):
        """Перезапуск компонента"""
        if name not in self.processes:
            logger.error(f"Компонент {name} не найден для перезапуска")
            return

        proc_info = self.processes[name]
        logger.info(f"🔄 Перезапуск компонента {name}")

        # Останавливаем
        await self.stop_component(name)

        # Небольшая пауза
        await asyncio.sleep(2)

        # Запускаем заново
        await self.start_component(
            name=name,
            command=proc_info.command,
            cwd=proc_info.cwd,
            auto_restart=proc_info.auto_restart,
        )

    async def stop_all(self):
        """Остановка всех процессов"""
        self.is_running = False
        logger.info("🛑 Остановка всех процессов...")

        # Копируем список для итерации
        components = list(self.processes.keys())

        # Останавливаем все процессы
        stop_tasks = []
        for name in components:
            stop_tasks.append(self.stop_component(name))

        # Ждем завершения всех
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        logger.info("✅ Все процессы остановлены")

    def get_process_info(self, name: str) -> dict[str, Any] | None:
        """Получение информации о процессе"""
        if name not in self.processes:
            return None

        proc_info = self.processes[name]

        # Получаем информацию через psutil
        try:
            process = psutil.Process(proc_info.pid)
            return {
                "name": name,
                "pid": proc_info.pid,
                "status": process.status(),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "start_time": proc_info.start_time,
                "restart_count": proc_info.restart_count,
                "uptime": datetime.now() - proc_info.start_time,
            }
        except psutil.NoSuchProcess:
            return {
                "name": name,
                "pid": proc_info.pid,
                "status": "terminated",
                "start_time": proc_info.start_time,
                "restart_count": proc_info.restart_count,
            }

    def get_all_processes_info(self) -> list[dict[str, Any]]:
        """Получение информации о всех процессах"""
        info_list = []
        for name in self.processes:
            info = self.get_process_info(name)
            if info:
                info_list.append(info)
        return info_list
