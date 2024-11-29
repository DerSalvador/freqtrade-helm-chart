kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n binance-juliano-futures exec -it pod/freqtrade-binance-juliano-futures-64f97687bf-wn6d6 -c freqtrade -- cat /extra_strategies/utils/dsHedging.py
#pragma pylint: disable=W0105, C0103, C0301, W1203

from datetime import datetime
from functools import reduce
# import timeit
import requests
# from freqtrade.rpc import RPCManager
# from freqtrade.rpc.external_message_consumer import ExternalMessageConsumer
# from freqtrade.rpc.rpc_types import (ProfitLossStr, RPCCancelMsg, RPCEntryMsg, RPCExitCancelMsg,
#                                      RPCExitMsg, RPCProtectionMsg)
# from freqtrade import rpc_singleton

import numpy as np
# Get rid of pandas warnings during backtesting
import pandas as pd
from pandas import DataFrame, Series
import scipy
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

# from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import RobustScaler
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

# import freqtrade.vendor.qtpylib.indicators as qtpylib

from freqtrade.strategy import (IStrategy, DecimalParameter, CategoricalParameter)
from freqtrade.persistence import Trade

pd.options.mode.chained_assignment = None  # default='warn'

# Strategy specific imports, files must reside in same folder as strategy
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import logging
import warnings

log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

class dsHedging():
    
    @staticmethod
    def logme(msg: str):
        print(f"{msg}")
        log.info(f"{msg}")
            
    @staticmethod
    def hedge_me(strategy: IStrategy, trade, pair, position, endpoint=None):
        if position is None or float(position[0]['positionAmt']) == 0.0:
            dsHedging.logme("No position exist, trying to hedge")
            if trade.is_short: 
                return dsHedging.hedge(strategy, pair, "long", endpoint)
            else:
                return dsHedging.hedge(strategy, pair, "short", endpoint)
        else:
            dsHedging.logme(f"NOT hedging because position already exists for {position} with amount {float(position[0]['positionAmt'])}")
            
                
    # Do *not* hyperopt for the roi and stoploss spaces
    @staticmethod
    def hedge(strategy: IStrategy, pair, direction, endpoint=None):
        # Get the current timestamp in UTC timezone
        current_timestamp = datetime.now()
        if endpoint is None:
            endpoint = strategy.hedging_url
            tag=f'ForcedHedging {pair} at {current_timestamp} with leverage {strategy.hedging_leverage}, '
            tag+=f'amount {strategy.hedging_stake_amount}, ' 
            tag+=f'direction {direction} on bot {endpoint}'
        else:
            tag=f'ForcedStoplossHedging {pair} at {current_timestamp} with leverage {strategy.hedging_leverage}, '
            tag+=f'amount {strategy.hedging_stake_amount}, ' 
            tag+=f'direction {direction} on bot {endpoint}'
            strategy.logme(f"Stoploss API will be called, setting new tag...")
        dsHedging.logme(f"Haleluja.... start finally hedging for pair {pair} with direction {direction}")
        dsHedging.logme(f"Entering Hedge Modus with direction {direction}")
        if ':' not in pair:
            pair += ':USDT'
        dsHedging.logme(f"Entering hedging: {tag}")
        payload = {
            "pair": pair,
            "side": direction,
            "ordertype": "market",
            "stakeamount": strategy.hedging_stake_amount,
            "entry_tag": tag,
            "leverage": strategy.hedging_leverage
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        username = strategy.config['api_server']['username']
        password = strategy.config['api_server']['password']
        auth = (username, password)

        try:
            response = requests.post(endpoint, json=payload, headers=headers, auth=auth)
            response.raise_for_status()  # Check for HTTP errors
            if response.status_code == 200:
                dsHedging.logme("Hedging successful. Response:")
                dsHedging.logme(response.json())
                return True
            else:
                dsHedging.logme(f"Request returned status code: {response.status_code}")
        except requests.RequestException as e:
            dsHedging.logme(f"An error occurred during hedging: {e}")
            log.error(f"An error occurred during hedging: {e}")
        dsHedging.logme("Leaving Hedge Modus")
        return False
        