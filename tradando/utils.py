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

def get_top_cryptos(limit: int = 1) -> List[str]:
    """Fetch top cryptocurrencies by market cap"""
    # For testing, just return BTC
    return ['BTC-USD']

def analyze_crypto(crypto: str, days: int = 5, stop_loss_pct: float = 5, take_profit_pct: float = 5) -> Dict[str, Any]:
    """Analyze a single cryptocurrency"""
    try:
        print(f"Starting analysis for {crypto} with SL:{stop_loss_pct}% TP:{take_profit_pct}%")
        
        # Fetch data
        data = fetch_historical_data(crypto, days)
        if data is None or data.empty:
            return {"error": f"No data available for {crypto}"}
            
        # Calculate price change percentage from start to end
        start_price = float(data['Close'].iloc[0])
        end_price = float(data['Close'].iloc[-1])
        price_change_pct = ((end_price - start_price) / start_price) * 100
        
        # Calculate indicators
        data['SMA20'] = data['Close'].rolling(window=20).mean()
        data['SMA50'] = data['Close'].rolling(window=50).mean()
        
        # Initialize portfolio
        initial_value = 10000
        portfolio = {
            'symbol': crypto,
            'initial_cash': initial_value,
            'cash': initial_value,
            'holdings': 0,
            'trades': [],
            'entry_price': None,
            'last_buy_trade': None  # Track the last buy trade for P&L calculation
        }
        
        # Run strategy
        for i in range(50, len(data)):
            current_price = float(data['Close'].iloc[i])
            current_time = data.index[i].strftime('%Y-%m-%d %H:%M')
            
            # Check stop-loss and take-profit if we have a position
            if portfolio['holdings'] > 0 and portfolio['entry_price'] is not None:
                price_change_pct = ((current_price - portfolio['entry_price']) / portfolio['entry_price']) * 100
                
                # Check stop-loss
                if price_change_pct <= -stop_loss_pct:
                    print(f"🔴 Stop loss triggered at {price_change_pct:.2f}% - Entry: ${portfolio['entry_price']:.2f}, Current: ${current_price:.2f}")
                    sell_amount = portfolio['holdings'] * current_price
                    shares_sold = portfolio['holdings']
                    portfolio['cash'] = sell_amount
                    portfolio['holdings'] = 0
                    
                    trade = {
                        'type': 'sell',
                        'reason': 'stop_loss',
                        'price': round(current_price, 2),
                        'timestamp': current_time,
                        'amount': round(sell_amount, 2),
                        'shares': round(shares_sold, 8),
                        'pnl_pct': round(price_change_pct, 2),
                        'pnl_amount': round(sell_amount - portfolio['last_buy_trade']['amount'], 2) if portfolio['last_buy_trade'] else 0,
                        'entry_price': round(portfolio['entry_price'], 2)
                    }
                    portfolio['trades'].append(trade)
                    portfolio['entry_price'] = None
                    portfolio['last_buy_trade'] = None
                    continue

                # Check take-profit
                if price_change_pct >= take_profit_pct:
                    print(f"🟢 Take profit triggered at {price_change_pct:.2f}% - Entry: ${portfolio['entry_price']:.2f}, Current: ${current_price:.2f}")
                    sell_amount = portfolio['holdings'] * current_price
                    shares_sold = portfolio['holdings']
                    portfolio['cash'] = sell_amount
                    portfolio['holdings'] = 0
                    
                    trade = {
                        'type': 'sell',
                        'reason': 'take_profit',
                        'price': round(current_price, 2),
                        'timestamp': current_time,
                        'amount': round(sell_amount, 2),
                        'shares': round(shares_sold, 8),
                        'pnl_pct': round(price_change_pct, 2),
                        'pnl_amount': round(sell_amount - portfolio['last_buy_trade']['amount'], 2) if portfolio['last_buy_trade'] else 0,
                        'entry_price': round(portfolio['entry_price'], 2)
                    }
                    portfolio['trades'].append(trade)
                    portfolio['entry_price'] = None
                    portfolio['last_buy_trade'] = None
                    continue

            # Regular strategy signals
            sma20 = data['SMA20'].iloc[i]
            sma50 = data['SMA50'].iloc[i]
            
            if sma20 > sma50 and portfolio['cash'] > 0:
                # Buy signal
                buy_amount = portfolio['cash']
                shares = buy_amount / current_price
                portfolio['holdings'] = shares
                portfolio['cash'] = 0
                portfolio['entry_price'] = current_price
                
                trade = {
                    'type': 'buy',
                    'reason': 'sma_cross',
                    'price': round(current_price, 2),
                    'timestamp': current_time,
                    'amount': round(buy_amount, 2),
                    'shares': round(shares, 8)
                }
                portfolio['trades'].append(trade)
                portfolio['last_buy_trade'] = trade
                print(f"🔵 Buy signal (SMA cross) - Entry price: ${current_price:.2f}")
                
            elif sma20 < sma50 and portfolio['holdings'] > 0:
                # Regular sell signal
                sell_amount = portfolio['holdings'] * current_price
                shares_sold = portfolio['holdings']
                price_change_pct = ((current_price - portfolio['entry_price']) / portfolio['entry_price']) * 100 if portfolio['entry_price'] else 0
                
                portfolio['cash'] = sell_amount
                portfolio['holdings'] = 0
                
                trade = {
                    'type': 'sell',
                    'reason': 'sma_cross',
                    'price': round(current_price, 2),
                    'timestamp': current_time,
                    'amount': round(sell_amount, 2),
                    'shares': round(shares_sold, 8),
                    'pnl_pct': round(price_change_pct, 2),
                    'pnl_amount': round(sell_amount - portfolio['last_buy_trade']['amount'], 2) if portfolio['last_buy_trade'] else 0,
                    'entry_price': round(portfolio['entry_price'], 2)
                }
                portfolio['trades'].append(trade)
                print(f"🟡 Sell signal (SMA cross) - PnL: {price_change_pct:.2f}%")
                portfolio['entry_price'] = None
                portfolio['last_buy_trade'] = None

        # Calculate final metrics
        final_price = float(data['Close'].iloc[-1])
        final_value = portfolio['cash'] + (portfolio['holdings'] * final_price)
        
        # Calculate trade statistics
        sl_trades = [t for t in portfolio['trades'] if t['type'] == 'sell' and t['reason'] == 'stop_loss']
        tp_trades = [t for t in portfolio['trades'] if t['type'] == 'sell' and t['reason'] == 'take_profit']
        signal_trades = [t for t in portfolio['trades'] if t['reason'] == 'sma_cross']
        
        return {
            'symbol': crypto,
            'initial_value': initial_value,
            'final_value': round(final_value, 2),
            'return_pct': round(((final_value - initial_value) / initial_value) * 100, 2),
            'price_change_pct': round(price_change_pct, 2),
            'n_trades': len(portfolio['trades']),
            'n_stop_losses': len(sl_trades),
            'n_take_profits': len(tp_trades),
            'n_signal_trades': len(signal_trades),
            'trades': portfolio['trades'],
            'current_price': round(final_price, 2),
            'holdings': round(portfolio['holdings'], 8),
            'cash': round(portfolio['cash'], 2)
        }
        
    except Exception as e:
        print(f"Error in analyze_crypto: {str(e)}")
        return {"error": f"Error analyzing {crypto}: {str(e)}"}
