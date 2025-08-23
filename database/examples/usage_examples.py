"""
Usage examples for the enhanced database architecture.

This file demonstrates how to use the new DBManager with all its features:
- Transaction management
- Bulk operations
- Circuit breakers
- Retry logic
- Monitoring
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import List

from database.db_manager import DBManager, get_db
from database.repositories.position_repository import Position
from database.models.ml_predictions import MLPrediction
from database.resilience.circuit_breaker import circuit_breaker
from database.resilience.retry_handler import with_retry


async def example_basic_operations():
    """Example of basic database operations."""
    print("=== Basic Operations Example ===")
    
    # Get database manager
    db = await get_db()
    
    # Simple ML prediction logging
    prediction = MLPrediction(
        symbol="BTC/USDT",
        prediction="BUY",
        confidence=0.85,
        signal_strength=0.72,
        expected_return=2.5,
        risk_score=0.3,
        exchange="bybit",
        timeframe="15m"
    )
    
    prediction_id = await db.ml_predictions.log_prediction(prediction)
    print(f"Logged ML prediction with ID: {prediction_id}")
    
    # Get recent predictions
    recent_predictions = await db.ml_predictions.get_recent_predictions(
        symbol="BTC/USDT",
        hours=1
    )
    print(f"Found {len(recent_predictions)} recent predictions")


async def example_bulk_operations():
    """Example of bulk database operations for high performance."""
    print("=== Bulk Operations Example ===")
    
    db = await get_db()
    
    # Create multiple ML predictions
    predictions = []
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT"]
    
    for i, symbol in enumerate(symbols):
        prediction = MLPrediction(
            symbol=symbol,
            prediction="BUY" if i % 2 == 0 else "SELL",
            confidence=0.7 + (i * 0.05),
            signal_strength=0.6 + (i * 0.08),
            expected_return=1.0 + (i * 0.5),
            risk_score=0.2 + (i * 0.1),
            exchange="bybit",
            timeframe="15m"
        )
        predictions.append(prediction)
    
    # Bulk insert - 20x faster than individual inserts
    start_time = asyncio.get_event_loop().time()
    prediction_ids = await db.ml_predictions.log_predictions_batch(predictions)
    end_time = asyncio.get_event_loop().time()
    
    print(f"Bulk inserted {len(prediction_ids)} predictions in {(end_time - start_time)*1000:.2f}ms")
    print(f"IDs: {prediction_ids}")


async def example_transaction_operations():
    """Example of transaction operations for atomicity."""
    print("=== Transaction Operations Example ===")
    
    db = await get_db()
    
    # Method 1: Using context manager
    async with db.transaction() as conn:
        # These operations will be atomic
        await conn.execute("""
            INSERT INTO orders (symbol, side, quantity, price, status, exchange)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, "BTC/USDT", "buy", 0.01, 50000.0, "pending", "bybit")
        
        await conn.execute("""
            INSERT INTO trades (symbol, side, quantity, price, status)
            VALUES ($1, $2, $3, $4, $5)
        """, "BTC/USDT", "buy", 0.01, 50000.0, "executed")
        
        print("Atomic order + trade creation completed")
    
    # Method 2: Using Unit of Work pattern
    uow = db.create_unit_of_work()
    
    async def create_position(conn):
        position = Position(
            symbol="ETH/USDT",
            exchange="bybit",
            side="long",
            quantity=Decimal("0.1"),
            entry_price=Decimal("3000"),
            leverage=5
        )
        return await db.positions.open_position(position)
    
    async def log_prediction_for_position(conn):
        prediction = MLPrediction(
            symbol="ETH/USDT",
            prediction="BUY",
            confidence=0.9
        )
        return await db.ml_predictions.log_prediction(prediction)
    
    uow.register_operation(create_position)
    uow.register_operation(log_prediction_for_position)
    
    try:
        results = await uow.commit()
        print(f"Unit of Work completed: Position ID {results[0]}, Prediction ID {results[1]}")
    except Exception as e:
        print(f"Unit of Work failed: {e}")


@circuit_breaker("example_operation")
async def example_circuit_breaker_operation():
    """Example operation protected by circuit breaker."""
    print("=== Circuit Breaker Example ===")
    
    # This operation is protected by circuit breaker
    db = await get_db()
    
    try:
        # Simulate potentially failing operation
        positions = await db.positions.get_open_positions()
        print(f"Circuit breaker allowed operation: Found {len(positions)} positions")
        return positions
    except Exception as e:
        print(f"Operation failed: {e}")
        raise


@with_retry("example_retry")
async def example_retry_operation():
    """Example operation with retry logic."""
    print("=== Retry Logic Example ===")
    
    db = await get_db()
    
    # This operation will be retried on transient failures
    stats = await db.ml_predictions.get_prediction_stats(hours=24)
    print(f"Retry handler allowed operation: {stats['total_predictions']} predictions in last 24h")
    
    return stats


