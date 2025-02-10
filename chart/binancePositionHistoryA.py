import sys
from binance.client import Client
from datetime import datetime, timedelta

def get_all_positions():
    try:
        client = Client(api_key, api_secret)
        # Fetch all account positions
        account_info = client.futures_account()
        positions = account_info['positions']
        # Filter positions with non-zero amounts
        active_positions = [
            {
                'symbol': position['symbol'],
                'positionAmt': float(position['positionAmt']),
                'entryPrice': float(position['entryPrice'])
            }
            for position in positions if float(position['positionAmt']) != 0
        ]
        return active_positions
    except Exception as e:
        print(f"Error fetching positions: {e}")
        return []

def get_positions_with_negative_unrealized_profit(api_key, api_secret):
    client = Client(api_key, api_secret)

    # Get all positions with positionAmt not equal to zero
    account_info = client.futures_account()
    # positions = [position for position in account_info['positions'] if float(position['positionAmt']) != 0]
    positions = get_all_positions()
    # Iterate through positions
    filtered_positions = []
    for position in positions:
        symbol = position['symbol']
        
        # Get position history for the current symbol
        position_history = client.futures_account_trades(symbol=symbol)
        
        # Filter positions with unrealized profit less than zero in the last 40 minutes
        current_time = datetime.now()
        for trade in position_history:
            if 'realizedPnl' in trade:
                trade_time = datetime.fromtimestamp(trade['time'] / 1000)
                if current_time - trade_time <= timedelta(minutes=40) and float(trade['realizedPnl']) < 0:
                    filtered_positions.append(trade)

    return filtered_positions

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python program.py <api_key> <api_secret>")
        sys.exit(1)

    api_key = sys.argv[1]
    api_secret = sys.argv[2]

    positions = get_positions_with_negative_unrealized_profit(api_key, api_secret)
    print(positions)

