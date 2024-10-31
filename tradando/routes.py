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
    try:
        ticker = request.form.get('ticker')
        data = fetch_historical_data(ticker)
        
        if data is None or data.empty:
            return {"error": "Price data unavailable."}, 500

        strategy = SMACrossStrategy()
        backtester = Backtester(strategy)
        result = backtester.run(data)
        
        # Format response with current portfolio state
        response_data = {
            'portfolio_value': round(result['final_value'], 2),
            'price': round(float(data['Close'].iloc[-1]), 2),
            'holdings': round(result['holdings'], 6),
            'cash': round(result['cash'], 2),
            'trades': result['trades'],
            'strategy_description': get_strategy_description()
        }
        
        return jsonify(response_data)
    except Exception as e:
        return {"error": str(e)}, 500

@api_bp.route('/backtest', methods=['POST'])
def backtest():
    try:
        ticker = request.form.get('ticker')
        days = int(request.form.get('days', '5'))
        
        data = fetch_historical_data(ticker, days)
        if data is None or data.empty:
            return {"error": "Historical data unavailable."}, 500
            
        strategy = SMACrossStrategy()
        backtester = Backtester(strategy)
        result = backtester.run(data)
        
        return jsonify(result)
    except Exception as e:
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
