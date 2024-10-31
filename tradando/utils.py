import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta  # Import only datetime here
import pytz
from tradando.config import Config
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def utc_to_local(utc_dt):
    local_tz = datetime.now().astimezone().tzinfo
    return utc_dt.replace(tzinfo=pytz.UTC).astimezone(local_tz)

def fetch_historical_data(symbol: str, days: int = 5) -> pd.DataFrame:
    """Fetch historical data with error handling and logging"""
    try:
        # Calculate start and end dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Fetching data for {symbol} from {start_date} to {end_date}")
        
        # Fetch data using yfinance
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval='5m')
        
        if df.empty:
            logger.error(f"No data received for {symbol}")
            return None
            
        logger.info(f"Received {len(df)} data points for {symbol}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

def get_strategy_description():
    headers = {"Authorization": f"Bearer {Config.HF_API_KEY}"}
    prompt = """
    This is a cryptocurrency trading strategy that uses Moving Average Crossover:
    - When the 20-period SMA crosses above the 50-period SMA (Golden Cross), it generates a buy signal
    - When the 20-period SMA crosses below the 50-period SMA (Death Cross), it generates a sell signal
    """
    try:
        response = requests.post(f"{Config.HF_API_URL}gpt2", headers=headers, json={"inputs": prompt})
        return response.json()[0]['generated_text']
    except Exception as e:
        print(f"Error fetching strategy description: {e}")
        return "A Moving Average Crossover strategy using SMA20 and SMA50."
