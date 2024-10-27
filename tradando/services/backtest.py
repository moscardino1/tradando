from typing import Dict, Any
from tradando.models.portfolio import Portfolio  # Use absolute import
from tradando.strategies.base import TradingStrategy
import pandas as pd

class Backtester:
    def __init__(self, strategy: TradingStrategy):
        self.strategy = strategy

    def run(self, data: pd.DataFrame, initial_value: float = 10000) -> Dict[str, Any]:
        """Run backtest with the given strategy"""
        portfolio = Portfolio(initial_value)
        df = self.strategy.generate_signals(data)
        
        # Get the minimum required periods from the strategy
        start_index = max(
            getattr(self.strategy, 'fast_period', 20),
            getattr(self.strategy, 'slow_period', 50)
        )
        
        for i in range(start_index, len(df)):
            current_price = float(df['Close'].iloc[i])
            current_time = df.index[i]
            
            # Check exit conditions if we have a position
            if portfolio.holdings > 0:
                exit_check = self.strategy.check_exit_conditions(
                    current_price, 
                    portfolio.entry_price
                )
                
                if exit_check['exit']:
                    portfolio.execute_sell(
                        current_price,
                        current_time,
                        reason=exit_check['reason']
                    )
                    continue
            
            # Check strategy signals
            signal = df['signal'].iloc[i]
            
            if signal > 0 and portfolio.cash > 0:
                portfolio.execute_buy(current_price, current_time)
            elif signal < 0 and portfolio.holdings > 0:
                portfolio.execute_sell(current_price, current_time)
        
        # Calculate final results
        final_price = float(df['Close'].iloc[-1])
        final_value = portfolio.get_current_value(final_price)
        
        stats = portfolio.get_statistics()
        return {
            'initial_value': initial_value,
            'final_value': round(final_value, 2),
            'return_pct': round(((final_value - initial_value) / initial_value) * 100, 2),
            'price_change_pct': round(((final_price - float(df['Close'].iloc[0])) / float(df['Close'].iloc[0])) * 100, 2),
            'current_price': round(final_price, 2),
            'holdings': round(portfolio.holdings, 8),
            'cash': round(portfolio.cash, 2),
            **stats
        }
