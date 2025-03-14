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
sleep = 5

def getPricePrecision(symbol):
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    for pos in data['symbols']:
        if pos['symbol'] == symbol:
            return pos['pricePrecision']

def getQuantityPrecision(symbol):
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    for pos in data['symbols']:
        if pos['symbol'] == symbol:
            return pos['quantityPrecision']

def get_open_positions(client):
    try:
        time.sleep(sleep)
        positions = client.futures_position_information()
        open_positions = [pos for pos in positions if float(pos["positionAmt"]) != 0]
        return open_positions
    except BinanceAPIException as e:
        logging.error(f"API Error: {e}")
        return []

def calculate_pnl(entry_price, mark_price):
    return ((mark_price - entry_price) / entry_price) * 100

def close_position(client, position):
    symbol = position["symbol"]
    qty = abs(float(position["positionAmt"]))

    if qty == 0:
        logging.info(f"No open position for {symbol}")
        return

    side = "SELL" if float(position["positionAmt"]) > 0 else "BUY"

    logging.info(f"Closing position: {side} {qty} {symbol}")
    try:
        time.sleep(sleep)
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
    symbol = position["symbol"]
    qty = abs(float(position["positionAmt"]))

    if qty == 0:
        logging.info(f"No open position for {symbol}")
        return

    close_position(client, position)

    new_side = "BUY" if float(position["positionAmt"]) < 0 else "SELL"

    logging.info(f"Reversing position: {new_side} {qty} {symbol}")
    try:
        time.sleep(sleep)
        order = client.futures_create_order(
            symbol=symbol,
            side=new_side,
            type="MARKET",
            quantity=qty
        )
        return order
    except BinanceAPIException as e:
        logging.error(f"Error reversing position: {e}")

def get_trade_history(client, symbol):
    try:
        time.sleep(sleep)
        trades = client.futures_account_trades(symbol=symbol)
        return trades
    except BinanceAPIException as e:
        logging.error(f"Error fetching trade history for {symbol}: {e}")
        return []

def has_recent_loss(client, symbol, hours=0.2):
    try:
        trades = get_trade_history(client, symbol)
    except Exception as e:
        logging.error(f"Failed to retrieve trade history for {symbol}: {e}")
        return False

    if not trades:
        logging.info(f"No trades found for {symbol}.")
        return False

    trades = sorted(trades, key=lambda x: x['time'], reverse=True)
    latest_trade = trades[0]

    if float(latest_trade['realizedPnl']) > 0:
        logging.info(f"Latest trade for {symbol} is profitable with PnL {latest_trade['realizedPnl']}. No recent loss reported.")
        return False

    current_time = time.time() * 1000
    cutoff_time = current_time - (hours * 3600 * 1000)

    for trade in trades:
        if trade['time'] >= cutoff_time and float(trade['realizedPnl']) < 0 and trade['symbol'] == symbol:
            logging.info(f"Recent loss detected for {symbol} in the last {hours} hours, loss {trade['realizedPnl']}.")
            return True

    return False

def place_order_if_no_position(client, symbol, leverage):
    """Places a buy or sell order based on market bias if there's no open position and no recent losses."""
    open_positions = get_open_positions(client)
    open_symbols = [pos['symbol'] for pos in open_positions]

    if symbol in open_symbols:
        logging.info(f"Position already open for {symbol}, skipping order.")
        return

    if has_recent_loss(client, symbol):
        logging.info(f"Skipping order for {symbol} due to recent loss.")
        return

    # Get market bias
    market_bias = coinGeckoAPI.get_file_sentiment(symbol, coinGeckoAPI.apikey, coinGeckoAPI.apisecret)
    logging.info(f"Market bias for {symbol} is {market_bias}")

    if market_bias == "neutral":
        logging.info(f"Market bias is neutral for {symbol}, skipping order.")
        return

    # Determine order side based on market bias
    order_side = "BUY" if market_bias == "long" else "SELL"
    logging.info(f"Placing {order_side} order for {symbol}")

    try:
        symbol_info = get_symbol_info(client, symbol)
        if not symbol_info:
            return

        client.futures_change_leverage(symbol=symbol, leverage=5)
        time.sleep(sleep)

        ticker = client.futures_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
        quantity = round(500 / current_price, getQuantityPrecision(symbol))

        time.sleep(sleep)
        order = client.futures_create_order(
            symbol=symbol,
            side=order_side,
            type="MARKET",
            quantity=round(quantity, getPricePrecision(symbol))
        )
        logging.info(f"Order placed for {symbol}: {order}")
    except BinanceAPIException as e:
        logging.error(f"Error placing {order_side} order for {symbol}: {e}")

# def place_buy_order_if_no_position(client, symbol):
#     open_positions = get_open_positions(client)
#     open_symbols = [pos['symbol'] for pos in open_positions]
# 
#     if symbol in open_symbols:
#         logging.info(f"Position already open for {symbol}, skipping buy order.")
#         return
# 
#     if has_recent_loss(client, symbol):
#         logging.info(f"Skipping buy order for {symbol} due to recent loss.")
#         return
# 
#     logging.info(f"Placing buy order for {symbol}")
#     try:
#         symbol_info = get_symbol_info(client, symbol)
#         if not symbol_info:
#             return
# 
#         client.futures_change_leverage(symbol=symbol, leverage=10)
#         time.sleep(sleep)
#         ticker = client.futures_symbol_ticker(symbol=symbol)
#         current_price = float(ticker['price'])
#         quantity = round(500 / current_price, getQuantityPrecision(symbol))
# 
#         time.sleep(sleep)
#         order = client.futures_create_order(
 # #            symbol=symbol,
