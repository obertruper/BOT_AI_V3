"""
Тестовый файл для проверки Claude Code интеграции
"""

def calculate_profit(buy_price, sell_price, amount):
    # TODO: добавить проверку на отрицательные значения
    profit = (sell_price - buy_price) * amount
    return profit

def risky_function():
    # Потенциальная SQL инъекция
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query

class TradingBot:
    def __init__(self):
        self.api_key = "sk-12345678"  # Утечка секрета!
        
    def execute_trade(self, symbol, amount):
        # Отсутствует обработка ошибок
        result = self.exchange.buy(symbol, amount)
        return result