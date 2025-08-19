#!/usr/bin/env python3
"""
ML Manager для управления PatchTST моделью в BOT Trading v3
"""

import os
import pickle
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from core.logger import setup_logger
from core.system.signal_deduplicator import signal_deduplicator
from core.system.worker_coordinator import worker_coordinator
from ml.logic.feature_engineering_production import (  # Production версия из обучающего файла
    ProductionFeatureEngineer as FeatureEngineer,
)
from ml.logic.patchtst_model import create_unified_model
from ml.logic.signal_quality_analyzer import SignalQualityAnalyzer
from ml.ml_prediction_logger import ml_prediction_logger

logger = setup_logger("ml_manager")

# Глобальные оптимизации GPU при импорте модуля - ТОЧНАЯ КОПИЯ из рабочего проекта
if torch.cuda.is_available():
    try:
        # Benchmark mode для cudnn
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.enabled = True

        # Установка float32 matmul precision для ускорения на новых GPU
        # torch.set_float32_matmul_precision('high')  # Временно отключено из-за warning

        # Дополнительные оптимизации для Ampere+ архитектуры (RTX 5090)
        # torch.backends.cuda.matmul.allow_tf32 = True  # Deprecated
        # torch.backends.cudnn.allow_tf32 = True  # Deprecated

        logger.info("✅ Глобальные GPU оптимизации включены")
    except Exception as e:
        logger.warning(f"Не удалось включить GPU оптимизации: {e}")


