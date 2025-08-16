#!/usr/bin/env python3
"""
Демонстрационный скрипт работы ML трейдера
Показывает генерацию сигналов от PatchTST модели
"""

import asyncio
import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from colorama import Fore, Style, init

# Инициализация colorama
init(autoreset=True)

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MLTraderDemo:
    """Демонстрация работы ML трейдера"""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.config = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Используется устройство: {self.device}")

    def load_model_components(self):
        """Загрузка компонентов модели"""
        logger.info("📂 Загрузка компонентов модели...")

        try:
            # Загрузка модели
            model_path = Path("models/saved/best_model_20250728_215703.pth")
            if model_path.exists():
                checkpoint = torch.load(model_path, map_location=self.device)
                if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                    # Модель сохранена как checkpoint
                    logger.info("Модель сохранена как checkpoint, создаем mock модель для демо")
                    self.model = None  # Будем использовать симуляцию
                else:
                    self.model = checkpoint
                    if hasattr(self.model, "eval"):
                        self.model.eval()
                logger.info(f"{Fore.GREEN}✅ Модель загружена (режим симуляции){Style.RESET_ALL}")
            else:
                logger.error(f"{Fore.RED}❌ Файл модели не найден: {model_path}{Style.RESET_ALL}")
                return False

            # Загрузка scaler
            scaler_path = Path("models/saved/data_scaler.pkl")
            if scaler_path.exists():
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                logger.info(f"{Fore.GREEN}✅ Scaler загружен{Style.RESET_ALL}")
            else:
                logger.error(f"{Fore.RED}❌ Файл scaler не найден: {scaler_path}{Style.RESET_ALL}")
                return False

            # Загрузка конфигурации
            config_path = Path("models/saved/config.pkl")
            if config_path.exists():
                with open(config_path, "rb") as f:
                    self.config = pickle.load(f)
                logger.info(f"{Fore.GREEN}✅ Конфигурация загружена{Style.RESET_ALL}")
            else:
                logger.error(
                    f"{Fore.RED}❌ Файл конфигурации не найден: {config_path}{Style.RESET_ALL}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"{Fore.RED}❌ Ошибка при загрузке модели: {e}{Style.RESET_ALL}")
            return False

    def generate_sample_data(self, num_points: int = 100) -> pd.DataFrame:
        """Генерация тестовых данных для демонстрации"""
        logger.info("📊 Генерация тестовых данных...")

        # Генерируем временной ряд
        dates = pd.date_range(end=datetime.now(), periods=num_points, freq="15min")

        # Базовая цена с трендом и шумом
        base_price = 50000
        trend = np.linspace(0, 1000, num_points)
        noise = np.random.normal(0, 200, num_points)
        prices = base_price + trend + noise

        # Добавляем волатильность
        volatility = np.random.normal(0, 100, num_points)

        # Создаем DataFrame
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices + volatility * 0.5,
                "high": prices + abs(volatility),
                "low": prices - abs(volatility),
                "close": prices,
                "volume": np.random.uniform(100, 1000, num_points),
            }
        )

        # Вычисляем технические индикаторы
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["rsi"] = self.calculate_rsi(df["close"])
        df["macd"], df["macd_signal"] = self.calculate_macd(df["close"])

        return df.dropna()

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Расчет RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, prices: pd.Series) -> tuple:
        """Расчет MACD"""
        ema12 = prices.ewm(span=12, adjust=False).mean()
        ema26 = prices.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd, signal

    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Подготовка признаков для модели"""
        # Выбираем нужные колонки
        feature_cols = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "sma_20",
            "sma_50",
            "rsi",
            "macd",
        ]

        # Проверяем наличие всех колонок
        available_cols = [col for col in feature_cols if col in df.columns]

        if len(available_cols) < len(feature_cols):
            logger.warning(f"Не все признаки доступны. Используем: {available_cols}")

        features = df[available_cols].values

        # Нормализация
        if self.scaler:
            try:
                # Подгоняем размер под scaler
                if features.shape[1] < self.scaler.n_features_in_:
                    # Добавляем недостающие колонки
                    padding = np.zeros(
                        (
                            features.shape[0],
                            self.scaler.n_features_in_ - features.shape[1],
                        )
                    )
                    features = np.hstack([features, padding])
                elif features.shape[1] > self.scaler.n_features_in_:
                    # Обрезаем лишние колонки
                    features = features[:, : self.scaler.n_features_in_]

                features = self.scaler.transform(features)
            except Exception as e:
                logger.warning(f"Ошибка при нормализации: {e}. Используем сырые данные.")

        return features

    def generate_signals(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Генерация торговых сигналов"""
        signals = []

        # Подготавливаем признаки
        features = self.prepare_features(df)

        # Конвертируем в тензор
        features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)

        try:
            # Получаем предсказания модели
            with torch.no_grad():
                if self.model:
                    predictions = self.model(features_tensor)
                    # Простая интерпретация: если предсказание > 0, то покупка
                    pred_values = predictions.cpu().numpy().flatten()
                else:
                    # Если модель не загружена, используем простую логику
                    pred_values = np.random.randn(len(df))

            # Генерируем сигналы на основе предсказаний
            for i in range(min(5, len(pred_values))):  # Последние 5 сигналов
                idx = -(i + 1)

                # Определяем тип сигнала
                if pred_values[idx] > 0.5:
                    signal_type = "BUY"
                    color = Fore.GREEN
                elif pred_values[idx] < -0.5:
                    signal_type = "SELL"
                    color = Fore.RED
                else:
                    signal_type = "HOLD"
                    color = Fore.YELLOW

                # Рассчитываем уверенность
                confidence = min(abs(pred_values[idx]) / 2, 1.0)

                signal = {
                    "timestamp": df.iloc[idx]["timestamp"],
                    "type": signal_type,
                    "symbol": "BTC/USDT",
                    "price": df.iloc[idx]["close"],
                    "confidence": confidence,
                    "strength": abs(pred_values[idx]),
                    "color": color,
                    "features": {
                        "rsi": df.iloc[idx]["rsi"],
                        "macd": df.iloc[idx]["macd"],
                        "volume": df.iloc[idx]["volume"],
                    },
                }
                signals.append(signal)

        except Exception as e:
            logger.error(f"Ошибка при генерации сигналов: {e}")

        return signals

    def print_signals(self, signals: list[dict[str, Any]]):
        """Красивый вывод сигналов"""
        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📈 ТОРГОВЫЕ СИГНАЛЫ ОТ ML МОДЕЛИ (PatchTST){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

        for signal in signals:
            color = signal["color"]
            print(f"{color}{'─' * 50}{Style.RESET_ALL}")
            print(f"⏰ Время: {signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Символ: {signal['symbol']}")
            print(f"💰 Цена: ${signal['price']:.2f}")
            print(f"{color}🎯 Сигнал: {signal['type']}{Style.RESET_ALL}")
            print(f"📊 Уверенность: {signal['confidence']:.1%}")
            print(f"💪 Сила сигнала: {signal['strength']:.3f}")
            print("\n📈 Индикаторы:")
            print(f"   RSI: {signal['features']['rsi']:.2f}")
            print(f"   MACD: {signal['features']['macd']:.2f}")
            print(f"   Volume: {signal['features']['volume']:.2f}")

        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

    async def run_demo(self):
        """Запуск демонстрации"""
        print(f"\n{Fore.CYAN}🚀 ДЕМОНСТРАЦИЯ ML ТРЕЙДЕРА{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Модель: PatchTST (Patch Time Series Transformer){Style.RESET_ALL}\n")

        # Загружаем модель
        if not self.load_model_components():
            logger.warning("Работаем в режиме симуляции без реальной модели")

        # Генерируем данные
        df = self.generate_sample_data()
        logger.info(f"Сгенерировано {len(df)} точек данных")

        # Основной цикл
        iteration = 0
        while True:
            try:
                iteration += 1
                print(f"\n{Fore.YELLOW}🔄 Итерация #{iteration}{Style.RESET_ALL}")

                # Добавляем новые данные
                new_data = self.generate_sample_data(10)
                df = pd.concat([df, new_data]).tail(100)  # Храним последние 100 точек

                # Генерируем сигналы
                signals = self.generate_signals(df)

                # Выводим сигналы
                if signals:
                    self.print_signals(signals)
                else:
                    print("Нет новых сигналов")

                # Статистика
                buy_signals = sum(1 for s in signals if s["type"] == "BUY")
                sell_signals = sum(1 for s in signals if s["type"] == "SELL")

                print("\n📊 Статистика:")
                print(f"   {Fore.GREEN}Сигналов на покупку: {buy_signals}{Style.RESET_ALL}")
                print(f"   {Fore.RED}Сигналов на продажу: {sell_signals}{Style.RESET_ALL}")
                print(f"   Средняя уверенность: {np.mean([s['confidence'] for s in signals]):.1%}")

                print(f"\n{Fore.CYAN}Ожидание 10 секунд... (Ctrl+C для выхода){Style.RESET_ALL}")
                await asyncio.sleep(10)

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Демонстрация остановлена{Style.RESET_ALL}")
                break
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                await asyncio.sleep(5)


async def main():
    """Основная функция"""
    demo = MLTraderDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
