"""create ml predictions table

Revision ID: ml_predictions_001
Revises:
Create Date: 2025-01-14 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "ml_predictions_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create ml_predictions table for storing all ML model inputs and outputs
    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.Column("datetime", sa.DateTime(timezone=True), nullable=False),
        # Input features summary
        sa.Column("features_count", sa.Integer(), nullable=False),
        sa.Column("features_hash", sa.BigInteger(), nullable=False),
        sa.Column("lookback_periods", sa.Integer(), nullable=False),
        # Key input features (for analysis)
        sa.Column("close_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(20, 8), nullable=False),
        sa.Column("rsi", sa.Float(), nullable=True),
        sa.Column("macd", sa.Float(), nullable=True),
        sa.Column("bb_position", sa.Float(), nullable=True),
        sa.Column("atr_pct", sa.Float(), nullable=True),
        sa.Column("volume_ratio", sa.Float(), nullable=True),
        sa.Column("trend_strength", sa.Float(), nullable=True),
        # Feature statistics
        sa.Column("features_mean", sa.Float(), nullable=True),
        sa.Column("features_std", sa.Float(), nullable=True),
        sa.Column("features_min", sa.Float(), nullable=True),
        sa.Column("features_max", sa.Float(), nullable=True),
        sa.Column("zero_variance_count", sa.Integer(), nullable=True),
        sa.Column("nan_count", sa.Integer(), nullable=True),
        # Model outputs - raw predictions
        sa.Column("predicted_return_15m", sa.Float(), nullable=False),
        sa.Column("predicted_return_1h", sa.Float(), nullable=False),
        sa.Column("predicted_return_4h", sa.Float(), nullable=False),
        sa.Column("predicted_return_12h", sa.Float(), nullable=False),
        # Direction predictions (probabilities)
        sa.Column("direction_15m", sa.String(10), nullable=False),
        sa.Column("direction_15m_confidence", sa.Float(), nullable=False),
        sa.Column("direction_1h", sa.String(10), nullable=False),
        sa.Column("direction_1h_confidence", sa.Float(), nullable=False),
        sa.Column("direction_4h", sa.String(10), nullable=False),
        sa.Column("direction_4h_confidence", sa.Float(), nullable=False),
        sa.Column("direction_12h", sa.String(10), nullable=False),
        sa.Column("direction_12h_confidence", sa.Float(), nullable=False),
        # Risk metrics
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("max_drawdown_predicted", sa.Float(), nullable=True),
        sa.Column("max_rally_predicted", sa.Float(), nullable=True),
        # Final signal
        sa.Column("signal_type", sa.String(10), nullable=False),  # LONG, SHORT, NEUTRAL
        sa.Column("signal_confidence", sa.Float(), nullable=False),
        sa.Column("signal_timeframe", sa.String(10), nullable=False),  # Primary timeframe
        # Model metadata
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("inference_time_ms", sa.Float(), nullable=True),
        # Actual outcomes (filled later for analysis)
        sa.Column("actual_return_15m", sa.Float(), nullable=True),
        sa.Column("actual_return_1h", sa.Float(), nullable=True),
        sa.Column("actual_return_4h", sa.Float(), nullable=True),
        sa.Column("actual_return_12h", sa.Float(), nullable=True),
        sa.Column("actual_direction_15m", sa.String(10), nullable=True),
        sa.Column("actual_direction_1h", sa.String(10), nullable=True),
        sa.Column("actual_direction_4h", sa.String(10), nullable=True),
        sa.Column("actual_direction_12h", sa.String(10), nullable=True),
        # Performance metrics (calculated later)
        sa.Column("accuracy_15m", sa.Boolean(), nullable=True),
        sa.Column("accuracy_1h", sa.Boolean(), nullable=True),
        sa.Column("accuracy_4h", sa.Boolean(), nullable=True),
        sa.Column("accuracy_12h", sa.Boolean(), nullable=True),
        sa.Column("return_error_15m", sa.Float(), nullable=True),
        sa.Column("return_error_1h", sa.Float(), nullable=True),
        sa.Column("return_error_4h", sa.Float(), nullable=True),
        sa.Column("return_error_12h", sa.Float(), nullable=True),
        # Full features array (JSONB for detailed analysis)
        sa.Column("features_array", postgresql.JSONB(), nullable=True),
        sa.Column("model_outputs_raw", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), onupdate=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index("idx_ml_predictions_symbol_datetime", "ml_predictions", ["symbol", "datetime"])
    op.create_index("idx_ml_predictions_signal_type", "ml_predictions", ["signal_type"])
    op.create_index("idx_ml_predictions_confidence", "ml_predictions", ["signal_confidence"])
    op.create_index("idx_ml_predictions_created_at", "ml_predictions", ["created_at"])
    op.create_index("idx_ml_predictions_features_hash", "ml_predictions", ["features_hash"])

    # Create unique constraint to prevent duplicates
    op.create_unique_constraint(
        "uq_ml_predictions_symbol_timestamp", "ml_predictions", ["symbol", "timestamp"]
    )

    # Create ml_feature_importance table for tracking feature importance over time
    op.create_table(
        "ml_feature_importance",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("feature_name", sa.String(100), nullable=False),
        sa.Column("feature_index", sa.Integer(), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("importance_rank", sa.Integer(), nullable=False),
        sa.Column("correlation_with_returns", sa.Float(), nullable=True),
        sa.Column("usage_count", sa.Integer(), default=0),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_feature_importance_name", "ml_feature_importance", ["feature_name"])
    op.create_index("idx_feature_importance_score", "ml_feature_importance", ["importance_score"])


def downgrade():
    op.drop_table("ml_feature_importance")
    op.drop_table("ml_predictions")
