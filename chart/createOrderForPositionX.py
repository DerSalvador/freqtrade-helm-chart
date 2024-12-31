import argparse
from binance.client import Client

# Initialize the Binance client
api_key = 'b3r35QxZ6z8PKS7vFSoJztdTwI4mQJ1owCBmp08pjKj1FQWhFFxvFZ9yqStfpGwm'
api_secret = 'tHwYon2naTO6111rCo3c6yv84szDFFsaovNnf9eUY9FYl5Ub07c9IuZ8WTZx4uov'
client = Client(api_key, api_secret)



def calculate_target_price(entry_price, profit_percentage, position_amt):
    """Calculate the target price for the order."""
    if position_amt > 0:  # Long position
        return entry_price * (1 + profit_percentage)
    elif position_amt < 0:  # Short position
        return entry_price * (1 - profit_percentage)
    else:
        raise ValueError("Position amount is zero, no active position to close.")

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
            price=round(target_price, 2)  # Adjust to 4 decimal places
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

        # Calculate the target price for a 10% profit
        target_price = calculate_target_price(entry_price, 0.1, position_amt)

        # Place the order
        place_order(symbol, position_amt, target_price)

    except Exception as e:
        print(f"Error fetching position or placing order: {e}")

if __name__ == "__main__":
    main()

