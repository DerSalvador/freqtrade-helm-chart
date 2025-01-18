import argparse
from binance.client import Client
from binance.helpers import round_step_size

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

#def calculate_target_price(entry_price, profit_percentage, loss_percentage, position_amt, tick_size):
#    """Calculate the target price and stop loss price for the order and round to the nearest tick size."""
#    if position_amt > 0:  # Long position
#        target_price = entry_price * (1 + profit_percentage)
#        stop_loss_price = entry_price * (1 - loss_percentage)
#    elif position_amt < 0:  # Short position
#        target_price = entry_price * (1 - profit_percentage)
#        stop_loss_price = entry_price * (1 + loss_percentage)
#    else:
#        raise ValueError("Position amount is zero, no active position to close.")

    # Round to the nearest tick size
#    return round(target_price / tick_size) * tick_size, round(stop_loss_price / tick_size) * tick_size

def calculate_target_price(entry_price, profit_percentage, loss_percentage, position_amt, tick_size):
    # Calculate target and stop loss prices
    # Round the stop loss price to the nearest tick size
    if position_amt > 0:  # Long position
        target_price = entry_price * (1 + profit_percentage)
        stop_loss_price = round_step_size(entry_price * (1 - loss_percentage), tick_size)
    elif position_amt < 0:  # Short position
        target_price = entry_price * (1 - profit_percentage)
        stop_loss_price = round_step_size(entry_price * (1 + loss_percentage), tick_size)
    else:
        raise ValueError("Position amount is zero, no active position to close.")
    print(f"position_amt: {position_amt},  stoploss: {abs(stop_loss_price)}, entry: {entry_price}")
    print(f"target_price: {target_price}")
    return round(target_price / tick_size) * tick_size, stop_loss_price

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


def place_order(symbol, position_amt, target_price, stop_loss_price, entry_price):
    """Place separate orders for take-profit and stop-loss."""
    side = 'SELL' if position_amt > 0 else 'BUY'
    quantity = abs(position_amt)  # Always positive for order quantity

    # Get the current market price
    try:
        market_price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
    except Exception as e:
        print(f"Error fetching market price: {e}")
        return

    # Adjust target and stop-loss prices if necessary
    tick_size = get_tick_size(symbol)

    #if side == 'SELL':
    #    if target_price <= market_price:
    #        target_price = market_price + tick_size
    #    if stop_loss_price >= market_price:
    #        stop_loss_price = market_price - tick_size
    #else:  # side == 'BUY'
    #    if target_price >= market_price:
    #        target_price = market_price - tick_size
    #    if stop_loss_price <= market_price:
    #        stop_loss_price = market_price + tick_size

    try:
        # Place take-profit limit order
        target_order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='LIMIT',
            timeInForce='GTC',  # Good Till Cancelled
            quantity=quantity,
            price=round(target_price, 2),  # Take-profit price
            reduceOnly=True  # Ensure the order is only for reducing the position
        )
        print(f"Take-Profit Order successfully placed: {target_order}")

        # Place stop-loss market order
        print(f"Stoploss price: {stop_loss_price}")
        print("SL Order")
        order = client.futures_create_order(symbol=symbol, 
                                            side='BUY' if position_amt < 0 else 'SELL',
                                            type='STOP_MARKET',
                                            # side='SELL' if side == 'BUY' else 'SELL', #side=client.SIDE_SELL,  
                                            newClientOrderId= "_SL",
                                            quantity=quantity, 
                                            # type=client.FUTURE_ORDER_TYPE_STOP, 
                                            stopPrice=round(stop_loss_price, 2), 
                                            #price=round(target_price, 2),  
                                            timeInForce="GTC", 
                                            reduceOnly = True)
        print(order)

       # stop_loss_order = client.futures_create_order(
      #      symbol=symbol,
     #       side='SELL' if side == 'BUY' else 'BUY',
     #       type='STOP_MARKET',  # Stop-loss market order
     #       quantity=quantity,
     #       stopPrice=round(stop_loss_price, 2)  # Stop-loss trigger price
     #   )
     #   print(f"Stop-Loss Order successfully placed: {stop_loss_order}")

    except Exception as e:
        print(f"Error placing orders: {e}")

def get_liquidation_price(symbol):
    """Fetch the liquidation price for the given symbol."""
    try:
        positions = client.futures_position_information()
        position = next((p for p in positions if p['symbol'] == symbol), None)
        if not position:
            raise ValueError(f"No active position found for {symbol}.")

        liquidation_price = float(position['liquidationPrice'])
        return liquidation_price
    except Exception as e:
        raise ValueError(f"Error fetching liquidation price: {e}")

def main():
    parser = argparse.ArgumentParser(description="Place a Binance order with 10% profit target and stoploss.")
    parser.add_argument('symbol', type=str, help="The trading pair symbol, e.g., LINKUSDT")
    parser.add_argument('api_key', type=str, help="Your Binance API key")
    parser.add_argument('api_secret', type=str, help="Your Binance API secret")
    parser.add_argument('profitpct', type=str, help="Take Profit percent, 0.1 = 10%")
    parser.add_argument('stoplosspct', type=str, help="Stoploss percent, 0.1 = 10%")
    args = parser.parse_args()

    api_key = args.api_key
    api_secret = args.api_secret
    profitpct = float(args.profitpct)
    stoplosspct = float(args.stoplosspct)
    loss_percentage = stoplosspct # 10% stoploss
    symbol = args.symbol

    client = Client(api_key, api_secret)

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
        # delete_existing_orders(symbol)

        # Check for existing open orders
        if check_existing_orders(symbol):
            print(f"There are already open orders for {symbol}. No new order will be placed.")
            return

        # Get the tick size for the symbol
        tick_size = get_tick_size(symbol)

        # Calculate the target price for a 10% profit and stop loss price
        print(f"entry_price: {entry_price}, profitpct: {profitpct}, loss_percentage: {loss_percentage}, position_amt: {position_amt}, tick_size: {tick_size}")
        # lp = get_liquidation_price(symbol)
        target_price, stop_loss_price = calculate_target_price(entry_price, profitpct, loss_percentage,  position_amt, tick_size)

        print(f"stop_loss_price: {stop_loss_price}")
        # Place the order with target and stop loss
        place_order(symbol, position_amt, target_price, stop_loss_price, entry_price)

    except Exception as e:
        print(f"Error fetching position or placing order: {e}")

if __name__ == "__main__":
    main()

