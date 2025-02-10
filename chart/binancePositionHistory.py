import sys
from binance.client import Client
from datetime import datetime, timedelta

def get_positions_with_negative_unrealized_profit(api_key, api_secret):
    client = Client(api_key, api_secret)

    # Get position history
    positions = client.futures_account_trades(symbol="XLMUSDT")
    # positions = client.futures_coin_historical_trades(symbol="BTCUSD_PERP")
    # print(positions)
    # Filter positions with unrealized profit less than zero in the last 40 minutes
    filtered_positions = []
    current_time = datetime.now()
    for position in positions:
        if 'realizedPnl' in position:
            position_time = datetime.fromtimestamp(position['time'] / 1000)
            if current_time - position_time <= timedelta(minutes=4200) and float(position['realizedPnl']) < 0:
                filtered_positions.append(position)

    return filtered_positions

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python program.py <api_key> <api_secret>")
        sys.exit(1)

    api_key = sys.argv[1]
    api_secret = sys.argv[2]

    positions = get_positions_with_negative_unrealized_profit(api_key, api_secret)
    print(positions)

