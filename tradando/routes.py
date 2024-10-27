from flask import Blueprint, render_template, jsonify, request
from tradando.models.portfolio import Portfolio
from tradando.utils import fetch_historical_data, utc_to_local, get_strategy_description#, get_top_cryptos, analyze_crypto
from tradando.config import Config
from datetime import datetime
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import logging
import pandas as pd
from tradando.strategies.sma_cross import SMACrossStrategy
from tradando.services.backtest import Backtester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index():
    return render_template('index.html', initial_cash=Config.INITIAL_CASH)

@api_bp.route('/update', methods=['POST'])
def update():
    ticker = request.form.get('ticker')  # Default to BTC-USD
    data = fetch_historical_data(ticker)
    
    if data is None or data.empty:
        return {"error": "Price data unavailable."}, 500

    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['SMA50'] = data['Close'].rolling(window=50).mean()

    current_price = float(data['Close'].iloc[-1])
    sma20 = float(data['SMA20'].iloc[-1])
    sma50 = float(data['SMA50'].iloc[-1])

    # Buy signal
    if portfolio.holdings == 0 and sma20 > sma50:
        shares_to_buy = portfolio.cash / current_price
        portfolio.holdings = shares_to_buy
        portfolio.cash -= shares_to_buy * current_price
        portfolio.add_trade('buy', current_price, shares_to_buy, datetime.now().astimezone().isoformat(), shares_to_buy * current_price)
        
    # Sell signal
    elif portfolio.holdings > 0 and sma20 < sma50:
        sell_value = portfolio.holdings * current_price
        portfolio.add_trade('sell', current_price, portfolio.holdings, datetime.now().astimezone().isoformat(), sell_value)
        portfolio.cash += sell_value
        portfolio.holdings = 0

    current_value = float(portfolio.cash + (portfolio.holdings * current_price))

    timestamps = [utc_to_local(idx).strftime('%Y-%m-%d %H:%M') for idx in data.index]
    prices = data['Close'].values.flatten().tolist()
    sma20_values = [float(x) if not np.isnan(x) else None for x in data['SMA20'].values]
    sma50_values = [float(x) if not np.isnan(x) else None for x in data['SMA50'].values]

    response_data = {
        'portfolio_value': round(current_value, 2),
        'price': round(current_price, 2),
        'historical_prices': prices,
        'sma20_values': sma20_values,
        'sma50_values': sma50_values,
        'timestamps': timestamps,
        'holdings': round(float(portfolio.holdings), 6),
        'cash': round(float(portfolio.cash), 2),
        'trades': portfolio.trades,
        'buy_signals': [t for t in portfolio.trades if t['type'] == 'buy'],
        'sell_signals': [t for t in portfolio.trades if t['type'] == 'sell'],
        'strategy_description': get_strategy_description()
    }
    return jsonify(response_data)

