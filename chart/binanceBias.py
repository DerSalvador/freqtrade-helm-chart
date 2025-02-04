import argparse
from binance.client import Client
import pandas as pd

# Function to fetch historical candlestick data
def get_candlestick_data(client, symbol, interval, limit=100):
    """
    Fetch candlestick (OHLC) data for a given symbol and interval.

    Args:
        client (Client): Binance API client.
        symbol (str): The trading pair (e.g., 'BTCUSDT').
        interval (str): Timeframe (e.g., '1d' for daily, '1h' for hourly).
        limit (int): Number of candles to fetch.

    Returns:
        pandas.DataFrame: Candlestick data.
    """
    candles = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    
    # Convert data to DataFrame
    df = pd.DataFrame(candles, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # Keep only relevant columns and convert to numeric
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to calculate SMA and detect trends
def detect_trend(df):
    df['SMA_20'] = df['close'].rolling(window=20).mean()  # 20-day SMA
    df['SMA_50'] = df['close'].rolling(window=50).mean()  # 50-day SMA

    # Determine trend
    def trend_logic(row):
        if row['SMA_20'] > row['SMA_50']:
            return "long"
        elif row['SMA_20'] < row['SMA_50']:
            return "short"
        else:
            return "neutral"

    df['trend'] = df.apply(trend_logic, axis=1)
    return df

# Main function
def main():
    parser = argparse.ArgumentParser(description="Fetch market trends using Binance API.")
    parser.add_argument("--apikey", required=True, help="Your Binance API key.")
    parser.add_argument("--apisecret", required=True, help="Your Binance API secret.")
    args = parser.parse_args()

    # Initialize Binance API client
    client = Client(args.apikey, args.apisecret)

    # Fetch BTC/USDT daily data
    symbol = "BTCUSDT"
    interval = "1d"
    df = get_candlestick_data(client, symbol, interval)

    # Calculate SMA and detect trends
    df = detect_trend(df)

    # Display the last few rows
    # print(df.tail())

    # Example: Check today's trend
    latest_trend = df.iloc[-1]['trend']
    print(f"The latest trend for {symbol} is: {latest_trend}")

if __name__ == "__main__":
    main()

