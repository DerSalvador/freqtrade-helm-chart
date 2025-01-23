import argparse, sys
from binance.client import Client
from binance.helpers import round_step_size

def main():
    parser = argparse.ArgumentParser(description="Place a Binance order with 10% profit target and stoploss.")
    parser.add_argument('api_key', type=str, help="Your Binance API key")
    parser.add_argument('api_secret', type=str, help="Your Binance API secret")
    args = parser.parse_args()

    api_key = args.api_key
    api_secret = args.api_secret

    client = Client(api_key, api_secret)

    # Fetch current position for the symbol
    try:
        positions = client.futures_position_information()
        # position = next((p for p in positions if p['symbol'] == symbol), None)
        for position in positions: # = next((p for p in positions if p['symbol'] == symbol), None)
            if not position:
                print(f"No active position found for {symbol}.")
                return

            position_amt = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            unRealizedProfit = float(position['unRealizedProfit'])
            sys.stderr.write(str(unRealizedProfit))
            if position_amt == 0:
                print(f"No active position to close for {symbol}.")
                return

    except Exception as e:
        print(f"Error fetching position or placing order: {e}")

if __name__ == "__main__":
    main()

