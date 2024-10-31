from tradando.strategies.base import TradingStrategy
import pandas as pd
import numpy as np

class RSIStrategy(TradingStrategy):
    def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30, **kwargs):
        super().__init__(**kwargs)
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.name = "RSI Strategy"
        self.description = f"RSI ({period}) with Overbought ({overbought}) and Oversold ({oversold}) levels"

    def calculate_rsi(self, data: pd.Series) -> pd.Series:
        """Calculate RSI indicator"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on RSI"""
        df = data.copy()
        df['RSI'] = self.calculate_rsi(df['Close'])
        
        # Generate signals
        df['signal'] = 0
        
        # Buy when RSI crosses below oversold level
        df.loc[df['RSI'] < self.oversold, 'signal'] = 1
        
        # Sell when RSI crosses above overbought level
        df.loc[df['RSI'] > self.overbought, 'signal'] = -1
        
        return df 