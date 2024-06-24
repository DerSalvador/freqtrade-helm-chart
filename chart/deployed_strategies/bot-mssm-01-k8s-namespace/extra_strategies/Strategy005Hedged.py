kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-mssm-01 exec -it pod/freqtrade-bot-mssm-01-858b999f6c-pf26r -c freqtrade -- cat /extra_strategies/Strategy005Hedged.py
# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
from freqtrade.strategy import CategoricalParameter, IntParameter
from functools import reduce
from pandas import DataFrame
from datetime import datetime
from functools import reduce
# import timeit
from freqtrade.strategy import (IStrategy, DecimalParameter, CategoricalParameter)
from freqtrade.persistence import Trade
import numpy as np
# Get rid of pandas warnings during backtesting
import pandas as pd
from pandas import DataFrame, Series
import scipy
# --------------------------------
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy  # noqa
import pywt
import talib.abstract as ta
from utils.DataframeUtils import DataframeUtils, ScalerType

from sklearn.preprocessing import RobustScaler
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from utils.FuturesPositionsFetcher import FuturesPositionFetcher
from typing import Dict, List, Optional, Tuple, Union

import logging
import warnings

log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

from utils.DataframeUtils import DataframeUtils, ScalerType
import pywt
import talib.abstract as ta

from freqtrade.rpc import RPCManager
from freqtrade.rpc.external_message_consumer import ExternalMessageConsumer
from freqtrade.rpc.rpc_types import (ProfitLossStr, RPCCancelMsg, RPCEntryMsg, RPCExitCancelMsg,
                                     RPCExitMsg, RPCProtectionMsg, RPCMessageType)

from utils.dsHedging import dsHedging

