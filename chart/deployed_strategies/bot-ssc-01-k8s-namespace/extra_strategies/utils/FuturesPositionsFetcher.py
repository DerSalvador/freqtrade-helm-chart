kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-ssc-01 exec -it pod/freqtrade-bot-ssc-01-6b8849f5f6-7xdz9 -c freqtrade -- cat /extra_strategies/utils/FuturesPositionsFetcher.py
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