#             side="BUY",
# #             type="MARKET",
#             quantity=round(quantity, getPricePrecision(symbol))
#         )
#         logging.info(f"Order placed for {symbol}: {order}")
#     except BinanceAPIException as e:
#         logging.error(f"Error placing buy order for {symbol}: {e}")

def getWhitelist():
    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "JTOUSDT",
        "DOTUSDT",
        "XRPUSDT",
        "XLMUSDT",
        "IOTAUSDT",
        "ALGOUSDT",
        "BCHUSDT",
        "DOGEUSDT",
        "GMXUSDT",
        "ADAUSDT"
    ]
    return [{"symbol": symbol} for symbol in symbols]    

def get_top_5_futures_pairs(client):
    return getWhitelist()

    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        response = requests.get(url)
        data = response.json()

        time.sleep(sleep)
        exchange_info = client.futures_exchange_info()
        valid_symbols = {s['symbol'] for s in exchange_info['symbols'] if s['contractType'] == 'PERPETUAL' and s['status'] != 'SETTLING'}
        filtered_data = [d for d in data if d['symbol'] in valid_symbols]

        sorted_pairs = sorted(filtered_data, key=lambda x: float(x['priceChangePercent']), reverse=True)
        return sorted_pairs[:5]
    except Exception as e:
        logging.error(f"Error fetching top futures pairs: {e}")
        return []

def get_symbol_info(client, symbol):
    try:
        time.sleep(sleep)
        exchange_info = client.futures_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                return s
        logging.error(f"Symbol {symbol} not found.")
        return None
    except BinanceAPIException as e:
        logging.error(f"Error fetching symbol info: {e}")
        return None

def monitor_and_manage(client, loss_threshold, profit_threshold, leverage):
    market_bias = coinGeckoAPI.get_file_sentiment(None, client.API_KEY, client.API_SECRET)
    logging.info(f"Market bias is {market_bias}")

    while True:
        time.sleep(sleep)
        coinGeckoAPI.bias_determination = coinGeckoAPI.getBiasDetermination()
        print(f"Bias Determination is {coinGeckoAPI.bias_determination}")
        open_positions = get_open_positions(client)
        top_5_pairs = get_top_5_futures_pairs(client)

        for pair in top_5_pairs:
            place_order_if_no_position(client, pair['symbol'], leverage)
            time.sleep(sleep)

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
            print(f"Market Bias is {market_bias}, determination: {coinGeckoAPI.bias_determination}, checking reverting by market_bias or loss or taking profit")
            if pnl_percentage <= -loss_threshold:
                logging.warning(f"Loss reached {pnl_percentage:.2f}% for {symbol}. Reversing position!, loss_stop_price: {loss_stop_price}")
                reverse_position(client, position)

            elif pnl_percentage >= profit_threshold:
                logging.info(f"Profit reached {pnl_percentage:.2f}% for {symbol}. Closing position!, profit_take_price: {profit_take_price}")
                close_position(client, position)

            elif market_bias == "long" and position_amt < 0:
                logging.info(f"Market bias is long, reverting short position for {symbol} to long.")
                reverse_position(client, position)

            elif market_bias == "short" and position_amt > 0:
                logging.info(f"Market bias is short, reverting long position for {symbol} to short.")
                reverse_position(client, position)
            else:
                logging.info(f"{symbol} has not reached loss nor profit and market bias has not changed {market_bias}")

        df = pd.DataFrame(position_data, columns=["Symbol", "Entry Price", "Current Price", "PnL (%)", f"{loss_threshold}% Loss Price", f"{profit_threshold}% Profit Price"])
        print(tabulate(df, headers="keys", tablefmt="pretty"))

        time.sleep(sleep)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Binance Futures Position Manager")
    parser.add_argument("--apikey", required=True, help="Your Binance API Key")
    parser.add_argument("--apisecret", required=True, help="Your Binance API Secret")
    parser.add_argument("--loss", type=float, default=5.0, help="Loss percentage to trigger position reversal (default: 5%)")
    parser.add_argument("--profit", type=float, default=6.0, help="Profit percentage to trigger position closure (default: 6%)")
    parser.add_argument("--sleep", type=float, default=5.0, help="sleep in seconds before api call")
    parser.add_argument("--leverage", type=float, default=5.0, help="leverage")

    args = parser.parse_args()

    coinGeckoAPI.coinGeckoAPIKey = "CG-AgEZRgMf3iLk1S8CwyCKp7N3"
    coinGeckoAPI.apikey = args.apikey
    coinGeckoAPI.apisecret = args.apisecret
    sleep = args.sleep
    leverage = args.leverage

    client = Client(args.apikey, args.apisecret)

    logging.info(f"Monitoring positions for {args.loss}% loss threshold and {args.profit}% profit threshold...")
    monitor_and_manage(client, args.loss, args.profit, leverage)

