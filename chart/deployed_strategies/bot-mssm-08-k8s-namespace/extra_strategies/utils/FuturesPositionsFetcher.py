kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-mssm-08 exec -it pod/freqtrade-bot-mssm-08-765d99b7b4-dl7gb -c freqtrade -- cat /extra_strategies/utils/FuturesPositionsFetcher.py
import logging
import sys
import argparse
import argparse
# from binance.spot import Spot as Client
from binance.client import Client
from binance.lib.utils import config_logging
# from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.INFO)

class FuturesPositionsFetcher:
    client: Client = None
    def __init__(self, api_key, api_secret):
        config_logging(logging, logging.INFO)
        self.client = Client(api_key, api_secret)

    def get_futures_position_information(self, symbol):
        if not symbol:
            raise ValueError("Symbol must be specified.")
        pos = self.client.futures_position_information(symbol=symbol)
        return pos