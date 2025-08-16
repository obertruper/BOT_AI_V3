#!/usr/bin/env python3
"""
Direct test of ML prediction logging to database
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

from database.connections.postgres import AsyncPGPool
from ml.ml_prediction_logger import MLPredictionLogger

console = Console()


async def test_direct_logging():
    """Direct test of ML prediction logging"""

    console.print("[bold cyan]=" * 60)
    console.print("[bold cyan]   DIRECT TEST OF ML PREDICTION LOGGING")
    console.print("[bold cyan]=" * 60)

    # Initialize DB pool
    await AsyncPGPool.init_pool()

    try:
        # Create logger instance
        logger = MLPredictionLogger()

        # Create test predictions
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

        for i, symbol in enumerate(symbols):
            console.print(f"\n[yellow]Creating prediction for {symbol}...[/yellow]")

            # Generate test data
            features = np.random.randn(240)
            model_outputs = np.random.randn(20)

            # Create prediction dict with all required fields
            predictions = {
                "signal_type": ["LONG", "SHORT", "NEUTRAL"][i % 3],
                "signal_confidence": 0.75 + i * 0.05,
                "timeframe": "15m",
                # Return predictions
                "returns_15m": model_outputs[0],
                "returns_1h": model_outputs[1],
                "returns_4h": model_outputs[2],
                "returns_12h": model_outputs[3],
                # Direction predictions
                "direction_15m": "UP" if model_outputs[0] > 0 else "DOWN",
                "confidence_15m": abs(model_outputs[0]),
                "direction_1h": "UP" if model_outputs[1] > 0 else "DOWN",
                "confidence_1h": abs(model_outputs[1]),
                "direction_4h": "UP" if model_outputs[2] > 0 else "DOWN",
                "confidence_4h": abs(model_outputs[2]),
                "direction_12h": "UP" if model_outputs[3] > 0 else "DOWN",
                "confidence_12h": abs(model_outputs[3]),
                # Risk metrics
                "risk_score": np.random.random(),
                "max_drawdown": np.random.random() * 0.1,
                "max_rally": np.random.random() * 0.2,
            }

            # Market data as DataFrame (expected format)
            market_data = pd.DataFrame(
                {
                    "close": [50000 + i * 1000],
                    "volume": [1000000 + i * 100000],
                    "timestamp": [int(datetime.now().timestamp() * 1000)],
                }
            )

            # Log the prediction
            await logger.log_prediction(
                symbol=symbol,
                features=features,
                model_outputs=model_outputs,
                predictions=predictions,
                market_data=market_data,
            )

            console.print(f"[green]✅ Logged prediction for {symbol}[/green]")

        # Force save the batch
        console.print("\n[yellow]Forcing batch save...[/yellow]")
        await logger.flush()

        # Check the database
        console.print("\n[cyan]Checking database...[/cyan]")

        # Query the ml_predictions table
        query = """
            SELECT
                symbol,
                signal_type,
                signal_confidence,
                predicted_return_15m,
                direction_15m,
                risk_score,
                created_at
            FROM ml_predictions
            WHERE created_at >= NOW() - INTERVAL '1 minute'
            ORDER BY created_at DESC
        """

        records = await AsyncPGPool.fetch(query)

        if records:
            # Create output table
            table = Table(title="ML Predictions in Database")
            table.add_column("Symbol", style="cyan")
            table.add_column("Signal", style="magenta")
            table.add_column("Confidence", style="green")
            table.add_column("Return 15m", style="yellow")
            table.add_column("Direction", style="blue")
            table.add_column("Risk", style="red")
            table.add_column("Time", style="white")

            for record in records:
                table.add_row(
                    record["symbol"],
                    record["signal_type"],
                    f"{record['signal_confidence']:.2%}",
                    f"{record['predicted_return_15m']:.4f}",
                    record["direction_15m"],
                    f"{record['risk_score']:.3f}" if record["risk_score"] else "N/A",
                    record["created_at"].strftime("%H:%M:%S"),
                )

            console.print(table)
            console.print(
                f"\n[bold green]✅ SUCCESS: Found {len(records)} records in database![/bold green]"
            )
        else:
            console.print("[bold red]❌ FAILED: No records found in database![/bold red]")

            # Check if table exists
            table_check = await AsyncPGPool.fetch(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'ml_predictions'
                );
            """
            )

            if not table_check[0]["exists"]:
                console.print("[red]Table ml_predictions does not exist! Run migrations:[/red]")
                console.print("[yellow]alembic upgrade head[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(test_direct_logging())
