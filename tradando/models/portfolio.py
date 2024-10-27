from typing import Dict, List, Any
from datetime import datetime

class Portfolio:
    def __init__(self, initial_value: float = 10000):
        self.initial_value = initial_value
        self.cash = initial_value
        self.holdings = 0
        self.trades = []
        self.entry_price = None
        self.last_buy_trade = None

    def execute_buy(self, price: float, timestamp) -> Dict[str, Any]:
        """Execute a buy trade"""
        if self.cash <= 0:
            return None
            
        buy_amount = self.cash
        shares = buy_amount / price
        self.holdings = shares
        self.cash = 0
        self.entry_price = price
        
        trade = {
            'type': 'buy',
            'reason': 'signal',
            'price': round(price, 2),
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else timestamp,
            'amount': round(buy_amount, 2),
            'shares': round(shares, 8)
        }
        self.trades.append(trade)
        self.last_buy_trade = trade
        return trade

    def execute_sell(self, price: float, timestamp, reason: str = 'signal') -> Dict[str, Any]:
        """Execute a sell trade"""
        if self.holdings <= 0:
            return None
            
        sell_amount = self.holdings * price
        shares_sold = self.holdings
        price_change_pct = ((price - self.entry_price) / self.entry_price) * 100 if self.entry_price else 0
        
        self.cash = sell_amount
        self.holdings = 0
        
        trade = {
            'type': 'sell',
            'reason': reason,
            'price': round(price, 2),
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else timestamp,
            'amount': round(sell_amount, 2),
            'shares': round(shares_sold, 8),
            'pnl_pct': round(price_change_pct, 2),
            'pnl_amount': round(sell_amount - self.last_buy_trade['amount'], 2) if self.last_buy_trade else 0,
            'entry_price': round(self.entry_price, 2) if self.entry_price else 0
        }
        self.trades.append(trade)
        self.entry_price = None
        self.last_buy_trade = None
        return trade

    def get_statistics(self) -> Dict[str, Any]:
        """Get portfolio statistics"""
        return {
            'n_trades': len(self.trades),
            'n_buys': len([t for t in self.trades if t['type'] == 'buy']),
            'n_sells': len([t for t in self.trades if t['type'] == 'sell']),
            'n_stop_losses': len([t for t in self.trades if t['reason'] == 'stop_loss']),
            'n_take_profits': len([t for t in self.trades if t['reason'] == 'take_profit']),
            'n_signal_trades': len([t for t in self.trades if t['reason'] == 'signal']),
            'trades': self.trades
        }

    def get_current_value(self, current_price: float) -> float:
        """Calculate current portfolio value"""
        return self.cash + (self.holdings * current_price)
