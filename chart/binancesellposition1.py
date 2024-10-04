import json
#from binance.client import Client
#
#def create_opposite_future_order(apikey, apisecret):
#    client = Client(apikey, apisecret)
#
#    # Sample JSON data
#    data = {
#        "symbol": "DOGEUSDT",
#        "positionAmt": "5923",
#        "entryPrice": "0.1066545918361",
#        "breakEvenPrice": "0.1161638548435",
#        "markPrice": "0.10723000",
#        "unRealizedProfit": "3.40815343",
#        "liquidationPrice": "0.08878222",
#        "leverage": "10",
#        "maxNotionalValue": "8000000",
#        "marginType": "isolated",
#        "isolatedMargin": "111.89550200",
#        "isAutoAddMargin": "false",
#        "positionSide": "BOTH",
#        "notional": "635.12329000",
#        "isolatedWallet": "108.48734857",
#        "updateTime": 1726992000887,
#        "isolated": True,
#        "adlQuantile": 3
#    }

#    # Extracting data from the JSON
#    symbol = data['symbol']
#    position_amt = float(data['positionAmt'])
#    current_price = float(data['markPrice'])
#    # amount = current_price * position_amt  # Calculating amount for opposite direction
#    amount = position_amt  # Calculating amount for opposite direction

#    # Creating opposite direction order
#    order = client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=amount)

#    print(f"Opposite direction future order created for symbol {symbol} with amount {amount}. Order details: {order}")

# Replace 'YOUR_API_KEY' and 'YOUR_API_SECRET' with your actual Binance API Key and Secret
#create_opposite_future_order("pX7yYyXSSTAeVWZRYGFlEfKCfxfb8I2b5d1FHJfk7lzo23CsxZh1pva1GZxaFz6A", "Ta2MTBjpKM8OHAHTvtbH72gtj40vqPfgcULY6w7cHWroWs7NhZe0tDMzWdBm4dYV")

import argparse
from binance.client import Client

def create_opposite_future_order(apikey, apisecret, symbol, side, type, quantity):
    client = Client(apikey, apisecret)

    order = client.futures_create_order(symbol=symbol, side=side, type=type, quantity=quantity)

    print(f"Opposite direction future order created for symbol {symbol} with amount {quantity}. Order details: {order}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create opposite direction future order on Binance.')
    parser.add_argument('--apikey', required=True, help='Binance API Key')
    parser.add_argument('--apisecret', required=True, help='Binance API Secret')
    parser.add_argument('--symbol', required=True, help='Symbol to trade')
    parser.add_argument('--side', default='SELL', help='Side of the order (default: SELL)')
    parser.add_argument('--type', default='MARKET', help='Type of the order (default: MARKET)')
    parser.add_argument('--quantity', type=float, required=True, help='Quantity/Amount of the order')

    args = parser.parse_args()

    create_opposite_future_order(args.apikey, args.apisecret, args.symbol, args.side, args.type, args.quantity)

