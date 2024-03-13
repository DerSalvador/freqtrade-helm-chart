import requests

url = "https://fapi.binance.com/fapi/v1/ticker/24hr"

response = requests.get(url)
pairs = response.json()

# Sort pairs by volume, descending
sorted_pairs = sorted(pairs, key=lambda x: float(x['volume']), reverse=True)

# Print top 10 most popular pairs
#for pair in sorted_pairs[:20]:
#    print(f"Pair: {pair['symbol']}, Volume: {pair['volume']}")
    
# Filter or sort the data as needed; here, we're just printing it
for pair in sorted_pairs[:20]:
    # Modify the output format to "CURRENCY/CURRENCY:USDT" if needed
    parts = pair["symbol"].split('USDT')
    sym=parts[0].strip()+"#USDT:USDT".replace(" ", "")
    print(sym)    
