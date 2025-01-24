import argparse
from binance.client import Client
from binance.helpers import round_step_size
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT
import uuid

# Initialize the Binance client
api_key = 'b3r35QxZ6z8PKS7vFSoJztdTwI4mQJ1owCBmp08pjKj1FQWhFFxvFZ9yqStfpGwm'
api_secret = 'tHwYon2naTO6111rCo3c6yv84szDFFsaovNnf9eUY9FYl5Ub07c9IuZ8WTZx4uov'


# Replace with your Binance API key and secret
API_KEY = api_key
API_SECRET = api_secret

client = Client(API_KEY, API_SECRET)

def fetch_open_stop_loss_orders():
    try:
        orders = client.futures_get_open_orders()
        sl_orders = [
            order for order in orders
            if order['type'] == 'STOP_MARKET' and order['clientOrderId'].startswith("SL_")
        ]
        return sl_orders
    except Exception as e:
        print(f"Error fetching stop loss orders: {e}")
        return []

def get_current_position(symbol):
    try:
        positions = client.futures_account()['positions']
        for position in positions:
            if position['symbol'] == symbol and float(position['positionAmt']) != 0:
                return {
                    'symbol': position['symbol'],
                    'positionAmt': float(position['positionAmt']),
                    'entryPrice': float(position['entryPrice'])
                }
        return None
    except Exception as e:
        print(f"Error fetching position: {e}")
        return None

def close_position(symbol, position_qty):
    try:
        side = SIDE_SELL if position_qty > 0 else SIDE_BUY
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=abs(position_qty)
        )
        print(f"Closed position for {symbol}: {order}")
    except Exception as e:
        print(f"Error closing position for {symbol}: {e}")

def main():
    # Fetch all stop loss orders identified by clientOrderId
    sl_orders = fetch_open_stop_loss_orders()

    if not sl_orders:
        print("No stop loss orders found.")
        return

    for sl_order in sl_orders:
        symbol = sl_order['symbol']
        stop_price = float(sl_order['stopPrice'])

        # Fetch the current position for the symbol
        position = get_current_position(symbol)
        if not position:
            print(f"No open position found for {symbol}, skipping.")
            continue

        # Fetch current market price
        try:
            ticker = client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
        except Exception as e:
            print(f"Error fetching market price for {symbol}: {e}")
            continue

        # Check if stop loss price has been reached
        if (position['positionAmt'] > 0 and current_price <= stop_price) or \
           (position['positionAmt'] < 0 and current_price >= stop_price):
            print(f"Stop loss triggered for {symbol}. Current Price: {current_price}, Stop Price: {stop_price}")

            # Close the position
            close_position(symbol, position['positionAmt'])

if __name__ == "__main__":
    main()


