#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


from exchanges.bybit.bybit_exchange import BybitExchange
from utils.config import Config


async def check_balance_and_positions():
    """Check Bybit balance and positions"""
    config = Config()

    # Initialize exchange
    exchange = BybitExchange(config)
    await exchange.initialize()

    print("\n" + "=" * 60)
    print("BYBIT ACCOUNT STATUS")
    print("=" * 60)

    try:
        # Get account balance
        balance_info = await exchange.get_balance()

        if balance_info:
            # CCXT format balance
            usdt_balance = balance_info.get("USDT", {})
            total_balance = float(usdt_balance.get("total", 0))
            available_balance = float(usdt_balance.get("free", 0))
            margin_used = float(usdt_balance.get("used", 0))

            print("\n💰 BALANCE:")
            print(f"  Total Equity: ${total_balance:.2f}")
            print(f"  Available: ${available_balance:.2f}")
            print(f"  Margin Used: ${margin_used:.2f}")

            # Check if balance is too low
            if available_balance < 10:
                print(f"\n⚠️  WARNING: Available balance (${available_balance:.2f}) is too low!")
                print("  Minimum required: $10 for opening new positions")

        # Get open positions
        positions = await exchange.get_positions()

        if positions:
            open_positions = [p for p in positions if p.get("contracts", 0) > 0]

            print(f"\n📊 POSITIONS: {len(open_positions)} open")

            total_margin = 0
            for pos in open_positions:
                symbol = pos.get("symbol")
                side = pos.get("side")
                size = float(pos.get("contracts", 0))
                entry_price = float(pos.get("markPrice", 0))
                leverage = float(pos.get("leverage", 1) or 1)
                position_value = size
                margin = position_value / leverage if leverage > 0 else position_value
                total_margin += margin

                print(f"\n  {symbol} {side}:")
                print(f"    Size: {size}")
                print(f"    Entry: ${entry_price:.4f}")
                print(f"    Value: ${position_value:.2f}")
                print(f"    Leverage: {leverage}x")
                print(f"    Margin: ${margin:.2f}")

            if open_positions:
                print(f"\n  Total Margin Used: ${total_margin:.2f}")

        # Check risk settings
        print("\n⚙️  RISK SETTINGS:")
        print(f"  Default Leverage: {config.DEFAULT_LEVERAGE}x")
        print(f"  Max Position Size: ${config.MAX_POSITION_SIZE}")
        print(f"  Risk per Trade: {config.RISK_LIMIT_PERCENTAGE}%")

        # Calculate max new position
        if balance_info:
            usdt = balance_info.get("USDT", {})
            available = float(usdt.get("free", 0))
            max_position_with_leverage = available * config.DEFAULT_LEVERAGE

            print("\n💡 MAX NEW POSITION:")
            print(f"  With {config.DEFAULT_LEVERAGE}x leverage: ${max_position_with_leverage:.2f}")
            print(f"  Safe size (2% risk): ${available * 0.02 * config.DEFAULT_LEVERAGE:.2f}")

            if available < 10:
                print("\n❌ CANNOT OPEN NEW POSITIONS - Insufficient balance!")
                print(f"   Need at least $10, have ${available:.2f}")

    except Exception as e:
        print(f"\n❌ Error checking balance: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(check_balance_and_positions())
