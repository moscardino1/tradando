from tradando.strategies.base import TradingStrategy
import pandas as pd
import numpy as np

class MACDStrategy(TradingStrategy):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, 
                 signal_period: int = 9, **kwargs):
        super().__init__(**kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.name = "MACD Strategy"
        self.description = (f"MACD ({fast_period}/{slow_period}/{signal_period}) "
                          "Crossover Strategy")

    def calculate_macd(self, data: pd.Series) -> tuple:
        """Calculate MACD line and signal line"""
        exp1 = data.ewm(span=self.fast_period, adjust=False).mean()
        exp2 = data.ewm(span=self.slow_period, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        return macd_line, signal_line

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on MACD crossover"""
        df = data.copy()
        
        # Calculate MACD and signal line
        df['MACD'], df['Signal_Line'] = self.calculate_macd(df['Close'])
        df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
        
        # Generate signals
        df['signal'] = 0
        
        # Buy when MACD crosses above signal line
        df.loc[(df['MACD'] > df['Signal_Line']) & 
               (df['MACD'].shift(1) <= df['Signal_Line'].shift(1)), 'signal'] = 1
        
        # Sell when MACD crosses below signal line
        df.loc[(df['MACD'] < df['Signal_Line']) & 
               (df['MACD'].shift(1) >= df['Signal_Line'].shift(1)), 'signal'] = -1
        
        return df 