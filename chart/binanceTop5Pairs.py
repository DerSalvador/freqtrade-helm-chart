import requests

# Binance Futures API endpoint
url = "https://fapi.binance.com/fapi/v1/ticker/24hr"

# Fetch data
response = requests.get(url)
data = response.json()

# Filter and sort data by price change percentage
sorted_pairs = sorted(data, key=lambda x: float(x['priceChangePercent']), reverse=True)

# Get the top 5 best-performing pairs
top_5_pairs = sorted_pairs[:5]

# Display the results
print("Top 5 Best-Performing Futures Pairs for Long Trading:")
for pair in top_5_pairs:
    print(f"Symbol: {pair['symbol']}, Price Change: {pair['priceChangePercent']}%")

