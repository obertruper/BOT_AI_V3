#!/usr/bin/env python3
"""
Тестирование создания ордеров с SL/TP на Bybit
"""

import asyncio
import os
import sys
from pathlib import Path
from decimal import Decimal

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from exchanges.bybit import BybitClient
from exchanges.base.order_types import OrderRequest, OrderType, OrderSide, TimeInForce
from core.logger import setup_logger
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = setup_logger("sltp_test")


async def test_market_order_with_sltp():
    """Тестируем создание рыночного ордера с SL/TP"""
    
    logger.info("=" * 60)
    logger.info("Тест создания рыночного ордера с SL/TP")
    logger.info("=" * 60)
    
    # Создаем клиента Bybit
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("Bybit API credentials not found")
        return
    
    client = BybitClient(
        api_key=api_key,
        api_secret=api_secret,
        sandbox=False
    )
    
    try:
        # Проверяем баланс
        logger.info("\n1. Проверяем баланс...")
        balance_params = {"accountType": "UNIFIED"}
        response = await client._make_request(
            "GET",
            "/v5/account/wallet-balance",
            balance_params,
            auth=True
        )
        
        if response.get("retCode") == 0:
            accounts = response.get("result", {}).get("list", [])
            if accounts:
                for account in accounts:
                    coins = account.get("coin", [])
                    for coin in coins:
                        if coin.get("coin") == "USDT":
                            available_str = coin.get("availableToWithdraw", "0")
                            if not available_str or available_str == "":
                                available_str = "0"
                            available = float(available_str)
                            logger.info(f"Доступный баланс USDT: {available:.2f}")
                            
                            if available < 2:
                                logger.error("Недостаточно USDT для теста (минимум 2 USDT)")
                                return
                            break
        
        # Параметры тестового ордера
        symbol = "BTCUSDT"
        
        # Получаем текущую цену
        ticker = await client.get_ticker(symbol)
        current_price = ticker.last_price
        logger.info(f"\n2. Текущая цена {symbol}: ${current_price:.2f}")
        
        # Получаем информацию об инструменте
        instrument_info = await client.get_instrument_info(symbol)
        min_qty = max(instrument_info.min_order_qty, 0.001)
        
        # Рассчитываем минимальный размер для $2
        quantity = 2.0 / float(current_price)
        quantity = max(quantity, min_qty)
        
        # Округляем по qty_step
        from decimal import Decimal, ROUND_DOWN
        qty_decimal = Decimal(str(quantity))
        step_decimal = Decimal(str(instrument_info.qty_step))
        rounded_qty = (qty_decimal / step_decimal).quantize(Decimal('1'), rounding=ROUND_DOWN) * step_decimal
        
        logger.info(f"Размер позиции: {rounded_qty} BTC (${float(rounded_qty) * current_price:.2f})")
        
        # Рассчитываем SL и TP
        # SL: 1.5% ниже для покупки
        stop_loss = current_price * 0.985  
        # TP: 4% выше для покупки
        take_profit = current_price * 1.04
        
        logger.info(f"\n3. Параметры ордера:")
        logger.info(f"   Направление: BUY")
        logger.info(f"   Количество: {rounded_qty}")
        logger.info(f"   Stop Loss: ${stop_loss:.2f} (-1.5%)")
        logger.info(f"   Take Profit: ${take_profit:.2f} (+4%)")
        
        # Создаем запрос ордера
        order_request = OrderRequest(
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=float(rounded_qty),
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=TimeInForce.IOC,
            exchange_params={}  # Дополнительные параметры при необходимости
        )
        
        # Отправляем ордер
        logger.info("\n4. Отправляем рыночный ордер...")
        order_response = await client.place_order(order_request)
        
        if order_response.success:
            logger.info(f"✅ Ордер создан успешно!")
            logger.info(f"   Order ID: {order_response.order_id}")
            logger.info(f"   Символ: {order_response.symbol}")
            logger.info(f"   Сторона: {order_response.side}")
            logger.info(f"   Тип: {order_response.order_type}")
            
            # Ждем немного и проверяем позицию
            await asyncio.sleep(2)
            
            logger.info("\n5. Проверяем позицию и SL/TP...")
            positions = await client.get_positions(symbol)
            
            if positions:
                for position in positions:
                    logger.info(f"\n✅ Позиция найдена:")
                    logger.info(f"   Символ: {position.symbol}")
                    logger.info(f"   Сторона: {position.side}")
                    logger.info(f"   Размер: {position.size}")
                    logger.info(f"   Цена входа: ${position.entry_price:.2f}")
                    logger.info(f"   Текущая цена: ${position.mark_price:.2f}")
                    
                    if position.stop_loss:
                        logger.info(f"   ✅ Stop Loss установлен: ${position.stop_loss:.2f}")
                    else:
                        logger.warning(f"   ⚠️ Stop Loss НЕ установлен!")
                    
                    if position.take_profit:
                        logger.info(f"   ✅ Take Profit установлен: ${position.take_profit:.2f}")
                    else:
                        logger.warning(f"   ⚠️ Take Profit НЕ установлен!")
                    
                    logger.info(f"   PnL: ${position.unrealised_pnl:.2f}")
                    
                    # Проверяем, нужно ли закрыть позицию
                    logger.info("\n6. Закрываем тестовую позицию...")
                    close_request = OrderRequest(
                        symbol=symbol,
                        order_type=OrderType.MARKET,
                        side=OrderSide.SELL if position.side == "Buy" else OrderSide.BUY,
                        quantity=position.size,
                        time_in_force=TimeInForce.IOC,
                        exchange_params={"reduceOnly": True}
                    )
                    
                    close_response = await client.place_order(close_request)
                    if close_response.success:
                        logger.info(f"✅ Позиция закрыта успешно")
                    else:
                        logger.warning(f"⚠️ Не удалось закрыть позицию: {close_response.error}")
            else:
                logger.warning("Позиции не найдены после создания ордера")
                
        else:
            logger.error(f"❌ Ошибка создания ордера: {order_response.error}")
            
    except Exception as e:
        logger.error(f"Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Закрываем сессию
        if hasattr(client, 'session'):
            await client.session.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("Тест завершен")
    logger.info("=" * 60)


async def main():
    """Главная функция"""
    await test_market_order_with_sltp()


if __name__ == "__main__":
    asyncio.run(main())