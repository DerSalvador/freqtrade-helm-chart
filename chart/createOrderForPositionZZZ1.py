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

def check_stop_market_exists(symbol):
    try:
        # Fetch open orders for the symbol
        orders = client.futures_get_open_orders(symbol=symbol)
        for order in orders:
            if order['type'] == 'STOP_MARKET':
                print(f"Stop market order already exists for {symbol}. Skipping...")
                return True
        return False
    except Exception as e:
        print(f"Error checking for existing stop market order: {e}")
        return True

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

def generate_client_order_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def get_symbol_tick_size(symbol):
    """Fetch the tick size for the symbol."""
    try:
        exchange_info = client.futures_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        return float(f['tickSize'])
        raise ValueError(f"Tick size not found for symbol: {symbol}")
    except Exception as e:
        print(f"Error fetching tick size for {symbol}: {e}")
        return None

def place_take_profit(symbol, position_qty, take_profit_price):
    try:
        tick_size = get_symbol_tick_size(symbol)
        if not tick_size:
            print(f"Unable to fetch tick size for {symbol}. Skipping take profit order.")
            return

        rounded_price = round_step_size(take_profit_price, tick_size)
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL if position_qty > 0 else SIDE_BUY,
            type=ORDER_TYPE_LIMIT,
            quantity=abs(position_qty),
            price=rounded_price,
            newClientOrderId=generate_client_order_id(f"TP"),
            timeInForce='GTC',
            reduceOnly=True
        )
        print(f"Take Profit order placed for {symbol}: {order}")
    except Exception as e:
        print(f"Error placing take profit for {symbol}: {e}")

def place_stop_loss(symbol, position_qty, stop_loss_price):
    try:
        tick_size = get_symbol_tick_size(symbol)
        if not tick_size:
            print(f"Unable to fetch tick size for {symbol}. Skipping stop loss order.")
            return

        rounded_price = round_step_size(stop_loss_price, tick_size)
        if check_stop_market_exists(symbol):
            return

        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL if position_qty > 0 else SIDE_BUY,
            type='STOP_MARKET',
            quantity=abs(position_qty),
            newClientOrderId=generate_client_order_id(f"SL"),
            stopPrice=rounded_price,
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

#def cancel_all_orders():
#    try:
#        orders = client.futures_get_open_orders()
#        for order in orders:
#            if order['type'] == 'STOP_MARKET':
#                client.futures_cancel_order(symbol=order['symbol'], orderId=order['orderId'])
#                print(f"Canceled STOP_MARKET order: {order}")
#        print("All existing STOP_MARKET orders have been canceled.")
#    except Exception as e:
#        print(f"Error canceling STOP_MARKET orders: {e}")

def main():
    risk_percentage = 0.2  # Stop loss percentage
    reward_percentage = 0.3  # Take profit percentage
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

