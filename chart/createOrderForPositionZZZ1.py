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

def get_all_positions():
    try:
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

def place_take_profit(symbol, position_qty, take_profit_price):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL if position_qty > 0 else SIDE_BUY,
            type=ORDER_TYPE_LIMIT,
            quantity=abs(position_qty),
            price=take_profit_price,
            newClientOrderId=generate_client_order_id(f"TP"),
            timeInForce='GTC',
            reduceOnly=True
        )
        print(f"Take Profit order placed for {symbol}: {order}")
    except Exception as e:
        print(f"Error placing take profit for {symbol}: {e}")

def generate_client_order_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def place_stop_loss(symbol, position_qty, stop_loss_price):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL if position_qty > 0 else SIDE_BUY,
            type='STOP_MARKET',
            quantity=abs(position_qty),
            newClientOrderId=generate_client_order_id(f"SL"),
            stopPrice=stop_loss_price,
            reduceOnly=True
        )
        print(f"Stop Loss order placed for {symbol}: {order}")
    except Exception as e:
        print(f"Error placing stop loss for {symbol}: {e}")

def cancel_all_orders():
    try:
        orders = client.futures_get_open_orders()
        for order in orders:
            client.futures_cancel_order(symbol=order['symbol'], orderId=order['orderId'])
        print("All existing orders have been canceled.")
    except Exception as e:
        print(f"Error canceling orders: {e}")

def main():
    risk_percentage = 10  # Stop loss percentage
    reward_percentage = 20  # Take profit percentage
    # cancel_all_orders()
    # Fetch all active positions
    active_positions = get_all_positions()
    print(active_positions)
    if not active_positions:
        print("No active positions found.")
        return

    for position in active_positions:
        symbol = position['symbol']
        position_qty = position['positionAmt']
        entry_price = position['entryPrice']

        # Calculate take profit and stop loss prices
        if position_qty > 0:  # Long position
            take_profit_price = entry_price * (1 + reward_percentage / 100)
            stop_loss_price = entry_price * (1 - risk_percentage / 100)
        else:  # Short position
            take_profit_price = entry_price * (1 - reward_percentage / 100)
            stop_loss_price = entry_price * (1 + risk_percentage / 100)

        print(f"{symbol} | Qty: {position_qty} | Entry: {entry_price} | TP: {take_profit_price} | SL: {stop_loss_price}")

        # Place take profit and stop loss orders
        place_take_profit(symbol, position_qty, round(take_profit_price, 2))
        place_stop_loss(symbol, position_qty, round(stop_loss_price, 2))

if __name__ == "__main__":
    main()