class MLManager:
    """
    Менеджер для управления ML моделями в торговой системе.
    Работает с PatchTST моделью для предсказания движений рынка.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Инициализация ML менеджера.

        Args:
            config: Конфигурация системы
        """
        self.config = config
        self.model = None
        self.scaler = None
        self.feature_engineer = None
        # Получаем device из конфигурации
        device_config = config.get("ml", {}).get("model", {}).get("device", "auto")

        # Детальная инициализация GPU с проверкой совместимости
        if device_config == "auto":
            try:
                # Проверяем наличие CUDA
                if torch.cuda.is_available():
                    # Получаем информацию о GPU
                    gpu_count = torch.cuda.device_count()
                    if gpu_count > 0:
                        # Выбираем GPU с наименьшей загрузкой памяти
                        best_gpu = 0
                        min_memory_used = float("inf")

                        for i in range(gpu_count):
                            try:
                                torch.cuda.set_device(i)
                                # Проверяем совместимость GPU
                                props = torch.cuda.get_device_properties(i)
                                logger.info(
                                    f"GPU {i}: {props.name}, "
                                    f"Compute Capability: {props.major}.{props.minor}, "
                                    f"Memory: {props.total_memory / 1024**3:.1f}GB"
                                )

                                # Проверяем использование памяти (защита от MagicMock в тестах)
                                try:
                                    memory_used = torch.cuda.memory_allocated(i)
                                    # Проверяем что это реальное число, а не MagicMock
                                    if (
                                        isinstance(memory_used, (int, float))
                                        and memory_used < min_memory_used
                                    ):
                                        min_memory_used = memory_used
                                        best_gpu = i
                                except (TypeError, AttributeError):
                                    # В тестах может быть MagicMock - используем GPU 0 по умолчанию
                                    logger.debug(
                                        f"Не удалось получить память GPU {i}, используем по умолчанию"
                                    )
                                    if i == 0:  # Первый GPU как fallback
                                        best_gpu = i
                            except Exception as gpu_error:
                                logger.warning(f"GPU {i} недоступен: {gpu_error}")
                                continue

                        # Устанавливаем лучший GPU
                        torch.cuda.set_device(best_gpu)
                        self.device = torch.device(f"cuda:{best_gpu}")

                        # Проверяем работоспособность GPU тестовым тензором
                        test_tensor = torch.zeros(1, 1).to(self.device)
                        _ = test_tensor * 2  # Простая операция для проверки

                        # RTX 5090 (Blackwell) особенности:
                        # - GPU полностью функционален с PyTorch 2.9.0+
                        # - torch.compile поддерживается для архитектуры sm_120
                        # - Может дать значительный прирост производительности
                        gpu_name = props.name.upper()
                        if "RTX 5090" in gpu_name or props.major >= 12:
                            logger.info(
                                f"🎯 Обнаружен RTX 5090 ({gpu_name}, sm_{props.major}{props.minor})"
                            )

                            # Проверяем поддержку torch.compile
                            try:
                                # Тест компиляции простой модели
                                import torch.nn as nn

                                test_model = nn.Linear(1, 1).to(self.device)
                                compiled_test = torch.compile(test_model)
                                test_input = torch.randn(1, 1).to(self.device)
                                _ = compiled_test(test_input)

                                logger.info(
                                    "✅ torch.compile поддерживается для RTX 5090 - включаем оптимизацию!"
                                )
                                # НЕ устанавливаем TORCH_COMPILE_DISABLE - позволяем использовать torch.compile

                            except Exception as compile_error:
                                logger.warning(
                                    f"⚠️ torch.compile недоступен для RTX 5090: {compile_error}. "
                                    "Продолжаем без оптимизации."
                                )
                                os.environ["TORCH_COMPILE_DISABLE"] = "1"

                        logger.info(f"✅ Успешно инициализирован GPU {best_gpu} ({props.name})")
                        logger.info(
                            f"💾 GPU память доступна: {props.total_memory / 1024**3:.2f} GB"
                        )
                    else:
                        logger.warning("CUDA доступна, но GPU не найдены")
                        self.device = torch.device("cpu")
                else:
                    logger.info("CUDA недоступна, используем CPU")
                    self.device = torch.device("cpu")

            except Exception as e:
                # Детальное логирование ошибки
                logger.warning(f"Ошибка инициализации GPU: {type(e).__name__}: {e}")
                logger.info("Переключаемся на CPU")
                self.device = torch.device("cpu")

                # Очищаем CUDA кеш при ошибке
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        else:
            # Ручная настройка device
            try:
                self.device = torch.device(device_config)
                # Проверяем работоспособность
                if "cuda" in device_config:
                    test_tensor = torch.zeros(1, 1).to(self.device)
                    _ = test_tensor * 2
                logger.info(f"Установлен device: {device_config}")
            except Exception as e:
                logger.warning(f"Не удалось установить device {device_config}: {e}")
                self.device = torch.device("cpu")

        # Флаг инициализации
        self._initialized = False

        # Кэш моделей (для MLManager совместимости с тестами)
        self._model_cache = {}
        self._cache_size = config.get("ml", {}).get("model_cache_size", 3)
        self._memory_limit = config.get("ml", {}).get("memory_limit_mb", 1024)

        # Пути к моделям - используем абсолютные пути
        base_dir = Path(__file__).parent.parent  # Корень проекта
        model_dir = base_dir / config.get("ml", {}).get("model_directory", "models/saved")
        self.model_path = model_dir / "best_model_20250728_215703.pth"
        self.scaler_path = model_dir / "data_scaler.pkl"

        # Параметры модели
        self.context_length = 96  # 24 часа при 15-минутных свечах
        self.num_features = 240  # Модель обучена на 240 признаках (проверено в checkpoint)
        self.num_targets = 20  # Модель выдает 20 выходов

        # Инициализируем анализатор качества сигналов
        self.quality_analyzer = SignalQualityAnalyzer(config)

        logger.info(f"MLManager initialized, device: {self.device}")

    async def initialize(self):
        """Инициализация и загрузка моделей"""
        try:
            # Регистрируемся в координаторе воркеров с soft-fail режимом
            await worker_coordinator.start()
            self.worker_id = await worker_coordinator.register_worker(
                worker_type="ml_manager",
                metadata={
                    "device": str(self.device),
                    "model_path": str(self.model_path),
                    "num_features": self.num_features,
                    "context_length": self.context_length,
                },
                allow_duplicates=True,  # Soft-fail режим: разрешаем дубликаты с предупреждением
            )

            if not self.worker_id:
                logger.warning("⚠️ Не удалось зарегистрироваться в WorkerCoordinator, но продолжаем")
                # Генерируем резервный worker_id
                import time

                self.worker_id = f"ml_manager_fallback_{int(time.time())}"

            # Загружаем модель
            await self._load_model()

            # Загружаем scaler
            await self._load_scaler()

            # Инициализируем feature engineer
            self.feature_engineer = FeatureEngineer(self.config)

            # Устанавливаем флаг инициализации
            self._initialized = True

            # Отправляем heartbeat о готовности
            await worker_coordinator.heartbeat(self.worker_id, status="running")

            logger.info("✅ ML components initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing ML components: {e}")
            if hasattr(self, "worker_id") and self.worker_id:
                await worker_coordinator.unregister_worker(self.worker_id)
            raise

    async def _load_model(self):
        """Загрузка PatchTST модели"""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model file not found: {self.model_path}")

            # Создаем экземпляр модели с правильной конфигурацией из сохраненного файла
            model_config = {
                "model": {
                    "input_size": self.num_features,  # 98 признаков
                    "output_size": self.num_targets,  # 20 выходов
                    "context_window": self.context_length,  # 96 временных точек
                    "patch_len": 16,
                    "stride": 8,
                    "d_model": 256,  # Согласно сохраненной модели
                    "n_heads": 4,
                    "e_layers": 3,
                    "d_ff": 512,
                    "dropout": 0.1,
                    "temperature_scaling": True,
                    "temperature": 2.0,
                }
            }
            self.model = create_unified_model(model_config)

            # Загружаем веса с безопасной обработкой CUDA ошибок
            try:
                # Пытаемся загрузить на выбранное устройство
                checkpoint = torch.load(self.model_path, map_location=self.device)
            except Exception as cuda_error:
                # Если ошибка CUDA, принудительно загружаем на CPU
                logger.warning(f"Ошибка загрузки на {self.device}, используем CPU: {cuda_error}")
                checkpoint = torch.load(self.model_path, map_location=torch.device("cpu"))
                self.device = torch.device("cpu")

            self.model.load_state_dict(checkpoint["model_state_dict"])

            # Безопасно перемещаем модель на устройство
            try:
                self.model.to(self.device)
            except Exception as e:
                logger.warning(
                    f"Не удалось переместить модель на {self.device}, используем CPU: {e}"
                )
                self.device = torch.device("cpu")
                self.model.to(self.device)

            self.model.eval()

            # Применяем torch.compile для ускорения инференса если доступно
            if os.environ.get("TORCH_COMPILE_DISABLE", "").lower() not in ("1", "true"):
                try:
                    logger.info("🚀 Применяем torch.compile для оптимизации модели...")

                    # Компилируем модель с оптимальными настройками для инференса
                    self.model = torch.compile(
                        self.model,
                        mode="max-autotune",  # Максимальная оптимизация
                        fullgraph=False,  # Позволяем graph breaks для стабильности
                        dynamic=False,  # Static shapes для лучшей оптимизации
                    )

                    logger.info("✅ torch.compile успешно применен к модели!")

                    # Warm-up run для JIT компиляции
                    logger.info("🔥 Прогрев модели с torch.compile...")
                    with torch.no_grad():
                        warmup_input = torch.randn(1, self.context_length, self.num_features).to(
                            self.device
                        )
                        _ = self.model(warmup_input)
                    logger.info("✅ Модель прогрета и готова к работе!")

                except Exception as compile_error:
                    logger.warning(f"⚠️ Не удалось применить torch.compile: {compile_error}")
                    logger.info("Продолжаем с обычной моделью без оптимизации")
            else:
                logger.info("ℹ️ torch.compile отключен переменной окружения")

            logger.info(f"Model loaded successfully from {self.model_path}")

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    async def _load_scaler(self):
        """Загрузка scaler для нормализации данных"""
        try:
            if not self.scaler_path.exists():
                raise FileNotFoundError(f"Scaler file not found: {self.scaler_path}")

            with open(self.scaler_path, "rb") as f:
                self.scaler = pickle.load(f)

            logger.info(f"Scaler loaded successfully from {self.scaler_path}")

        except Exception as e:
            logger.error(f"Error loading scaler: {e}")
            raise

    async def predict(
        self, input_data: pd.DataFrame | np.ndarray, symbol: str | None = None
    ) -> dict[str, Any]:
        """
        Делает предсказание на основе данных.

        Args:
            input_data: DataFrame с OHLCV данными (минимум 96 свечей) или numpy array с признаками
            symbol: Опциональный символ для логирования (используется когда input_data это numpy array)

        Returns:
            Dict с предсказаниями и рекомендациями
        """
        try:
            # ВАЛИДАЦИЯ: Проверяем что модель инициализирована
            if not self._initialized or self.model is None:
                raise ValueError("ML model not initialized. Call initialize() first.")

            # ВАЛИДАЦИЯ: Проверяем тип входных данных
            if not isinstance(input_data, (pd.DataFrame, np.ndarray)):
                raise TypeError(
                    f"input_data must be pd.DataFrame or np.ndarray, got {type(input_data)}"
                )

            # Если это numpy array - используем как есть (уже предобработанные признаки)
            if isinstance(input_data, np.ndarray):
                # Обрабатываем 3D массивы (batch_size, sequence_length, features)
                if input_data.ndim == 3:
                    # Проверяем, что это одиночный батч
                    if input_data.shape[0] == 1:
                        input_data = input_data.squeeze(0)  # Убираем лишнее измерение
                    else:
                        raise ValueError(
                            f"Expected single batch, got batch_size={input_data.shape[0]}"
                        )

                # Теперь проверяем 2D форму
                if (
                    input_data.shape[0] != self.context_length
                    or input_data.shape[1] != self.num_features
                ):
                    raise ValueError(
                        f"Expected shape ({self.context_length}, {self.num_features}), got {input_data.shape}"
                    )
                # Сохраняем оригинальные признаки для логирования
                features = input_data
                # Нормализуем numpy array с помощью scaler
                features_scaled = self.scaler.transform(input_data)
                logger.info("✅ Numpy array нормализован с помощью scaler")

            # Если это DataFrame - обрабатываем как OHLCV данные
            else:
                # ИСПРАВЛЕНО: Правильная обработка DataFrame с async/await логикой
                # Проверяем количество данных
                if len(input_data) < self.context_length:
                    raise ValueError(
                        f"Need at least {self.context_length} candles, got {len(input_data)}"
                    )

                # Проверяем наличие колонки symbol
                if "symbol" not in input_data.columns:
                    logger.warning(
                        "⚠️ Отсутствует колонка 'symbol' в входных данных! Это может привести к неточным предсказаниям."
                    )
                    input_data = input_data.copy()
                    input_data["symbol"] = "UNKNOWN_SYMBOL"  # Помечаем как неизвестный символ

                # Генерируем признаки - теперь это синхронный вызов
                features_result = self.feature_engineer.create_features(input_data)

                # Обрабатываем результат - может быть DataFrame или ndarray
                if isinstance(features_result, pd.DataFrame):
                    # Извлекаем числовые признаки из DataFrame
                    numeric_cols = features_result.select_dtypes(include=[np.number]).columns
                    # Исключаем целевые переменные и метаданные
                    feature_cols = [
                        col
                        for col in numeric_cols
                        if not col.startswith(("future_", "direction_", "profit_"))
                        and col not in ["id", "timestamp", "datetime", "symbol"]
                    ]
                    features_array = features_result[feature_cols].values

                    # Проверяем количество признаков
                    if features_array.shape[1] != self.num_features:
                        logger.warning(
                            f"Feature count mismatch: expected {self.num_features}, got {features_array.shape[1]}"
                        )
                        # Если признаков больше - берем первые num_features
                        if features_array.shape[1] > self.num_features:
                            features_array = features_array[:, : self.num_features]
                        else:
                            # Если меньше - дополняем нулями
                            padding = np.zeros(
                                (
                                    features_array.shape[0],
                                    self.num_features - features_array.shape[1],
                                )
                            )
                            features_array = np.hstack([features_array, padding])

                elif isinstance(features_result, np.ndarray):
                    features_array = features_result
                else:
                    raise ValueError(
                        f"Expected DataFrame or np.ndarray from create_features, got {type(features_result)}"
                    )

                # Берем только последние context_length строк
                if len(features_array) >= self.context_length:
                    features = features_array[-self.context_length :]

                    # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ВХОДНЫХ ПРИЗНАКОВ
                    if hasattr(self, "feature_engineer") and hasattr(
                        self.feature_engineer, "feature_names"
                    ):
                        feature_names = self.feature_engineer.feature_names
                    else:
                        # Загружаем из конфигурации
                        from ml.config.features_240 import get_required_features_list

                        feature_names = get_required_features_list()

                    # Берем последнюю строку для логирования текущих значений
                    current_features = features[-1] if len(features) > 0 else features[0]

                    # Создаем красивую таблицу с входными признаками
                    features_table = []
                    features_table.append(
                        "\n╔══════════════════════════════════════════════════════════════════════╗"
                    )
                    features_table.append(
                        f"║            ВХОДНЫЕ ПАРАМЕТРЫ МОДЕЛИ - {len(current_features)} ПРИЗНАКОВ             ║"
                    )
                    features_table.append(
                        "╠══════════════════════════════════════════════════════════════════════╣"
                    )

                    # Ключевые индикаторы для быстрого просмотра
                    key_indicators = [
                        ("returns", 0),
                        ("rsi", 9),
                        ("macd", 12),
                        ("bb_position", 19),
                        ("atr_pct", 24),
                        ("stoch_k", 25),
                        ("adx", 27),
                        ("volume_ratio", 4),
                        ("obv_trend", 71),
                        ("momentum_1h", 115),
                        ("trend_1h", 124),
                        ("signal_strength", 139),
                    ]

                    features_table.append(
                        "║ 🎯 КЛЮЧЕВЫЕ ИНДИКАТОРЫ:                                             ║"
                    )
                    for i in range(0, len(key_indicators), 2):
                        if i < len(key_indicators):
                            name1, idx1 = key_indicators[i]
                            val1 = current_features[idx1] if idx1 < len(current_features) else 0

                            if i + 1 < len(key_indicators):
                                name2, idx2 = key_indicators[i + 1]
                                val2 = current_features[idx2] if idx2 < len(current_features) else 0
                                features_table.append(
                                    f"║   • {name1:15s}: {val1:>8.4f}  │  {name2:15s}: {val2:>8.4f}  ║"
                                )
                            else:
                                features_table.append(
                                    f"║   • {name1:15s}: {val1:>8.4f}  │                                  ║"
                                )

                    # Статистика по признакам
                    nan_count = np.sum(np.isnan(current_features))
                    zero_count = np.sum(current_features == 0)
                    mean_val = np.nanmean(current_features)
                    std_val = np.nanstd(current_features)

                    features_table.append(
                        "╟──────────────────────────────────────────────────────────────────────╢"
                    )
                    features_table.append(
                        "║ 📊 СТАТИСТИКА ПРИЗНАКОВ:                                            ║"
                    )
                    features_table.append(
                        f"║   • Всего признаков: {len(current_features):<6} • NaN: {nan_count:<6} • Zeros: {zero_count:<6}         ║"
                    )
                    features_table.append(
                        f"║   • Mean: {mean_val:>8.4f}  • Std: {std_val:>8.4f}                           ║"
                    )
                    features_table.append(
                        "╚══════════════════════════════════════════════════════════════════════╝"
                    )

                    # Выводим таблицу одним блоком
                    logger.info("\n".join(features_table))

                else:
                    # Если данных меньше чем нужно - дополняем нулями (padding)
                    padding_size = self.context_length - len(features_array)
                    padding = np.zeros((padding_size, features_array.shape[1]))
                    features = np.vstack([padding, features_array])

                # Нормализуем данные с помощью загруженного scaler
                features_scaled = self.scaler.transform(features)
                logger.info("✅ Данные нормализованы с помощью scaler")
                
                # ФИЛЬТРАЦИЯ ZERO VARIANCE FEATURES (из BOT_AI_V2)
                # Находим признаки с нулевой дисперсией
                feature_stds = features_scaled.std(axis=0)
                zero_variance_mask = feature_stds < 1e-6
                zero_variance_count = zero_variance_mask.sum()
                
                if zero_variance_count > 0:
                    logger.warning(f"🚨 Обнаружено {zero_variance_count} признаков с нулевой дисперсией")
                    
                    # Заменяем zero variance признаки на малое случайное значение
                    # (подход из BOT_AI_V2: сохраняем размерность но добавляем шум)
                    for i, is_zero_var in enumerate(zero_variance_mask):
                        if is_zero_var:
                            # Добавляем небольшой гауссов шум вместо константных значений
                            noise = np.random.normal(0, 1e-4, features_scaled.shape[0])
                            features_scaled[:, i] = features_scaled[:, i] + noise
                    
                    logger.info(f"✅ Zero variance признаки заменены на шум для улучшения ML качества")
                else:
                    logger.info("✅ Zero variance признаки не обнаружены")

            # Преобразуем в тензор
            x = torch.FloatTensor(features_scaled).unsqueeze(0).to(self.device)

            # РАСШИРЕННАЯ ДИАГНОСТИКА ВХОДНЫХ ДАННЫХ
            logger.warning(
                f"""
🔍 ML ВХОДНЫЕ ДАННЫЕ - ДЕТАЛЬНЫЙ АНАЛИЗ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Feature Statistics:
   Shape: {features_scaled.shape}
   Min: {features_scaled.min():.6f}
   Max: {features_scaled.max():.6f}
   Mean: {features_scaled.mean():.6f}
   Std: {features_scaled.std():.6f}

📈 Первые 10 признаков (последняя временная точка):
   {features_scaled[-1, :10]}

🎯 Проверка данных:
   NaN count: {np.isnan(features_scaled).sum()}
   Inf count: {np.isinf(features_scaled).sum()}
   Zero variance features: {(features_scaled.std(axis=0) < 1e-6).sum()}
   🔍 Variance statistics:
     Min std: {features_scaled.std(axis=0).min():.8f}
     Max std: {features_scaled.std(axis=0).max():.8f}
     Mean std: {features_scaled.std(axis=0).mean():.8f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            )
            logger.debug(f"Input tensor shape: {x.shape}")

            # Мониторинг GPU памяти перед inference
            if self.device.type == "cuda":
                gpu_memory_before = torch.cuda.memory_allocated(self.device) / 1024**2  # MB
                gpu_memory_cached = torch.cuda.memory_reserved(self.device) / 1024**2  # MB
                logger.debug(
                    f"GPU Memory before inference: {gpu_memory_before:.1f}MB allocated, {gpu_memory_cached:.1f}MB cached"
                )

            # Делаем предсказание с замером времени
            import time

            start_time = time.time()

            with torch.no_grad():
                outputs = self.model(x)

            inference_time = (time.time() - start_time) * 1000  # в миллисекундах

            # Мониторинг GPU памяти после inference
            if self.device.type == "cuda":
                gpu_memory_after = torch.cuda.memory_allocated(self.device) / 1024**2  # MB
                logger.debug(f"GPU Memory after inference: {gpu_memory_after:.1f}MB allocated")
                logger.info(f"Inference time: {inference_time:.1f}ms on {self.device}")

            # Отладка выходов модели
            outputs_np = outputs.cpu().numpy()[0]
            logger.debug(
                f"Model outputs: min={outputs_np.min():.3f}, max={outputs_np.max():.3f}, mean={outputs_np.mean():.3f}"
            )
            logger.debug(f"Model outputs sample: {outputs_np[:10]}")

            # Интерпретируем результаты
            predictions = self._interpret_predictions(outputs)

            # Логируем предсказание для анализа
            try:
                # Используем переданный symbol параметр если есть, иначе пытаемся извлечь из DataFrame
                if symbol:
                    # Используем переданный символ
                    pass
                elif isinstance(input_data, pd.DataFrame) and "symbol" in input_data.columns:
                    symbol = input_data["symbol"].iloc[-1] if not input_data.empty else "UNKNOWN"
                else:
                    symbol = "UNKNOWN"

                # Асинхронно логируем предсказание
                import asyncio

                if asyncio.iscoroutinefunction(ml_prediction_logger.log_prediction):
                    await ml_prediction_logger.log_prediction(
                        symbol=symbol,
                        features=features[
                            -1
                        ],  # Используем оригинальные признаки, не нормализованные
                        model_outputs=outputs_np,
                        predictions=predictions,
                        market_data=input_data if isinstance(input_data, pd.DataFrame) else None,
                    )
                else:
                    # Если метод синхронный, создаем задачу
                    asyncio.create_task(
                        ml_prediction_logger.log_prediction(
                            symbol=symbol,
                            features=features[-1],  # Используем оригинальные признаки
                            model_outputs=outputs_np,
                            predictions=predictions,
                            market_data=(
                                input_data if isinstance(input_data, pd.DataFrame) else None
                            ),
                        )
                    )
            except Exception as log_error:
                logger.warning(f"Не удалось залогировать предсказание: {log_error}")

            # Отправляем heartbeat после успешного предсказания
            try:
                if hasattr(self, "worker_id") and self.worker_id:
                    await worker_coordinator.heartbeat(
                        self.worker_id, status="running", active_tasks=1
                    )
            except Exception as heartbeat_error:
                logger.warning(f"Ошибка отправки heartbeat: {heartbeat_error}")

            # Проверяем уникальность сигнала перед возвратом
            try:
                # Создаем сигнал для проверки дедупликации
                signal_data = {
                    "symbol": symbol,
                    "direction": predictions.get("primary_direction", "NEUTRAL"),
                    "strategy": "ml_patchtst",
                    "timestamp": datetime.now(),
                    "signal_strength": predictions.get("primary_confidence", 0.0),
                    "price_level": predictions.get("primary_returns", {}).get("15m", 0.0),
                }

                # Проверяем уникальность сигнала
                is_unique = await signal_deduplicator.check_and_register_signal(signal_data)
                if not is_unique:
                    logger.warning(f"🔄 Дубликат ML сигнала отфильтрован для {symbol}")
                    predictions["is_duplicate"] = True
                else:
                    predictions["is_duplicate"] = False

            except Exception as dedup_error:
                logger.warning(f"Ошибка дедупликации сигнала: {dedup_error}")
                predictions["is_duplicate"] = False

            logger.info(f"ML Manager возвращает предсказание: {predictions}")
            return predictions

        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            # Отправляем heartbeat об ошибке
            try:
                if hasattr(self, "worker_id") and self.worker_id:
                    await worker_coordinator.heartbeat(self.worker_id, status="error")
            except Exception as heartbeat_error:
                logger.warning(f"Ошибка отправки heartbeat при ошибке: {heartbeat_error}")
            raise

    def _interpret_predictions(self, outputs: torch.Tensor) -> dict[str, Any]:
        """
        УЛУЧШЕННАЯ интерпретация выходов модели с анализом качества сигналов.

        КРИТИЧЕСКИ ВАЖНО: Правильная интерпретация классов направления!
        В обучении модели было установлено:
        - Класс 0 = LONG (покупка, рост цены)
        - Класс 1 = SHORT (продажа, падение цены)
        - Класс 2 = NEUTRAL/FLAT (боковое движение, нет торговли)

        Args:
            outputs: Тензор с 20 выходами модели

        Returns:
            Dict с ПРАВИЛЬНО интерпретированными предсказаниями и метриками качества
        """
        # Определяем константы и словари в начале функции
        timeframes = ["15m", "1h", "4h", "12h"]
        direction_names = {0: "LONG↗️", 1: "SHORT↘️", 2: "FLAT➡️"}
        direction_map = {0: "LONG", 1: "SHORT", 2: "NEUTRAL"}

        # Этап 1: Извлечение и валидация данных модели
        outputs_np = outputs.cpu().numpy()[0]

        # Структура выходов (20 значений):
        # 0-3: future returns (15m, 1h, 4h, 12h)
        # 4-15: direction logits (12 values = 3 classes × 4 timeframes)
        # 16-19: risk metrics

        future_returns = outputs_np[0:4]
        direction_logits = outputs_np[4:16]  # 12 значений!
        risk_metrics = outputs_np[16:20]

        # ПРАВИЛЬНАЯ ИНТЕРПРЕТАЦИЯ DIRECTIONS (12 значений = 4 таймфрейма × 3 класса)
        direction_logits_reshaped = direction_logits.reshape(4, 3)  # 4 таймфрейма × 3 класса

        # Применяем softmax к каждому таймфрейму
        directions = []
        direction_probs = []

        for i, logits in enumerate(direction_logits_reshaped):
            # Softmax для получения вероятностей
            exp_logits = np.exp(logits - np.max(logits))  # Для численной стабильности
            probs = exp_logits / exp_logits.sum()
            direction_probs.append(probs)

            # Argmax для получения класса (0=LONG, 1=SHORT, 2=NEUTRAL)
            direction_class = np.argmax(probs)
            directions.append(direction_class)

        directions = np.array(directions)

        # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ВСЕХ ПАРАМЕТРОВ МОДЕЛИ
        # Форматируем выходы для красивого отображения
        outputs_formatted = [f"{x:.4f}" for x in outputs_np]

        logger.info(
            f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    🤖 ML MODEL PREDICTION ANALYSIS                   ║
╠══════════════════════════════════════════════════════════════════════╣
║ 📊 RAW MODEL OUTPUTS (20 parameters):                                ║
║  [0-4]:  {', '.join(outputs_formatted[0:5]):50s}    ║
║  [5-9]:  {', '.join(outputs_formatted[5:10]):50s}    ║
║  [10-14]: {', '.join(outputs_formatted[10:15]):50s}   ║
║  [15-19]: {', '.join(outputs_formatted[15:20]):50s}   ║
╠══════════════════════════════════════════════════════════════════════╣
║ 📈 FUTURE RETURNS (ожидаемые доходности):                           ║
║   • 15m:  {future_returns[0]:+.6f} ({future_returns[0]*100:+6.3f}%)                       ║
║   • 1h:   {future_returns[1]:+.6f} ({future_returns[1]*100:+6.3f}%)                       ║
║   • 4h:   {future_returns[2]:+.6f} ({future_returns[2]*100:+6.3f}%)                       ║
║   • 12h:  {future_returns[3]:+.6f} ({future_returns[3]*100:+6.3f}%)                       ║
╠══════════════════════════════════════════════════════════════════════╣
║ 🎯 НАПРАВЛЕНИЯ ПО ТАЙМФРЕЙМАМ:                                      ║
║   • 15m:  {direction_names.get(directions[0], str(directions[0])):8s} | Conf: {direction_probs[0].max():.3f} |                      ║
║      Probs: [LONG: {direction_probs[0][0]:.3f}, SHORT: {direction_probs[0][1]:.3f}, NEUTRAL: {direction_probs[0][2]:.3f}]          ║
║   • 1h:   {direction_names.get(directions[1], str(directions[1])):8s} | Conf: {direction_probs[1].max():.3f} |                      ║
║      Probs: [LONG: {direction_probs[1][0]:.3f}, SHORT: {direction_probs[1][1]:.3f}, NEUTRAL: {direction_probs[1][2]:.3f}]          ║
║   • 4h:   {direction_names.get(directions[2], str(directions[2])):8s} | Conf: {direction_probs[2].max():.3f} |                      ║
║      Probs: [LONG: {direction_probs[2][0]:.3f}, SHORT: {direction_probs[2][1]:.3f}, NEUTRAL: {direction_probs[2][2]:.3f}]          ║
║   • 12h:  {direction_names.get(directions[3], str(directions[3])):8s} | Conf: {direction_probs[3].max():.3f} |                      ║
║      Probs: [LONG: {direction_probs[3][0]:.3f}, SHORT: {direction_probs[3][1]:.3f}, NEUTRAL: {direction_probs[3][2]:.3f}]          ║
╠══════════════════════════════════════════════════════════════════════╣
║ ⚡ RISK METRICS (метрики риска):                                     ║
║   • Max Drawdown 1h:  {risk_metrics[0]:+.6f}                                  ║
║   • Max Rally 1h:     {risk_metrics[1]:+.6f}                                  ║
║   • Max Drawdown 4h:  {risk_metrics[2]:+.6f}                                  ║
║   • Max Rally 4h:     {risk_metrics[3]:+.6f}                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        )

        # ДОПОЛНИТЕЛЬНОЕ ЛОГИРОВАНИЕ: Интерпретация всех 20 выходов модели
        logger.info(
            f"""
╔══════════════════════════════════════════════════════════════════════╗
║               📊 ДЕТАЛЬНАЯ ИНТЕРПРЕТАЦИЯ 20 ВЫХОДОВ МОДЕЛИ           ║
╠══════════════════════════════════════════════════════════════════════╣
║ 🔮 ПРЕДСКАЗАНИЯ ДОХОДНОСТИ (outputs 0-3):                           ║
║   • Out[0] = {outputs_np[0]:+.6f} → 15m return prediction            ║
║   • Out[1] = {outputs_np[1]:+.6f} → 1h return prediction             ║
║   • Out[2] = {outputs_np[2]:+.6f} → 4h return prediction             ║
║   • Out[3] = {outputs_np[3]:+.6f} → 12h return prediction            ║
╠══════════════════════════════════════════════════════════════════════╣
║ 🎯 ЛОГИТЫ НАПРАВЛЕНИЯ 15m (outputs 4-6):                            ║
║   • Out[4] = {outputs_np[4]:+.6f} → Logit for LONG                   ║
║   • Out[5] = {outputs_np[5]:+.6f} → Logit for SHORT                  ║
║   • Out[6] = {outputs_np[6]:+.6f} → Logit for NEUTRAL                ║
╠══════════════════════════════════════════════════════════════════════╣
║ 🎯 ЛОГИТЫ НАПРАВЛЕНИЯ 1h (outputs 7-9):                             ║
║   • Out[7] = {outputs_np[7]:+.6f} → Logit for LONG                   ║
║   • Out[8] = {outputs_np[8]:+.6f} → Logit for SHORT                  ║
║   • Out[9] = {outputs_np[9]:+.6f} → Logit for NEUTRAL                ║
╠══════════════════════════════════════════════════════════════════════╣
║ 🎯 ЛОГИТЫ НАПРАВЛЕНИЯ 4h (outputs 10-12):                           ║
║   • Out[10] = {outputs_np[10]:+.6f} → Logit for LONG                 ║
║   • Out[11] = {outputs_np[11]:+.6f} → Logit for SHORT                ║
║   • Out[12] = {outputs_np[12]:+.6f} → Logit for NEUTRAL              ║
╠══════════════════════════════════════════════════════════════════════╣
║ 🎯 ЛОГИТЫ НАПРАВЛЕНИЯ 12h (outputs 13-15):                          ║
║   • Out[13] = {outputs_np[13]:+.6f} → Logit for LONG                 ║
║   • Out[14] = {outputs_np[14]:+.6f} → Logit for SHORT                ║
║   • Out[15] = {outputs_np[15]:+.6f} → Logit for NEUTRAL              ║
╠══════════════════════════════════════════════════════════════════════╣
║ ⚠️ МЕТРИКИ РИСКА (outputs 16-19):                                   ║
║   • Out[16] = {outputs_np[16]:+.6f} → Max Drawdown 1h                ║
║   • Out[17] = {outputs_np[17]:+.6f} → Max Rally 1h                   ║
║   • Out[18] = {outputs_np[18]:+.6f} → Max Drawdown 4h                ║
║   • Out[19] = {outputs_np[19]:+.6f} → Max Rally 4h                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        )

        # Этап 2: Расчет weighted_direction для совместимости
        weights = np.array([0.4, 0.3, 0.2, 0.1])
        weighted_direction = np.sum(directions * weights)

        # Этап 3: Анализ качества сигнала с помощью нового анализатора
        filter_result = self.quality_analyzer.analyze_signal_quality(
            directions=directions,
            direction_probs=direction_probs,
            future_returns=future_returns,
            risk_metrics=risk_metrics,
            weighted_direction=weighted_direction,
        )

        # Этап 4: Принятие решения на основе анализа качества
        if not filter_result.passed:
            # Сигнал не прошел фильтры качества
            signal_type = "NEUTRAL"
            signal_strength = 0.25  # Минимальное значение
            combined_confidence = 0.25
            stop_loss_pct = None
            take_profit_pct = None

            logger.warning(
                f"🚫 Сигнал отклонен анализатором качества. "
                f"Причины: {'; '.join(filter_result.rejection_reasons)}"
            )
        else:
            # Сигнал прошел фильтры - используем результат анализа
            signal_type = filter_result.signal_type
            metrics = filter_result.quality_metrics

            # Используем метрики качества для финальных параметров
            signal_strength = metrics.agreement_score
            combined_confidence = metrics.confidence_score

            # Расчет SL/TP на основе качества сигнала
            if signal_type in ["LONG", "SHORT"]:
                # Адаптивные SL/TP на основе качества
                base_sl = 0.01  # 1%
                base_tp = 0.02  # 2%

                # Корректировка на основе качества сигнала
                quality_multiplier = 0.8 + (metrics.quality_score * 0.4)  # 0.8-1.2

                stop_loss_pct = base_sl * quality_multiplier
                take_profit_pct = base_tp * quality_multiplier

                # Корректировка на волатильность
                volatility = np.std(future_returns[:2])  # Ближайшие ТФ
                if volatility > 0.01:
                    stop_loss_pct *= 1.2
                    take_profit_pct *= 1.2

                # Финальные ограничения
                stop_loss_pct = np.clip(stop_loss_pct, 0.005, 0.025)  # 0.5% - 2.5%
                take_profit_pct = np.clip(take_profit_pct, 0.01, 0.05)  # 1% - 5%
            else:
                stop_loss_pct = None
                take_profit_pct = None

        # Этап 5: Подготовка финального результата
        # Дополнительные метрики для совместимости
        confidence_scores = np.array([np.max(probs) for probs in direction_probs])
        model_confidence = float(np.mean(confidence_scores))
        avg_risk = float(np.mean(risk_metrics))
        risk_level = "LOW" if avg_risk < 0.3 else "MEDIUM" if avg_risk < 0.7 else "HIGH"

        # Focal weighting для совместимости с логгером
        focal_alpha = 0.25
        focal_gamma = 2.0
        focal_weighted_confidence = focal_alpha * (1 - model_confidence) ** focal_gamma

        # Логирование финального результата
        quality_score = filter_result.quality_metrics.quality_score if filter_result.passed else 0.0
        strategy_used = filter_result.strategy_used.value

        sl_str = f"{stop_loss_pct:.3f}" if stop_loss_pct else "не определен"
        tp_str = f"{take_profit_pct:.3f}" if take_profit_pct else "не определен"

        # Цветовая индикация для сигнала
        signal_emoji = "🟢" if signal_type == "LONG" else "🔴" if signal_type == "SHORT" else "⚪"
        passed_emoji = "✅" if filter_result.passed else "❌"

        logger.info(
            f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    📊 ML PREDICTION FINAL RESULT                     ║
╠══════════════════════════════════════════════════════════════════════╣
║ {signal_emoji} SIGNAL TYPE: {signal_type:8s} | Strategy: {strategy_used:12s}        ║
║ {passed_emoji} Quality Filter: {'PASSED' if filter_result.passed else 'REJECTED':8s} | Score: {quality_score:.3f}              ║
╠══════════════════════════════════════════════════════════════════════╣
║ 📈 PREDICTIONS BY TIMEFRAME:                                         ║
║   15m: {direction_map.get(int(directions[0]), 'N/A'):8s} | Ret: {future_returns[0]:+.4f} | Conf: {confidence_scores[0]:.3f}       ║
║   1h:  {direction_map.get(int(directions[1]), 'N/A'):8s} | Ret: {future_returns[1]:+.4f} | Conf: {confidence_scores[1]:.3f}       ║
║   4h:  {direction_map.get(int(directions[2]), 'N/A'):8s} | Ret: {future_returns[2]:+.4f} | Conf: {confidence_scores[2]:.3f}       ║
║   12h: {direction_map.get(int(directions[3]), 'N/A'):8s} | Ret: {future_returns[3]:+.4f} | Conf: {confidence_scores[3]:.3f}       ║
╠══════════════════════════════════════════════════════════════════════╣
║ 💪 SIGNAL STRENGTH: {signal_strength:.3f} | CONFIDENCE: {combined_confidence:.1%}           ║
║ ⚠️  RISK LEVEL: {risk_level:6s} | Score: {avg_risk:.3f}                         ║
║ 🛡️  STOP LOSS:  {sl_str:8s} | 🎯 TAKE PROFIT: {tp_str:8s}          ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        )

        # Подготавливаем детальные данные для логирования

        return {
            # Основные параметры сигнала
            "signal_type": signal_type,
            "signal_strength": float(signal_strength),
            "confidence": float(combined_confidence),
            "signal_confidence": float(combined_confidence),  # Для совместимости
            "success_probability": float(combined_confidence),
            # SL/TP проценты
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            # Оценка риска
            "risk_level": risk_level,
            "risk_score": float(avg_risk),
            "max_drawdown": float(risk_metrics[0]) if len(risk_metrics) > 0 else 0,
            "max_rally": float(risk_metrics[1]) if len(risk_metrics) > 1 else 0,
            # Детализированные предсказания
            "returns_15m": float(future_returns[0]),
            "returns_1h": float(future_returns[1]),
            "returns_4h": float(future_returns[2]),
            "returns_12h": float(future_returns[3]),
            # Направления и уверенность по таймфреймам
            "direction_15m": direction_map.get(int(directions[0]), "NEUTRAL"),
            "direction_1h": direction_map.get(int(directions[1]), "NEUTRAL"),
            "direction_4h": direction_map.get(int(directions[2]), "NEUTRAL"),
            "direction_12h": direction_map.get(int(directions[3]), "NEUTRAL"),
            "confidence_15m": float(confidence_scores[0]),
            "confidence_1h": float(confidence_scores[1]),
            "confidence_4h": float(confidence_scores[2]),
            "confidence_12h": float(confidence_scores[3]),
            # Метрики качества от анализатора
            "quality_score": quality_score,
            "agreement_score": (
                filter_result.quality_metrics.agreement_score if filter_result.passed else 0.0
            ),
            "filter_strategy": strategy_used,
            "passed_quality_filters": filter_result.passed,
            "rejection_reasons": filter_result.rejection_reasons,
            # Дополнительные данные
            "primary_timeframe": "4h",  # Основной таймфрейм
            "predictions": {
                "returns_15m": float(future_returns[0]),
                "returns_1h": float(future_returns[1]),
                "returns_4h": float(future_returns[2]),
                "returns_12h": float(future_returns[3]),
                "direction_score": float(weighted_direction),
                "directions_by_timeframe": directions.tolist(),
                "direction_probabilities": [p.tolist() for p in direction_probs],
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def update_model(self, new_model_path: str):
        """
        Обновление модели на новую версию.

        Args:
            new_model_path: Путь к новой модели
        """
        try:
            # Сохраняем старую модель как резервную
            backup_path = self.model_path.with_suffix(".pth.backup")
            if self.model_path.exists():
                self.model_path.rename(backup_path)

            # Копируем новую модель
            Path(new_model_path).rename(self.model_path)

            # Перезагружаем модель
            await self._load_model()

            logger.info(f"Model updated successfully from {new_model_path}")

        except Exception as e:
            logger.error(f"Error updating model: {e}")
            # Восстанавливаем старую модель
            if backup_path.exists():
                backup_path.rename(self.model_path)
            raise

    def get_model_info(self) -> dict[str, Any]:
        """Получение информации о модели"""
        return {
            "model_type": "UnifiedPatchTST",
            "model_path": str(self.model_path),
            "context_length": self.context_length,
            "num_features": self.num_features,
            "num_targets": self.num_targets,
            "device": str(self.device),
            "model_loaded": self.model is not None,
            "scaler_loaded": self.scaler is not None,
        }

    def switch_filtering_strategy(self, strategy: str) -> bool:
        """
        Переключение стратегии фильтрации сигналов

        Args:
            strategy: Название стратегии (conservative/moderate/aggressive)

        Returns:
            True если успешно переключено
        """
        if self.quality_analyzer.switch_strategy(strategy):
            logger.info(f"✅ Стратегия фильтрации переключена на: {strategy}")
            return True
        else:
            logger.error(f"❌ Не удалось переключить стратегию на: {strategy}")
            return False

    def get_filtering_statistics(self) -> dict[str, Any]:
        """
        Получение статистики работы системы фильтрации

        Returns:
            Словарь с детальной статистикой
        """
        return self.quality_analyzer.get_strategy_statistics()

    def get_available_strategies(self) -> list[str]:
        """
        Получение списка доступных стратегий фильтрации

        Returns:
            Список названий стратегий
        """
        return ["conservative", "moderate", "aggressive"]

    def get_current_strategy_config(self) -> dict[str, Any]:
        """
        Получение конфигурации текущей стратегии

        Returns:
            Параметры активной стратегии
        """
        return {
            "active_strategy": self.quality_analyzer.active_strategy.value,
            "strategy_params": self.quality_analyzer.strategy_params,
            "timeframe_weights": self.quality_analyzer.timeframe_weights.tolist(),
            "quality_weights": self.quality_analyzer.quality_weights,
        }
