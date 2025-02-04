import argparse
import logging
import time
import pandas as pd
from tabulate import tabulate
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

def monitor_and_manage(client, loss_threshold, profit_threshold):
    """Monitors positions, reverses on loss, and closes on profit."""
    while True:
        open_positions = get_open_positions(client)

        if not open_positions:
            logging.info("No open positions found. Waiting...")
            time.sleep(5)
            continue

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
    parser.add_argument("--profit", type=float, default=15.0, help="Profit percentage to trigger position closure (default: 15%)")

    args = parser.parse_args()

    client = Client(args.apikey, args.apisecret)

    logging.info(f"Monitoring positions for {args.loss}% loss threshold and {args.profit}% profit threshold...")
    monitor_and_manage(client, args.loss, args.profit)

