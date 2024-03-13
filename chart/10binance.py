import requests, sys

# Binance API endpoint for fetching trading pairs
url = 'https://api.binance.com/api/v3/exchangeInfo'
response = requests.get(url)

if response.status_code == 200:
    data = response.json()

    usdt_pairs = [pair['symbol'] for pair in data['symbols'] if pair['quoteAsset'] == 'USDT']
    print (usdt_pairs, file=sys.stderr)
    pair_volumes = {}
    for usdt_pair in usdt_pairs:
        # Binance API endpoint for fetching 24hr ticker price change statistics
        ticker_url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={usdt_pair}'
        ticker_response = requests.get(ticker_url)

        if ticker_response.status_code == 200:
            ticker_data = ticker_response.json()
            pair_volumes[usdt_pair] = float(ticker_data['quoteVolume'])

    popular_pairs = sorted(pair_volumes, key=pair_volumes.get, reverse=True)[:10]

    print("Top 10 most popular USDT trading pairs on Binance:", file=sys.stderr)
    for pair in popular_pairs:
        print(pair.replace("USDT", "#USDT"))
else:
    print("Failed to fetch trading pairs. Status code:", response.status_code, file=sys.stderr)

