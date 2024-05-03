import sys
from binance.client import Client

# Function to get funding wallet value
def get_funding_wallet_value(api_key, api_secret):
    # Initialize the Binance client
    client = Client(api_key, api_secret)
    
    # Fetch funding wallet info
    try:
        funding_wallet = client.get_funding_wallet()
        print("Funding Wallet Information:", funding_wallet)
    except Exception as e:
        print("Error fetching funding wallet information:", str(e))

# Main function
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <API_KEY> <API_SECRET>")
        sys.exit(1)
    
    # Command line arguments
    api_key = sys.argv[1]
    api_secret = sys.argv[2]
    
    # Get and print the funding wallet value
    get_funding_wallet_value(api_key, api_secret)

