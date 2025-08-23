#!/usr/bin/env python3
from database.connections.postgres import AsyncPGPool
import asyncio
from datetime import datetime, timedelta

async def analyze_performance():
    # Получаем ордера за последние 24 часа
    orders_query = '''
    SELECT 
        COUNT(*) as total_orders,
        COUNT(CASE WHEN status = 'filled' THEN 1 END) as filled_orders,
        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_orders,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders,
        COUNT(CASE WHEN status = 'open' THEN 1 END) as open_orders
    FROM orders 
    WHERE created_at > NOW() - INTERVAL '24 hours'
    '''
    
    trades_query = '''
    SELECT 
        COUNT(*) as total_trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as profitable_trades,
        SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as loss_trades,
        AVG(pnl) as avg_pnl,
        SUM(pnl) as total_pnl
    FROM trades
    WHERE created_at > NOW() - INTERVAL '24 hours'
    '''
    
    orders_result = await AsyncPGPool.fetch(orders_query)
    trades_result = await AsyncPGPool.fetch(trades_query)
    
    print('=== ПРОИЗВОДИТЕЛЬНОСТЬ ЗА 24 ЧАСА ===')
    print('\nОрдера:')
    if orders_result:
        o = orders_result[0]
        print(f'  Всего: {o["total_orders"]}')
        print(f'  Исполнено: {o["filled_orders"]}')
        print(f'  Отменено: {o["cancelled_orders"]}')
        print(f'  В ожидании: {o["pending_orders"]}')
        print(f'  Открыто: {o["open_orders"]}')
    
    print('\nТрейды:')
    if trades_result:
        t = trades_result[0]
        total = t['total_trades'] or 0
        profitable = t['profitable_trades'] or 0
        losses = t['loss_trades'] or 0
        
        print(f'  Всего: {total}')
        if total > 0:
            print(f'  Прибыльных: {profitable} ({profitable/total*100:.1f}%)')
            print(f'  Убыточных: {losses} ({losses/total*100:.1f}%)')
            print(f'  Средний PnL: ${t["avg_pnl"] or 0:.2f}')
            print(f'  Общий PnL: ${t["total_pnl"] or 0:.2f}')

asyncio.run(analyze_performance())