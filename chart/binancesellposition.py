from binance.client import Client

def sell_market_order(apikey, apisecret, amount):
    client = Client(apikey, apisecret)

    symbol = 'DOGEUSDT'
    quantity = amount

    order = client.create_order(
        symbol=symbol,
        side=Client.SIDE_SELL,
        type=Client.ORDER_TYPE_MARKET,
        quantity=quantity
    )

    print("Market sell order placed successfully.")

# Example JSON data provided
data = {
    'symbol': 'DOGEUSDT',
    'positionAmt': '5923',
    'entryPrice': '0.1066545918361',
    'breakEvenPrice': '0.1161638548435',
    'markPrice': '0.10716973',
    'unRealizedProfit': '3.05117422',
    'liquidationPrice': '0.08878222',
    'leverage': '10',
    'maxNotionalValue': '8000000',
    'marginType': 'isolated',
    'isolatedMargin': '111.53852279',
    'isAutoAddMargin': 'false',
    'positionSide': 'BOTH',
    'notional': '634.76631079',
    'isolatedWallet': '108.48734857',
    'updateTime': 1726992000887,
    'isolated': True,
    'adlQuantile': 3
}

# Extract the amount from the JSON data to sell
amount_to_sell = float(data['positionAmt'])

# Your Binance API Key and Secret
#    key: "pX7yYyXSSTAeVWZRYGFlEfKCfxfb8I2b5d1FHJfk7lzo23CsxZh1pva1GZxaFz6A"
#    secret: "Ta2MTBjpKM8OHAHTvtbH72gtj40vqPfgcULY6w7cHWroWs7NhZe0tDMzWdBm4dYV"
apikey = "pX7yYyXSSTAeVWZRYGFlEfKCfxfb8I2b5d1FHJfk7lzo23CsxZh1pva1GZxaFz6A"
apisecret = "Ta2MTBjpKM8OHAHTvtbH72gtj40vqPfgcULY6w7cHWroWs7NhZe0tDMzWdBm4dYV"

# Sell the specified amount as a market order
sell_market_order(apikey, apisecret, amount_to_sell)
