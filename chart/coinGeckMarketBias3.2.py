import requests, sys

# API endpoint for CoinGecko
url = "https://pro-api.coingecko.com/api/v3"

def get_bitcoin_data():
    # API endpoint and key for CoinGecko
    API_URL = "https://pro-api.coingecko.com/api/v3"
    API_KEY = "CG-AgEZRgMf3iLk1S8CwyCKp7N3"
    endpoint = f"{API_URL}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin",
        "order": "market_cap_desc",
        "per_page": 1,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
        "x_cg_pro_api_key": API_KEY,
    }
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data[0] if data else None
    except requests.RequestException as e:
        print(f"Error fetching Bitcoin data: {e}")
        return None

# Function to analyze market trend bias (bullish or bearish)
def analyze_trend( data):
    change_24h = data.get("price_change_percentage_24h", 0)
    change_7d = data.get("price_change_percentage_7d_in_currency", 0)
    volume = data.get("total_volume", 0)

    # Determine bias based on 24-hour and 7-day changes
    if change_24h > 0 and change_7d > 0:
        trend = "long"
    elif change_24h < 0 and change_7d < 0:
        trend = "short"
    else:
        trend = "neutral"

    return {
        "24h_change": change_24h,
        "7d_change": change_7d,
        "volume": volume,
        "trend": trend,
    }

# Main function
def main():
    bitcoin_data = get_bitcoin_data()
    if bitcoin_data:
        print(analyze_trend(bitcoin_data))
    else:
        print("Failed to fetch Bitcoin data")

if __name__ == "__main__":
    main()

