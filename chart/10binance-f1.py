import requests

def get_futures_pairs():
    url = "https://fapi.binance.com/fapi/v1/ticker/price"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX/5XX
        futures_data = response.json()
        
        # Filter or sort the data as needed; here, we're just printing it
        for pair in futures_data:
            # Modify the output format to "CURRENCY/CURRENCY:USDT" if needed
            print(pair["symbol"], ":", pair["price"])
            
    except requests.RequestException as e:
        print(f"Error fetching futures pairs data: {e}")

# Call the function
get_futures_pairs()