class Strategy005Hedged(IStrategy):
    rpc: RPCManager = None
    # DerSalvador Hedging
    hedging_url = ""
    hedging_leverage = 1
    hedging_stake_amount = 0
    hedging_apikey = ""
    hedging_apisecret = ""    
    existing_position_on_exchange = None    
    """
    Strategy 005
    author@: Gerald Lonlas
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy005
    """
    INTERFACE_VERSION = 3
    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {'1440': 0.01, '80': 0.02, '40': 0.03, '20': 0.04, '0': 0.05}
    # Optimal stoploss designed for the strategy
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.1
    # Optimal timeframe for the strategy
    timeframe = '5m'
    # trailing stoploss
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    # run "populate_indicators" only for new candle
    process_only_new_candles = False
    # Experimental settings (configuration will overide these if set)
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = False
    # Optional order type mapping
    order_types = {'entry': 'limit', 'exit': 'limit', 'stoploss': 'market', 'stoploss_on_exchange': False}
    entry_volumeAVG = IntParameter(low=50, high=300, default=70, space='entry', optimize=True)
    entry_rsi = IntParameter(low=1, high=100, default=30, space='entry', optimize=True)
    entry_fastd = IntParameter(low=1, high=100, default=30, space='entry', optimize=True)
    entry_fishRsiNorma = IntParameter(low=1, high=100, default=30, space='entry', optimize=True)
    exit_rsi = IntParameter(low=1, high=100, default=70, space='exit', optimize=True)
    exit_minusDI = IntParameter(low=1, high=100, default=50, space='exit', optimize=True)
    exit_fishRsiNorma = IntParameter(low=1, high=100, default=50, space='exit', optimize=True)
    exit_trigger = CategoricalParameter(['rsi-macd-minusdi', 'sar-fisherRsi'], default=30, space='exit', optimize=True)
    # Buy hyperspace params:
    entry_params = {'entry_fastd': 1, 'entry_fishRsiNorma': 5, 'entry_rsi': 26, 'entry_volumeAVG': 150}
    # Sell hyperspace params:
    exit_params = {'exit_fishRsiNorma': 30, 'exit_minusDI': 4, 'exit_rsi': 74, 'exit_trigger': 'rsi-macd-minusdi'}
    trade_reset_flags = {}
    # df_coeffs: DataFrame = None
    coeff_array = None
    coeff_model = None
    dataframeUtils = None
    scaler = RobustScaler()

    # Initialize a dictionary to track the start time and reset flag for each trade
    trade_start_times = {}
    trade_reset_flags = {}

    @staticmethod
    def setRPCManager(rpc: RPCManager):
        Strategy005Hedged.rpc = rpc
        
    ############################################
    def hedging_config(self, config) -> None:
        self.hedging_url = config['dersalvador']['hedging']['hedge_bot_api']
        self.hedging_leverage = config['dersalvador']['hedging']['leverage']
        self.hedging_stake_amount = config['dersalvador']['hedging']['stake_amount']
        self.hedging_apikey = config['dersalvador']['hedging']['apikey']
        self.hedging_apisecret = config['dersalvador']['hedging']['apisecret']
        self.hedging_trigger_timeout_seconds = config['dersalvador']['hedging']['trigger_timeout_seconds']
            
    # ###################################
    # def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
    #     self.logme("Bot loop start ")
    #     return 
        
    @staticmethod
    def sendMessageToTelegram(msg: str):
        msg = {
            'type': RPCMessageType.STARTUP,
            'status': f"{msg}"
        }
        if Strategy005Hedged.rpc is not None: 
            Strategy005Hedged.rpc.send_msg(msg)
        else:
            log.warning("RPC Telegram object not initialized in Strategy")
            
    ###################################
    def hedge(self, pair, direction):
        dsHedging.hedge(self, pair, direction)
        
    def bot_start(self, **kwargs) -> None:
        if self.config['dersalvador']['hedging'] is not None:
            msg = self.showHedgingConfig()
            Strategy005Hedged.sendMessageToTelegram(msg)
        else:
            msg="No Hedging section found in config file"
            self.logme(msg)
            Strategy005Hedged.sendMessageToTelegram(msg)

        return

    def showHedgingConfig(self):
        msg = "No hedging config found"
        if self.config['dersalvador']['hedging'] is not None:
            self.hedging_config(self.config)
            msg=f'*Found Hedging section in config*\n'
            msg+=f'*API:* {self.hedging_url}\n'
            msg+=f'*Amount:* {self.hedging_stake_amount}\n' 
            msg+=f'*Leverage:* {self.hedging_leverage}\n'
            self.logme(msg)
        return msg
    
    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    # Define the rapid drop condition
    def rapid_drop_condition(self, dataframe: DataFrame) -> DataFrame:
        dataframe['price_change'] = dataframe['close'].pct_change()
        dataframe['rapid_drop'] = (dataframe['price_change'] < -0.02).rolling(window=5).sum() >= 3
        return dataframe
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        """
        dataframe = self.rapid_drop_condition(dataframe)        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        # Minus Directional Indicator / Movement
        dataframe['minus_di'] = ta.MINUS_DI(dataframe)
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)
        # Inverse Fisher transform on RSI, values [-1.0, 1.0] (https://goo.gl/2JGGoy)
        rsi = 0.1 * (dataframe['rsi'] - 50)
        dataframe['fisher_rsi'] = (numpy.exp(2 * rsi) - 1) / (numpy.exp(2 * rsi) + 1)
        # Inverse Fisher transform on RSI normalized, value [0.0, 100.0] (https://goo.gl/2JGGoy)
        dataframe['fisher_rsi_norma'] = 50 * (dataframe['fisher_rsi'] + 1)
        # Stoch fast
        stoch_fast = ta.STOCHF(dataframe)
        dataframe['fastd'] = stoch_fast['fastd']
        dataframe['fastk'] = stoch_fast['fastk']
        # Overlap Studies
        # ------------------------------------
        # SAR Parabol
        dataframe['sar'] = ta.SAR(dataframe)
        # SMA - Simple Moving Average
        dataframe['sma'] = ta.SMA(dataframe, timeperiod=40)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with entry column
        """
        dataframe.loc[
            (dataframe['rapid_drop']),
            'enter_long'] = 0
        dataframe.loc[
            (dataframe['rapid_drop']),
            'enter_short'] = 1        
        # Prod
        dataframe.loc[(dataframe['close'] > 2e-06) & (dataframe['volume'] > dataframe['volume'].rolling(self.entry_volumeAVG.value).mean() * 4) & (dataframe['close'] < dataframe['sma']) & (dataframe['fastd'] > dataframe['fastk']) & (dataframe['rsi'] > self.entry_rsi.value) & (dataframe['fastd'] > self.entry_fastd.value) & (dataframe['fisher_rsi_norma'] < self.entry_fishRsiNorma.value), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with entry column
        """
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0        
        conditions = []
        if self.exit_trigger.value == 'rsi-macd-minusdi':
            conditions.append(qtpylib.crossed_above(dataframe['rsi'], self.exit_rsi.value))
            conditions.append(dataframe['macd'] < 0)
            conditions.append(dataframe['minus_di'] > self.exit_minusDI.value)
        if self.exit_trigger.value == 'sar-fisherRsi':
            conditions.append(dataframe['sar'] > dataframe['close'])
            conditions.append(dataframe['fisher_rsi'] > self.exit_fishRsiNorma.value)
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        return dataframe
    
    def custom_exit(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        self.showHedgingConfig()
        dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
                          
        self.goShortWithCondition(pair, trade, current_time, current_rate,
                    current_profit, dataframe, **kwargs)

        return None

    def logme(self, msg: str):
        print(f"{msg}")
        log.info(f"{msg}")

    def goShortWithCondition(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float,dataframe: DataFrame, **kwargs):
        # Exit the trade if it has been more than 5 minutes with a negative profit
        self.getPositionInBinance(pair, current_time, current_rate, current_profit)
        dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
            # Example indicator: if MACD is below signal line, indicating bearish trend
            
        if trade.id not in self.trade_start_times:
            # If this is the first time seeing this trade, record the start time
            self.trade_start_times[trade.id] = current_time
            self.trade_reset_flags[trade.id] = False
        
        # Calculate the duration the trade has been open in seconds
        duration = (current_time - self.trade_start_times[trade.id]).total_seconds()
        
        if current_profit > 0 or (int(self.hedging_trigger_timeout_seconds) - duration) < 0: 
            # Reset the timer if profit becomes greater than zero
            self.trade_start_times[trade.id] = current_time
            self.trade_reset_flags[trade.id] = True
        
        last_candle = dataframe.iloc[-1]
                        
        remaining_seconds = int(self.hedging_trigger_timeout_seconds) - duration
        self.logme(f"countdown waiting {self.hedging_trigger_timeout_seconds} seconds to fire hedging process for pair {pair}, remaining {remaining_seconds} seconds until hedging starts")
        if duration > int(self.hedging_trigger_timeout_seconds) and last_candle['rapid_drop'] and current_profit < 0:
            if last_candle['macd'] < last_candle['macdsignal']:
                self.logme(f"Hedging: MACD bearish")
                dsHedging.hedge_me(self, trade, pair, Strategy005Hedged.existing_position_on_exchange)
                log.info(f"Leaving custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
                return 'macd_bearish'
            self.logme(f"Leaving custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}") 

    def getPositionInBinance(self, pair, current_time, current_rate, current_profit):
        self.logme(f"Entering custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
        positionFetcher = FuturesPositionFetcher(self.hedging_apikey, self.hedging_apisecret)
        symbol=pair.split('/')[0]+"USDT"
        Strategy005Hedged.existing_position_on_exchange = positionFetcher.get_futures_position_information(symbol)               
