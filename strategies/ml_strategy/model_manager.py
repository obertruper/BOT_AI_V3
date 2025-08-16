#!/usr/bin/env python3
"""
Менеджер для управления ML моделями в торговых стратегиях
Обеспечивает загрузку, обновление и мониторинг моделей
"""

import json
import logging
import pickle
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import torch
import yaml

from ml.logic.patchtst_model import UnifiedPatchTSTForTrading, load_model_safe


class ModelManager:
    """
    Менеджер ML моделей для торговых стратегий

    Функции:
    - Загрузка и кеширование моделей
    - Версионирование моделей
    - Мониторинг производительности
    - Автоматическое обновление моделей
    - A/B тестирование моделей
    """

    def __init__(
        self,
        models_dir: str = "models",
        cache_dir: str = "cache/models",
        logger: logging.Logger | None = None,
    ):
        """
        Инициализация менеджера моделей

        Args:
            models_dir: Директория с моделями
            cache_dir: Директория для кеша
            logger: Логгер
        """
        self.models_dir = Path(models_dir)
        self.cache_dir = Path(cache_dir)
        self.logger = logger or logging.getLogger(__name__)

        # Создаем директории если не существуют
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Кеш загруженных моделей
        self.loaded_models: dict[str, dict[str, Any]] = {}

        # Метрики производительности моделей
        self.model_metrics: dict[str, dict[str, Any]] = {}

        # Конфигурация
        self.config = self._load_config()

        # Устройство для вычислений
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _load_config(self) -> dict[str, Any]:
        """Загрузка конфигурации менеджера"""
        config_path = self.models_dir / "manager_config.yaml"

        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        else:
            # Конфигурация по умолчанию
            return {
                "auto_update": True,
                "update_interval_hours": 24,
                "performance_threshold": 0.6,
                "max_cache_size_gb": 10,
                "enable_ab_testing": False,
                "model_versioning": True,
            }

    async def load_model(
        self, model_name: str, version: str | None = None
    ) -> tuple[Any, dict[str, Any]]:
        """
        Загрузка модели с кешированием

        Args:
            model_name: Имя модели
            version: Версия модели (если None - последняя)

        Returns:
            Кортеж (модель, метаданные)
        """
        # Проверяем кеш
        cache_key = f"{model_name}_{version or 'latest'}"
        if cache_key in self.loaded_models:
            self.logger.debug(f"Загрузка модели {cache_key} из кеша")
            return (
                self.loaded_models[cache_key]["model"],
                self.loaded_models[cache_key]["metadata"],
            )

        # Определяем путь к модели
        model_path = self._get_model_path(model_name, version)

        if not model_path.exists():
            raise FileNotFoundError(f"Модель не найдена: {model_path}")

        # Загружаем модель и компоненты
        try:
            model_data = await self._load_model_components(model_path)

            # Кешируем
            self.loaded_models[cache_key] = model_data

            # Очищаем старый кеш если превышен лимит
            await self._cleanup_cache()

            self.logger.info(f"Модель {model_name} v{version or 'latest'} успешно загружена")

            return model_data["model"], model_data["metadata"]

        except Exception as e:
            self.logger.error(f"Ошибка загрузки модели {model_name}: {e}")
            raise

    async def _load_model_components(self, model_path: Path) -> dict[str, Any]:
        """Загрузка всех компонентов модели"""
        model_dir = model_path.parent

        # Загрузка метаданных
        metadata_path = model_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
        else:
            metadata = {}

        # Загрузка конфигурации модели
        config_path = model_dir / "config.pkl"
        with open(config_path, "rb") as f:
            model_config = pickle.load(f)

        # Загрузка scaler
        scaler_path = model_dir / "scaler.pkl"
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)

        # Создание и загрузка модели
        model = UnifiedPatchTSTForTrading(model_config)

        # Безопасная загрузка весов с обработкой несовместимостей
        try:
            model = load_model_safe(model, str(model_path), device=str(self.device))
            self.logger.info("Модель загружена с использованием безопасной функции")

            # Пытаемся загрузить дополнительные метрики если есть
            checkpoint = torch.load(model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and "metrics" in checkpoint:
                metadata["training_metrics"] = checkpoint["metrics"]
        except Exception as e:
            self.logger.warning(f"Ошибка при безопасной загрузке, пробуем стандартный метод: {e}")
            # Фоллбэк на стандартную загрузку
            checkpoint = torch.load(model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"], strict=False)
                if "metrics" in checkpoint:
                    metadata["training_metrics"] = checkpoint["metrics"]
            else:
                model.load_state_dict(checkpoint, strict=False)

        model.to(self.device)
        model.eval()

        # Загрузка feature names если есть
        feature_names_path = model_dir / "feature_names.pkl"
        if feature_names_path.exists():
            with open(feature_names_path, "rb") as f:
                feature_names = pickle.load(f)
        else:
            feature_names = None

        return {
            "model": model,
            "scaler": scaler,
            "config": model_config,
            "feature_names": feature_names,
            "metadata": metadata,
            "loaded_at": datetime.utcnow(),
        }

    def _get_model_path(self, model_name: str, version: str | None = None) -> Path:
        """Получение пути к модели"""
        if version:
            return self.models_dir / model_name / f"v{version}" / "model.pth"
        else:
            # Ищем последнюю версию
            model_dir = self.models_dir / model_name
            if not model_dir.exists():
                return self.models_dir / model_name / "model.pth"

            versions = [d for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
            if versions:
                latest_version = sorted(versions, key=lambda x: x.name)[-1]
                return latest_version / "model.pth"
            else:
                return model_dir / "model.pth"

    async def update_model(self, model_name: str, new_model_path: str) -> bool:
        """
        Обновление модели с версионированием

        Args:
            model_name: Имя модели
            new_model_path: Путь к новой модели

        Returns:
            True если обновление успешно
        """
        try:
            # Проверяем новую модель
            new_model_dir = Path(new_model_path)
            if not new_model_dir.exists():
                self.logger.error(f"Новая модель не найдена: {new_model_path}")
                return False

            # Определяем версию
            if self.config.get("model_versioning", True):
                version = self._get_next_version(model_name)
                target_dir = self.models_dir / model_name / f"v{version}"
            else:
                target_dir = self.models_dir / model_name
                # Делаем бекап текущей версии
                if target_dir.exists():
                    backup_dir = (
                        self.models_dir
                        / model_name
                        / f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    )
                    shutil.move(str(target_dir), str(backup_dir))

            # Копируем новую модель
            shutil.copytree(new_model_dir, target_dir)

            # Обновляем метаданные
            metadata = {
                "version": version if self.config.get("model_versioning", True) else "latest",
                "updated_at": datetime.utcnow().isoformat(),
                "source": new_model_path,
            }

            with open(target_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            # Очищаем кеш для этой модели
            cache_keys_to_remove = [
                k for k in self.loaded_models.keys() if k.startswith(model_name)
            ]
            for key in cache_keys_to_remove:
                del self.loaded_models[key]

            self.logger.info(
                f"Модель {model_name} успешно обновлена до версии {metadata['version']}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Ошибка обновления модели {model_name}: {e}")
            return False

    def _get_next_version(self, model_name: str) -> str:
        """Получение следующей версии модели"""
        model_dir = self.models_dir / model_name
        if not model_dir.exists():
            return "1.0"

        versions = [
            d.name[1:] for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("v")
        ]

        if not versions:
            return "1.0"

        # Парсим версии и увеличиваем
        latest_version = sorted(versions, key=lambda x: [int(p) for p in x.split(".")])[-1]
        major, minor = map(int, latest_version.split("."))

        return f"{major}.{minor + 1}"

    async def _cleanup_cache(self):
        """Очистка кеша если превышен лимит"""
        # Подсчитываем размер кеша
        total_size = 0
        for model_data in self.loaded_models.values():
            # Примерная оценка размера модели в памяти
            if "model" in model_data:
                model = model_data["model"]
                size = sum(p.numel() * p.element_size() for p in model.parameters())
                total_size += size

        # Конвертируем в GB
        total_size_gb = total_size / (1024**3)

        if total_size_gb > self.config.get("max_cache_size_gb", 10):
            # Удаляем самые старые модели
            sorted_models = sorted(
                self.loaded_models.items(),
                key=lambda x: x[1].get("loaded_at", datetime.utcnow()),
            )

            # Удаляем 20% самых старых
            to_remove = int(len(sorted_models) * 0.2)
            for key, _ in sorted_models[:to_remove]:
                del self.loaded_models[key]

            self.logger.info(f"Очищено {to_remove} моделей из кеша")

    def track_prediction(
        self,
        model_name: str,
        prediction: dict[str, Any],
        actual_outcome: dict[str, Any] | None = None,
    ):
        """
        Отслеживание предсказаний модели для оценки производительности

        Args:
            model_name: Имя модели
            prediction: Предсказание модели
            actual_outcome: Фактический результат (если известен)
        """
        if model_name not in self.model_metrics:
            self.model_metrics[model_name] = {
                "predictions": [],
                "correct_predictions": 0,
                "total_predictions": 0,
                "profit_loss": 0.0,
                "last_update": datetime.utcnow(),
            }

        metrics = self.model_metrics[model_name]
        metrics["total_predictions"] += 1

        # Сохраняем предсказание
        prediction_record = {
            "timestamp": datetime.utcnow(),
            "prediction": prediction,
            "outcome": actual_outcome,
        }

        metrics["predictions"].append(prediction_record)

        # Ограничиваем историю
        max_history = 10000
        if len(metrics["predictions"]) > max_history:
            metrics["predictions"] = metrics["predictions"][-max_history:]

        # Обновляем статистику если есть результат
        if actual_outcome:
            self._update_performance_metrics(model_name, prediction, actual_outcome)

    def _update_performance_metrics(
        self, model_name: str, prediction: dict[str, Any], outcome: dict[str, Any]
    ):
        """Обновление метрик производительности"""
        metrics = self.model_metrics[model_name]

        # Проверяем правильность направления
        if "direction" in prediction and "actual_direction" in outcome:
            if prediction["direction"] == outcome["actual_direction"]:
                metrics["correct_predictions"] += 1

        # Обновляем PnL
        if "pnl" in outcome:
            metrics["profit_loss"] += outcome["pnl"]

        # Рассчитываем точность
        if metrics["total_predictions"] > 0:
            metrics["accuracy"] = metrics["correct_predictions"] / metrics["total_predictions"]

        metrics["last_update"] = datetime.utcnow()

    def get_model_performance(self, model_name: str) -> dict[str, Any]:
        """Получение метрик производительности модели"""
        if model_name not in self.model_metrics:
            return {
                "accuracy": 0.0,
                "total_predictions": 0,
                "profit_loss": 0.0,
                "status": "no_data",
            }

        metrics = self.model_metrics[model_name]

        return {
            "accuracy": metrics.get("accuracy", 0.0),
            "total_predictions": metrics["total_predictions"],
            "profit_loss": metrics["profit_loss"],
            "last_update": metrics["last_update"].isoformat(),
            "status": self._get_performance_status(metrics),
        }

    def _get_performance_status(self, metrics: dict[str, Any]) -> str:
        """Определение статуса производительности"""
        if metrics["total_predictions"] < 100:
            return "insufficient_data"

        accuracy = metrics.get("accuracy", 0.0)
        threshold = self.config.get("performance_threshold", 0.6)

        if accuracy >= threshold:
            return "good"
        elif accuracy >= threshold * 0.8:
            return "acceptable"
        else:
            return "poor"

    async def run_ab_test(
        self, model_a: str, model_b: str, test_duration_hours: int = 24
    ) -> dict[str, Any]:
        """
        Запуск A/B теста между двумя моделями

        Args:
            model_a: Имя первой модели
            model_b: Имя второй модели
            test_duration_hours: Длительность теста в часах

        Returns:
            Результаты A/B теста
        """
        if not self.config.get("enable_ab_testing", False):
            raise ValueError("A/B тестирование отключено в конфигурации")

        test_id = f"ab_test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        ab_test = {
            "test_id": test_id,
            "model_a": model_a,
            "model_b": model_b,
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow() + timedelta(hours=test_duration_hours),
            "status": "running",
            "results": {
                model_a: {"predictions": 0, "correct": 0, "pnl": 0.0},
                model_b: {"predictions": 0, "correct": 0, "pnl": 0.0},
            },
        }

        # Сохраняем конфигурацию теста
        test_path = self.cache_dir / f"{test_id}.json"
        with open(test_path, "w") as f:
            json.dump(ab_test, f, indent=2, default=str)

        self.logger.info(f"A/B тест {test_id} запущен между {model_a} и {model_b}")

        return ab_test

    def get_recommended_model(self, model_type: str = "patchtst") -> str | None:
        """
        Получение рекомендованной модели на основе производительности

        Args:
            model_type: Тип модели

        Returns:
            Имя рекомендованной модели или None
        """
        # Фильтруем модели по типу
        relevant_models = [name for name in self.model_metrics.keys() if model_type in name.lower()]

        if not relevant_models:
            # Возвращаем дефолтную модель
            return f"{model_type}_default"

        # Сортируем по производительности
        model_scores = []
        for model_name in relevant_models:
            perf = self.get_model_performance(model_name)

            # Комбинированный скор
            score = (
                perf["accuracy"] * 0.6
                + (1 if perf["profit_loss"] > 0 else 0) * 0.3
                + min(perf["total_predictions"] / 1000, 1.0) * 0.1
            )

            model_scores.append((model_name, score))

        # Возвращаем лучшую модель
        best_model = max(model_scores, key=lambda x: x[1])

        return best_model[0]

    async def export_model_report(self, output_path: str):
        """Экспорт отчета о всех моделях"""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "models": {},
            "recommendations": {},
        }

        # Информация о каждой модели
        for model_name in self.model_metrics.keys():
            report["models"][model_name] = self.get_model_performance(model_name)

        # Рекомендации
        model_types = ["patchtst", "xgboost", "lstm"]
        for model_type in model_types:
            recommended = self.get_recommended_model(model_type)
            if recommended:
                report["recommendations"][model_type] = recommended

        # Сохраняем отчет
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Отчет о моделях сохранен в {output_path}")


# Глобальный экземпляр менеджера
_model_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """Получение глобального экземпляра менеджера моделей"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
