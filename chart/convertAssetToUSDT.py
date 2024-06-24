#!/usr/bin/env python

# This file is part of krakenex.
# Licensed under the Simplified BSD license. See `examples/LICENSE.txt`.

# Prints the account blance to standard output.

import sys
import time
import math
import requests
import urllib.parse
import hashlib
import hmac
import base64
import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
from binance.error import ClientError

# Read Kraken API key and secret stored in environment variables
kraken_api_url = "https://api.kraken.com"
binance_api_url = "https://api.binance.com"

# kraken hellen
# api_key = '7T77qjKhPC7jbKq0eyDtFSM99pLluWN1v+oxmtciibIbBFoxTdQ+JO+0'
# api_sec = 'UwKS092Z0SXRycR/6CmWj39LcJJN4hexqTrMbME8b9pW8XIL/38w3mNZhPqpTpQ/OjAWfUtOuvistsp2iMYuvw=='
# Adriana
# api_key = '+H4NKdY1EIWMVwq4s+qOymZATOYoQPvND+wCMzo+jasiN+zScLEVPODo'
# api_sec = 'jOrx0aLMbRzOjAoagVx0nU1fW2qzTvvT+2bZQNIehqjKfieATglkZ+o92QJm9AuCCdmH4k3owys+nWHKlCEJmw=='

def kraken_request(uri_path, data, api_key, api_sec):
    headers = {}
    headers['API-Key'] = api_key
    # get_kraken_signature() as defined in the 'Authentication' section
    headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)             
    req = requests.post((kraken_api_url + uri_path), headers=headers, data=data)
    return req


def get_kraken_signature(urlpath, data, secret):

    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

def main():
    # Check if the correct number of arguments are provided
    if len(sys.argv) != 6:
        print("Usage: python script_name.py key secret symbol amount exchange")
    else:
        key = sys.argv[1]
        secret = sys.argv[2]
        symbol = sys.argv[3]
        volume = sys.argv[4]
        exchange = sys.argv[5]
        # Now you can use these arguments as needed in your program
        print(f"Key: {key}")
        print(f"Secret: {secret}")
        print(f"Symbol: {symbol}")
        print(f"Volume: {volume}")
        #if len(key) == 4:
        #    key = key[-3:]
        non_scientific_number = '{:.12}'.format(float(volume))
        if float(eval(non_scientific_number)) != 0 and symbol != "USDT":
            #if len(symbol) == 4 and symbol[0] == 'X':
            #    symbol = symbol[-3:]
            print(f"Placing Market Order for {symbol} {volume} on {exchange}")
            if exchange == "kraken":
                resp = kraken_request_wrapper(symbol, non_scientific_number, key, secret)
            elif exchange == "binance":
                resp = binance_request(symbol, non_scientific_number, key, secret)
            else:
                print("Exchange not defined")
                sys.exit(2)
            if type(resp) is type(None):
                print("Response is of NoneType")
            else:
                if hasattr(resp, 'json'):
                    print(resp.json())
                else:
                    print("Response is not JSON: " + resp )
        else:
            print(f"WARNING: No Market Order placed for {key} {volume}")


def kraken_request_wrapper(symbol, volume, key, secret):
    resp = kraken_request('/0/private/AddOrder', {
    "nonce": str(int(1000*time.time())),
    "ordertype": "market",
    "type": "sell",
    "volume": volume,
    "pair": f"{symbol}USDT"
    #"price": 27500
    }, key, secret)
    return resp

def getStepSize(data, symbol):
    # Iterate through the symbols to find the specific symbol
    for symbol_info in data['symbols']:
        if symbol_info['symbol'] == symbol:
            # Retrieve the step size
            filters = symbol_info['filters']
            for filter_info in filters:
                if filter_info['filterType'] == 'LOT_SIZE':
                    step_size = float(filter_info['stepSize'])
                    print(f"The step size for symbol {symbol} is {step_size}")
                    return step_size
                    break
            break
        
def getMinQty(data, symbol):
    # Iterate through the symbols to find the specific symbol
    for symbol_info in data['symbols']:
        if symbol_info['symbol'] == symbol:
            # Retrieve the step size
            filters = symbol_info['filters']
            for filter_info in filters:
                if filter_info['filterType'] == 'LOT_SIZE':
                    minQty = float(filter_info['minQty'])
                    print(f"The minQty for symbol {symbol} is {minQty}")
                    return minQty
                    break
            break
        
def binance_request(symbol, volume, key, secret):
    config_logging(logging, logging.INFO)

    api_key = key
    api_secret = secret
    params = {
        "symbol": f"{symbol}USDT",
        "side": "SELL",
        "type": "MARKET",
        "quantity": volume
        #"timeInForce": "GTC",
        #"price": 9500,
    }
    client = Client(api_key, api_secret, base_url="https://api.binance.com")
    resp = client.exchange_info()
    step_size = getStepSize(resp, symbol+"USDT")
    minQty = getMinQty(resp, symbol+"USDT")
    if minQty > float(volume):
        logging.warning(f"Volume ${volume} is less than Min Quantity ${minQty} for pair {symbol}USDT")
        return;
    volume = str(step_size * math.floor(float(volume) / step_size))
    try:
        response = client.new_order(**params)
        logging.info(response)
        return response
    except ClientError as error:
        logging.error(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

if __name__ == "__main__":
    main()


# print(k.query_private('Balance'))
# # Construct the request and print the result
# resp = kraken_request('/0/private/BalanceEx', {
#     "nonce": str(int(1000*time.time()))
# }, api_key, api_sec)
# print(resp)
# jsontxt = k.query_private('Balance')
# # Access the keys and values
# result = jsontxt['result']
# for key, value in result.items():
#     print(key, ":", value)
#     # Attaches auth headers and returns results of a POST request
#     # Construct the request and print the result

# resp = kraken_request('/0/private/AddOrder', {
#     "nonce": str(int(1000*time.time())),
#     "ordertype": "market",
#     "type": "exit",
#     "volume": 7.9632,
#     "pair": f"DOGEUSDT"
#     #"price": 27500
# }, api_key, api_sec)

# print(resp)
