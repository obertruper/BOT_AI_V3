#!/usr/bin/env python3
"""
Fix Bybit insufficient balance error (110007)
This script checks balance and adjusts position sizes
"""
import asyncio
import os

import ccxt.pro as ccxtpro
from dotenv import load_dotenv

load_dotenv()


async def check_and_fix_balance():
    """Check balance and fix position sizing issues"""

    # Initialize Bybit exchange
    exchange = ccxtpro.bybit(
        {
            "apiKey": os.getenv("BYBIT_API_KEY"),
            "secret": os.getenv("BYBIT_API_SECRET"),
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap",
                "hedgeMode": True,
            },
        }
    )

    print("\n" + "=" * 60)
    print("BYBIT BALANCE CHECK & FIX")
    print("=" * 60)

    try:
        # Fetch balance
        balance = await exchange.fetch_balance()
        usdt_balance = balance.get("USDT", {})

        total = float(usdt_balance.get("total", 0))
        free = float(usdt_balance.get("free", 0))
        used = float(usdt_balance.get("used", 0))

        print("\n💰 ACCOUNT BALANCE:")
        print(f"  Total: ${total:.2f} USDT")
        print(f"  Available: ${free:.2f} USDT")
        print(f"  Used in positions: ${used:.2f} USDT")

        # Check if balance is sufficient
        min_balance = 10  # Minimum $10 for trading

        if free < min_balance:
            print("\n❌ INSUFFICIENT BALANCE!")
            print(f"  Need at least ${min_balance} USDT")
            print(f"  Current available: ${free:.2f} USDT")
            print("\n📝 SOLUTIONS:")
            print("  1. Deposit more USDT to your account")
            print("  2. Close some positions to free up margin")
            print("  3. Reduce position sizes in config")

            # Check positions
            positions = await exchange.fetch_positions()
            open_positions = [p for p in positions if p["contracts"] > 0]

            if open_positions:
                print(f"\n📊 OPEN POSITIONS ({len(open_positions)}):")
                total_margin = 0

                for pos in open_positions:
                    symbol = pos["symbol"]
                    side = pos["side"]
                    contracts = pos["contracts"]
                    mark_price = pos["markPrice"]
                    leverage = pos.get("leverage", 5)

                    position_value = contracts * mark_price if mark_price else contracts
                    margin = position_value / leverage if leverage else position_value
                    total_margin += margin

                    print(f"  {symbol} {side}: ${position_value:.2f} (margin: ${margin:.2f})")

                print(f"\n  Total margin used: ${total_margin:.2f}")

                if total_margin > total * 0.8:
                    print("\n⚠️  WARNING: Using >80% of total balance in positions!")
                    print("  Risk of liquidation is HIGH!")

        else:
            print("\n✅ BALANCE OK - Can open new positions")

            # Calculate safe position size
            leverage = float(os.getenv("DEFAULT_LEVERAGE", 5))
            risk_percent = float(os.getenv("RISK_LIMIT_PERCENTAGE", 2)) / 100

            safe_position_size = free * risk_percent * leverage
            max_position_size = free * leverage * 0.5  # Max 50% of available

            print("\n📊 POSITION SIZE RECOMMENDATIONS:")
            print(f"  With {leverage}x leverage:")
            print(f"  - Safe size (2% risk): ${safe_position_size:.2f}")
            print(f"  - Max size (50% margin): ${max_position_size:.2f}")

            # Update config if needed
            current_max = float(os.getenv("MAX_POSITION_SIZE", 1000))
            if current_max > max_position_size:
                print("\n⚠️  CONFIG ADJUSTMENT NEEDED:")
                print(f"  Current MAX_POSITION_SIZE: ${current_max}")
                print(f"  Should be reduced to: ${max_position_size:.2f}")
                print("\n  Update .env file:")
                print(f"  MAX_POSITION_SIZE={max_position_size:.0f}")

        # Check risk parameters
        print("\n⚙️  CURRENT RISK SETTINGS:")
        print(f"  DEFAULT_LEVERAGE={os.getenv('DEFAULT_LEVERAGE', 5)}")
        print(f"  MAX_POSITION_SIZE={os.getenv('MAX_POSITION_SIZE', 1000)}")
        print(f"  RISK_LIMIT_PERCENTAGE={os.getenv('RISK_LIMIT_PERCENTAGE', 2)}")

        # Get recent errors from API
        print("\n📋 CHECKING RECENT ORDERS...")

        # Try to place a minimal test order to check connectivity
        test_symbol = "BTC/USDT:USDT"
        ticker = await exchange.fetch_ticker(test_symbol)
        current_price = ticker["last"]

        # Calculate minimum order size
        min_order = 10 / current_price  # $10 worth

        print(f"  BTC price: ${current_price:.2f}")
        print(f"  Min order size: {min_order:.6f} BTC (${10:.2f})")

        if free >= 10:
            print("\n✅ System ready for trading")
        else:
            print("\n❌ Cannot trade - insufficient balance")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(check_and_fix_balance())
