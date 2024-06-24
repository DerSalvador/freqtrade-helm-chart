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
    def hedge_me(strategy: IStrategy, trade, pair, position):
        if position is None or float(position[0]['positionAmt']) == 0.0:
            dsHedging.logme("No position exist, trying to hedge")
            if trade.is_short: 
                dsHedging.hedge(strategy, pair, "long")
            else:
                dsHedging.hedge(strategy, pair, "short")
        else:
            dsHedging.logme("MSSM: Not hedging because position already exists for {position}")
            
                
    # Do *not* hyperopt for the roi and stoploss spaces
    @staticmethod
    def hedge(strategy: IStrategy, pair, direction):
        # Get the current timestamp in UTC timezone
        dsHedging.logme("Entering Hedge Modus")
        current_timestamp = datetime.now()
        tag=f'ForcedHedging {pair} at {current_timestamp} with leverage {strategy.hedging_leverage}, '
        tag+=f'amount {strategy.hedging_stake_amount}, ' 
        tag+=f'direction {direction} on bot {strategy.hedging_url}'
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
            response = requests.post(strategy.hedging_url, json=payload, headers=headers, auth=auth)
            response.raise_for_status()  # Check for HTTP errors
            if response.status_code == 200:
                dsHedging.logme("Hedging successful. Response:")
                dsHedging.logme(response.json())
            else:
                dsHedging.logme(f"Request returned status code: {response.status_code}")
        except requests.RequestException as e:
            dsHedging.logme(f"An error occurred during hedging: {e}")
            log.error(f"An error occurred during hedging: {e}")
        dsHedging.logme("Leaving Hedge Modus")
        