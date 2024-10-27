from flask import Blueprint, render_template, jsonify, request
from models import portfolio
from utils import fetch_historical_data, utc_to_local, get_strategy_description
from config import Config
from datetime import datetime
import numpy as np

api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index():
    return render_template('index.html', initial_cash=Config.INITIAL_CASH)

@api_bp.route('/update', methods=['POST'])
def update():
    ticker = request.form.get('ticker', 'BTC-USD')
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
        ticker = request.form.get('ticker', 'BTC-USD')
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
 