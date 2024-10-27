from tradando.strategies.base import TradingStrategy
import pandas as pd

class SMACrossStrategy(TradingStrategy):
    def __init__(self, fast_period: int = 20, slow_period: int = 50, **kwargs):
        super().__init__(**kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = "SMA Crossover"
        self.description = f"Simple Moving Average Crossover ({fast_period}/{slow_period})"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on SMA crossover"""
        df = data.copy()
        df[f'SMA{self.fast_period}'] = df['Close'].rolling(window=self.fast_period).mean()
        df[f'SMA{self.slow_period}'] = df['Close'].rolling(window=self.slow_period).mean()
        
        # Generate signals
        df['signal'] = 0
        df.loc[df[f'SMA{self.fast_period}'] > df[f'SMA{self.slow_period}'], 'signal'] = 1
        df.loc[df[f'SMA{self.fast_period}'] < df[f'SMA{self.slow_period}'], 'signal'] = -1
        
        return df
