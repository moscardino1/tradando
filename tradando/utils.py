import yfinance as yf
import pandas as pd
import requests
from datetime import datetime  # Import only datetime here
import pytz
from config import Config

def utc_to_local(utc_dt):
    local_tz = datetime.now().astimezone().tzinfo
    return utc_dt.replace(tzinfo=pytz.UTC).astimezone(local_tz)

def fetch_historical_data(ticker, period="5d", interval="5m"):
    try:
        if not ticker.endswith('-USD'):
            ticker = f"{ticker}-USD"
        data = yf.download(ticker, period=period, interval=interval)
        print(f"Fetched {len(data)} data points with {interval} interval")
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
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
