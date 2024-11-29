kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-mssm-06 exec -it pod/freqtrade-bot-mssm-06-696c8d58c4-fkj6j -c freqtrade -- cat /extra_strategies/LizStrategy.py
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
pd.options.display.float_format = '{:f}'.format
pd.set_option('display.max_columns', None)

import sqlite3

from pandas import DataFrame, Series
import scipy
# --------------------------------
import talib.abstract as ta
import ta as taa
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy  # noqa
import talib
import mailtrap as mt

import requests
import json
import pywt
import talib.abstract as ta
from utils.DataframeUtils import DataframeUtils, ScalerType

from sklearn.preprocessing import RobustScaler
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from utils.FuturesPositionsFetcher import FuturesPositionsFetcher
from typing import Dict, List, Optional, Tuple, Union
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import threading

import logging
import warnings
from scipy.stats import linregress
    
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
import numpy as np
from enum import Enum

# Host live.smtp.mailtrap.io
# Port 587 (recommended), 2525 or 25
# Username api
# Password 50bf8b9214e6cf207cfe6252769ca5e4
# Auth PLAIN, LOGIN
# STARTTLS Required
# curl \
# --ssl-reqd \
# --url 'smtp://live.smtp.mailtrap.io:587' \
# --user 'api:********a5e4' \
# --mail-from mailtrap@demomailtrap.com \
# --mail-rcpt filekeys@gmail.com \
# --upload-file - <<EOF
# From: Magic Elves <mailtrap@demomailtrap.com>
# To: Mailtrap Inbox <filekeys@gmail.com>
# Subject: You are awesome!
# Content-Type: multipart/alternative; boundary="boundary-string"

class Constants(Enum):
    LINEAR_INCREASING = 1
    LINEAR_DECREASING = 2
    LINEAR_STABLE = 3
    PAIR = 4
    MARKET = 5
    
