import requests, sys
import json

# API endpoint to retrieve data
url = "https://pro-api.coingecko.com/api/v3/global?x_cg_pro_api_key=CG-AgEZRgMf3iLk1S8CwyCKp7N3"

# Make a GET request to the API endpoint
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    
    # Extract relevant data from the JSON response
    market_cap_change_percentage_24h_usd = data["data"]["market_cap_change_percentage_24h_usd"]
    sys.stderr.write(f"market_cap_change_percentage_24h_usd: {market_cap_change_percentage_24h_usd}")
    
    # Determine market trend bias based on the percentage change in market capitalization
    market_trend_bias = "neutral" 
    if market_cap_change_percentage_24h_usd > 0:
       market_trend_bias = "long" 
    elif  market_cap_change_percentage_24h_usd < 0:
       market_trend_bias = "short" 
    
    # Print the market trend bias
    print(market_trend_bias)
else:
    print("Failed to retrieve data. Status code:", response.status_code)
