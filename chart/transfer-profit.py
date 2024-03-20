import sys
import argparse
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode

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

def transfer_spot_to_funding(api_key, api_secret, asset, amount, funding_type):
    path = '/sapi/v1/asset/transfer'
    params = {
        'type': funding_type,
        'asset': asset,
        'amount': amount,
        'timestamp': get_timestamp()
    }
    params['signature'] = sign_request(params, api_secret)
    headers['X-MBX-APIKEY'] = api_key
    url = base_url + path
    response = requests.post(url, headers=headers, params=params)
    return response.json()

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='Transfer assets from Spot Wallet to Funding Wallet on Binance')
        parser.add_argument('api_key', type=str, help='Binance API key')
        parser.add_argument('api_secret', type=str, help='Binance API secret')
        parser.add_argument('asset', type=str, help='Asset symbol to transfer, e.g., USDT')
        parser.add_argument('amount', type=str, help='Amount to transfer, e.g., 5')
        parser.add_argument('funding_type', type=str, default='MAIN_FUNDING', choices=['MAIN_FUNDING', 'FUNDING_MAIN', 'UMFUTURE_FUNDING', 'FUNDING_UMFUTURE'], help='Type of funding transfer. Allowed values are MAIN_FUNDING and FUNDING_MAIN')
        
        args = parser.parse_args()

        response = transfer_spot_to_funding(args.api_key, args.api_secret, args.asset, args.amount, args.funding_type)
        print(response)
    except Exception as e:
        print(f"Caught an exception: {e}")
        # Exiting with code 10
        sys.exit(10)

