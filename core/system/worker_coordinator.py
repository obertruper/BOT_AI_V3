"""
Координатор воркеров для предотвращения дублирующих ML процессов
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class WorkerInfo:
    """Информация о воркере"""

    worker_id: str
    process_id: int
    worker_type: str  # 'ml_manager', 'signal_processor', 'trading_engine'
    started_at: datetime
    last_heartbeat: datetime
    status: str  # 'starting', 'running', 'stopping', 'error'
    tasks: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkerCoordinator:
    """
    Централизованный координатор воркеров для предотвращения дублирования процессов

    Основные функции:
    - Регистрация и отслеживание воркеров
    - Предотвращение запуска дублирующих процессов
    - Мониторинг состояния воркеров
    - Автоматическое восстановление упавших воркеров
    - Координация задач между воркерами
    """

    def __init__(self):
        self.workers: dict[str, WorkerInfo] = {}
        self.worker_locks: dict[str, asyncio.Lock] = {}
        self.task_assignments: dict[str, str] = {}  # task_id -> worker_id
        self.heartbeat_timeout = timedelta(minutes=2)
        self.cleanup_interval = 60  # секунд
        self._running = False
        self._cleanup_task = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Запуск координатора"""
        if self._running:
            logger.warning("WorkerCoordinator уже запущен")
            return

        self._running = True
        logger.info("🚀 Запуск WorkerCoordinator")

        # Очистка zombie процессов
        await self._cleanup_dead_processes()

        # Запуск периодической очистки
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def stop(self):
        """Остановка координатора"""
        if not self._running:
            return

        self._running = False
        logger.info("🛑 Остановка WorkerCoordinator")

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Уведомляем всех воркеров об остановке
        for worker_id in list(self.workers.keys()):
            await self.unregister_worker(worker_id)

    async def register_worker(
        self,
        worker_type: str,
        worker_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Регистрация воркера

        Args:
            worker_type: Тип воркера ('ml_manager', 'signal_processor', etc.)
            worker_id: Уникальный ID воркера (если None - автогенерация)
            metadata: Дополнительные метаданные воркера

        Returns:
            worker_id если регистрация успешна, None если такой воркер уже работает
        """
        async with self._lock:
            # Проверяем, есть ли уже активный воркер данного типа
            active_workers = self._get_active_workers_by_type(worker_type)

            if active_workers:
                logger.warning(
                    f"⚠️  Воркер типа '{worker_type}' уже активен: {[w.worker_id for w in active_workers]}"
                )
                return None

            # Генерируем ID если не указан
            if worker_id is None:
                worker_id = f"{worker_type}_{int(time.time())}_{os.getpid()}"

            # Проверяем уникальность ID
            if worker_id in self.workers:
                logger.error(f"❌ Воркер с ID '{worker_id}' уже существует")
                return None

            # Создаем воркера
            worker_info = WorkerInfo(
                worker_id=worker_id,
                process_id=os.getpid(),
                worker_type=worker_type,
                started_at=datetime.now(),
                last_heartbeat=datetime.now(),
                status="starting",
                metadata=metadata or {},
            )

            self.workers[worker_id] = worker_info
            self.worker_locks[worker_id] = asyncio.Lock()

            logger.info(
                f"✅ Зарегистрирован воркер: {worker_id} (тип: {worker_type}, PID: {os.getpid()})"
            )
            return worker_id

    async def unregister_worker(self, worker_id: str):
        """Снятие воркера с регистрации"""
        async with self._lock:
            if worker_id not in self.workers:
                logger.warning(f"⚠️  Воркер '{worker_id}' не найден для снятия с регистрации")
                return

            worker = self.workers[worker_id]
            worker.status = "stopping"

            # Освобождаем задачи
            tasks_to_reassign = []
            for task_id, assigned_worker in self.task_assignments.items():
                if assigned_worker == worker_id:
                    tasks_to_reassign.append(task_id)

            for task_id in tasks_to_reassign:
                del self.task_assignments[task_id]

            # Удаляем воркера
            del self.workers[worker_id]
            if worker_id in self.worker_locks:
                del self.worker_locks[worker_id]

            logger.info(f"🗑️  Снят с регистрации воркер: {worker_id}")

            if tasks_to_reassign:
                logger.info(f"📋 Освобождены задачи: {tasks_to_reassign}")

    async def heartbeat(
        self,
        worker_id: str,
        status: str | None = None,
        active_tasks: int | None = None,
        tasks: set[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Отправка heartbeat от воркера

        Args:
            worker_id: ID воркера
            status: Текущий статус воркера
            active_tasks: Количество активных задач (для совместимости)
            tasks: Текущие задачи воркера
            metadata: Дополнительные метаданные

        Returns:
            True если heartbeat принят, False если воркер не найден
        """
        async with self._lock:
            if worker_id not in self.workers:
                logger.warning(f"⚠️  Heartbeat от незарегистрированного воркера: {worker_id}")
                return False

            worker = self.workers[worker_id]
            worker.last_heartbeat = datetime.now()

            if status:
                worker.status = status

            if tasks is not None:
                worker.tasks = tasks

            # Обновляем метаданные если переданы
            if metadata:
                worker.metadata.update(metadata)

            # Обновляем количество активных задач если передано
            if active_tasks is not None:
                worker.metadata["active_tasks"] = active_tasks

            return True

    async def can_assign_task(self, task_id: str, worker_type: str) -> bool:
        """
        Проверка возможности назначения задачи

        Args:
            task_id: ID задачи
            worker_type: Требуемый тип воркера

        Returns:
            True если задачу можно назначить
        """
        async with self._lock:
            # Проверяем, не назначена ли уже задача
            if task_id in self.task_assignments:
                assigned_worker = self.task_assignments[task_id]
                if assigned_worker in self.workers:
                    logger.debug(f"📋 Задача '{task_id}' уже назначена воркеру '{assigned_worker}'")
                    return False
                else:
                    # Воркер умер, освобождаем задачу
                    del self.task_assignments[task_id]

            # Проверяем наличие активного воркера нужного типа
            active_workers = self._get_active_workers_by_type(worker_type)
            return len(active_workers) > 0

    async def assign_task(self, task_id: str, worker_type: str) -> str | None:
        """
        Назначение задачи воркеру

        Args:
            task_id: ID задачи
            worker_type: Требуемый тип воркера

        Returns:
            worker_id если задача назначена, None если не удалось
        """
        async with self._lock:
            if not await self.can_assign_task(task_id, worker_type):
                return None

            # Находим наименее загруженного воркера подходящего типа
            active_workers = self._get_active_workers_by_type(worker_type)
            if not active_workers:
                logger.error(
                    f"❌ Нет активных воркеров типа '{worker_type}' для задачи '{task_id}'"
                )
                return None

            # Выбираем воркера с минимальным количеством задач
            best_worker = min(active_workers, key=lambda w: len(w.tasks))

            # Назначаем задачу
            self.task_assignments[task_id] = best_worker.worker_id
            best_worker.tasks.add(task_id)

            logger.info(f"📋 Назначена задача '{task_id}' воркеру '{best_worker.worker_id}'")
            return best_worker.worker_id

    async def complete_task(self, task_id: str, worker_id: str):
        """Завершение задачи воркером"""
        async with self._lock:
            if task_id in self.task_assignments:
                if self.task_assignments[task_id] == worker_id:
                    del self.task_assignments[task_id]

                    if worker_id in self.workers:
                        self.workers[worker_id].tasks.discard(task_id)

                    logger.info(f"✅ Задача '{task_id}' завершена воркером '{worker_id}'")
                else:
                    logger.warning(
                        f"⚠️  Попытка завершить задачу '{task_id}' воркером '{worker_id}', но она назначена другому"
                    )

    def get_worker_stats(self) -> dict[str, Any]:
        """Получение статистики воркеров"""
        stats = {
            "total_workers": len(self.workers),
            "workers_by_type": {},
            "workers_by_status": {},
            "active_tasks": len(self.task_assignments),
            "workers": [],
        }

        for worker in self.workers.values():
            # Группировка по типам
            if worker.worker_type not in stats["workers_by_type"]:
                stats["workers_by_type"][worker.worker_type] = 0
            stats["workers_by_type"][worker.worker_type] += 1

            # Группировка по статусам
            if worker.status not in stats["workers_by_status"]:
                stats["workers_by_status"][worker.status] = 0
            stats["workers_by_status"][worker.status] += 1

            # Информация о воркере
            stats["workers"].append(
                {
                    "worker_id": worker.worker_id,
                    "worker_type": worker.worker_type,
                    "process_id": worker.process_id,
                    "status": worker.status,
                    "started_at": worker.started_at.isoformat(),
                    "last_heartbeat": worker.last_heartbeat.isoformat(),
                    "active_tasks": len(worker.tasks),
                    "tasks": list(worker.tasks),
                    "uptime_seconds": (datetime.now() - worker.started_at).total_seconds(),
                }
            )

        return stats

    def _get_active_workers_by_type(self, worker_type: str) -> list[WorkerInfo]:
        """Получение активных воркеров определенного типа"""
        now = datetime.now()
        active_workers = []

        for worker in self.workers.values():
            if (
                worker.worker_type == worker_type
                and worker.status in ["running", "starting"]
                and (now - worker.last_heartbeat) < self.heartbeat_timeout
            ):
                active_workers.append(worker)

        return active_workers

    async def _cleanup_dead_processes(self):
        """Очистка мертвых процессов"""
        to_remove = []

        for worker_id, worker in self.workers.items():
            try:
                # Проверяем, жив ли процесс
                if not psutil.pid_exists(worker.process_id):
                    logger.warning(
                        f"💀 Процесс {worker.process_id} воркера '{worker_id}' не найден"
                    )
                    to_remove.append(worker_id)
                    continue

                # Проверяем timeout heartbeat
                if (datetime.now() - worker.last_heartbeat) > self.heartbeat_timeout:
                    logger.warning(
                        f"💔 Воркер '{worker_id}' не отвечает (последний heartbeat: {worker.last_heartbeat})"
                    )
                    to_remove.append(worker_id)

            except Exception as e:
                logger.error(f"❌ Ошибка проверки воркера '{worker_id}': {e}")
                to_remove.append(worker_id)

        # Удаляем мертвые воркеры
        for worker_id in to_remove:
            await self.unregister_worker(worker_id)

    async def _periodic_cleanup(self):
        """Периодическая очистка мертвых процессов"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_dead_processes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка периодической очистки: {e}")


# Глобальный экземпляр координатора
worker_coordinator = WorkerCoordinator()
