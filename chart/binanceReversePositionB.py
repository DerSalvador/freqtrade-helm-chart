import argparse
import logging
import time
from coinGeckoAPI import CoinGeckoAPI
import pandas as pd
from tabulate import tabulate
from binance.client import Client
from binance.exceptions import BinanceAPIException
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
coinGeckoAPI = CoinGeckoAPI()

def getPricePrecision(symbol):
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        response = requests.get(url)
        data = response.json()
        for pos in data['symbols']:
            print(f"Price Precision: {pos['symbol']} {pos['pricePrecision']}")
            if pos['symbol'] == symbol:
                return pos['pricePrecision']

def getQuantityPrecision(symbol):
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        response = requests.get(url)
        data = response.json()
        for pos in data['symbols']:
            print(f"Quantity Precision: {pos['symbol']} {pos['quantityPrecision']}")            
            if pos['symbol'] == symbol:
                return pos['quantityPrecision']

def get_open_positions(client):
    """Fetches all open positions from Binance Futures and filters non-zero positions."""
    try:
        positions = client.futures_position_information()
        open_positions = [pos for pos in positions if float(pos["positionAmt"]) != 0]
        return open_positions
    except BinanceAPIException as e:
        logging.error(f"API Error: {e}")
        return []

def calculate_pnl(entry_price, mark_price):
    """Calculates unrealized PNL percentage."""
    return ((mark_price - entry_price) / entry_price) * 100

def close_position(client, position):
    """Closes an open position."""
    symbol = position["symbol"]
    qty = abs(float(position["positionAmt"]))

    if qty == 0:
        logging.info(f"No open position for {symbol}")
        return

    side = "SELL" if float(position["positionAmt"]) > 0 else "BUY"

    logging.info(f"Closing position: {side} {qty} {symbol}")
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=qty
        )
        return order
    except BinanceAPIException as e:
        logging.error(f"Error closing position: {e}")

def reverse_position(client, position):
    """Reverses an open position."""
    symbol = position["symbol"]
    qty = abs(float(position["positionAmt"]))

    if qty == 0:
        logging.info(f"No open position for {symbol}")
        return

    close_position(client, position)

    new_side = "BUY" if float(position["positionAmt"]) < 0 else "SELL"

    logging.info(f"Reversing position: {new_side} {qty} {symbol}")
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=new_side,
            type="MARKET",
            quantity=qty
        )
        return order
    except BinanceAPIException as e:
        logging.error(f"Error reversing position: {e}")

def buy_btc_futures():
    """Place a market order to buy BTC futures with 500 USDT."""
    client.futures_change_leverage(symbol='BTCUSDT', leverage=50)

    # Get the current BTCUSDT price
    ticker = client.futures_symbol_ticker(symbol='BTCUSDT')
    current_price = float(ticker['price'])

    # Calculate the quantity of BTC to buy with 100 USDT
    quantity = 500 / current_price

    # Place a market order
    order = client.futures_create_order(
        symbol='BTCUSDT',
        side="BUY",
        type="MARKET",
        quantity=round(quantity, 2)  # Adjust precision if needed
    )
    print(f"Order placed: {order}")

#def get_top_5_futures_pairs():
#    """Fetches the top 5 best-performing futures pairs for long trading."""
#    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
#    try:
#        response = requests.get(url)
#        data = response.json()
#        sorted_pairs = sorted(data, key=lambda x: float(x['priceChangePercent']), reverse=True)
#        return sorted_pairs[:5]
#    except Exception as e:
#        logging.error(f"Error fetching top futures pairs: {e}")
#        return []

def get_top_5_futures_pairs(client):
    """Fetches the top 5 best-performing futures pairs for long trading that are not settling."""
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        response = requests.get(url)
        data = response.json()

        # Filter out pairs that are settling
        exchange_info = client.futures_exchange_info()
        valid_symbols = {s['symbol'] for s in exchange_info['symbols'] if s['contractType'] == 'PERPETUAL' and s['status'] != 'SETTLING'}
        filtered_data = [d for d in data if d['symbol'] in valid_symbols]

        # Sort by price change percentage
        sorted_pairs = sorted(filtered_data, key=lambda x: float(x['priceChangePercent']), reverse=True)
        return sorted_pairs[:5]
    except Exception as e:
        logging.error(f"Error fetching top futures pairs: {e}")
        return []