# Backtesting Route (To be expanded based on requirements)
@api_bp.route('/backtest', methods=['POST'])
def backtest():
    try:
        ticker = request.form.get('ticker')  # Default to BTC-USD
        days = int(request.form.get('days', '5'))  # Default to 30 days
        
        # Reset portfolio for backtesting
        backtest_portfolio = {
            'cash': Config.INITIAL_CASH,
            'holdings': 0,
            'trades': []
        }
        
        # Fetch historical data for backtesting
        data = fetch_historical_data(ticker, period=f"{days}d", interval="5m")
        
        if data is None or data.empty:
            return {"error": "Historical data unavailable."}, 500
        
        # Calculate indicators
        data['SMA20'] = data['Close'].rolling(window=20).mean()
        data['SMA50'] = data['Close'].rolling(window=50).mean()
        
        # Simulate trading
        for i in range(50, len(data)):  # Start after SMA50 has enough data
            current_price = float(data['Close'].iloc[i])
            sma20 = float(data['SMA20'].iloc[i])
            sma50 = float(data['SMA50'].iloc[i])
            
            if backtest_portfolio['holdings'] == 0 and sma20 > sma50:  # Buy signal
                shares_to_buy = backtest_portfolio['cash'] / current_price
                backtest_portfolio['holdings'] = shares_to_buy
                backtest_portfolio['cash'] -= shares_to_buy * current_price
                backtest_portfolio['trades'].append({
                    'type': 'buy',
                    'price': current_price,
                    'amount': shares_to_buy,
                    'timestamp': data.index[i].isoformat(),
                    'value': shares_to_buy * current_price
                })
                
            elif backtest_portfolio['holdings'] > 0 and sma20 < sma50:  # Sell signal
                sell_value = backtest_portfolio['holdings'] * current_price
                backtest_portfolio['trades'].append({
                    'type': 'sell',
                    'price': current_price,
                    'amount': backtest_portfolio['holdings'],
                    'timestamp': data.index[i].isoformat(),
                    'value': sell_value
                })
                backtest_portfolio['cash'] += sell_value
                backtest_portfolio['holdings'] = 0
        
        # Convert timestamps in backtest trades
        for trade in backtest_portfolio['trades']:
            utc_dt = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
            trade['timestamp'] = utc_to_local(utc_dt).isoformat()
            
        # Calculate final portfolio value
        final_price = float(data['Close'].iloc[-1])
        final_value = backtest_portfolio['cash'] + (backtest_portfolio['holdings'] * final_price)
        
        return jsonify({
            'initial_value': Config.INITIAL_CASH,
            'final_value': round(final_value, 2),
            'return_percentage': round(((final_value - Config.INITIAL_CASH) / Config.INITIAL_CASH) * 100, 2),
            'number_of_trades': len(backtest_portfolio['trades']),
            'trades': backtest_portfolio['trades']
        })
        
    except Exception as e:
        print(f"Backtest error: {e}")
        return {"error": str(e)}, 500

@api_bp.route('/analyze', methods=['POST'])
def analyze():
    try:
        days = int(request.form.get('days', '5'))
        stop_loss = float(request.form.get('stop_loss', '5'))
        take_profit = float(request.form.get('take_profit', '5'))
        strategy_name = request.form.get('strategy', 'sma_cross')
        ticker = request.form.get('ticker')  # Default to BTC-USD


        # Create strategy (can be expanded for multiple strategies)
        if strategy_name == 'sma_cross':
            strategy = SMACrossStrategy(
                stop_loss_pct=stop_loss,
                take_profit_pct=take_profit
            )
        else:
            return jsonify({"error": "Invalid strategy"}), 400
            
        # Create backtester
        backtester = Backtester(strategy)
        
        # Get data and run backtest
        symbol = ticker  # For testing
        data = fetch_historical_data(symbol, days)
        
        if data is None or data.empty:
            return jsonify({"error": "No data available"}), 404
            
        result = backtester.run(data)
        result['symbol'] = symbol
        
        response_data = {
            'summary': {
                'total_profit': round(result['final_value'] - result['initial_value'], 2),
                'average_return_pct': result['return_pct'],
                'best_performer': symbol,
                'best_return_pct': result['return_pct'],
                'analyzed_pairs': 1
            },
            'results': [result]
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in analyze route: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/get_historical_data', methods=['POST'])
def get_historical_data():
    try:
        data = request.json
        symbol = data.get('symbol')
        days = int(data.get('days', 5))
        
        # Fetch historical data
        df = fetch_historical_data(symbol, days)
        
        if df is None or df.empty:
            return jsonify({"error": "No data available"}), 404
            
        # Calculate SMAs
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()
            
        # Convert NaN values to None (null in JSON)
        def clean_nans(x):
            return None if pd.isna(x) else float(x)
            
        # Prepare data for the chart
        response_data = {
            'timestamps': df.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'prices': [clean_nans(x) for x in df['Close'].tolist()],
            'sma20': [clean_nans(x) for x in df['SMA20'].tolist()],
            'sma50': [clean_nans(x) for x in df['SMA50'].tolist()]
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error getting historical data: {str(e)}")
        return jsonify({"error": str(e)}), 500
