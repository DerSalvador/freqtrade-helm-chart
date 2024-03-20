import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode

# Replace these with your own API key and secret from Binance
api_key = 'Ie1qiv3hF3gfMGIsyZxdxNDSVSfz8INIWGRKkUwPEejNGRikh2toUVZb1WlH2X2P'
api_secret = '3z4uF8JTXEJLN23IZmQJ9uQuOBc8AdD7ZEwkO5kg5FWm1SsbFMTIIp48usFzhk9r'

base_url = 'https://api.binance.com'

headers = {
    'X-MBX-APIKEY': api_key
}

def get_timestamp():
    return int(time.time() * 1000)

def sign_request(data):
    query_string = urlencode(data)
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def transfer_spot_to_funding(asset, amount):
    path = '/sapi/v1/asset/transfer'
    params = {
        'type': 'MAIN_FUNDING',  # Change this accordingly if necessary. MAIN_UMFUTURE is for transferring from Spot Wallet to Funding Wallet
        'asset': asset,
        'amount': amount,
        'timestamp': get_timestamp()
    }
    params['signature'] = sign_request(params)
    url = base_url + path
    response = requests.post(url, headers=headers, params=params)
    return response.json()

# Example usage
asset = 'USDT'  # e.g., 'BTC'
amount = '5'  # e.g., '0.01'
response = transfer_spot_to_funding(asset, amount)
print(response)

