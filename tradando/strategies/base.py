from abc import ABC, abstractmethod
from typing import Dict, List, Any
import pandas as pd

class TradingStrategy(ABC):
    def __init__(self, stop_loss_pct: float = 5, take_profit_pct: float = 5):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.name = "Base Strategy"
        self.description = "Base strategy class"

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate buy/sell signals based on the strategy"""
        pass

    def check_exit_conditions(self, current_price: float, entry_price: float) -> Dict[str, Any]:
        """Check stop loss and take profit conditions"""
        if entry_price is None:
            return {'exit': False}
            
        price_change_pct = ((current_price - entry_price) / entry_price) * 100
        
        if price_change_pct <= -self.stop_loss_pct:
            return {
                'exit': True,
                'reason': 'stop_loss',
                'pnl_pct': price_change_pct
            }
            
        if price_change_pct >= self.take_profit_pct:
            return {
                'exit': True,
                'reason': 'take_profit',
                'pnl_pct': price_change_pct
            }
            
        return {'exit': False}
