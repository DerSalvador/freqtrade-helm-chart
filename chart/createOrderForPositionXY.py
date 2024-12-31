import argparse
from binance.client import Client

# Initialize the Binance client
api_key = 'b3r35QxZ6z8PKS7vFSoJztdTwI4mQJ1owCBmp08pjKj1FQWhFFxvFZ9yqStfpGwm'
api_secret = 'tHwYon2naTO6111rCo3c6yv84szDFFsaovNnf9eUY9FYl5Ub07c9IuZ8WTZx4uov'
client = Client(api_key, api_secret)

def get_tick_size(symbol):
    """Fetch the tick size for the given symbol."""
    try:
        exchange_info = client.futures_exchange_info()
        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
        if not symbol_info:
            raise ValueError(f"Symbol {symbol} not found in exchange info.")

        for filter in symbol_info['filters']:
            if filter['filterType'] == 'PRICE_FILTER':
                return float(filter['tickSize'])
        raise ValueError(f"Tick size not found for symbol {symbol}.")
    except Exception as e:
        raise ValueError(f"Error fetching tick size: {e}")

def calculate_target_price(entry_price, profit_percentage, position_amt, tick_size):
    """Calculate the target price for the order and round to the nearest tick size."""
    if position_amt > 0:  # Long position
        raw_price = entry_price * (1 + profit_percentage)
    elif position_amt < 0:  # Short position
        raw_price = entry_price * (1 - profit_percentage)
    else:
        raise ValueError("Position amount is zero, no active position to close.")

    # Round to the nearest tick size
    return round(raw_price / tick_size) * tick_size

def delete_existing_orders(symbol):
    """Delete all existing open orders for the symbol."""
    try:
        open_orders = client.futures_get_open_orders(symbol=symbol)
        for order in open_orders:
            client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
        print(f"All existing orders for {symbol} have been deleted.")
    except Exception as e:
        print(f"Error deleting open orders: {e}")

def check_existing_orders(symbol):
    """Check if there are existing open orders for the symbol."""
    try:
        open_orders = client.futures_get_open_orders(symbol=symbol)
        return len(open_orders) > 0
    except Exception as e:
        print(f"Error checking open orders: {e}")
        return False

def place_order(symbol, position_amt, target_price):
    """Place the appropriate order based on position_amt."""
    side = 'SELL' if position_amt > 0 else 'BUY'
    quantity = abs(position_amt)  # Always positive for order quantity

    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='LIMIT',
            timeInForce='GTC',  # Good Till Cancelled
            quantity=quantity,
            price=round(target_price, 8)  # Adjust precision as needed
        )
        print(f"Order successfully placed: {order}")
    except Exception as e:
        print(f"Error placing order: {e}")

def main():
    parser = argparse.ArgumentParser(description="Place a Binance order with 10% profit target.")
    parser.add_argument('symbol', type=str, help="The trading pair symbol, e.g., LINKUSDT")
    args = parser.parse_args()

    symbol = args.symbol

    # Fetch current position for the symbol
    try:
        positions = client.futures_position_information()
        position = next((p for p in positions if p['symbol'] == symbol), None)

        if not position:
            print(f"No active position found for {symbol}.")
            return

        position_amt = float(position['positionAmt'])
        entry_price = float(position['entryPrice'])

        if position_amt == 0:
            print(f"No active position to close for {symbol}.")
            return

        # Delete existing open orders
        delete_existing_orders(symbol)

        # Check for existing open orders
        if check_existing_orders(symbol):
            print(f"There are already open orders for {symbol}. No new order will be placed.")
            return



        # Get the tick size for the symbol
        tick_size = get_tick_size(symbol)

        # Calculate the target price for a 10% profit
        target_price = calculate_target_price(entry_price, 0.1, position_amt, tick_size)

        # Place the order
        place_order(symbol, position_amt, target_price)

    except Exception as e:
        print(f"Error fetching position or placing order: {e}")

if __name__ == "__main__":
    main()

