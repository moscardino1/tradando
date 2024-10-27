class Portfolio:
    def __init__(self, initial_cash):
        self.cash = initial_cash
        self.holdings = 0
        self.trades = []

    def add_trade(self, trade_type, price, amount, timestamp, value):
        trade = {
            'type': trade_type,
            'price': price,
            'amount': amount,
            'timestamp': timestamp,
            'value': value
        }
        self.trades.append(trade)

# Initialize portfolio
portfolio = Portfolio(initial_cash=10000)