def get_symbol_info(client, symbol):
    """Fetches symbol information including precision details."""
    try:
        exchange_info = client.futures_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                return s
        logging.error(f"Symbol {symbol} not found.")
        return None
    except BinanceAPIException as e:
        logging.error(f"Error fetching symbol info: {e}")
        return None

def place_buy_order_if_no_position(client, symbol):
    """Places a buy order if there's no open position for the given symbol."""
    open_positions = get_open_positions(client)
    open_symbols = [pos['symbol'] for pos in open_positions]

    if symbol in open_symbols:
        logging.info(f"Position already open for {symbol}, skipping buy order.")
        return


    logging.info(f"Placing buy order for {symbol}")
    try:
        # Fetch symbol information
        symbol_info = get_symbol_info(client, symbol)
        print(symbol_info)
        if not symbol_info:
            return
        client.futures_change_leverage(symbol=symbol, leverage=50)
        ticker = client.futures_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
        quantity = round(500 / current_price, getQuantityPrecision(symbol))  # Adjust the USDT amount as needed

        order = client.futures_create_order(
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quantity=round(quantity, getPricePrecision(symbol))
        )
        logging.info(f"Order placed for {symbol}: {order}")
    except BinanceAPIException as e:
        logging.error(f"Error placing buy order for {symbol}: {e}")

def monitor_and_manage(client, loss_threshold, profit_threshold):
    """Monitors positions, places buy orders for top pairs, reverses on loss, and closes on profit."""
    while True:
        open_positions = get_open_positions(client)

        #if not open_positions:
        #logging.info("No open positions found. Fetching top 5 futures pairs.")
        # buy_btc_futures():
        top_5_pairs = get_top_5_futures_pairs(client)
        place_buy_order_if_no_position(client, "BTCUSDT")
        for pair in top_5_pairs:
            place_buy_order_if_no_position(client, pair['symbol'])
            time.sleep(5)
        # continue

        position_data = []

        for position in open_positions:
            symbol = position["symbol"]
            entry_price = float(position["entryPrice"])
            mark_price = float(position["markPrice"])
            position_amt = float(position["positionAmt"])
            pnl_percentage = calculate_pnl(entry_price, mark_price)

            loss_stop_price = entry_price * ((100 - loss_threshold) / 100 if position_amt > 0 else (100 + loss_threshold) / 100)
            profit_take_price = entry_price * ((100 + profit_threshold) / 100 if position_amt > 0 else (100 - profit_threshold) / 100)

            position_data.append([
                symbol, entry_price, mark_price, f"{pnl_percentage:.2f}%", f"{loss_stop_price:.2f}", f"{profit_take_price:.2f}"
            ])

            # Check if loss threshold is reached → Reverse position
            if pnl_percentage <= -loss_threshold:
                logging.warning(f"Loss reached {pnl_percentage:.2f}% for {symbol}. Reversing position!")
                reverse_position(client, position)

            # Check if profit threshold is reached → Close position
            elif pnl_percentage >= profit_threshold:
                logging.info(f"Profit reached {pnl_percentage:.2f}% for {symbol}. Closing position!")
                close_position(client, position)

        df = pd.DataFrame(position_data, columns=["Symbol", "Entry Price", "Current Price", "PnL (%)", f"{loss_threshold}% Loss Price", f"{profit_threshold}% Profit Price"])
        print(tabulate(df, headers="keys", tablefmt="pretty"))

        time.sleep(5)  # Check positions every 5 seconds

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Binance Futures Position Manager")
    parser.add_argument("--apikey", required=True, help="Your Binance API Key")
    parser.add_argument("--apisecret", required=True, help="Your Binance API Secret")
    parser.add_argument("--loss", type=float, default=5.0, help="Loss percentage to trigger position reversal (default: 5%)")
    parser.add_argument("--profit", type=float, default=6.0, help="Profit percentage to trigger position closure (default: 6%)")

    args = parser.parse_args()

    coinGeckoAPI.coinGeckoAPIKey = "CG-AgEZRgMf3iLk1S8CwyCKp7N3"
    coinGeckoAPI.apikey = args.apikey
    coinGeckoAPI.apisecret = args.apisecret
    bias = coinGeckoAPI.get_file_sentiment(None, args.apikey, args.apisecret)
    print(f"Market bias is {bias}")
    client = Client(args.apikey, args.apisecret)

    logging.info(f"Monitoring positions for {args.loss}% loss threshold and {args.profit}% profit threshold...")
    monitor_and_manage(client, args.loss, args.profit)

