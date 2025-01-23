import requests, sys

# API endpoint for CoinGecko
url = "https://pro-api.coingecko.com/api/v3"

# Function to get the current price and price change in 24 hours for Bitcoin
def get_bitcoin_data():
    endpoint = f"{url}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&x_cg_pro_api_key=CG-AgEZRgMf3iLk1S8CwyCKp7N3"
    response = requests.get(endpoint)
    if response.status_code == 200:
        data = response.json()
        return data["bitcoin"]
    else:
        return None

# Function to analyze the trend bias
def analyze_trend_bias(data):
    price_change_percentage_24h = data["usd_24h_change"]
    sys.stderr.write(f"price_change_percentage_24h: {price_change_percentage_24h}")    
    if price_change_percentage_24h > 0:
        return "long"
    elif price_change_percentage_24h < 0:
        return "short"
    else:
        return "neutral"

# Main function
def main():
    bitcoin_data = get_bitcoin_data()
    if bitcoin_data:
        print(analyze_trend_bias(bitcoin_data))
    else:
        print("Failed to fetch Bitcoin data")

if __name__ == "__main__":
    main()

