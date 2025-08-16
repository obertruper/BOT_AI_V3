#!/usr/bin/env python3
"""
Test file for Claude Code Review verification.
This file contains intentional issues for Claude to detect.
"""

import asyncio

# Issue 1: Hardcoded API key (should be detected)
API_KEY = "sk-test-12345678901234567890"  # pragma: allowlist secret

# Issue 2: Using wrong PostgreSQL port
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,  # Should be 5555 for this project
    "database": "bot_trading_v3",
}


# Issue 3: Missing async/await pattern
def fetch_data_from_database(query: str):  # Should be async
    """Fetch data from database - missing async."""
    # This should be an async function
    # Simulating connection (undefined on purpose for test)
    conn = None  # connect_to_db would be here
    result = f"Query result for: {query}"  # Should use await
    return result


# Issue 4: Missing type hints
def process_trading_signal(signal, amount):  # Missing type hints
    """Process trading signal - missing type hints."""
    if signal == "BUY":
        return amount * 1.1
    elif signal == "SELL":
        return amount * 0.9
    return amount


# Issue 5: Blocking I/O in async function
async def save_to_file(data: dict):
    """Save data to file - has blocking I/O."""
    with open("output.txt", "w") as f:  # Should use aiofiles
        f.write(str(data))  # Blocking I/O in async function
    return True


# Issue 6: No error handling
def risky_operation(value: float) -> float:
    """Risky operation without error handling."""
    result = 100 / value  # Can raise ZeroDivisionError
    return result


# Good example (for comparison)
async def proper_async_function(data: list[str]) -> dict[str, int]:
    """Properly implemented async function with type hints."""
    try:
        result = {}
        for item in data:
            # Simulate async operation
            await asyncio.sleep(0.01)
            result[item] = len(item)
        return result
    except Exception as e:
        print(f"Error processing data: {e}")
        return {}


if __name__ == "__main__":
    print("Test file for Claude Code Review")
    print(f"Database port: {DATABASE_CONFIG['port']}")  # Will show wrong port

    # Test the functions
    test_data = ["BTC", "ETH", "SOL"]
    asyncio.run(proper_async_function(test_data))
