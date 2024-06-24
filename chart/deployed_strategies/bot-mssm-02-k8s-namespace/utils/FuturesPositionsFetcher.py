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
    def __init__(self, api_key, api_secret):
        config_logging(logging, logging.INFO)
        self.client = Client(api_key, api_secret)

    def get_futures_position_information(self, symbol):
        if not symbol:
            raise ValueError("Symbol must be specified.")
        return self.client.futures_position_information(symbol=symbol)