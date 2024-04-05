import urllib
import base64
import sys
import argparse
import requests
import time
import hmac
import hashlib
import time
import os
from urllib.parse import urlencode

# Read Kraken API key and secret stored in environment variables
api_url = "https://api.kraken.com"

def get_kraken_signature(urlpath, data, secret):

    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

# Attaches auth headers and returns results of a POST request
def kraken_request(uri_path, data, api_key, api_sec):
    headers = {}
    headers['API-Key'] = api_key
    # print("API-Sign: {}".format(signature))
    # get_kraken_signature() as defined in the 'Authentication' section
    headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)
    req = requests.post((api_url + uri_path), headers=headers, data=data)
    return req

def transfer_spot_to_funding(api_key, api_secret, asset, amount, funding_type):
    # Construct the request and print the result
    resp = kraken_request('/0/private/WalletTransfer', {
        "nonce": str(int(1000*time.time())),
        "asset": asset, # "ETH",
        "amount": amount,
        "from":"Spot Wallet",
        "to":"Futures Wallet"
    }, api_key, api_secret)

    print(resp.json())

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='Transfer assets from Spot Wallet to Funding Wallet on Kraken')
        parser.add_argument('api_key', type=str, help='Binance API key')
        parser.add_argument('api_secret', type=str, help='Binance API secret')
        parser.add_argument('asset', type=str, help='Asset symbol to transfer, e.g., USDT')
        parser.add_argument('amount', type=str, help='Amount to transfer, e.g., 5')
        parser.add_argument('funding_type', type=str, default='MAIN_FUNDING', choices=['Spot Wallet', 'Funding Wallet', 'Futures Wallet'], help='Type of funding transfer. Allowed values are Spot Wallet, Funding Wallet, Futures Wallet')
        
        args = parser.parse_args()

        response = transfer_spot_to_funding(args.api_key, args.api_secret, args.asset, args.amount, args.funding_type)
        print(response)
    except Exception as e:
        print(f"Caught an exception: {e}")
        # Exiting with code 10
        sys.exit(10)

