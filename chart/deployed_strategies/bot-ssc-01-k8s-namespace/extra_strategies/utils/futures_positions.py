kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-ssc-01 exec -it pod/freqtrade-bot-ssc-01-6b8849f5f6-7xdz9 -c freqtrade -- cat /extra_strategies/utils/futures_positions.py
#!/usr/bin/env python

import logging
import sys
import argparse
import argparse

# from binance.spot import Spot as Client
from binance.client import Client
from binance.lib.utils import config_logging
# from examples.utils.prepare_env import get_api_key
from FuturesPositionsFetcher import FuturesPositionsFetcher

config_logging(logging, logging.INFO)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Fetch futures position information from Binance with a specified symbol')
    parser.add_argument('-s', '--symbol', required=True, help='Symbol to retrieve information for (e.g., BTCUSDT, ETHUSDT)')
    parser.add_argument('-k', '--apikey', required=True, help='API keys')
    parser.add_argument('-i', '--apisecret', required=True, help='API Secret')
    args = parser.parse_args()

    if not hasattr(args, 'symbol') or not args.symbol:
        parser.error('Please specify the symbol using -s or --symbol option. Example: -s BTCUSDT')
    if not hasattr(args, 'apikey') or not args.apikey:
        parser.error('Please specify the api key with -k or --key')
    if not hasattr(args, 'apisecret') or not args.apisecret:
        parser.error('Please specify the api secret with -i or --secret')

    fetcher = FuturesPositionsFetcher(args.apikey, args.apisecret)
    position_info = fetcher.get_futures_position_information(args.symbol)
    print(position_info)

if __name__ == '__main__':
    main()

# # Parse command-line arguments
# parser = argparse.ArgumentParser(description='Fetch futures position information from Binance with a specified symbol')
# parser.add_argument('-s', '--symbol', required=True, help='Symbol to retrieve information for (e.g., BTCUSDT, ETHUSDT)')
# parser.add_argument('-k', '--apikey', required=True, help='API keys')
# parser.add_argument('-i', '--apisecret', required=True, help='API Secret')
# args = parser.parse_args()


# if not hasattr(args, 'symbol') or not args.symbol:
#     parser.error('Please specify the symbol using -s or --symbol option. Example: -s BTCUSDT')
# if not hasattr(args, 'apikey') or not args.apikey:
#     parser.error('Please specify the api key with -k or --key')
# if not hasattr(args, 'apisecret') or not args.apisecret:
#     parser.error('Please specify the api secret with -i or --secret')

# # api_key, api_secret = get_api_key()

# cf = Client(args.apikey, args.apisecret)
# print(cf.futures_position_information(symbol=args.symbol))

