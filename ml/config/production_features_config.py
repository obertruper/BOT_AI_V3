# Конфигурация для 270 признаков из обучения
EXPECTED_FEATURES = 270

# Служебные колонки (не подавать в модель)
SERVICE_COLUMNS = [
    "datetime",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "timestamp",
    "id",
    "exchange",
]

# Целевые переменные (не подавать в модель)
TARGET_VARIABLES = [
    "future_return_15m",
    "future_return_1h",
    "future_return_4h",
    "future_return_12h",
    "direction_15m",
    "direction_1h",
    "direction_4h",
    "direction_12h",
    "will_reach_2pct_4h",
    "will_reach_5pct_12h",
    "will_reach_10pct_24h",
    "max_drawdown_4h",
    "max_rally_4h",
    "max_drawdown_12h",
    "max_rally_12h",
    "volatility_1h",
    "volatility_4h",
    "volatility_12h",
    "best_action",
]

# Параметры модели
SEQUENCE_LENGTH = 168  # 42 часа при 15-минутных свечах
BATCH_SIZE = 32


def validate_features(df):
    """Валидация количества признаков"""
    feature_cols = [
        col for col in df.columns if col not in SERVICE_COLUMNS and col not in TARGET_VARIABLES
    ]

    actual_count = len(feature_cols)
    if actual_count != EXPECTED_FEATURES:
        raise ValueError(f"Ожидается {EXPECTED_FEATURES} признаков, получено {actual_count}")

    return feature_cols
