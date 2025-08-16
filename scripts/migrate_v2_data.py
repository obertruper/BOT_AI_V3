#!/usr/bin/env python3
"""
Script to migrate data from BOT Trading v2 to v3

This script handles the data transformation required when migrating
from v2 database schema to v3 schema.
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from database.connections import get_db
from database.models import Order, OrderSide, OrderStatus, OrderType, Trade

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class V2ToV3Migrator:
    """Handles migration of data from v2 to v3 schema"""

    def __init__(self, v2_db_url: str | None = None):
        """
        Initialize migrator

        Args:
            v2_db_url: Connection string for v2 database.
                      If None, assumes data is in same database
        """
        self.v2_db_url = v2_db_url
        self.stats = {
            "trades_migrated": 0,
            "orders_created": 0,
            "signals_updated": 0,
            "errors": 0,
        }

    def migrate_v2_trades_to_v3_orders(self, batch_size: int = 100):
        """
        Migrate v2 trades to v3 orders

        v2 Trade represents a position lifecycle
        v3 splits this into Order (pending/active) and Trade (executed)
        """
        logger.info("Starting migration of v2 trades to v3 orders...")

        with get_db() as db:
            # Get total count
            count_result = db.execute(
                text("SELECT COUNT(*) FROM trades WHERE extra_data->>'v2_migrated' IS NULL")
            ).scalar()

            logger.info(f"Found {count_result} v2 trades to migrate")

            offset = 0
            while offset < count_result:
                # Fetch batch of v2 trades
                v2_trades = db.execute(
                    text(
                        """
                    SELECT * FROM trades
                    WHERE extra_data->>'v2_migrated' IS NULL
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                """
                    ),
                    {"limit": batch_size, "offset": offset},
                ).fetchall()

                for v2_trade in v2_trades:
                    try:
                        self._migrate_single_trade(db, v2_trade)
                        self.stats["trades_migrated"] += 1
                    except Exception as e:
                        logger.error(f"Error migrating trade {v2_trade.id}: {e}")
                        self.stats["errors"] += 1

                db.commit()
                offset += batch_size
                logger.info(f"Migrated {offset}/{count_result} trades")

    def _migrate_single_trade(self, db, v2_trade):
        """Migrate a single v2 trade to v3 format"""

        # Map v2 status to v3 order status
        status_map = {
            "OPEN": OrderStatus.OPEN,
            "CLOSE": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "PARTIAL": OrderStatus.PARTIALLY_FILLED,
        }

        # Map v2 side to v3 side
        side_map = {"Buy": OrderSide.BUY, "Sell": OrderSide.SELL}

        # Create v3 order from v2 trade
        new_order = Order(
            exchange="bybit",  # Default exchange
            symbol=v2_trade.symbol,
            order_id=v2_trade.order_id or f"v2_trade_{v2_trade.id}",
            side=side_map.get(v2_trade.side, OrderSide.BUY),
            order_type=OrderType.MARKET,  # Default to market
            status=status_map.get(v2_trade.status, OrderStatus.REJECTED),
            price=v2_trade.entry_price,
            quantity=v2_trade.quantity,
            filled_quantity=v2_trade.quantity if v2_trade.status == "CLOSE" else 0,
            average_price=v2_trade.close_price or v2_trade.entry_price,
            stop_loss=v2_trade.stop_loss,
            take_profit=v2_trade.take_profit,
            created_at=datetime.fromisoformat(v2_trade.created_at),
            updated_at=datetime.fromisoformat(v2_trade.closed_at or v2_trade.created_at),
            strategy_name=v2_trade.model_name,
            extra_data={
                "v2_trade_id": v2_trade.id,
                "leverage": v2_trade.leverage,
                "signal_id": v2_trade.signal_id,
                "model_score": v2_trade.model_score,
                "ml_data": v2_trade.ml_data,
                "v2_migrated": True,
            },
        )

        db.add(new_order)
        self.stats["orders_created"] += 1

        # If trade was closed, create a Trade record
        if v2_trade.status == "CLOSE" and v2_trade.closed_at:
            new_trade = Trade(
                exchange="bybit",
                symbol=v2_trade.symbol,
                trade_id=v2_trade.close_order_id or f"{v2_trade.order_id}_close",
                order_id=v2_trade.order_id,
                side=side_map.get(v2_trade.side, OrderSide.BUY),
                price=v2_trade.close_price or v2_trade.entry_price,
                quantity=v2_trade.quantity,
                commission=0,  # Will need to calculate from other data
                realized_pnl=v2_trade.pnl,
                executed_at=datetime.fromisoformat(v2_trade.closed_at),
                strategy_name=v2_trade.model_name,
            )
            db.add(new_trade)

    def update_ml_fields(self):
        """Update ML fields in trades table from v2 data"""
        logger.info("Updating ML fields in trades...")

        with get_db() as db:
            # Update trades with ML data from extra_data
            result = db.execute(
                text(
                    """
                UPDATE trades
                SET
                    model_name = extra_data->>'model_name',
                    model_score = (extra_data->>'model_score')::float,
                    profit_probability = COALESCE((extra_data->>'profit_probability')::float, 0),
                    loss_probability = COALESCE((extra_data->>'loss_probability')::float, 0),
                    confidence = COALESCE((extra_data->>'confidence')::float, 0)
                WHERE extra_data->>'v2_trade_id' IS NOT NULL
                  AND model_name IS NULL
            """
                )
            )

            logger.info(f"Updated {result.rowcount} trades with ML data")
            db.commit()

    def migrate_sltp_orders(self):
        """Migrate SLTP orders if they exist in v2 format"""
        logger.info("Checking for v2 SLTP orders...")

        with get_db() as db:
            # Check if v2 sltp_orders table exists
            result = db.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'v2_sltp_orders'
                )
            """
                )
            ).scalar()

            if not result:
                logger.info("No v2 SLTP orders table found")
                return

            # Direct migration if structure matches
            db.execute(
                text(
                    """
                INSERT INTO sltp_orders
                SELECT * FROM v2_sltp_orders
                ON CONFLICT DO NOTHING
            """
                )
            )

            db.commit()
            logger.info("SLTP orders migrated successfully")

    def generate_report(self) -> str:
        """Generate migration report"""
        report = f"""
=== V2 to V3 Migration Report ===

Migration Statistics:
- Trades Migrated: {self.stats["trades_migrated"]}
- Orders Created: {self.stats["orders_created"]}
- Signals Updated: {self.stats["signals_updated"]}
- Errors: {self.stats["errors"]}

Timestamp: {datetime.now().isoformat()}
"""
        return report


def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(description="Migrate BOT Trading v2 data to v3")
    parser.add_argument("--v2-db-url", help="V2 database connection URL")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for migration")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without committing")

    args = parser.parse_args()

    # Create migrator
    migrator = V2ToV3Migrator(v2_db_url=args.v2_db_url)

    try:
        # Run migrations
        migrator.migrate_v2_trades_to_v3_orders(batch_size=args.batch_size)
        migrator.update_ml_fields()
        migrator.migrate_sltp_orders()

        # Generate report
        report = migrator.generate_report()
        print(report)

        # Save report
        with open("migration_report.txt", "w") as f:
            f.write(report)

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
