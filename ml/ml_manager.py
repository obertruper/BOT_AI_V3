#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Manager для управления PatchTST моделью в BOT Trading v3
"""

import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Union

import numpy as np
import pandas as pd
import torch

from core.logger import setup_logger
from ml.logic.feature_engineering import (  # Оригинальная версия с 240+ признаками
    FeatureEngineer,
)
from ml.logic.patchtst_model import create_unified_model

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

    def __init__(self, config: Dict[str, Any]):
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

                                # Проверяем использование памяти
                                if torch.cuda.memory_allocated(i) < min_memory_used:
                                    min_memory_used = torch.cuda.memory_allocated(i)
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
                        # - GPU полностью функционален после перезагрузки системы
                        # - torch.compile пока не поддерживает архитектуру sm_120
                        # - Это не влияет на производительность или функциональность
                        gpu_name = props.name.upper()
                        if "RTX 5090" in gpu_name or props.major >= 12:
                            logger.info(
                                f"🎯 Обнаружен RTX 5090 ({gpu_name}, sm_{props.major}{props.minor})"
                            )
                            logger.warning(
                                "⚠️ torch.compile отключен для RTX 5090 (sm_120) - не поддерживается текущей версией PyTorch. Это нормально и не влияет на функциональность."
                            )
                            # Отключаем компиляцию для новых архитектур
                            os.environ["TORCH_COMPILE_DISABLE"] = "1"

                        logger.info(
                            f"✅ Успешно инициализирован GPU {best_gpu} ({props.name})"
                        )
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
        model_dir = base_dir / config.get("ml", {}).get(
            "model_directory", "models/saved"
        )
        self.model_path = model_dir / "best_model_20250728_215703.pth"
        self.scaler_path = model_dir / "data_scaler.pkl"

        # Параметры модели
        self.context_length = 96  # 24 часа при 15-минутных свечах
        self.num_features = 240  # Вернули обратно для совместимости с моделью
        self.num_targets = 20  # Модель выдает 20 выходов

        logger.info(f"MLManager initialized, device: {self.device}")

    async def initialize(self):
        """Инициализация и загрузка моделей"""
        try:
            # Загружаем модель
            await self._load_model()

            # Загружаем scaler
            await self._load_scaler()

            # Инициализируем feature engineer
            self.feature_engineer = FeatureEngineer(self.config)

            # Устанавливаем флаг инициализации
            self._initialized = True

            logger.info("ML components initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing ML components: {e}")
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
                logger.warning(
                    f"Ошибка загрузки на {self.device}, используем CPU: {cuda_error}"
                )
                checkpoint = torch.load(
                    self.model_path, map_location=torch.device("cpu")
                )
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
        self, input_data: Union[pd.DataFrame, np.ndarray]
    ) -> Dict[str, Any]:
        """
        Делает предсказание на основе данных.

        Args:
            input_data: DataFrame с OHLCV данными (минимум 96 свечей) или numpy array с признаками

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
                    input_data["symbol"] = (
                        "UNKNOWN_SYMBOL"  # Помечаем как неизвестный символ
                    )

                # Генерируем признаки - теперь это синхронный вызов
                features_result = self.feature_engineer.create_features(input_data)

                # Обрабатываем результат - может быть DataFrame или ndarray
                if isinstance(features_result, pd.DataFrame):
                    # Извлекаем числовые признаки из DataFrame
                    numeric_cols = features_result.select_dtypes(
                        include=[np.number]
                    ).columns
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
                else:
                    # Если данных меньше чем нужно - дополняем нулями (padding)
                    padding_size = self.context_length - len(features_array)
                    padding = np.zeros((padding_size, features_array.shape[1]))
                    features = np.vstack([padding, features_array])

                # Нормализуем данные с помощью загруженного scaler
                features_scaled = self.scaler.transform(features)
                logger.info("✅ Данные нормализованы с помощью scaler")

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
                gpu_memory_before = (
                    torch.cuda.memory_allocated(self.device) / 1024**2
                )  # MB
                gpu_memory_cached = (
                    torch.cuda.memory_reserved(self.device) / 1024**2
                )  # MB
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
                gpu_memory_after = (
                    torch.cuda.memory_allocated(self.device) / 1024**2
                )  # MB
                logger.debug(
                    f"GPU Memory after inference: {gpu_memory_after:.1f}MB allocated"
                )
                logger.info(f"Inference time: {inference_time:.1f}ms on {self.device}")

            # Отладка выходов модели
            outputs_np = outputs.cpu().numpy()[0]
            logger.debug(
                f"Model outputs: min={outputs_np.min():.3f}, max={outputs_np.max():.3f}, mean={outputs_np.mean():.3f}"
            )
            logger.debug(f"Model outputs sample: {outputs_np[:10]}")

            # Интерпретируем результаты
            predictions = self._interpret_predictions(outputs)

            logger.info(f"ML Manager возвращает предсказание: {predictions}")
            return predictions

        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            raise

    def _interpret_predictions(self, outputs: torch.Tensor) -> Dict[str, Any]:
        """
        Интерпретация выходов модели.

        Args:
            outputs: Тензор с 32 выходами модели

        Returns:
            Dict с интерпретированными предсказаниями
        """
        outputs_np = outputs.cpu().numpy()[0]

        # Структура выходов (20 значений):
        # 0-3: future returns (15m, 1h, 4h, 12h)
        # 4-15: direction logits (12 values = 3 classes × 4 timeframes)
        # 16-19: risk metrics

        # ВАЖНО: в модели с 20 выходами нет отдельных long/short levels!
        # Используем future returns для расчета уровней

        future_returns = outputs_np[0:4]
        direction_logits = outputs_np[4:16]  # 12 значений!
        risk_metrics = outputs_np[16:20]

        # В модели с 20 выходами используем future_returns для расчета уровней
        # Конвертируем предсказанные доходности в проценты для SL/TP
        long_levels = future_returns  # Используем future returns как базу для уровней
        short_levels = -future_returns  # Инвертируем для коротких позиций

        # ИСПРАВЛЕНИЕ: Не используем risk_metrics как confidence_scores
        # Вместо этого используем вероятности направлений как индикатор уверенности
        # Максимальная вероятность среди классов показывает уверенность модели
        confidence_scores = np.zeros(4)
        for i in range(4):
            logits = direction_logits[i * 3 : (i + 1) * 3]
            probs = np.exp(logits) / np.sum(np.exp(logits))
            # Используем максимальную вероятность как уверенность
            confidence_scores[i] = np.max(probs)

        # ДИАГНОСТИЧЕСКОЕ ЛОГИРОВАНИЕ
        logger.warning(
            f"""
🔍 ML ДИАГНОСТИКА - ИСПРАВЛЕННАЯ ИНТЕРПРЕТАЦИЯ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Raw Model Outputs (все 20 значений):
   {outputs_np}

📈 Future Returns (0-3):
   15m: {future_returns[0]:.6f}
   1h:  {future_returns[1]:.6f}
   4h:  {future_returns[2]:.6f}
   12h: {future_returns[3]:.6f}

🎯 Direction Logits (4-15) - 12 значений:
   Raw logits: {direction_logits}
   Структура: 4 таймфрейма × 3 класса (LONG=0, SHORT=1, NEUTRAL=2)

⚡ Risk Metrics (16-19):
   {risk_metrics}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        )

        # ПРАВИЛЬНАЯ ИНТЕРПРЕТАЦИЯ DIRECTIONS (12 значений = 4 таймфрейма × 3 класса)
        # Разбиваем на 4 группы по 3 логита
        direction_logits_reshaped = direction_logits.reshape(
            4, 3
        )  # 4 таймфрейма × 3 класса

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

            logger.info(
                f"Таймфрейм {i + 1}: logits={logits}, probs={probs}, class={direction_class}"
            )

        directions = np.array(directions)
        logger.info(f"Direction predictions: {directions}")

        # Определяем основной сигнал
        # Используем взвешенное среднее классов с большим весом на ближайшие таймфреймы
        weights = np.array([0.4, 0.3, 0.2, 0.1])
        weighted_direction = np.sum(directions * weights)

        # Определяем силу сигнала на основе согласованности предсказаний
        # Чем больше таймфреймов согласны, тем сильнее сигнал
        direction_counts = np.bincount(directions, minlength=3)
        max_agreement = direction_counts.max() / len(directions)
        signal_strength = max_agreement  # от 0.25 до 1.0

        logger.info(f"Weighted direction: {weighted_direction:.3f}")
        logger.info(
            f"Direction counts: LONG={direction_counts[0]}, SHORT={direction_counts[1]}, NEUTRAL={direction_counts[2]}"
        )
        logger.info(f"Signal strength (agreement): {signal_strength:.3f}")

        # Определяем тип сигнала на основе взвешенного среднего
        # ИСПРАВЛЕНО: Правильная интерпретация классов модели + улучшенные пороги
        # В обучении: 0=LONG (покупка), 1=SHORT (продажа), 2=FLAT (нейтрально)
        #
        # НОВАЯ ЛОГИКА С УЧЕТОМ СИЛЫ СИГНАЛА:
        # weighted_direction находится в диапазоне 0.0 - 2.0
        # где 0.0 = все LONG, 1.0 = все SHORT, 2.0 = все NEUTRAL
        #
        # Используем согласованность как дополнительный фактор
        # Если большинство таймфреймов согласны - сильный сигнал

        # Считаем голоса за каждое направление
        long_votes = np.sum(directions == 0)
        short_votes = np.sum(directions == 1)
        neutral_votes = np.sum(directions == 2)

        # ИСПРАВЛЕННАЯ ЛОГИКА: Определяем сигнал по большинству голосов
        if long_votes >= 3:  # 3+ из 4 таймфреймов за LONG
            signal_type = "LONG"
        elif short_votes >= 3:  # 3+ из 4 таймфреймов за SHORT
            signal_type = "SHORT"
        elif neutral_votes >= 3:  # 3+ из 4 таймфреймов за NEUTRAL
            signal_type = "NEUTRAL"
        else:
            # Нет явного большинства - используем более гибкую логику
            # Приоритет отдаем торговым сигналам (LONG/SHORT) над NEUTRAL

            if long_votes > short_votes and long_votes > neutral_votes:
                # LONG больше всего голосов
                signal_type = "LONG"
            elif short_votes > long_votes and short_votes > neutral_votes:
                # SHORT больше всего голосов
                signal_type = "SHORT"
            elif long_votes == short_votes and long_votes > neutral_votes:
                # LONG и SHORT равны, но больше NEUTRAL - используем взвешенное среднее
                if weighted_direction < 1.0:
                    signal_type = "LONG"  # Ближе к 0 (LONG)
                else:
                    signal_type = "SHORT"  # Ближе к 1 (SHORT)
            else:
                # NEUTRAL побеждает или ничья с торговыми сигналами
                # Используем более мягкие пороги для взвешенного среднего
                if weighted_direction < 0.5:
                    signal_type = "LONG"  # Сильный LONG
                elif weighted_direction > 1.5:
                    signal_type = "NEUTRAL"  # Сильный NEUTRAL
                elif weighted_direction > 1.2:
                    signal_type = "SHORT"  # Умеренный SHORT
                else:
                    # Промежуточная зона - решаем по силе сигнала
                    if signal_strength > 0.4:  # Снижен с 0.6
                        # При достаточной силе сигнала выбираем торговое направление
                        if weighted_direction < 1.0:
                            signal_type = "LONG"
                        else:
                            signal_type = "SHORT"
                    else:
                        signal_type = "NEUTRAL"

        # Рассчитываем уровни SL/TP на основе future_returns
        # future_returns содержит предсказанные доходности для разных таймфреймов

        if signal_type == "LONG":
            # Для LONG позиций:
            # Stop Loss: используем минимальную (возможно отрицательную) доходность
            # Take Profit: используем максимальную положительную доходность

            # Берем минимальное значение как риск для stop loss
            min_return = float(np.min(future_returns))
            max_return = float(np.max(future_returns))

            # Конвертируем в разумные проценты (ограничиваем диапазон)
            # Stop Loss: от 1% до 5%
            stop_loss_pct = np.clip(abs(min_return) * 100, 1.0, 5.0) / 100.0

            # Take Profit: от 2% до 10%
            take_profit_pct = np.clip(max_return * 100, 2.0, 10.0) / 100.0

        elif signal_type == "SHORT":
            # Для SHORT позиций логика инвертирована
            min_return = float(np.min(future_returns))
            max_return = float(np.max(future_returns))

            # Stop Loss для SHORT = риск роста цены
            stop_loss_pct = np.clip(abs(max_return) * 100, 1.0, 5.0) / 100.0

            # Take Profit для SHORT = падение цены
            take_profit_pct = np.clip(abs(min_return) * 100, 2.0, 10.0) / 100.0

        else:
            stop_loss_pct = None
            take_profit_pct = None

        # Примечание: фактические цены SL/TP будут рассчитаны в ml_signal_processor
        # на основе текущей цены и этих процентов

        # Оценка риска
        avg_risk = float(np.mean(risk_metrics))
        risk_level = "LOW" if avg_risk < 0.3 else "MEDIUM" if avg_risk < 0.7 else "HIGH"

        # Вычисляем общую уверенность на основе:
        # 1. Согласованности предсказаний (signal_strength)
        # 2. Confidence scores от модели
        # 3. Риск метрик

        # ИСПРАВЛЕНИЕ: confidence_scores уже содержат вероятности (0-1), не нужен sigmoid
        model_confidence = float(np.mean(confidence_scores))

        # ИСПРАВЛЕННАЯ формула комбинированной уверенности
        # Увеличиваем базовую уверенность для торговых сигналов
        base_confidence = 0.4 if signal_type in ["LONG", "SHORT"] else 0.2

        # Бонус за согласованность предсказаний
        consistency_bonus = 0.0
        max_votes = max(long_votes, short_votes, neutral_votes)
        if signal_type in ["LONG", "SHORT"]:
            # Для торговых сигналов даем бонус даже при относительном большинстве
            consistency_bonus = (
                max_votes - 1
            ) * 0.15  # 0.15 за каждый дополнительный голос

        # Комбинированная уверенность с учетом типа сигнала
        combined_confidence = min(
            0.95,
            base_confidence
            + signal_strength * 0.3
            + model_confidence * 0.2
            + (1.0 - avg_risk) * 0.1
            + consistency_bonus,
        )

        # Вероятность успеха
        success_probability = combined_confidence

        # Логируем все предсказания для анализа
        sl_str = f"{stop_loss_pct:.3f}" if stop_loss_pct is not None else "не определен"
        tp_str = (
            f"{take_profit_pct:.3f}" if take_profit_pct is not None else "не определен"
        )

        logger.info(
            f"""
📊 ML Предсказание (ПРАВИЛЬНАЯ ИНТЕРПРЕТАЦИЯ):
   Направление: {signal_type} (взвешенное: {weighted_direction:.3f})
   Предсказания по таймфреймам: {directions}
   Сила сигнала (согласованность): {signal_strength:.3f}
   Уверенность модели: {model_confidence:.1%}
   Комбинированная уверенность: {combined_confidence:.1%}
   Риск: {risk_level} ({avg_risk:.3f})
   Будущие доходности: 15м={future_returns[0]:.3f}, 1ч={future_returns[1]:.3f}, 4ч={future_returns[2]:.3f}, 12ч={future_returns[3]:.3f}
   Stop Loss %: {sl_str}
   Take Profit %: {tp_str}
"""
        )

        return {
            "signal_type": signal_type,
            "signal_strength": float(signal_strength),
            "confidence": float(combined_confidence),
            "success_probability": float(success_probability),
            "stop_loss_pct": stop_loss_pct,  # Процент, не абсолютная цена!
            "take_profit_pct": take_profit_pct,  # Процент, не абсолютная цена!
            "risk_level": risk_level,
            "predictions": {
                "returns_15m": float(future_returns[0]),
                "returns_1h": float(future_returns[1]),
                "returns_4h": float(future_returns[2]),
                "returns_12h": float(future_returns[3]),
                "direction_score": float(weighted_direction),
                "directions_by_timeframe": directions.tolist(),  # [15m, 1h, 4h, 12h]
                "direction_probabilities": [p.tolist() for p in direction_probs],
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
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

    def get_model_info(self) -> Dict[str, Any]:
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
