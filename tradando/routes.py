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
from tradando.strategies.rsi import RSIStrategy
from tradando.strategies.macd import MACDStrategy

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
        data = request.get_json()
        days = int(data.get('days', '5'))
        stop_loss = float(data.get('stop_loss', '5'))
        take_profit = float(data.get('take_profit', '5'))
        strategies = data.get('strategies', ['sma_cross'])  # Now accepts multiple strategies
        tickers = data.get('tickers', [])

        if not tickers:
            return jsonify({"error": "No tickers selected"}), 400

        all_results = []
        total_profit = 0
        
        # Create strategy instances
        strategy_instances = {}
        for strategy_name in strategies:
            if strategy_name == 'sma_cross':
                strategy_instances[strategy_name] = SMACrossStrategy(
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit
                )
            elif strategy_name == 'rsi':
                strategy_instances[strategy_name] = RSIStrategy(
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit
                )
            elif strategy_name == 'macd':
                strategy_instances[strategy_name] = MACDStrategy(
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit
                )
            else:
                continue

        # Run analysis for each combination of ticker and strategy
        for symbol in tickers:
            data = fetch_historical_data(symbol, days)
            
            if data is None or data.empty:
                continue
                
            for strategy_name, strategy in strategy_instances.items():
                backtester = Backtester(strategy)
                result = backtester.run(data)
                result['symbol'] = symbol
                result['strategy'] = strategy.name
                result['strategy_key'] = strategy_name
                all_results.append(result)
                total_profit += (result['final_value'] - result['initial_value'])

        if not all_results:
            return jsonify({"error": "No data available for selected pairs"}), 404

        # Sort results by return percentage
        all_results.sort(key=lambda x: x['return_pct'], reverse=True)
        
        # Enhanced summary statistics
        strategy_stats = {}
        for strategy_name in strategies:
            strategy_results = [r for r in all_results if r['strategy_key'] == strategy_name]
            if strategy_results:
                avg_return = sum(r['return_pct'] for r in strategy_results) / len(strategy_results)
                best_trade = max(strategy_results, key=lambda x: x['return_pct'])
                worst_trade = min(strategy_results, key=lambda x: x['return_pct'])
                
                strategy_stats[strategy_name] = {
                    'avg_return': round(avg_return, 2),
                    'best_trade': {
                        'symbol': best_trade['symbol'],
                        'return': round(best_trade['return_pct'], 2)
                    },
                    'worst_trade': {
                        'symbol': worst_trade['symbol'],
                        'return': round(worst_trade['return_pct'], 2)
                    },
                    'total_trades': sum(r['n_trades'] for r in strategy_results),
                    'profit': sum(r['final_value'] - r['initial_value'] for r in strategy_results)
                }
        
        response_data = {
            'summary': {
                'total_profit': round(total_profit, 2),
                'average_return_pct': round(sum(r['return_pct'] for r in all_results) / len(all_results), 2),
                'best_performer': all_results[0]['symbol'],
                'best_return_pct': round(all_results[0]['return_pct'], 2),
                'analyzed_pairs': len(set(r['symbol'] for r in all_results)),
                'strategy_stats': strategy_stats
            },
            'results': all_results
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