class LizStrategy(IStrategy):
    rpc: RPCManager = None
    # DerSalvador Hedging
    bot_role = ""
    bot_name = ""
    hedging_url = ""
    hedging_leverage = 1
    hedging_stake_amount = 0
    hedging_apikey = ""
    hedging_apisecret = ""
    hedging_analyse_timeframe = "1h"  
    stoploss_apikey = ""
    stoploss_apisecret = ""    
    spot_bot_api_status = ""
    spot_bot_api_forceenter = ""   
    bot_username = ""
    bot_password = ""
    hedging_trigger_timeout_seconds = 0
    hedging_pair_profits_check_array_length = 0
    hedging_aggregated_pair_profits_check_array_length = 0
    hedging_market_profits_check_array_length = 0
    
    existing_position_on_exchange = None    
    trade_start_times = {}
    trigger_linear_regression_adjustment_dict = {}
    pair_dataframe_dict = {}
    aggregated_pair_dataframe_dict = {}
    market_aggregated_pair_dataframe_dict = {}
    stoploss_dataframe_dict = {}
    pair_stoploss_dict = {}
    linearRegressionThreshold_Offset_Adjustment_Market = 0.001    
    linearRegressionThreshold_Offset_Adjustment_Pair = 0.0001
    trigger_linear_regression_adjustment = 300
    linearRegressionIncreasingThreshold_Start_Pair = 0.5
    linearRegressionIncreasingThreshold_Start_Market = 0.2
    linearRegressionIncreasingThreshold_End = 9999999
    linearRegressionDecreasingThreshold_Start_Pair = -0.5
    linearRegressionDecreasingThreshold_Start_Market = -0.2
    linearRegressionDecreasingThreshold_End = -9999999
    linear_regression_winrate_threshold = 0 
    start_profit_abs_positiv = 0.1
    start_profit_abs_negative = -0.1
    stoploss_bot_api = ""
    market_rising_count = 0
    market_falling_count = 0
    market_stable_count = 0
    market_threshold_pct = 0.8
    market_analysis = False
    pair_aggregated_analysis = False
    enable_email_logging = False
    threads = []    
    # Example usage:
    # Replace these with actual credentials and recipient information
    sender_email = 'mailtrap@demomailtrap.com'
    sender_password = '50bf8b9214e6cf207cfe6252769ca5e4'  # or App password if 2FA is enabled
    recipient_email = 'filekeys@gmail.com'
    subject = 'Bot Mail'
    body = 'Test'

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
    process_only_new_candles = True
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
    exit_trigger = CategoricalParameter(['rsi-macd-minusdi', 'sar-fisherRsi'], default="rsi-macd-minusdi", space='exit', optimize=True)
    # Buy hyperspace params:
    entry_params = {'entry_fastd': 1, 'entry_fishRsiNorma': 5, 'entry_rsi': 26, 'entry_volumeAVG': 150}
    # Sell hyperspace params:
    exit_params = {'exit_fishRsiNorma': 30, 'exit_minusDI': 4, 'exit_rsi': 74, 'exit_trigger': 'rsi-macd-minusdi'}

    # Dictionary to keep track of which labels/tags have already been processed
    processed_labels = {}

    # df_coeffs: DataFrame = None
    coeff_array = None
    coeff_model = None
    dataframeUtils = None
    scaler = RobustScaler()
    # Initialize a dictionary to track the start time and reset flag for each trade
    trade_profit_dataframe: DataFrame = pd.DataFrame()
    market_status_df: DataFrame = pd.DataFrame()
    
    @staticmethod
    def setRPCManager(rpc: RPCManager):
        LizStrategy.rpc = rpc
        
    ############################################
    def hedging_config(self, config) -> None:
        self.bot_name = config['bot_name']
        self.bot_role = config['dersalvador']['hedging']['role']
        self.hedging_url = config['dersalvador']['hedging']['hedge_bot_api']
        self.hedging_leverage = config['dersalvador']['hedging']['leverage']
        self.hedging_stake_amount = config['dersalvador']['hedging']['stake_amount']
        self.hedging_apikey = config['dersalvador']['hedging']['apikey']
        self.hedging_apisecret = config['dersalvador']['hedging']['apisecret']
        self.stoploss_apikey = config['dersalvador']['hedging']['stoploss_apikey']
        self.stoploss_apisecret = config['dersalvador']['hedging']['stoploss_apisecret']
        self.hedging_trigger_timeout_seconds = config['dersalvador']['hedging']['trigger_timeout_seconds']
        self.hedging_pair_profits_check_array_length = config['dersalvador']['hedging']['profits_check_array_length']
        self.hedging_aggregated_pair_profits_check_array_length = config['dersalvador']['hedging']['aggregated_profits_check_array_length']
        self.hedging_market_profits_check_array_length = config['dersalvador']['hedging']['market_profits_check_array_length']
        self.spot_bot_api_status = config['dersalvador']['hedging']['spot_bot_api_status']
        self.spot_bot_api_forceenter = config['dersalvador']['hedging']['spot_bot_api_forceenter']
        self.hedge_bot_api_status = config['dersalvador']['hedging']['hedge_bot_api_status']
        self.hedge_bot_api_profit = config['dersalvador']['hedging']['hedge_bot_api_profit']
        self.bot_username =  config['api_server']['username']
        self.bot_password =  config['api_server']['password']
        self.linearRegressionThreshold_Offset_Adjustment_Pair = config['dersalvador']['hedging']['linearRegressionThreshold_Offset_Adjustment_Pair'] 
        self.linearRegressionThreshold_Offset_Adjustment_Market = config['dersalvador']['hedging']['linearRegressionThreshold_Offset_Adjustment_Market']
        self.trigger_linear_regression_adjustment = config['dersalvador']['hedging']['trigger_linear_regression_adjustment']
        self.linearRegressionIncreasingThreshold_Start_Pair = config['dersalvador']['hedging']['linearRegressionIncreasingThreshold_Start_Pair']
        self.linearRegressionIncreasingThreshold_Start_Market = config['dersalvador']['hedging']['linearRegressionIncreasingThreshold_Start_Market']
        self.linearRegressionIncreasingThreshold_End = config['dersalvador']['hedging']['linearRegressionIncreasingThreshold_End']
        self.linearRegressionDecreasingThreshold_Start_Pair = config['dersalvador']['hedging']['linearRegressionDecreasingThreshold_Start_Pair']
        self.linearRegressionDecreasingThreshold_Start_Market = config['dersalvador']['hedging']['linearRegressionDecreasingThreshold_Start_Market']
        self.linearRegressionDecreasingThreshold_End = config['dersalvador']['hedging']['linearRegressionDecreasingThreshold_End']
        self.linear_regression_winrate_threshold = config['dersalvador']['hedging']['linear_regression_winrate_threshold']
        self.start_profit_abs_positiv = config['dersalvador']['hedging']['start_profit_abs_positiv']
        self.start_profit_abs_negative = config['dersalvador']['hedging']['start_profit_abs_negative']
        self.stoploss_bot_api  = config['dersalvador']['hedging']['stoploss_bot_api']
        self.market_threshold_pct  = config['dersalvador']['hedging']['market_threshold_pct']
        self.market_analysis = config['dersalvador']['hedging']['market_analysis']
        self.pair_aggregated_analysis = config['dersalvador']['hedging']['pair_aggregated_analysis']
        self.enable_email_logging = config['dersalvador']['enable_email_logging']
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
        if LizStrategy.rpc is not None: 
            LizStrategy.rpc.send_msg(msg)
        else:
            log.warning("RPC Telegram object not initialized in Strategy")
            
    ###################################
    def hedge(self, pair, direction):
        dsHedging.hedge(self, pair, direction)
        
    def bot_start(self, **kwargs) -> None:
        if self.config['dersalvador']['hedging'] is not None:
            self.hedging_config(self.config)
            msg = self.showHedgingConfig()
            LizStrategy.sendMessageToTelegram(msg)
        else:
            msg="No Hedging section found in config file"
            self.logme(msg)
            LizStrategy.sendMessageToTelegram(msg)

        return

    def showHedgingConfig(self):
        msg = "No hedging config found"
        if self.config['dersalvador']['hedging'] is not None:
            msg=f'*Found Hedging section in config*\n'
            msg+=f'*Role:* {self.bot_role}\n'
            msg+=f'*API:* {self.hedging_url}\n'
            msg+=f'*Amount:* {self.hedging_stake_amount}\n' 
            msg+=f'*Leverage:* {self.hedging_leverage}\n'
            msg+=f'*profits_check_array_length:* {self.hedging_pair_profits_check_array_length}\n'
            msg+=f'*aggregated_profits_check_array_length:* {self.hedging_aggregated_pair_profits_check_array_length}\n'
            msg+=f'*market_profits_check_array_length:* {self.hedging_market_profits_check_array_length}\n'
            msg+=f'*trigger_timeout_seconds:* {self.hedging_trigger_timeout_seconds}\n'
            msg+=f'*spot_bot_api_status:* {self.spot_bot_api_status}\n'
            msg+=f'*spot_bot_api_forceenter:* {self.spot_bot_api_forceenter}\n'
            msg+=f'*bot_username:* {self.bot_username}\n'
            msg+=f'*bot_password:* {self.bot_password}\n'
            msg+=f'*linearRegressionIncreasingThreshold_Start_Pair:* {self.linearRegressionIncreasingThreshold_Start_Pair}\n'
            msg+=f'*linearRegressionIncreasingThreshold_Start_Market:* {self.linearRegressionIncreasingThreshold_Start_Market}\n'
            msg+=f'*linearRegressionIncreasingThreshold_End:* {self.linearRegressionIncreasingThreshold_End}\n'
            msg+=f'*linearRegressionDecreasingThreshold_Start_Pair:* {self.linearRegressionDecreasingThreshold_Start_Pair}\n'
            msg+=f'*linearRegressionDecreasingThreshold_Start_Market:* {self.linearRegressionDecreasingThreshold_Start_Market}\n'
            msg+=f'*linearRegressionDecreasingThreshold_End:* {self.linearRegressionDecreasingThreshold_End}\n'
            msg+=f'*start_profit_abs_positiv:* {self.start_profit_abs_positiv}\n'
            msg+=f'*start_profit_abs_negative:* {self.start_profit_abs_negative}\n'
            msg+=f'*stoploss_bot_api:* {self.stoploss_bot_api}\n'
            msg+=f'*market_analysis:* {self.market_analysis}\n'
            msg+=f'*pair_aggregated_analysis:* {self.pair_aggregated_analysis}\n'
            msg+=f'*market_threshold_pct:* {self.market_threshold_pct}\n'
            msg+=f'*linearRegressionThreshold_Offset_Adjustment_Pair:* {self.linearRegressionThreshold_Offset_Adjustment_Pair}\n'
            msg+=f'*linearRegressionThreshold_Offset_Adjustment_Market:* {self.linearRegressionThreshold_Offset_Adjustment_Market}\n'
            msg+=f'*trigger_linear_regression_adjustment:* {self.trigger_linear_regression_adjustment}\n'
            msg+=f'*linear_regression_winrate_threshold:* {self.linear_regression_winrate_threshold}\n'
            msg+=f'*enable_email_logging:* {self.enable_email_logging}\n'
            
            self.logme(msg)
        return msg

    def resetDatabase(self):
        data_dir = self.config['dersalvador']['database_path']
        conn = None 
        try:
            # data_dir = "/Users/msantana/dersalvador/freqtrading/freqtrade/user_data/tradesv3.sqlite" # self.config['db_url']
            # conn = sqlite3.connect(os.path.join(data_dir, "tradesv3.sqlite"))
            conn = sqlite3.connect(data_dir)
            cursor = conn.cursor()

            # cursor.execute(".tables")
            self.logme(cursor.fetchall())
            cursor.execute("delete from KeyValueStore;")
            cursor.execute("delete from orders;")
            cursor.execute("delete from trades;")
            cursor.execute("delete from pairlocks;")
            cursor.execute("delete from trade_custom_data;")
            cursor.execute("select count(*) from trades;")
            self.logme(cursor.fetchall())
        except Exception as ex:
          self.logme(f"Something went wrong in resetDatabase: {ex}")
        finally:
            if conn is not None:
                conn.close()
            print('resetDatabase: The try except is finished')
            
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
        # get access to all pairs available in whitelist.
        pairs = self.dp.current_whitelist()
        # Assign tf to each pair so they can be downloaded and cached for strategy.
        informative_pairs = [(pair, self.hedging_analyse_timeframe) for pair in pairs]
        return informative_pairs
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        """ 
        # MACD
        if self.bot_role == "strategy":         
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
        else:
            self.logme(f"Bot {self.bot_name} Role is {self.bot_role} and not strategy, ignoring entry and exit trends...")
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with entry column
        """
        dataframe.loc[(), 'enter_long'] = 0
        dataframe.loc[(), 'enter_short'] = 0
        dataframe.loc[(), 'exit_short'] = 0    
        dataframe.loc[(), 'exit_long'] = 0    
        if self.bot_role == "strategy":         
            dataframe.loc[(dataframe['close'] > 2e-06) & (dataframe['volume'] > dataframe['volume'].rolling(self.entry_volumeAVG.value).mean() * 4) & (dataframe['close'] < dataframe['sma']) & (dataframe['fastd'] > dataframe['fastk']) & (dataframe['rsi'] > self.entry_rsi.value) & (dataframe['fastd'] > self.entry_fastd.value) & (dataframe['fisher_rsi_norma'] < self.entry_fishRsiNorma.value), 'enter_long'] = 1
        else:
            self.logme(f"Bot {self.bot_name} Role is {self.bot_role} and not strategy, ignoring entry and exit trends...")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with entry column
        """
        dataframe.loc[(), 'enter_long'] = 0
        dataframe.loc[(), 'enter_short'] = 0
        dataframe.loc[(), 'exit_short'] = 0    
        dataframe.loc[(), 'exit_long'] = 0    
        if self.bot_role == "strategy":         
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
            else:
                dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 0
        else:
            self.logme(f"Bot {self.bot_name} Role is {self.bot_role} and not strategy, ignoring entry and exit trends...")
        return dataframe
    
    def remove_decimal_digits(self, num):
        num_str = str(num)        
        if '.' not in num_str:
            return num  # Return the number as is if there's no decimal point
        decimal_index = num_str.index('.')
        # Find the first non-zero digit after the decimal point
        for i in range(decimal_index + 1, len(num_str)):
            if num_str[i] != '0':
                new_num_str = num_str[:i + 1]
                break
        else:
            # In case there are no non-zero digits after the decimal point
            new_num_str = num_str[:decimal_index + 2]
        new_num = float(new_num_str)
        return new_num

    def custom_stoploss(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        newstoploss = self.config['stoploss']
        if self.bot_role == "mixed" or self.bot_role == "hedger":
            if pair not in self.pair_stoploss_dict:
                self.pair_stoploss_dict[pair] = float(self.config['stoploss'])
            self.logme(f"----------------------------------------------------------")
            self.logme(f"Entering custom stoploss for pair {pair}, current stoploss value {self.pair_stoploss_dict[pair]}")
            stoploss_distance_to_zero = trade.amount*trade.open_rate*trade.stop_loss_pct-current_profit
            self.logme(f"Stoploss distance for pair {pair}: {stoploss_distance_to_zero}")
            # config_stoploss = float(self.config['stoploss'])
            t = self.getJsonTrade(pair)
            if t is not None:
                profit_abs = t.get('profit_abs')
            else:
                s = f"No Trade found for Pair {pair} in custom_stoploss function"
                raise Exception(s)
            current_profit = profit_abs        
            if current_profit < 0:
                newstoploss = self.pair_stoploss_dict[pair] - 0.001
            else:
                newstoploss = self.pair_stoploss_dict[pair] + 0.002
            # Stoploss passed 100%
            if newstoploss < -0.5:
                newstoploss = -0.5
            # Stoploss in direction positive
            if newstoploss > 0:
                newstoploss = -0.1
            self.logme(f"Setting new stoploss pct to {newstoploss} based on config stoploss {self.config['stoploss']} and current_profit {current_profit} with offset 0.01, for pair {pair} in bot {self.bot_name}")
            self.pair_stoploss_dict[pair] = newstoploss
        else:
            self.logme(f"Bot role is {self.bot_role}, only bot role hedger uses custom stoploss")
        return newstoploss

    def adjustLinearRegressionThreshold(self):
        json = self.getJsonFromAPI(self.hedge_bot_api_profit)
        profit_all_coin = json['profit_all_coin']
        winning_trades = json['winning_trades']
        loosing_trades = json['losing_trades']
        winrate = json['winrate']
        self.logme(f"Profit in hedgebot {self.hedge_bot_api_profit} for all coins is: {profit_all_coin}" )
        if profit_all_coin < 0: 
            self.logme(f"@@@@@@@@@@@@@@@@@@@@ Profit all coins is negative {profit_all_coin}, adjusting linear market regression threshold with value " + 
                       f"{self.linearRegressionThreshold_Offset_Adjustment_Market} @@@@@@@@@@@@@@@@@@@@ ")
            self.logme(f"@@@@@@@@@@@@@@@@@@@@ Profit all coins is negative {profit_all_coin}, adjusting linear pair regression threshold with value" +
                       f"{self.linearRegressionThreshold_Offset_Adjustment_Pair} @@@@@@@@@@@@@@@@@@@@")
            self.logme(f"Adjusting Linear Regression Slope and resetting database to start over")
            self.resetDatabase()
            self.hedging_trigger_timeout_seconds += 1
            self.hedging_market_profits_check_array_length += 1
            self.linearRegressionDecreasingThreshold_Start_Market -= self.linearRegressionThreshold_Offset_Adjustment_Market
            self.linearRegressionDecreasingThreshold_Start_Pair -= self.linearRegressionThreshold_Offset_Adjustment_Pair
            self.linearRegressionIncreasingThreshold_Start_Market += self.linearRegressionThreshold_Offset_Adjustment_Market
            self.linearRegressionIncreasingThreshold_Start_Pair += self.linearRegressionThreshold_Offset_Adjustment_Pair
            if self.bot_role == "hedger" or self.bot_role == "mixed":
                self.send_email(f"Profit all Coins is negative {profit_all_coin}\n" + 
                                f"adjusting slope threshold, New linear regression adjustment for Market is {self.linearRegressionDecreasingThreshold_Start_Market}\n" + 
                                f"New linear regression adjustment for Pair Decreasing is {self.linearRegressionDecreasingThreshold_Start_Pair}\n" + 
                                f"New linear regression adjustment for Market Decreasing is {self.linearRegressionDecreasingThreshold_Start_Market}\n" + 
                                f"New linear regression adjustment for Pair Increasing is {self.linearRegressionIncreasingThreshold_Start_Pair}\n" + 
                                f"New linear regression adjustment for Market Increasing is {self.linearRegressionIncreasingThreshold_Start_Market}"
                                )

        else:
            if self.bot_role == "hedger" or self.bot_role == "mixed":
                self.send_email(f"Winrate is {winrate} with profit all coins {profit_all_coin}, use following parameters for the configuration\n" + 
                                f"Current linear regression adjustment for Market Decreasing is {self.linearRegressionDecreasingThreshold_Start_Market}\n" +
                                f"Current linear regression adjustment for Pair Decreasing is {self.linearRegressionDecreasingThreshold_Start_Pair}\n" +
                                f"Current linear regression adjustment for Market Increasing is {self.linearRegressionIncreasingThreshold_Start_Market}\n" +
                                f"Current linear regression adjustment for Pair Increasing is {self.linearRegressionIncreasingThreshold_Start_Pair}\n" +
                                f"hedging_trigger_timeout_seconds: {self.hedging_trigger_timeout_seconds}"
                                )
            self.logme(f"Profit all coins is positive {profit_all_coin}, with following configuration")
            self.logme(f"linearRegressionDecreasingThreshold_Start_Market: {self.linearRegressionDecreasingThreshold_Start_Market}")
            self.logme(f"linearRegressionDecreasingThreshold_Start_Pair: {self.linearRegressionDecreasingThreshold_Start_Pair}")
            self.logme(f"linearRegressionIncreasingThreshold_Start_Market: {self.linearRegressionIncreasingThreshold_Start_Market}")
            self.logme(f"linearRegressionIncreasingThreshold_Start_Pair: {self.linearRegressionIncreasingThreshold_Start_Pair}")
            self.logme(f"hedging_trigger_timeout_seconds: {self.hedging_trigger_timeout_seconds}")
            
    def force_enter_trade(self, pair):
        # Example usage:
        side = "long"
        ordertype = "market"
        stake_amount = 1000  # Replace with your STAKE
        leverage = 1  # Replace with your LEVERAGE
        username = self.config['api_server']['username']
        password = self.config['api_server']['password']
        entry_tag = f"Force entry in bot {self.bot_name} to fill status table for market evaluation and hedging."
        url = self.spot_bot_api_forceenter
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        data = {
            "pair": pair,
            "side": side,
            "ordertype": ordertype,
            "stakeamount": stake_amount,
            "entry_tag": entry_tag,
            "leverage": leverage
        }
        auth = (username, password)
        try:
            response = requests.post(url, json=data, headers=headers, auth=auth)
            response.raise_for_status()  # Check for HTTP errors
            if response.status_code == 200:
                dsHedging.logme("Force Enter successful. Response:")
                dsHedging.logme(response.json())
                return True
            else:
                dsHedging.logme(f"Request returned status code: {response.status_code}")            
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"force_enter_trade: {self.bot_name}: HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"force_enter_trade: {self.bot_name}: Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"force_enter_trade: {self.bot_name}: Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"force_enter_trade: {self.bot_name}: An error occurred: {req_err}")


    def custom_exit(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        if self.bot_role != "master" and self.bot_role != "mixed" : 
            self.logme(f"Bot {self.bot_name} role is {self.bot_role} and not master, leaving custom_exit... ")
            return False
        self.logme(f"Wait until Status table has at least as much positions as the current whitelist, otherwise ignore custom_exit...")
        whitelist_len = len(self.dp.current_whitelist())
        if whitelist_len == 0:
            self.logme(f"Whitelist is still empty for bot {self.bot_name}, waiting until whitelist is filled")
            return False
        positions = self.getJsonFromAPI(self.spot_bot_api_status)
        positions_len = len(positions)
        # if positions_len < whitelist_len:
        #     self.logme(f"Need to create positions according to whitelist length or whitelist is still empty, whitelist_length={whitelist_len}...")
        #     for pair in self.dp.current_whitelist(): 
        #         self.logme(f"Creating position for pair {pair} in bot {self.config['bot_name']}")
        #         self.force_enter_trade(pair)
        if positions_len >= whitelist_len:
            self.logme(f"Created {positions_len} positions, whitelist length {whitelist_len} hedging process can continue")
        else:
            self.logme(f"Not enough positions {positions_len} created, must reach at least whitelist length {whitelist_len}")
            return False
        self.logme(f"Entering custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")        
        run_mode = self.dp.runmode.value
        # if run_mode in ('backtest', 'live', 'dry_run'):        
        if run_mode in ('live', 'dry_run'):  
            self.showHedgingConfig()
            dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
            self.hedgeMe(pair, trade, current_time, current_rate,
                        current_profit, dataframe, **kwargs)
        # else:
        #     self.logme(f"Run mode is: {run_mode}")
        return None
        # self.showHedgingConfig()
        # dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
                          
        # self.hedgeMe(pair, trade, current_time, current_rate,
        #             current_profit, dataframe, **kwargs)

        # return False

    def logme(self, msg: str):
        # print(f"{msg}")
        log.info(f"{msg}")

    def getJsonFromAPI(self, endpoint):
        url = f"{endpoint}"
        auth = (self.bot_username, self.bot_password)

        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Ensure we notice bad responses
        data = response.json()
        return data

    def getJsonTrade(self, pair, endpoint=None):
        if endpoint is None:
            endpoint = self.spot_bot_api_status
        url = f"{endpoint}"
        auth = (self.bot_username, self.bot_password)

        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Ensure we notice bad responses
        if '/USDT' not in pair:
            pair += '/USDT'
        if ':USDT' not in pair:
            pair += ':USDT'
        data = response.json()
        for trade in data:
            if (trade.get('pair') == pair):
                # jsonTrade.profit_abs = trade.get('profit_abs')
                # jsonTrade.stoploss_entry_dist = = trade.get('stoploss_entry_dist')
                # return trade.get('profit_abs')
                return trade
        return None

    def getStatusTableAsDataframe(self, endpoint=None):
        if endpoint is None:
            endpoint = self.spot_bot_api_status
        url = f"{endpoint}"
        auth = (self.bot_username, self.bot_password)
        self.market_status_df = pd.DataFrame()
        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Ensure we notice bad responses
        # if '/USDT' not in pair:
        #     pair += '/USDT'
        # if ':USDT' not in pair:
        #     pair += ':USDT'
        data = response.json()
        for trade in data:            
            pair = trade.get('pair')
            current_profit = trade.get('profit_abs')
            tradeid = trade.get("trade_id")
            open_timestamp = trade.get("open_timestamp")
            stop_loss_pct = trade.get("stop_loss_pct")
            new_row = {
                       'label': "status_table",                  
                       'timestamp': open_timestamp, 
                       'current_profit': current_profit, 
                       'pair': pair, 
                       "trade_id": tradeid, 
                       "stop_loss_pct": stop_loss_pct}
            if self.market_status_df.empty:
                new_rows_df = pd.DataFrame(new_row, index=[0])
            else:
                new_rows_df = pd.DataFrame(new_row, index=[len(self.market_status_df['timestamp'])])
            self.market_status_df = self.market_status_df._append(new_rows_df)
        return self.market_status_df

    def send_email(self, body):
        try:
            enableEmail = self.config['dersalvador']['enable_email_logging']
            if enableEmail:
                mail = mt.Mail(
                    sender=mt.Address(email="mailtrap@demomailtrap.com", name=f"{self.bot_name}: Bot Mail"),
                    to=[mt.Address(email="filekeys@gmail.com")],
                    subject=f"{self.bot_name}: Bot Email",
                    text=body,
                    category="Integration Test",
                )
                client = mt.MailtrapClient(token="50bf8b9214e6cf207cfe6252769ca5e4")
                client.send(mail)
            else:
                self.logme(f"Not send logs to email: enableEmail={enableEmail}")            
        except Exception as e:
            print(f'Failed to send email. Error: {str(e)}')
        
    def hedgeMe(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float, dataframe: DataFrame, **kwargs): 
        hedged = False;
        self.logme(f"MSSM: Entering Hedging Logic for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}") 
        if self.bot_role == "hedger" or self.bot_role == "mixed":
            t = self.getJsonTrade(pair, self.hedge_bot_api_status)
        else:
            t = self.getJsonTrade(pair)
        
        if t is not None:
            profit_abs = t.get('profit_abs')
            self.logme(f"Profit via Json API = {profit_abs}, current_profit via freqtrade custom_exit function = {current_profit}")
            # self.logme(dataframe)
            # Exit the trade if it has been more than 5 minutes with a negative profit
            if profit_abs > self.start_profit_abs_positiv or profit_abs < self.start_profit_abs_negative: 
                existing_position_on_exchange = self.getPositionInBinance(pair, self.hedging_apikey, self.hedging_apisecret)
                # dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
                # current_profit = self.remove_decimal_digits(profit_abs)
                hedged = self.hedgeMeCore(pair, trade, current_time, current_rate, profit_abs, existing_position_on_exchange)
            else:
                self.logme(f"Filtering profit abs {profit_abs} because is inside range start_profit_abs_negative-start_profit_abs_positiv: {self.start_profit_abs_negative}-{self.start_profit_abs_positiv}")
        else:
            self.logme(f"Pair {pair} not found via Json API in bot {self.bot_name}")
        return hedged

    def get_aggregated_pair_dataframe_from_dict(self, key):
        if key in self.aggregated_pair_dataframe_dict:
            return self.aggregated_pair_dataframe_dict[key]
        else:
            empty_df = pd.DataFrame()
            self.aggregated_pair_dataframe_dict[key] = empty_df
            return empty_df

    def set_aggregated_pair_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        self.aggregated_pair_dataframe_dict[key] = dataframe
    
    def get_pair_dataframe_from_dict(self, key):
        if key in self.pair_dataframe_dict:
            return self.pair_dataframe_dict[key]
        else:
            empty_df = pd.DataFrame()
            self.pair_dataframe_dict[key] = empty_df
            return empty_df
    
    def set_pair_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        self.pair_dataframe_dict[key] = dataframe
    
    def get_market_aggregated_pair_dataframe_from_dict(self, key):
        if key in self.market_aggregated_pair_dataframe_dict:
            return self.market_aggregated_pair_dataframe_dict[key]
        else:
            empty_df = pd.DataFrame()
            self.market_aggregated_pair_dataframe_dict[key] = empty_df
            return empty_df

    def set_market_aggregated_pair_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        self.market_aggregated_pair_dataframe_dict[key] = dataframe
    
    def get_stoploss_dataframe_from_dict(self, key):
        if key in self.stoploss_dataframe_dict:
            return self.stoploss_dataframe_dict[key]
        else:
            empty_df = pd.DataFrame()
            self.stoploss_dataframe_dict[key] = empty_df
            return empty_df

    def set_stoploss_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        self.stoploss_dataframe_dict[key] = dataframe
       
    def hedgeMeCore(self, pair, trade, current_time, current_rate, profit_abs, existing_position_on_exchange):
        profit_abs = round(profit_abs,2)
        seconds_past_pair = 0
        seconds_past_linear_regression = 0
        current_profit = profit_abs
        if pair not in self.trade_start_times:
            self.trade_start_times[pair] = current_time
        if pair not in self.trigger_linear_regression_adjustment_dict:
            self.trigger_linear_regression_adjustment_dict[pair] = current_time            
        hedged: bool = False
        seconds_past_pair = (current_time - self.trade_start_times[pair]).total_seconds()
        seconds_past_linear_regression = (current_time - self.trigger_linear_regression_adjustment_dict[pair]).total_seconds()
        if  self.hedging_trigger_timeout_seconds > 0: 
            self.logme(f"Triggering Hedging after {self.hedging_trigger_timeout_seconds} seconds, seconds past: {seconds_past_pair}")
        
        if (seconds_past_linear_regression >= int(self.trigger_linear_regression_adjustment)):
            self.logme(f"Adjusting linear regression threshold after {self.trigger_linear_regression_adjustment} seconds...")
            if self.bot_role == "hedger" or self.bot_role == "mixed":
                self.send_email(f"Triggering linear regression adjustment after {self.trigger_linear_regression_adjustment} seconds")
            self.adjustLinearRegressionThreshold()
            for key in self.trigger_linear_regression_adjustment_dict:
                self.trigger_linear_regression_adjustment_dict[key] = current_time
        else:
            self.logme(f"Remaining {self.trigger_linear_regression_adjustment - seconds_past_pair} seconds before adjusting linear threshold adjustment after {self.trigger_linear_regression_adjustment}")

        if seconds_past_pair >= int(self.hedging_trigger_timeout_seconds):
            # if self.trade_profit_dataframe.empty:
            #     new_rows_df = pd.DataFrame(new_row, index=[0])
            # else:            
            #     new_rows_df = pd.DataFrame(new_row, index=[len(self.trade_profit_dataframe)])            
            # self.trade_profit_dataframe = self.trade_profit_dataframe._append(new_rows_df)
                # self.trade_profit_dataframe = self.trade_profit_dataframe._append(self.getStatusTableAsDataframe(), ignore_index=True) 
                #self.trade_profit_dataframe.reset_index(drop=True)
                # aggregate market status dataframe to one aggregated dataframe
                # aggregate pair dataframes to on aggregated dataframe
            # for key in self.trade_start_times:
            #     self.trade_start_times[key] = current_time
            # Check if the label has already been processed
            self.trade_start_times[pair] = current_time
            if pair in self.processed_labels:
                print(f"Label '{pair}' already processed, skipping function execution.")
                del self.processed_labels[pair]
            else:
                self.processed_labels[pair] = True
                thread = threading.Thread(target=self.pair_processing, args=(pair,current_time, current_profit, trade.id,))
                thread.start()
            # pair, pair_dataframe, filtered_df, aggregate_df = self.pair_processing(pair)
            # self.threads.append(thread)                    
            self.populateAggregatedMarketDataframe(current_time)
            self.logme(f"Length of aggregated market dataframe={len(self.get_market_aggregated_pair_dataframe_from_dict(Constants.MARKET))}, maximum configured={self.hedging_pair_profits_check_array_length}")
            market_aggregrated_df = self.get_market_aggregated_pair_dataframe_from_dict(Constants.MARKET)
            market_aggregrated_df = self.get_market_aggregated_pair_dataframe_from_dict(Constants.MARKET)
            aggregate_df = self.get_aggregated_pair_dataframe_from_dict(pair)
            pair_dataframe = self.get_pair_dataframe_from_dict(pair)
            # if aggregate_df is not None and len(aggregate_df) >= self.hedging_aggregated_pair_profits_check_array_length:
            if pair_dataframe is not None and len(pair_dataframe) >= self.hedging_pair_profits_check_array_length:
                if len(market_aggregrated_df) >= self.hedging_market_profits_check_array_length:
                    self.hedging_market_profits_check_array_length *= -1
                    market_aggregrated_df = market_aggregrated_df.iloc[self.hedging_market_profits_check_array_length:]
                self.logme(f"++++ Start Check Trends ++++++++++++++++++++++")
                self.logme(f"Checking now trends for pair {pair}")
                pair_dataframe = self.get_pair_dataframe_from_dict(pair)
                # if pair_dataframe is not None and len(pair_dataframe) >= self.hedging_pair_profits_check_array_length:                
                hedged = self.checkTrends(pair, trade, current_time, current_rate, current_profit, pair_dataframe, market_aggregrated_df, aggregate_df, existing_position_on_exchange, "pair") 
                # filtered_df = self.trade_profit_dataframe[self.trade_profit_dataframe['pair'] != pair]
                # filtered_df = filtered_df.reset_index(drop=True)
                # self.trade_profit_dataframe = filtered_df
                self.dumpCurrentProfitAsArray(market_aggregrated_df)
                self.set_aggregated_pair_dataframe_from_dict(pair, pd.DataFrame())
                self.set_pair_dataframe_from_dict(pair, pd.DataFrame())
                self.set_market_aggregated_pair_dataframe_from_dict(Constants.MARKET, pd.DataFrame())
                # market_aggregrated_df.drop(index=market_aggregrated_df.index, inplace=True)
                # market_aggregrated_df = self.get_market_aggregated_pair_dataframe_from_dict(Constants.MARKET)
                # self.logCheckEnd(pair, filtered_df)
                pair_dataframe.drop(index=pair_dataframe.index, inplace=True)
                self.set_pair_dataframe_from_dict(pair, pd.DataFrame())                
                self.logme(f"++++ End Check Trends ++++++++++++++++++++++")
                self.logme(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")                
        if hedged:
            result_market = self.get_market_aggregated_pair_dataframe_from_dict(Constants.MARKET)['current_profit'].to_string(header=False, index=False).replace('\n', ',')
            result_pair = pair_dataframe['current_profit'].to_string(header=False, index=False).replace('\n', ',')
            if self.bot_role == "hedger":
                self.send_email(f"#################### Successfully hedged Dataframe for Pair {pair}, Pair Dataframe:\n{pair_dataframe}\n" + 
                                f"Market Dataframe:\n{self.get_market_aggregated_pair_dataframe_from_dict(Constants.MARKET)}\n" +
                                f"Aggregated Pair Dataframe:\n{self.get_aggregated_pair_dataframe_from_dict(pair_dataframe.iloc[0]['pair'])}\n"
                                f"Market Dataframe Array for Jupyter:\n{result_market}\n"
                                f"Pair Dataframe Array for Jupyter::\n{result_pair}\n"
                                )
        self.logme(f"Leaving Hedging Modus for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
        return hedged

    def pair_processing(self, pair, current_time, current_profit, trade_id):
        # Process the function for the label
        print(f"Processing function for label '{pair}'")
        lock = threading.Lock()
        # Acquire a lock for the label to ensure only one thread processes it
        try:
            lock.acquire()
            self.logme(f"Thread: all positions dataframe")
            new_row = { 
                        'label': "pair", 
                        'timestamp': current_time, 
                        'current_profit': current_profit, 
                        'pair': pair, 
                        "trade_id": trade_id
                        }            
            pair_dataframe = self.get_pair_dataframe_from_dict(pair)
            if pair_dataframe.empty:
                new_rows_df = pd.DataFrame(new_row, index=[0])
            else:            
                new_rows_df = pd.DataFrame(new_row, index=[len(pair_dataframe)])            
            pair_dataframe = pair_dataframe._append(new_rows_df)
            self.set_pair_dataframe_from_dict(pair, pair_dataframe)            
            if pair_dataframe.empty == False and pair_dataframe is not None:
                pair_dataframe['label'] = "Pair"
                pair_dataframe = pair_dataframe.reset_index(drop=True)
                self.logme(f"Thread: {pair} pair dataframe")
                self.logme(f"Extracting pair {pair} from dataframe until {self.hedging_pair_profits_check_array_length} elements are reached, now: {len(pair_dataframe)} ")
                self.dumpCurrentProfitAsArray(pair_dataframe)
                if len(pair_dataframe) >= self.hedging_pair_profits_check_array_length:
                    self.populateAggregatedPairDataframe(pair, pair_dataframe, current_time)
                    # pair_dataframe.drop(index=pair_dataframe.index, inplace=True)
                    # self.set_pair_dataframe_from_dict(pair, pd.DataFrame())
            else:
                self.logme(f"Pair dataframe is empty")
        finally:
            self.logme(f"Thread pair_processing {pair} is finished")
            del self.processed_labels[pair]
            # Release the lock
            lock.release()
                    
        return

    def populateAggregatedPairDataframe(self, pair, pair_dataframe, current_time):
        cumulated_current_profit = pair_dataframe['current_profit'].sum()
        new_aggregate_row = { 
                    'label': "aggregated_pairs", 
                    'timestamp': current_time, 
                    'current_profit': cumulated_current_profit,
                    'pair': pair_dataframe.iloc[0]['pair'], 
                    'trade_id': pair_dataframe.iloc[0]['trade_id']
                }
        aggregate_df = self.get_aggregated_pair_dataframe_from_dict(pair)
        aggregate_df = aggregate_df._append(new_aggregate_row, ignore_index=True)                
        self.set_aggregated_pair_dataframe_from_dict(pair, aggregate_df)
        self.logme(f"Aggregated Dataframe Length for pair {pair}: {len(aggregate_df)}")
        self.dumpCurrentProfitAsArray(aggregate_df)
        return aggregate_df

    def populateAggregatedMarketDataframe(self, current_time):
        status_df = self.getStatusTableAsDataframe()
        # Identify indices of rows with lowest and highest current_profit values
        if not status_df.empty:
            # lowest_index = status_df['current_profit'].idxmin()
            # highest_index = status_df['current_profit'].idxmax()

            # # Drop rows with lowest and highest values
            # status_df = status_df.drop([lowest_index, highest_index])        
            cumulated_market_profit = status_df['current_profit'].sum()
            new_market_aggregate_row = {
                    'label': "aggregated_market",                 
                    'timestamp': current_time, 
                    'current_profit': cumulated_market_profit 
                }
            market_aggregate_df = self.get_market_aggregated_pair_dataframe_from_dict(Constants.MARKET)
            market_aggregate_df = market_aggregate_df._append(new_market_aggregate_row, ignore_index=True)                
            self.set_market_aggregated_pair_dataframe_from_dict(Constants.MARKET, market_aggregate_df)
            self.logme(f"Aggregated Markt Dataframe with slope value:")
            self.dumpCurrentProfitAsArray(market_aggregate_df)

    def logCheckEnd(self, pair, df):
        self.logme(f"END of Checking trends for pair {pair}")
        self.logme(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        self.logme(f"Filtered out {pair}, remaining dataframe")
        self.dumpCurrentProfitAsArray(df)
        self.logme(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    
    def checkTrends(self, pair, trade, current_time, current_rate, current_profit, pair_dataframe, market_aggregrated_df, aggregate_df, existing_position_on_exchange, infix=""):
        hedged: bool = False
        trend_pair, slope_pair = self.detectLinearRegression(pair_dataframe, Constants.PAIR)
        trend_market, slope_market = self.detectLinearRegression(market_aggregrated_df, Constants.MARKET)
        if self.market_analysis == False:
            self.logme(f"Market Analysis is disabled")
            trend_market = trend_pair
            slope_market = 0
        trend_pair_aggregated, slope_pair_aggregated = self.detectLinearRegression(aggregate_df, Constants.PAIR)
        if self.pair_aggregated_analysis == False:
            self.logme(f"Pair Aggregated Analysis is disabled")
            trend_pair_aggregated = trend_pair
            slope_pair_aggregated = 0
        self.logme(f"Trend Pair {pair}")
        self.dumpCurrentProfitAsArray(pair_dataframe)
        self.logme(f"Trend Market")
        self.dumpCurrentProfitAsArray(market_aggregrated_df)
        self.logme(f"Trend Pair Aggregated {pair}")
        self.dumpCurrentProfitAsArray(aggregate_df)
        self.logme(f"Results: Trend Pair={trend_pair}, Trend Market={trend_market}, Trend Pair Aggregated={trend_pair_aggregated}")
        if trend_pair == Constants.LINEAR_DECREASING and trend_market == Constants.LINEAR_DECREASING and trend_pair_aggregated == Constants.LINEAR_DECREASING:            
            log.info(f"Found subsequent decreases in current profit, hedging now short for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
            self.logme(f"Analysed pair dataframe going short:")
            hedging_direction = "short"
            trade.is_short = False # hedge_me goes now short (opposite)
            hedged = dsHedging.hedge_me(self, trade, pair, existing_position_on_exchange)
            self.writeDataframeToFile(pair, pair_dataframe, hedging_direction + "_Pair_LINEAR_DECREASING", slope_pair)  
            self.writeDataframeToFile(pair, market_aggregrated_df, hedging_direction + "_Market_LINEAR_DECREASING", slope_market)  
            self.writeDataframeToFile(pair, aggregate_df, hedging_direction + "_Pair_Aggregated_LINEAR_DECREASING", slope_pair_aggregated)  
        elif trend_pair == Constants.LINEAR_INCREASING and trend_market == Constants.LINEAR_INCREASING and trend_pair_aggregated == Constants.LINEAR_INCREASING:
            log.info(f"Found subsequent rises in current profit, hedging now long for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
            hedging_direction = "long"
            trade.is_short = True # hedge_me goes now long (opposite) 
            hedged = dsHedging.hedge_me(self, trade, pair, existing_position_on_exchange)
            self.writeDataframeToFile(pair, pair_dataframe, hedging_direction + "_Pair_LINEAR_INCREASING", slope_pair)  
            self.writeDataframeToFile(pair, market_aggregrated_df, hedging_direction + "_Market_LINEAR_INCREASING", slope_market)  
            self.writeDataframeToFile(pair, aggregate_df, hedging_direction + "_Pair_Aggregated_LINEAR_INCREASING", slope_pair_aggregated)  
        else:
            self.logme(f"Not hedging {pair}, because no patterns found")
            hedged = False
        return hedged

    def detectMarketTrend(self, key: str):
        market_aggregate_df = self.get_market_aggregated_pair_dataframe_from_dict(key)
        market_trend = None
        if not market_aggregate_df.empty:
            self.logme("Checking Market Trend from status table on spot bot with following aggregated market dataframe")
            self.dumpCurrentProfitAsArray(market_aggregate_df)
            # self.logme(f"{status_df}")
            # market_trend = self.check_market_trend(status_df)
            market_trend, _ = self.detectLinearRegression(market_aggregate_df, Constants.MARKET)
            self.logme(f"Found following market trend in bot status={market_trend}")
        else:
            raise Exception(f"Empty Status Table Market Data, create trades first in master bot...")
        return market_trend

    def dumpCurrentProfitAsArray(self, dataframe: pd.DataFrame):
        self.logme("dumpCurrentProfitAsArray")
        self.logme(dataframe)
        market_trend, slope = self.detectLinearRegression(dataframe, Constants.MARKET)
        self.logme(f"Slope value: {slope}, Market Trend: {market_trend}")
        result = dataframe['current_profit'].to_string(header=False, index=False).replace('\n', ',')
        self.logme("Jupyter Array for Testing: [" + result + "]")

    def writeDataframeToFile(self, pair: str, dataframe: DataFrame, direction: str, slope):      
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pair = pair.replace("/USDT:USDT", "")
        pair = pair.replace("/USDT", "")
        # Define the file name with timestamp
        slope = "{:.3f}".format(slope)
        tradeids = ""
        if 'trade_id' in dataframe.columns:
            tradeids = dataframe.loc[0, 'trade_id']
        result = dataframe['current_profit'].to_string(header=False, index=False).replace('\n', ',')
        file_name = f"hedged_{pair}_id_{tradeids}_slope_{slope}_{direction}_{timestamp}.csv"
        file_name_array = f"hedged_{pair}_id_{tradeids}_slope_{slope}_{direction}_{timestamp}_jupyter.csv"
        with open(file_name_array, 'w') as file:
            # Write a string to the file
            file.write('[' + result + ']')        
        # file_name_market = f"hedged_{pair}_id_{tradeids}_slope_{slope}_{direction}_{timestamp}_market.csv"
        # file_name_aggregated_market = f"hedged_{pair}_id_{tradeids}_slope_{slope}_{direction}_{timestamp}_aggregated_market.csv"
        # Write DataFrame to file
        dataframe.to_csv(file_name, index=True)
        # self.logme(f"Saving market trends as status table to {file_name_market}")
        # status_df = self.getStatusTableAsDataframe()
        # status_df.to_csv(file_name_market, index=True)
        # market_aggregate_df = self.get_market_aggregated_pair_dataframe_from_dict(Constants.MARKET)
        # market_aggregate_df.to_csv(file_name_aggregated_market, index=True)
        # self.logme("Found following market trend in bot status={market_trend}")
        self.logme(f"DataFrame written to file: {file_name}")

    def getPositionInBinance(self, pair, apikey, apisecret):
        positionFetcher = FuturesPositionsFetcher(apikey, apisecret)
        symbol=pair.split('/')[0]+"USDT"
        existing_position_on_exchange = positionFetcher.get_futures_position_information(symbol)
        # run_mode = self.dp.runmode.value        
        # if run_mode in ('live', 'dry_run'):  
        #     existing_position_on_exchange[0]['positionAmt'] = trade.amount
        return existing_position_on_exchange            

    # def getPositionInBinanceStoploss(self, pair, current_time, current_rate, current_profit):
    #     self.logme(f"Entering custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
    #     positionFetcher = FuturesPositionsFetcher(self.stoploss_apikey, self.stoploss_apisecret)
    #     symbol=pair.split('/')[0]+"USDT"
    #     self.existing_position_on_exchange = positionFetcher.get_futures_position_information(symbol)               
                
    def detectLinearRegression(self, df: DataFrame, domain: Constants, column: str = "current_profit"):
        # Step 2: Perform linear regression using scipy.stats.linregress
        slope = None
        if len(df) > 1: 
            slope, intercept, r_value, p_value, std_err = linregress(df.index, df[column])

            # Output the slope of the regression line
            self.logme(f'Slope of the regression line: {slope}')
            linreg_Increasing_Start = 0
            linreg_Decreasing_Start = 0
            if domain == Constants.PAIR:
                linreg_Increasing_Start = self.linearRegressionIncreasingThreshold_Start_Pair
                linreg_Decreasing_Start = self.linearRegressionDecreasingThreshold_Start_Pair
                self.logme(f"Using Pair Values for linear Regression, linreg_Increasing_Start={linreg_Increasing_Start}, linreg_Decreasing_Start={linreg_Decreasing_Start}")
            elif domain == Constants.MARKET:
                linreg_Increasing_Start = self.linearRegressionIncreasingThreshold_Start_Market
                linreg_Decreasing_Start = self.linearRegressionDecreasingThreshold_Start_Market
                self.logme(f"Using Market Values for linear Regression, linreg_Increasing_Start={linreg_Increasing_Start}, linreg_Decreasing_Start={linreg_Decreasing_Start}")
            else:
                raise Exception("Slope Ranges not define (linearRegression....)")
                
            # Step 3: Check if the values are decreasing or increasing based on the slope
            if slope > linreg_Increasing_Start and slope < self.linearRegressionIncreasingThreshold_End:
                self.logme('Values are increasing')
                return Constants.LINEAR_INCREASING, slope
            elif slope < linreg_Decreasing_Start and slope > self.linearRegressionDecreasingThreshold_End:
                self.logme('Values are decreasing')
                return Constants.LINEAR_DECREASING, slope
            if 'pair' in df.columns:
                self.logme(f"detectLinearRegression: No Linear Regression found for pair {df.iloc[0]['pair']}")
            self.logme(df)
            self.logme(f"detectLinearRegression: Current Slope Value: {slope},")
            self.logme(f"detectLinearRegression: Increase Linear Threshold Pair between: {self.linearRegressionIncreasingThreshold_Start_Pair}-{self.linearRegressionIncreasingThreshold_End}")
            self.logme(f"detectLinearRegression: Decrease Linear Threshold Pair between: {self.linearRegressionDecreasingThreshold_Start_Pair}-{self.linearRegressionDecreasingThreshold_End}")
            self.logme(f"detectLinearRegression: Increase Linear Threshold Market between: {self.linearRegressionIncreasingThreshold_Start_Market}-{self.linearRegressionIncreasingThreshold_End}")
            self.logme(f"detectLinearRegression: Decrease Linear Threshold Market between: {self.linearRegressionDecreasingThreshold_Start_Market}-{self.linearRegressionDecreasingThreshold_End}")
        else:
            self.logme(f"Cannot calculate slope for dataframe, cause must be more than one row in dataframe")
        return Constants.LINEAR_STABLE, slope
    
    # def check_market_trend(self, df: pd.DataFrame):
    #     positive_count = 0
    #     negative_count = 0
    #     total_pairs = len(df)
    #     for  _, row  in df.iterrows():
    #         # Consider the current_profit of the last record of each crypto pair in the last hour
    #         last_profit = row['current_profit']
            
    #         # Determine if the profit is positive or negative
    #         if last_profit > 0:
    #             positive_count += 1
    #         elif last_profit < 0:
    #             negative_count += 1
        
    #     # Determine if 80% of pairs have a positive or negative current_profit
    #     if positive_count / total_pairs >= self.market_threshold_pct:
    #         return Constants.LINEAR_INCREASING
    #     elif negative_count / total_pairs >= self.market_threshold_pct:
    #         return Constants.LINEAR_DECREASING
    #     else:
    #         return Constants.LINEAR_STABLE


    # def check_market_trend(self, dataframe: pd.DataFrame):
    #     # # Assuming the dataframe is sorted by timestamp
    #     # df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    #     # # Determine the end time which is the maximum timestamp in the dataframe
    #     # end_time = df['timestamp'].max()
    #     # start_time = end_time - pd.Timedelta(hours=1)
        
    #     # # Filter the dataframe for the last one hour
    #     # df_last_hour = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
        
    #     # if df_last_hour.empty:
    #     #     return None  # No data for the last hour

    #     # # Group by crypto pair
    #     groups = dataframe.groupby('pair')
        
    #     # rising_count = 0
    #     # falling_count = 0
    #     # stable_count = 0
    #     total_pairs = len(groups)
        
    #     for group in groups:
    #         if len(group) > 1:
    #             start_profit = group.iloc[0]['current_profit']
    #             end_profit = group.iloc[-1]['current_profit']
    #             profit_diff = end_profit - start_profit
                
    #             # Determine the trend
    #             if profit_diff > 0:
    #                 self.market_rising_count += 1
    #             elif profit_diff < 0:
    #                 self.market_falling_count += 1
    #             else:
    #                 self.market_stable_count += 1
        
    #     # Determine if 80% of pairs are rising, falling, or stable
    #     if self.rising_count / total_pairs >= self.market_threshold_pct:
    #         self.logme("Market is increasing according to threshold {self.market_threshold_pct} >= falling_count={rising_count} / totalpairs={total_pairs}")
    #         return Constants.LINEAR_INCREASING
    #     elif self.falling_count / total_pairs >= self.market_threshold_pct:
    #         self.logme("Market is decreasing according to threshold {self.market_threshold_pct} >= falling_count={falling_count} / totalpairs={total_pairs}")
    #         return Constants.LINEAR_DECREASING
    #     else:
    #         self.logme("Market is stable according to threshold {self.market_threshold_pct}")
    #         return Constants.LINEAR_STABLE

    