async def example_monitoring_and_metrics():
    """Example of monitoring and metrics collection."""
    print("=== Monitoring and Metrics Example ===")
    
    db = await get_db()
    
    # Get overall database health
    health = await db.health_check()
    print(f"Database health: {health['status']}")
    print(f"Connection pool: {health['pool']}")
    
    # Get comprehensive stats
    stats = await db.get_stats()
    print(f"Total queries: {stats['queries']['total']}")
    print(f"Success rate: {stats['queries']['success_rate']:.1f}%")
    
    # Get circuit breaker status
    if 'circuit_breakers' in stats:
        cb_health = stats['circuit_breakers']
        print(f"Circuit breakers: {cb_health['total_breakers']} total, {cb_health['open_breakers']} open")
    
    # Get query optimizer stats
    if 'query_optimizer' in stats:
        qo_stats = stats['query_optimizer']
        print(f"Query cache hit rate: {qo_stats['cache_hit_rate']:.1f}%")
        print(f"Prepared statements: {qo_stats['prepared_statements_count']}")


async def example_position_management():
    """Example of position management operations."""
    print("=== Position Management Example ===")
    
    db = await get_db()
    
    # Open a new position
    position = Position(
        symbol="BTC/USDT",
        exchange="bybit",
        side="long",
        quantity=Decimal("0.05"),
        entry_price=Decimal("45000"),
        stop_loss=Decimal("43000"),
        take_profit=Decimal("48000"),
        leverage=5
    )
    
    position_id = await db.positions.open_position(position)
    print(f"Opened position {position_id}")
    
    # Update position price
    update_result = await db.positions.update_position_price(
        position_id, 
        Decimal("46000")
    )
    print(f"Updated position: PnL = ${update_result['pnl']:.2f}")
    
    # Get all open positions
    open_positions = await db.positions.get_open_positions()
    print(f"Total open positions: {len(open_positions)}")
    
    # Get position statistics
    position_stats = await db.positions.get_position_stats()
    print(f"Win rate: {position_stats['win_rate']:.1f}%")
    print(f"Total PnL: ${position_stats['total_pnl']:.2f}")


async def example_ml_prediction_analytics():
    """Example of ML prediction analytics."""
    print("=== ML Prediction Analytics Example ===")
    
    db = await get_db()
    
    # Get prediction statistics
    stats = await db.ml_predictions.get_prediction_stats(hours=24)
    print(f"24h Predictions: {stats['total_predictions']}")
    print(f"Average confidence: {stats['avg_confidence']:.2f}")
    print(f"Signal distribution: {stats['signal_distribution']}")
    
    # Get top performing symbols
    top_symbols = await db.ml_predictions.get_top_performing_symbols(limit=5)
    print("Top performing symbols:")
    for symbol_data in top_symbols:
        print(f"  {symbol_data['symbol']}: {symbol_data['avg_expected_return']:.2f}% expected return")
    
    # Check for unique predictions (deduplication)
    unique_check = await db.ml_predictions.get_unique_predictions("BTC/USDT", "15m", minutes=5)
    if unique_check:
        print(f"Recent prediction exists for BTC/USDT: {unique_check.prediction}")
    else:
        print("No recent duplicate predictions found")


async def example_performance_testing():
    """Example of performance testing with metrics."""
    print("=== Performance Testing Example ===")
    
    db = await get_db()
    
    # Test bulk insert performance
    large_batch = []
    for i in range(100):
        prediction = MLPrediction(
            symbol=f"SYMBOL{i % 10}/USDT",
            prediction="BUY" if i % 2 == 0 else "SELL",
            confidence=0.5 + (i % 50) / 100,
            exchange="bybit"
        )
        large_batch.append(prediction)
    
    start_time = asyncio.get_event_loop().time()
    ids = await db.ml_predictions.log_predictions_batch(large_batch)
    end_time = asyncio.get_event_loop().time()
    
    duration_ms = (end_time - start_time) * 1000
    throughput = len(ids) / (duration_ms / 1000)
    
    print(f"Bulk insert performance:")
    print(f"  - {len(ids)} predictions in {duration_ms:.2f}ms")
    print(f"  - Throughput: {throughput:.0f} predictions/second")
    
    # Test batch position updates
    position_updates = [
        (i, {"current_price": 45000 + i * 10, "pnl": i * 5})
        for i in range(1, 21)  # Update positions 1-20
    ]
    
    start_time = asyncio.get_event_loop().time()
    updated_count = await db.positions.update_positions_batch(position_updates)
    end_time = asyncio.get_event_loop().time()
    
    print(f"Batch position updates: {updated_count} positions in {(end_time - start_time)*1000:.2f}ms")


async def run_all_examples():
    """Run all examples in sequence."""
    examples = [
        example_basic_operations,
        example_bulk_operations,
        example_transaction_operations,
        example_circuit_breaker_operation,
        example_retry_operation,
        example_monitoring_and_metrics,
        example_position_management,
        example_ml_prediction_analytics,
        example_performance_testing
    ]
    
    print("🚀 Running Database Architecture Examples")
    print("=" * 50)
    
    for example_func in examples:
        try:
            await example_func()
            print("✅ Success")
        except Exception as e:
            print(f"❌ Failed: {e}")
        
        print("-" * 30)
        await asyncio.sleep(0.5)  # Brief pause between examples
    
    print("🏁 All examples completed!")


if __name__ == "__main__":
    # Run examples
    asyncio.run(run_all_examples())