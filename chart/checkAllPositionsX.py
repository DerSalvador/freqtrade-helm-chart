import argparse
from binance.client import Client

def determine_trade(api_key, api_secret):
    client = Client(api_key, api_secret)

    try:
        positions = client.futures_position_information()
        
        total_unrealized_profit = sum([float(position['unRealizedProfit']) for position in positions])
        unrealized_profits_count = sum([1 for position in positions if float(position['unRealizedProfit']) > 0])

        if unrealized_profits_count / len(positions) >= 0.8:
            return 'long'
        elif unrealized_profits_count / len(positions) <= 0.2:
            return 'short'
        else:
            return 'hold'
    
    except Exception as e:
        print(f"Error fetching position or placing order: {e}")
        return 'error'

def main():
    parser = argparse.ArgumentParser(description="Place a Binance order with 10% profit target and stop loss.")
    parser.add_argument('api_key', type=str, help="Your Binance API key")
    parser.add_argument('api_secret', type=str, help="Your Binance API secret")
    args = parser.parse_args()

    api_key = args.api_key
    api_secret = args.api_secret

    trade_decision = determine_trade(api_key, api_secret)
    
    if trade_decision == 'short':
        print("Short position recommended.")
    elif trade_decision == 'long':
        print("Long position recommended.")
    elif trade_decision == 'hold':
        print("Hold position.")
    else:
        print("Error occurred while processing trade decision.")
    
if __name__ == "__main__":
    main()

