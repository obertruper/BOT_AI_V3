"""
SQLAlchemy models for ML predictions tracking and analysis
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MLPrediction(Base):
    """
    Stores detailed ML model predictions with inputs and outputs for analysis
    """

    __tablename__ = "ml_predictions"

    # Primary key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Symbol and timing
    symbol = Column(String(20), nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    datetime = Column(DateTime(timezone=True), nullable=False)

    # Input features summary
    features_count = Column(Integer, nullable=False)
    features_hash = Column(BigInteger, nullable=False)
    lookback_periods = Column(Integer, nullable=False)

    # Key input features (for analysis)
    close_price = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    bb_position = Column(Float, nullable=True)
    atr_pct = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    trend_strength = Column(Float, nullable=True)

    # Feature statistics
    features_mean = Column(Float, nullable=True)
    features_std = Column(Float, nullable=True)
    features_min = Column(Float, nullable=True)
    features_max = Column(Float, nullable=True)
    zero_variance_count = Column(Integer, nullable=True)
    nan_count = Column(Integer, nullable=True)

    # Model outputs - raw predictions
    predicted_return_15m = Column(Float, nullable=False)
    predicted_return_1h = Column(Float, nullable=False)
    predicted_return_4h = Column(Float, nullable=False)
    predicted_return_12h = Column(Float, nullable=False)

    # Direction predictions (with confidence)
    direction_15m = Column(String(10), nullable=False)
    direction_15m_confidence = Column(Float, nullable=False)
    direction_1h = Column(String(10), nullable=False)
    direction_1h_confidence = Column(Float, nullable=False)
    direction_4h = Column(String(10), nullable=False)
    direction_4h_confidence = Column(Float, nullable=False)
    direction_12h = Column(String(10), nullable=False)
    direction_12h_confidence = Column(Float, nullable=False)

    # Risk metrics
    risk_score = Column(Float, nullable=True)
    max_drawdown_predicted = Column(Float, nullable=True)
    max_rally_predicted = Column(Float, nullable=True)

    # Final signal
    signal_type = Column(String(10), nullable=False)  # LONG, SHORT, NEUTRAL
    signal_confidence = Column(Float, nullable=False)
    signal_timeframe = Column(String(10), nullable=False)  # Primary timeframe

    # Model metadata
    model_version = Column(String(50), nullable=False)
    inference_time_ms = Column(Float, nullable=True)

    # Actual outcomes (filled later for analysis)
    actual_return_15m = Column(Float, nullable=True)
    actual_return_1h = Column(Float, nullable=True)
    actual_return_4h = Column(Float, nullable=True)
    actual_return_12h = Column(Float, nullable=True)
    actual_direction_15m = Column(String(10), nullable=True)
    actual_direction_1h = Column(String(10), nullable=True)
    actual_direction_4h = Column(String(10), nullable=True)
    actual_direction_12h = Column(String(10), nullable=True)

    # Performance metrics (calculated later)
    accuracy_15m = Column(Boolean, nullable=True)
    accuracy_1h = Column(Boolean, nullable=True)
    accuracy_4h = Column(Boolean, nullable=True)
    accuracy_12h = Column(Boolean, nullable=True)
    return_error_15m = Column(Float, nullable=True)
    return_error_1h = Column(Float, nullable=True)
    return_error_4h = Column(Float, nullable=True)
    return_error_12h = Column(Float, nullable=True)

    # Full features array (JSONB for detailed analysis)
    features_array = Column(JSONB, nullable=True)
    model_outputs_raw = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=text("now()"), nullable=True)

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_ml_predictions_symbol_datetime", "symbol", "datetime"),
        Index("idx_ml_predictions_signal_type", "signal_type"),
        Index("idx_ml_predictions_confidence", "signal_confidence"),
        Index("idx_ml_predictions_created_at", "created_at"),
        Index("idx_ml_predictions_features_hash", "features_hash"),
        UniqueConstraint("symbol", "timestamp", name="uq_ml_predictions_symbol_timestamp"),
    )

    def __repr__(self):
        return (
            f"<MLPrediction(symbol={self.symbol}, "
            f"signal={self.signal_type}, "
            f"confidence={self.signal_confidence:.2f}, "
            f"datetime={self.datetime})>"
        )


class MLFeatureImportance(Base):
    """
    Tracks feature importance scores over time for model interpretation
    """

    __tablename__ = "ml_feature_importance"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    feature_name = Column(String(100), nullable=False)
    feature_index = Column(Integer, nullable=False)
    importance_score = Column(Float, nullable=False)
    importance_rank = Column(Integer, nullable=False)
    correlation_with_returns = Column(Float, nullable=True)
    usage_count = Column(Integer, default=0)
    model_version = Column(String(50), nullable=False)
    calculated_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_feature_importance_name", "feature_name"),
        Index("idx_feature_importance_score", "importance_score"),
    )

    def __repr__(self):
        return (
            f"<MLFeatureImportance(feature={self.feature_name}, "
            f"score={self.importance_score:.4f}, "
            f"rank={self.importance_rank})>"
        )
