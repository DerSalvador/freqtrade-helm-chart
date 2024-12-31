from binance.client import Client

# Initialize the Binance client
api_key = 'b3r35QxZ6z8PKS7vFSoJztdTwI4mQJ1owCBmp08pjKj1FQWhFFxvFZ9yqStfpGwm'
api_secret = 'tHwYon2naTO6111rCo3c6yv84szDFFsaovNnf9eUY9FYl5Ub07c9IuZ8WTZx4uov'
client = Client(api_key, api_secret)


# Define the position details
symbol = 'LINKUSDT'
position_amt = 142.19  # Short position
target_price = 21.208 * 1.1  # 10% profit target
quantity = abs(position_amt)  # Convert positionAmt to positive for the order

# Place a limit order to close the position with a 10% profit
try:
    order = client.futures_create_order(
        symbol=symbol,
        side='SELL',  # Buy to close the short position
        type='LIMIT',
        timeInForce='GTC',  # Good Till Cancelled
        quantity=quantity,
        price=round(target_price, 2)  # Round the target price to 4 decimals
    )
    print("Order successfully placed:", order)
except Exception as e:
    print("Error placing order:", e)

