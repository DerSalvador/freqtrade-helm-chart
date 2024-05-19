import sys
import argparse
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
from binance.client import Client

base_url = 'https://api.binance.com'

headers = {
    'X-MBX-APIKEY': ''
}

def get_timestamp():
    return int(time.time() * 1000)

def sign_request(data, api_secret):
    query_string = urlencode(data)
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_account_balances(api_key, api_secret):

    # Create a new client object to interact with the Binance API
    client = Client(api_key, api_secret)
    # Retrieve the balances of all coins in the user’s Binance account
    account_balances = client.get_account()['balances']

    # Get the current price of all tickers from the Binance API
    ticker_info = client.get_all_tickers()

    # Create a dictionary of tickers and their corresponding prices
    ticker_prices = {ticker['symbol']: float(ticker['price']) for ticker in ticker_info}

    # Calculate the USDT value of each coin in the user’s account
    coin_values = []
    for coin_balance in account_balances:
        # Get the coin symbol and the free and locked balance of each coin
        coin_symbol = coin_balance['asset']
        unlocked_balance = float(coin_balance['free'])
        locked_balance = float(coin_balance['locked'])

    # If the coin is USDT and the total balance is greater than 1, add it to the list of coins with their USDT values
    if coin_symbol == 'USDT' and unlocked_balance + locked_balance > 1:
        coin_values.append(('USDT', (unlocked_balance + locked_balance)))
    # Otherwise, check if the coin has a USDT trading pair or a BTC trading pair
    elif unlocked_balance + locked_balance > 0.0:
    # Check if the coin has a USDT trading pair
        if (any(coin_symbol + 'USDT' in i for i in ticker_prices)):
        # If it does, calculate its USDT value and add it to the list of coins with their USDT values
            ticker_symbol = coin_symbol + 'USDT'
            ticker_price = ticker_prices.get(ticker_symbol)
            coin_usdt_value = (unlocked_balance + locked_balance) * ticker_price
        if coin_usdt_value > 1:
            coin_values.append((coin_symbol, coin_usdt_value))
        # If the coin does not have a USDT trading pair, check if it has a BTC trading pair
        elif (any(coin_symbol + 'BTC' in i for i in ticker_prices)):
        # If it does, calculate its USDT value and add it to the list of coins with their USDT values
            ticker_symbol = coin_symbol + 'BTC'
            ticker_price = ticker_prices.get(ticker_symbol)
            coin_usdt_value = (unlocked_balance + locked_balance) * ticker_price * ticker_prices.get('BTCUSDT')
        if coin_usdt_value > 1:
            coin_values.append((coin_symbol, coin_usdt_value))

    # Sort the list of coins and their USDT values by USDT value in descending order
    coin_values.sort(key=lambda x: x[1], reverse=True)

    # Return the list of coins and their USDT values
    return coin_values

def getBalance(api_key, api_secret, wallet):
    # get_account_balances(api_key, api_secret, wallet)
    current_timestamp_ms = int(round(time.time() * 1000))
    path = '/sapi/v1/asset/wallet/balance'
    params = {
        'wallet': wallet, # 'FUNDING_WALLET', # SPOT_WALLET
        'currency': 'USDT',
        'timestamp': current_timestamp_ms
    }
    params['signature'] = sign_request(params, api_secret)
    headers['X-MBX-APIKEY'] = api_key
    url = base_url + path
    response = requests.get(url, headers=headers, params=params)
    return response.json()

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='Get Wallet Value')
        parser.add_argument('api_key', type=str, help='Binance API key')
        parser.add_argument('api_secret', type=str, help='Binance API secret')
        parser.add_argument('wallet', type=str, default='FUNDING_WALLET', choices=['FUNDING_WALLET', 'SPOT_WALLET'], help='Type of funding transfer. Allowed values are SPOT_WALLET and FUNDING_WALLET')
        
        args = parser.parse_args()

        response = getBalance(args.api_key, args.api_secret, args.wallet)
        print(response)
    except Exception as e:
        print(f"Caught an exception: {e}")
        # Exiting with code 10
        sys.exit(10)

