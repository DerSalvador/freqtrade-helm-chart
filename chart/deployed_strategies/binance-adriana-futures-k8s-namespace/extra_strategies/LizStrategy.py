kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n binance-adriana-futures exec -it pod/freqtrade-binance-adriana-futures-55cb57df55-dhrkz -c freqtrade -- cat /extra_strategies/LizStrategy.py
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
pd.set_option('display.max_rows', 200)

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
    BULLISH = 6
    BEARISH = 7 
    
class LizStrategy(IStrategy):
    rpc: RPCManager = None
    # DerSalvador Hedging
    hedging_version = 0.0
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
    trigger_threshold_adjustment_dict = {}
    pair_dataframe_dict = {}
    aggregated_pair_dataframe_dict = {}
    market_aggregated_dataframe_dict = {}
    stoploss_dataframe_dict = {}
    pair_stoploss_dict = {}
    trigger_threshold_adjustment = 300
    start_profit_abs_positiv = 0.1
    start_profit_abs_negative = -0.1
    previous_profit_all_coin = 0.0
    stoploss_bot_api = ""
    market_rising_count = 0
    market_falling_count = 0
    market_stable_count = 0
    market_analysis = False
    pair_aggregated_analysis = False
    enable_email_logging = False
    bullish_threshold_pct = 0.7
    bearish_threshold_pct = 0.7
    candle_divisor = 3.0
    bullish_partial_threshold_pct = 0.75
    bearish_partial_threshold_pct = 0.75
    minutesLatestTradeDuration = 0
    hedge_bot_api_show_config = ""
    last_trend_entries = 3
    bullish_threshold_pct_offset = 0.0       
    bearish_threshold_pct_offset = 0.0     
    threads = []    
    # Example usage:
    # Replace these with actual credentials and recipient information
    
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
    processed_PairProcessing = {}
    processed_hedgeMeProcessing = {}
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
        self.hedging_version = config['dersalvador']['hedging']['hedging_version']
        self.bot_role = config['dersalvador']['hedging']['role']
        self.hedging_url = config['dersalvador']['hedging']['hedge_bot_api']
        self.hedging_leverage = config['dersalvador']['hedging']['leverage']
        self.hedging_stake_amount = config['dersalvador']['hedging']['stake_amount']
        self.hedging_apikey = config['dersalvador']['hedging']['apikey']
        self.hedging_apisecret = config['dersalvador']['hedging']['apisecret']
        self.stoploss_apikey = config['dersalvador']['hedging']['stoploss_apikey']
        self.stoploss_apisecret = config['dersalvador']['hedging']['stoploss_apisecret']
        self.hedging_trigger_timeout_seconds = config['dersalvador']['hedging']['hedging_trigger_timeout_seconds']
        self.hedging_pair_profits_check_array_length = config['dersalvador']['hedging']['profits_check_array_length']
        self.hedging_aggregated_pair_profits_check_array_length = config['dersalvador']['hedging']['aggregated_pair_profits_check_array_length']
        self.hedging_market_profits_check_array_length = config['dersalvador']['hedging']['market_profits_check_array_length']
        self.spot_bot_api_status = config['dersalvador']['hedging']['spot_bot_api_status']
        self.spot_bot_api_forceenter = config['dersalvador']['hedging']['spot_bot_api_forceenter']
        self.hedge_bot_api_status = config['dersalvador']['hedging']['hedge_bot_api_status']
        self.hedge_bot_api_profit = config['dersalvador']['hedging']['hedge_bot_api_profit']
        self.bot_username =  config['api_server']['username']
        self.bot_password =  config['api_server']['password']
        self.trigger_threshold_adjustment = config['dersalvador']['hedging']['trigger_threshold_adjustment']
        self.start_profit_abs_positiv = config['dersalvador']['hedging']['start_profit_abs_positiv']
        self.start_profit_abs_negative = config['dersalvador']['hedging']['start_profit_abs_negative']
        self.stoploss_bot_api  = config['dersalvador']['hedging']['stoploss_bot_api']
        self.market_analysis = config['dersalvador']['hedging']['market_analysis']
        self.pair_aggregated_analysis = config['dersalvador']['hedging']['pair_aggregated_analysis']
        self.bullish_threshold_pct = config['dersalvador']['hedging']['bullish_threshold_pct']
        self.bearish_threshold_pct = config['dersalvador']['hedging']['bearish_threshold_pct']
        self.bullish_threshold_pct_offset = config['dersalvador']['hedging']['bullish_threshold_pct_offset']
        self.bearish_threshold_pct_offset = config['dersalvador']['hedging']['bearish_threshold_pct_offset']
        self.candle_divisor = config['dersalvador']['hedging']['candle_divisor']
        self.bullish_partial_threshold_pct = config['dersalvador']['hedging']['bullish_partial_threshold_pct']
        self.bearish_partial_threshold_pct = config['dersalvador']['hedging']['bearish_partial_threshold_pct']
        self.minutesLatestTradeDuration = config['dersalvador']['hedging']['minutesLatestTradeDuration']
        self.hedge_bot_api_show_config = config['dersalvador']['hedging']['hedge_bot_api_show_config']
        self.last_trend_entries = config['dersalvador']['hedging']['last_trend_entries']
        self.enable_email_logging = config['dersalvador']['enable_email_logging']

        try:
            self.logme(f"Setting new hedging trigger timeout according to whitelist length {len(self.dp.current_whitelist())}")
            self.hedging_trigger_timeout_seconds = 3//len(self.dp.current_whitelist())
            self.logme(f"New hedging trigger timeout for whitelist length {len(self.dp.current_whitelist())}: { self.hedging_trigger_timeout_seconds}sec")
        except:
          print('Ignore exception')
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
        self.logme(f"---------------------------------------------------------------")
        self.logme(f"Hedging Version: {self.hedging_version}")
        self.logme(f"---------------------------------------------------------------")
        return

    def showHedgingConfig(self):
        msg = "No hedging config found"
        if self.config['dersalvador']['hedging'] is not None:
            msg=f'*Found Hedging section in config*\n'
            msg+=f'*Botname:* {self.bot_name}\n'
            msg+=f'*Role:* {self.bot_role}\n'
            msg+=f'*Amount:* {self.hedging_stake_amount}\n' 
            msg+=f'*Leverage:* {self.hedging_leverage}\n'
            msg+=f'*profits_check_array_length:* {self.hedging_pair_profits_check_array_length}\n'
            msg+=f'*aggregated_pair_profits_check_array_length:* {self.hedging_aggregated_pair_profits_check_array_length}\n'
            msg+=f'*market_profits_check_array_length:* {self.hedging_market_profits_check_array_length}\n'
            msg+=f'*hedging_trigger_timeout_seconds:* {self.hedging_trigger_timeout_seconds}\n'
            msg+=f'*bot_username:* {self.bot_username}\n'
            msg+=f'*bot_password:* {self.bot_password}\n'
            msg+=f'*start_profit_abs_positiv:* {self.start_profit_abs_positiv}\n'
            msg+=f'*start_profit_abs_negative:* {self.start_profit_abs_negative}\n'
            msg+=f'*market_analysis:* {self.market_analysis}\n'
            msg+=f'*pair_aggregated_analysis:* {self.pair_aggregated_analysis}\n'
            msg+=f'*enable_email_logging:* {self.enable_email_logging}\n'
            msg+=f'*bullish_threshold_pct:* {self.bullish_threshold_pct}\n'
            msg+=f'*bearish_threshold_pct:* {self.bearish_threshold_pct}\n'
            msg+=f'*candle_divisor:* {self.candle_divisor}\n'
            msg+=f'*bullish_partial_threshold_pct:* {self.bullish_partial_threshold_pct}\n'
            msg+=f'*bearish_partial_threshold_pct:* {self.bearish_partial_threshold_pct}\n'
            msg+=f'*minutesLatestTradeDuration:* {self.minutesLatestTradeDuration}\n'
            msg+=f'*last_trend_entries:* {self.last_trend_entries}\n'
            msg+=f'*bullish_threshold_pct_offset:* {self.bullish_threshold_pct_offset}\n'
            msg+=f'*bearish_threshold_pct_offset:* {self.bearish_threshold_pct_offset}\n'
            msg+=f'*trigger_threshold_adjustment:* {self.trigger_threshold_adjustment}\n'
            self.logme(msg)
        return msg

    def resetDatabase(self):
        data_dir = self.config['dersalvador']['database_path']
        conn = None 
        try:
            conn = sqlite3.connect(data_dir)
            cursor = conn.cursor()

            # cursor.execute(".tables")
            self.logme(cursor.fetchall())
            self.logme("Starting to reset all tables")
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
            self.logme('resetDatabase: The try except is finished')
            
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
            profit_abs = 0
            open_rate = 0
            stop_loss_pct = 0
            amount = 0            
            t = self.getJsonTrade(pair, self.hedge_bot_api_status)
            if t is not None:
                profit_abs = t.get('profit_abs')
                open_rate = t.get('open_rate')
                stop_loss_pct = t.get('stop_loss_pct')
                amount = t.get('amount')
            else:
                s = f"No Trade found for Pair {pair} in custom_stoploss function"
                raise Exception(s)
            current_profit = profit_abs
            stoploss_distance_to_zero = (stop_loss_pct*amount*open_rate)/100 - current_profit
            self.logme(f"----------------------------------------------------------")
            self.logme(f"Entering custom stoploss for pair {pair}, current stoploss value {self.pair_stoploss_dict[pair]}")
            self.logme(f"Stoploss distance for pair {pair}: {stoploss_distance_to_zero}")
            profit_pct = (profit_abs * 100) / (amount*open_rate)
            if profit_pct < 0:
                newstoploss -= -0.01
            if profit_pct > 0:
                newstoploss += 0.01
            if newstoploss < -0.5:
                newstoploss = -0.5
            if newstoploss > 0:
                newstoploss = -0.1
            self.logme(f"Setting new stoploss pct to {newstoploss} based on config stoploss {self.config['stoploss']} and current_profit {current_profit} with offset 0.01, for pair {pair} in bot {self.bot_name}")
            self.pair_stoploss_dict[pair] = newstoploss
        else:
            self.logme(f"Bot role is {self.bot_role}, only bot role hedger uses custom stoploss")
        return newstoploss

    def minutesPassedFromLatestTrade(self, tradeTimestamp):
        timestamp1 = datetime.now().timestamp()*1000
        timestamp2 = tradeTimestamp
        # Convert timestamps to datetime objects
        datetime1 = datetime.fromtimestamp(timestamp1 / 1000)
        datetime2 = datetime.fromtimestamp(timestamp2 / 1000)
        # Calculate the time difference in minutes
        time_difference_minutes = abs((datetime2 - datetime1).total_seconds() / 60)
        self.logme(f"Minutes between the two timestamps: {time_difference_minutes}")
        return time_difference_minutes
        
    def adjustThresholds(self):
        botconfig = self.getJsonFromAPI(self.hedge_bot_api_show_config)
        run_mode = botconfig['runmode']
        if run_mode != 'dry_run':
            self.logme(f"Adjust Thresholds only in dry_run mode, leaving adjusting thresholds")
            return         
        json = self.getJsonFromAPI(self.hedge_bot_api_profit)
        if json: 
            profit_all_coin = json['profit_all_coin']
            winning_trades = json['winning_trades']
            losing_trades = json['losing_trades']
            winrate = json['winrate']
            self.logme(f"Profit in hedgebot {self.hedge_bot_api_profit} for all coins is: {profit_all_coin}" )
            if self.previous_profit_all_coin == 0.0:
               self.previous_profit_all_coin = profit_all_coin 
            minutesPassed = self.minutesPassedFromLatestTrade(json['latest_trade_timestamp'])
            self.logme(f"Bot {self.bot_name}. Minutes passed from latest trade: {minutesPassed} minutes")
            if (winning_trades == 0 and losing_trades == 0) or minutesPassed > self.minutesLatestTradeDuration:
                if self.trigger_threshold_adjustment > 10: 
                    self.trigger_threshold_adjustment -= 10
                else:
                    self.trigger_threshold_adjustment = self.config['dersalvador']['hedging']['trigger_threshold_adjustment']
                self.logme(f"<<<<<<<<<<<<<<<<<<<<<<<<<< Warning: No trades done yet or minutes {self.minutesLatestTradeDuration} elapsed from latest trade, adjusting thresholds ")
                if self.last_trend_entries > 3:
                    self.logme(f"Adjusting self.last_trend_entries: {self.last_trend_entries}")
                    self.last_trend_entries -= 1
                    self.logme(f"New self.last_trend_entries: {self.last_trend_entries}")
                else:
                    self.last_trend_entries = self.config['dersalvador']['hedging']['last_trend_entries']

                if self.hedging_pair_profits_check_array_length > 6:
                    self.logme(f"Adjusting self.hedging_pair_profits_check_array_length: {self.hedging_pair_profits_check_array_length}")
                    self.hedging_pair_profits_check_array_length -= 1
                    self.logme(f"New self.hedging_pair_profits_check_array_length: {self.hedging_pair_profits_check_array_length}")
                else:
                    self.hedging_pair_profits_check_array_length = self.config['dersalvador']['hedging']['profits_check_array_length']
                    
                if self.hedging_trigger_timeout_seconds > 10:
                    self.logme(f"Adjusting self.hedging_trigger_timeout_seconds: {self.hedging_trigger_timeout_seconds}")
                    self.hedging_trigger_timeout_seconds -= 1
                    self.logme(f"New self.hedging_trigger_timeout_seconds: {self.hedging_trigger_timeout_seconds}")
                else:
                    self.hedging_trigger_timeout_seconds = self.config['dersalvador']['hedging']['hedging_trigger_timeout_seconds']
                    
                if self.hedging_market_profits_check_array_length > 10:
                    self.logme(f"Adjusting self.hedging_market_profits_check_array_length: {self.hedging_market_profits_check_array_length}")
                    self.hedging_market_profits_check_array_length -= 1
                    self.logme(f"New self.hedging_market_profits_check_array_length: {self.hedging_market_profits_check_array_length}")
                else:
                    self.hedging_market_profits_check_array_length = self.config['dersalvador']['hedging']['market_profits_check_array_length']
                    
                if self.hedging_aggregated_pair_profits_check_array_length > 10:
                    self.logme(f"Adjusting self.hedging_aggregated_pair_profits_check_array_length: {self.hedging_aggregated_pair_profits_check_array_length}")
                    self.hedging_aggregated_pair_profits_check_array_length -= 1
                    self.logme(f"New self.hedging_aggregated_pair_profits_check_array_length: {self.hedging_aggregated_pair_profits_check_array_length}")
                else:
                    self.hedging_aggregated_pair_profits_check_array_length = self.config['dersalvador']['hedging']['aggregated_pair_profits_check_array_length']
                    
                if self.bullish_threshold_pct > 0.6 + self.bullish_threshold_pct_offset:
                    self.logme(f"Adjusting self.bullish_threshold_pct: {self.bullish_threshold_pct}")
                    self.bullish_threshold_pct -= self.bullish_threshold_pct_offset # 0.005
                    self.logme(f"New self.bullish_threshold_pct: {self.bullish_threshold_pct}")
                else:
                    self.bullish_threshold_pct = self.config['dersalvador']['hedging']['bullish_threshold_pct']

                if self.bearish_threshold_pct > 0.6 + self.bearish_threshold_pct_offset:
                    self.logme(f"Adjusting self.bearish_threshold_pct: {self.bearish_threshold_pct}")
                    self.bearish_threshold_pct -= self.bearish_threshold_pct_offset # 0.005
                    self.logme(f"New self.bearish_threshold_pct: {self.bearish_threshold_pct}")
                else:
                    self.bearish_threshold_pct = self.config['dersalvador']['hedging']['bearish_threshold_pct']
                    
                if self.bullish_partial_threshold_pct > 0.6 + self.bullish_threshold_pct_offset:
                    self.logme(f"Adjusting self.bullish_partial_threshold_pct: {self.bullish_partial_threshold_pct}")
                    self.bullish_partial_threshold_pct -= self.bullish_threshold_pct_offset # 0.005
                    self.logme(f"New self.bullish_partial_threshold_pct: {self.bullish_partial_threshold_pct}")
                else:
                    self.bullish_partial_threshold_pct = self.config['dersalvador']['hedging']['bullish_partial_threshold_pct']
                    
                if self.bearish_partial_threshold_pct > 0.6 + self.bearish_threshold_pct_offset:  
                    self.logme(f"Adjusting self.bearish_partial_threshold_pct: {self.bearish_partial_threshold_pct}")
                    self.bearish_partial_threshold_pct -= self.bearish_threshold_pct_offset # 0.005  
                    self.logme(f"New self.bearish_partial_threshold_pct: {self.bearish_partial_threshold_pct}")
                else:
                    self.bearish_partial_threshold_pct = self.config['dersalvador']['hedging']['bearish_partial_threshold_pct']
            elif profit_all_coin < 0 or profit_all_coin < self.previous_profit_all_coin or winning_trades < losing_trades: 
                self.logme(f"@@@@@@@@@@@@@@@@@@@@ Profit all coins is negative bot {self.bot_name}: {profit_all_coin} or winning trades less than losing trades, adjusting thresholds" )
                self.logme(f"Adjusting Hedging Thresholds and resetting database to start over")
                self.logme(f"ReSetting Database for hedging...")
                self.resetDatabase()
                self.logme(f"Setting new threshold values for hedging...")
                self.last_trend_entries += 2
                self.hedging_pair_profits_check_array_length += 2
                self.hedging_trigger_timeout_seconds += 2
                self.hedging_market_profits_check_array_length += 2
                self.hedging_aggregated_pair_profits_check_array_length += 2
                self.bullish_threshold_pct += self.bullish_threshold_pct_offset 
                self.bearish_threshold_pct += self.bearish_threshold_pct_offset
                self.bullish_partial_threshold_pct += self.bullish_threshold_pct_offset
                self.bearish_partial_threshold_pct += self.bearish_threshold_pct_offset                 
            elif self.previous_profit_all_coin > 0 and profit_all_coin > 0 and self.previous_profit_all_coin > profit_all_coin:
                self.logme(f"Profit all coins is positive {profit_all_coin}, previous profit is greater = {self.previous_profit_all_coin}, Adjusting Hedging Thresholds")
                self.last_trend_entries += 1
                self.hedging_pair_profits_check_array_length += 1
                self.hedging_trigger_timeout_seconds += 1
                self.hedging_market_profits_check_array_length += 1
                self.hedging_aggregated_pair_profits_check_array_length += 1
                self.bullish_threshold_pct += self.bullish_threshold_pct_offset
                self.bearish_threshold_pct += self.bearish_threshold_pct_offset
                self.bullish_partial_threshold_pct += self.bullish_threshold_pct_offset
                self.bearish_partial_threshold_pct += self.bearish_threshold_pct_offset
                self.previous_profit_all_coin = profit_all_coin
                self.logme(f"Profit all coins is positive {profit_all_coin}, with following configuration")
                self.logme(f"self.hedging_pair_profits_check_array_length={self.hedging_pair_profits_check_array_length}")
                self.logme(f"self.hedging_trigger_timeout_seconds={self.hedging_trigger_timeout_seconds}")
                self.logme(f"self.hedging_market_profits_check_array_length={self.hedging_market_profits_check_array_length}")
                self.logme(f"self.hedging_aggregated_pair_profits_check_array_length={self.hedging_aggregated_pair_profits_check_array_length}")
                self.logme(f"self.bullish_threshold_pct={self.bullish_threshold_pct}")
                self.logme(f"self.bearish_threshold_pct={self.bearish_threshold_pct}")
                self.logme(f"self.bullish_partial_threshold_pct={self.bullish_partial_threshold_pct}")
                self.logme(f"self.bearish_partial_threshold_pct={self.bearish_partial_threshold_pct}")
                self.logme(f"self.candle_divisor={self.candle_divisor}")
            if self.bot_role == "hedger" or self.bot_role == "mixed":
                self.send_email(f"Winrate is {winrate} with profit all coins {profit_all_coin}, previois profit = {self.previous_profit_all_coin}, use following parameters for the configuration\n" + 
                                f"hedging_pair_profits_check_array_length {self.hedging_pair_profits_check_array_length}\n" +
                                f"hedging_trigger_timeout_seconds {self.hedging_trigger_timeout_seconds}\n" +
                                f"hedging_market_profits_check_array_length {self.hedging_market_profits_check_array_length}\n" +
                                f"hedging_aggregated_pair_profits_check_array_length {self.hedging_aggregated_pair_profits_check_array_length}\n" 
                                f"bullish_threshold_pct {self.bullish_threshold_pct}\n" 
                                f"bearish_threshold_pct {self.bearish_threshold_pct}\n" 
                                f"bullish_partial_threshold_pct {self.bullish_partial_threshold_pct}\n" 
                                f"bearish_partial_threshold_pct {self.bearish_partial_threshold_pct}\n" 
                                f"candle_divisor {self.candle_divisor}\n" 
                                )            

        else:
            raise Exception(f"Cannot get profit from bot: {self.hedge_bot_api_profit}")
 
            
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
            self.logme(f"force_enter_trade: {self.bot_name}: HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            self.logme(f"force_enter_trade: {self.bot_name}: Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            self.logme(f"force_enter_trade: {self.bot_name}: Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            self.logme(f"force_enter_trade: {self.bot_name}: An error occurred: {req_err}")


    def custom_exit(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        if self.bot_role != "master" and self.bot_role != "mixed" : 
            self.logme(f"Bot {self.bot_name} role is {self.bot_role} and not master, leaving custom_exit hedging approach... ")
            return False
        self.logme(f"Wait until Status table has at least as much positions as the current whitelist, otherwise ignore custom_exit...")
        whitelist_len = len(self.dp.current_whitelist())
        if whitelist_len == 0:
            self.logme(f"Whitelist is still empty for bot {self.bot_name}, waiting until whitelist is filled")
            return False
        positions = self.getJsonFromAPI(self.spot_bot_api_status)
        positions_len = len(positions)
        if positions_len >= whitelist_len:
            self.logme(f"Created {positions_len} positions, whitelist length {whitelist_len} hedging process can continue")
        else:
            self.logme(f"Not enough positions {positions_len} created, must reach at least whitelist length {whitelist_len}")
            return False
        self.logme(f"Entering custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")        
        run_mode = self.dp.runmode.value      
        if run_mode in ('live', 'dry_run'):  
            self.showHedgingConfig()
            dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
            if pair in self.processed_hedgeMeProcessing:
                self.logme(f"Label '{pair}' already processed, skipping function execution.")
                del self.processed_hedgeMeProcessing[pair]
            else:
                self.processed_hedgeMeProcessing[pair] = True
                thread = threading.Thread(target=self.hedgeMeProcessing, args=(pair, trade, current_time, current_rate, current_profit, dataframe,))
                thread.start()
        return None

    def hedgeMeProcessing(self,pair, trade, current_time, current_rate,
                        current_profit, dataframe):
        # Process the function for the label
        self.logme(f"hedgeMeProcessing function for label '{pair}'")
        lock = threading.Lock()
        # Acquire a lock for the label to ensure only one thread processes it
        try:
            lock.acquire()    
            self.hedgeMe(pair, trade, current_time, current_rate,
                        current_profit, dataframe)
        finally:
            self.logme(f"Thread hedgeMeProcessing {pair} is finished")
            del self.processed_hedgeMeProcessing[pair]
            # Release the lock
            lock.release()            
        
    def logme(self, msg: str):
        # self.logme(f"{msg}")
        log.info(f"{msg}")

    def getJsonFromAPI(self, endpoint):
        url = endpoint
        auth = (self.bot_username, self.bot_password)

        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Ensure we notice bad responses
        data = response.json()
        return data

    def getJsonTrade(self, pair, endpoint=None):
        if endpoint is None:
            endpoint = self.spot_bot_api_status
        url = endpoint
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
                return trade
        return None

    def getStatusTableAsDataframe(self, endpoint=None):
        if endpoint is None:
            endpoint = self.spot_bot_api_status
        url = endpoint
        auth = (self.bot_username, self.bot_password)
        self.market_status_df = pd.DataFrame()
        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Ensure we notice bad responses
        data = response.json()
        for trade in data:            
            pair = trade.get('pair')
            # find pair dataframe             
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
            # Connecting via SMTP
            # SMTP Server:  mail.smtp2go.com

            # SMTP Port: 2525
            # Alternative/TLS Ports: 8025, 587, 80 or 25. TLS is available on the same ports.

            # SSL is available on ports:  465, 8465 and 443.            
            if enableEmail:
                sender = "Freqtrade Bot <michael.santana@dersalvador.com>"
                receiver = "Freqtrade Filekeys <filekeys@gmail.com>"

                message = f"""\
                Subject: Freqtrade Bot {self.bot_name} with previous profit {self.previous_profit_all_coin}
                To: {receiver}
                From: {sender}

                {body}"""

                with smtplib.SMTP("mail.smtp2go.com", 2525) as server:
                    server.starttls()
                    server.login("dersalvador.com", "SHAfq8oadIfNtFQd")
                    server.sendmail(sender, receiver, message)
            else:
                self.logme(f"Not sending logs to email: enableEmail={enableEmail}")            
        except Exception as e:
            self.logme(f'Failed to send email. Error: {str(e)}')
        
    def hedgeMe(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float, dataframe: DataFrame, **kwargs): 
        hedged = False;
        self.logme(f"MSSM: Entering Hedging Logic for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}") 
        if self.bot_role == "hedger":
            t = self.getJsonTrade(pair, self.hedge_bot_api_status)
        else:
            t = self.getJsonTrade(pair)        
        if t is not None:
            profit_abs = t.get('profit_abs')
            self.logme(f"Profit via Json API = {profit_abs}, current_profit via freqtrade custom_exit function = {current_profit}")

            if profit_abs > self.start_profit_abs_positiv or profit_abs < self.start_profit_abs_negative: 
                existing_position_on_exchange = self.getPositionInBinance(pair, self.hedging_apikey, self.hedging_apisecret)

                hedged = self.hedgeMeCore(pair, trade, current_time, current_rate, profit_abs, existing_position_on_exchange)
            else:
                self.logme(f"Filtering profit abs {profit_abs} because is inside range start_profit_abs_negative-start_profit_abs_positiv: {self.start_profit_abs_negative}-{self.start_profit_abs_positiv}")
        else:
            s = f"Pair {pair} not found via Json API in bot {self.bot_name}"
            raise Exception(s)
        return hedged

    def get_aggregated_pair_dataframe_from_dict(self, key):
        if key in self.aggregated_pair_dataframe_dict:
            df = self.aggregated_pair_dataframe_dict[key]
            df.fillna(value=False, inplace=True)
            return df  
        else:
            empty_df = pd.DataFrame()
            self.aggregated_pair_dataframe_dict[key] = empty_df
            return empty_df

    def set_aggregated_pair_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        dataframe = dataframe.reset_index(drop=True)
        self.aggregated_pair_dataframe_dict[key] = dataframe
    
    def get_pair_dataframe_from_dict(self, key):
        if key in self.pair_dataframe_dict:
            df = self.pair_dataframe_dict[key]
            df.fillna(value=False, inplace=True)
            return df  
        else:
            empty_df = pd.DataFrame()
            self.pair_dataframe_dict[key] = empty_df
            return empty_df
    
    def set_pair_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        dataframe = dataframe.reset_index(drop=True)
        self.pair_dataframe_dict[key] = dataframe
    
    def get_market_aggregated_dataframe_from_dict(self, key):
        if key in self.market_aggregated_dataframe_dict:
            df = self.market_aggregated_dataframe_dict[key]
            df.fillna(value=False, inplace=True)
            return df  
        else:
            empty_df = pd.DataFrame()
            self.market_aggregated_dataframe_dict[key] = empty_df
            return empty_df

    def set_market_aggregated_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        dataframe = dataframe.reset_index(drop=True)
        self.market_aggregated_dataframe_dict[key] = dataframe
    
    def get_stoploss_dataframe_from_dict(self, key):
        if key in self.stoploss_dataframe_dict:
            df = self.stoploss_dataframe_dict[key]
            df.fillna(value=False, inplace=True)
            return df  
        else:
            empty_df = pd.DataFrame()
            self.stoploss_dataframe_dict[key] = empty_df
            return empty_df

    def set_stoploss_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        dataframe = dataframe.reset_index(drop=True)
        self.stoploss_dataframe_dict[key] = dataframe
       
    def hedgeMeCore(self, pair, trade, current_time, current_rate, profit_abs, existing_position_on_exchange):
        profit_abs = round(profit_abs,2)
        seconds_past_pair = 0
        seconds_past_linear_regression = 0
        current_profit = profit_abs
        if pair not in self.trade_start_times:
            self.trade_start_times[pair] = current_time
        if pair not in self.trigger_threshold_adjustment_dict:
            self.trigger_threshold_adjustment_dict[pair] = current_time            
        hedged: bool = False
        seconds_past_pair = (current_time - self.trade_start_times[pair]).total_seconds()
        seconds_past_linear_regression = (current_time - self.trigger_threshold_adjustment_dict[pair]).total_seconds()
        if  self.hedging_trigger_timeout_seconds > 0: 
            self.logme(f"Triggering Hedging after {self.hedging_trigger_timeout_seconds} seconds, seconds past: {seconds_past_pair}")
        
        if (seconds_past_linear_regression >= int(self.trigger_threshold_adjustment)):
            self.logme(f"Adjusting linear regression threshold after {self.trigger_threshold_adjustment} seconds...")
            if self.bot_role == "hedger" or self.bot_role == "mixed":
                self.send_email(f"Triggering linear regression adjustment after {self.trigger_threshold_adjustment} seconds")
            self.adjustThresholds()
            for key in self.trigger_threshold_adjustment_dict:
                self.trigger_threshold_adjustment_dict[key] = current_time
        else:
            self.logme(f"Remaining {self.trigger_threshold_adjustment - seconds_past_pair} seconds before adjusting linear threshold adjustment after {self.trigger_threshold_adjustment}")

        if seconds_past_pair >= int(self.hedging_trigger_timeout_seconds):
            self.trade_start_times[pair] = current_time
            if pair in self.processed_PairProcessing:
                self.logme(f"Label '{pair}' already processed, skipping function execution.")
                del self.processed_PairProcessing[pair]
            else:
                self.processed_PairProcessing[pair] = True
                thread = threading.Thread(target=self.pair_processing, args=(pair,current_time, current_profit, trade.id,))
                thread.start()
            # pair, pair_dataframe, filtered_df, aggregate_pair_df = self.pair_processing(pair)
            # self.threads.append(thread)                  
            self.populateAggregatedMarketDataframe(current_time)
            market_aggregrated_df = self.get_market_aggregated_dataframe_from_dict(Constants.MARKET)
            aggregate_pair_df = self.get_aggregated_pair_dataframe_from_dict(pair)
            pair_dataframe = self.get_pair_dataframe_from_dict(pair)
            self.logme(f"Length of aggregated market dataframe {pair}, maximum configured={self.hedging_market_profits_check_array_length}:\n{market_aggregrated_df}")
            self.logme(f"Length of aggregated pair {pair} dataframe: {len(aggregate_pair_df)}, maximum configured={self.hedging_aggregated_pair_profits_check_array_length}:\n{aggregate_pair_df}")
            self.logme(f"Length of pair {pair}  dataframe maximum configured={self.hedging_pair_profits_check_array_length}:\n{pair_dataframe}")
            # if aggregate_pair_df is not None and len(aggregate_pair_df) >= self.hedging_aggregated_pair_profits_check_array_length:
            self.logme(f"Waiting until aggregated pair {pair} threshold {self.hedging_aggregated_pair_profits_check_array_length} is reached, aggregated now { len(aggregate_pair_df)} rows")
            if aggregate_pair_df is not None and len(aggregate_pair_df) >= self.hedging_aggregated_pair_profits_check_array_length:
                if len(market_aggregrated_df) >= self.hedging_market_profits_check_array_length:
                    l_hedging_market_profits_check_array_length = self.hedging_market_profits_check_array_length * -1
                    market_aggregrated_df = market_aggregrated_df.iloc[l_hedging_market_profits_check_array_length:]
                    self.set_market_aggregated_dataframe_from_dict(Constants.MARKET, market_aggregrated_df)
                self.logme(f"++++ Start Check Trends ++++++++++++++++++++++")
                self.logme(f"++++++++++++++++++++++++++")
                self.logme(f"Checking now trends for pair {pair}")
                pair_dataframe = self.get_pair_dataframe_from_dict(pair)
                hedged = self.checkTrends(pair, trade, current_time, current_rate, current_profit, pair_dataframe, market_aggregrated_df, aggregate_pair_df, existing_position_on_exchange, "pair") 
                self.dumpCurrentProfitAsArray(pair_dataframe,"pair_dataframe")
                self.dumpCurrentProfitAsArray(aggregate_pair_df, "aggregate_pair_df")
                self.dumpCurrentProfitAsArray(market_aggregrated_df,"market_aggregrated_df")
                pair_dataframe.drop(index=pair_dataframe.index, inplace=True)
                aggregate_pair_df.drop(index=aggregate_pair_df.index, inplace=True)
                self.set_pair_dataframe_from_dict(pair, pd.DataFrame())                
                self.set_aggregated_pair_dataframe_from_dict(pair, pd.DataFrame())
                self.logme(f"++++ End Check Trends ++++++++++++++++++++++")
                self.logme(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")                
        if hedged:
            result_pair_aggregated = self.get_pair_dataframe_from_dict(pair)['current_profit'].to_string(header=False, index=False).replace('\n', ',')
            result_market = self.get_market_aggregated_dataframe_from_dict(Constants.MARKET)['current_profit'].to_string(header=False, index=False).replace('\n', ',')
            result_pair = pair_dataframe['current_profit'].to_string(header=False, index=False).replace('\n', ',')
            self.send_email(f"#################### Successfully hedged Dataframe for Pair {pair}, Pair Dataframe:\n{pair_dataframe}\n" + 
                            f"Market Dataframe:\n{self.get_market_aggregated_dataframe_from_dict(Constants.MARKET)}\n" +
                            f"Aggregated Pair Dataframe:\n{self.get_aggregated_pair_dataframe_from_dict(pair)}\n"
                            f"Market Dataframe Array for Jupyter:\n{result_market}\n"
                            f"Pair Dataframe Array for Jupyter::\n{result_pair}\n"
                            f"Pair Aggregated Dataframe Array for Jupyter::\n{result_pair_aggregated}\n"
                            )
        self.logme(f"Leaving Hedging Modus for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
        return hedged

    def pair_processing(self, pair, current_time, current_profit, trade_id):
        # Process the function for the label
        self.logme(f"Processing function for label '{pair}'")
        lock = threading.Lock()
        # Acquire a lock for the label to ensure only one thread processes it
        try:
            lock.acquire()
            new_row = { 
                        'label': "pair", 
                        'timestamp': current_time, 
                        'current_profit': current_profit, 
                        'pair': pair, 
                        "trade_id": trade_id,
                        "processed": False
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
                pair_dataframe_not_processed = pair_dataframe[pair_dataframe['processed'] == False] 
                self.logme(f"Thread: {pair} pair dataframe")
                self.logme(f"Extracting pair {pair} from dataframe until {self.hedging_pair_profits_check_array_length} unprocessed rows are reached, current unprocessed rows in pair_dataframe: {len(pair_dataframe_not_processed)}, all rows: {len(pair_dataframe)} ")
                self.dumpCurrentProfitAsArray(pair_dataframe_not_processed, "pair_dataframe_not_processed")
                if len(pair_dataframe_not_processed) >= self.hedging_pair_profits_check_array_length:
                    self.populateAggregatedPairDataframe(pair, pair_dataframe, current_time)
                    pair_dataframe = self.get_pair_dataframe_from_dict(pair)                                
                    pair_dataframe_not_processed = pair_dataframe[pair_dataframe['processed'] == False] 
                    self.logme(f"Extracting pair {pair} from dataframe until {self.hedging_pair_profits_check_array_length} unprocessed rows are reached, current unprocessed rows in pair_dataframe: {len(pair_dataframe_not_processed)}, all rows: {len(pair_dataframe)} ")
                    # pair_dataframe.drop(index=pair_dataframe.index, inplace=True)
                    # self.set_pair_dataframe_from_dict(pair, pd.DataFrame())
                else:
                    self.logme(f"Length pair dataframe not processed: {len(pair_dataframe_not_processed)}, configured threshold {self.hedging_pair_profits_check_array_length}")
            else:
                raise Exception(f"Pair dataframe is empty")
        finally:
            self.logme(f"Thread pair_processing {pair} is finished")
            del self.processed_PairProcessing[pair]
            # Release the lock
            lock.release()
                    
        return

    def populateAggregatedPairDataframe(self, pair, pair_dataframe, current_time):
        pair_dataframe.fillna(value=False, inplace=True)
        if "processed" in pair_dataframe:
            filtered_df = pair_dataframe[pair_dataframe['processed'] == False]
        else:
            filtered_df = pair_dataframe
        cumulated_current_profit = filtered_df['current_profit'].sum()
        new_aggregate_row = { 
                    'label': "aggregated_pairs", 
                    'timestamp': current_time, 
                    'current_profit': cumulated_current_profit,
                    'pair': pair_dataframe.iloc[0]['pair'], 
                    'trade_id': pair_dataframe.iloc[0]['trade_id']
                }
        pair_dataframe['processed'] = True
        self.set_pair_dataframe_from_dict(pair, pair_dataframe)
        aggregate_pair_df = self.get_aggregated_pair_dataframe_from_dict(pair)
        aggregate_pair_df = aggregate_pair_df._append(new_aggregate_row, ignore_index=True)                
        self.set_aggregated_pair_dataframe_from_dict(pair, aggregate_pair_df)
        self.logme(f"Aggregated Dataframe Length for pair {pair}: {len(aggregate_pair_df)}")
        self.dumpCurrentProfitAsArray(aggregate_pair_df,"aggregate_pair_df")
        return aggregate_pair_df

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
            market_aggregate_df = self.get_market_aggregated_dataframe_from_dict(Constants.MARKET)
            market_aggregate_df = market_aggregate_df._append(new_market_aggregate_row, ignore_index=True)                
            self.set_market_aggregated_dataframe_from_dict(Constants.MARKET, market_aggregate_df)
            self.dumpCurrentProfitAsArray(market_aggregate_df,"market_aggregate_df")

    def checkTrends(self, pair, trade, current_time, current_rate, current_profit, pair_dataframe, market_aggregrated_df, aggregate_pair_df, existing_position_on_exchange, infix=""):
        hedged: bool = False
        trend_pair = self.detectLinearRegression(pair_dataframe)
        trend_market = self.detectLinearRegression(market_aggregrated_df)
        if self.market_analysis == False:
            self.logme(f"Market Analysis is disabled")
            trend_market = trend_pair
        trend_pair_aggregated = self.detectLinearRegression(aggregate_pair_df)
        if self.pair_aggregated_analysis == False:
            self.logme(f"Pair Aggregated Analysis is disabled")
            trend_pair_aggregated = trend_pair
        self.logme(f"Trend Pair {pair}")
        self.dumpCurrentProfitAsArray(pair_dataframe,"pair_dataframe")
        self.logme(f"Trend Market")
        self.dumpCurrentProfitAsArray(market_aggregrated_df,"market_aggregrated_df")
        self.logme(f"Trend Pair Aggregated {pair}")
        self.dumpCurrentProfitAsArray(aggregate_pair_df, "aggregate_pair_df")
        self.logme(f"Results: Trend Pair={trend_pair}, Trend Market={trend_market}, Trend Pair Aggregated={trend_pair_aggregated}")
        if trend_pair == Constants.LINEAR_DECREASING and trend_market == Constants.LINEAR_DECREASING and trend_pair_aggregated == Constants.LINEAR_DECREASING:            
            log.info(f"Found subsequent decreases in current profit, hedging now short for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
            self.logme(f"Analysed pair dataframe going short:")
            hedging_direction = "short"
            trade.is_short = False # hedge_me goes now short (opposite)
            hedged = dsHedging.hedge_me(self, trade, pair, existing_position_on_exchange)
            self.writeDataframeToFile(pair, pair_dataframe, hedging_direction + "_Pair_LINEAR_DECREASING")  
            self.writeDataframeToFile(pair, market_aggregrated_df, hedging_direction + "_Market_LINEAR_DECREASING")  
            self.writeDataframeToFile(pair, aggregate_pair_df, hedging_direction + "_Pair_Aggregated_LINEAR_DECREASING")  
        elif trend_pair == Constants.LINEAR_INCREASING and trend_market == Constants.LINEAR_INCREASING and trend_pair_aggregated == Constants.LINEAR_INCREASING:
            log.info(f"Found subsequent rises in current profit, hedging now long for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
            hedging_direction = "long"
            trade.is_short = True # hedge_me goes now long (opposite) 
            hedged = dsHedging.hedge_me(self, trade, pair, existing_position_on_exchange)
            self.writeDataframeToFile(pair, pair_dataframe, hedging_direction + "_Pair_LINEAR_INCREASING")  
            self.writeDataframeToFile(pair, market_aggregrated_df, hedging_direction + "_Market_LINEAR_INCREASING")  
            self.writeDataframeToFile(pair, aggregate_pair_df, hedging_direction + "_Pair_Aggregated_LINEAR_INCREASING")  
        else:
            self.logme(f"Not hedging {pair}, because no patterns found, trend_pair: {trend_pair}, trend_market: {trend_market}, trend_pair_aggregated: {trend_pair_aggregated} ")
            hedged = False
        return hedged

    def detectMarketTrend(self, key: str):
        market_aggregate_df = self.get_market_aggregated_dataframe_from_dict(key)
        market_trend = None
        if not market_aggregate_df.empty:
            self.logme("Checking Market Trend from status table on spot bot with following aggregated market dataframe")
            self.dumpCurrentProfitAsArray(market_aggregate_df,"market_aggregate_df")
            # self.logme(f"{status_df}")
            # market_trend = self.check_market_trend(status_df)
            market_trend = self.detectLinearRegression(market_aggregate_df)
            self.logme(f"Found following market trend in bot status={market_trend}")
        else:
            raise Exception(f"Empty Status Table Market Data, create trades first in master bot...")
        return market_trend

    def dumpCurrentProfitAsArray(self, dataframe: pd.DataFrame, label: str = ""):
        self.logme(f"$$$$$$$$$ {label}: Start: dumpCurrentProfitAsArray ---------------------------------------------------------")
        self.logme(dataframe)
        if dataframe.empty is False:
            result = dataframe['current_profit'].to_string(header=False, index=False).replace('\n', ',')
            trend = self.detectLinearRegression(dataframe)
            self.logme(label + ": Jupyter Array for Testing:\n[" + result + "]")
            self.logme(label + f"Trend: {trend}")
            self.logme(f"$$$$$$$$$$ {label}: End: dumpCurrentProfitAsArray ---------------------------------------------------------")
        else:
            self.logme("Warning: " + label + f": Dataframe is empty")

    def writeDataframeToFile(self, pair: str, dataframe: DataFrame, direction: str):      
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pair = pair.replace("/USDT:USDT", "")
        pair = pair.replace("/USDT", "")
        tradeids = ""
        if 'trade_id' in dataframe.columns:
            tradeids = dataframe.loc[0, 'trade_id']
        if dataframe.empty == False:
            result = dataframe['current_profit'].to_string(header=False, index=False).replace('\n', ',')
            file_name = f"hedged_{pair}_id_{tradeids}_{direction}_{timestamp}.csv"
            file_name_array = f"hedged_{pair}_id_{tradeids}_{direction}_{timestamp}_jupyter.csv"
            with open(file_name_array, 'w') as file:
                # Write a string to the file
                file.write('[' + result + ']')        

            dataframe.to_csv(file_name, index=True)
            self.logme(f"DataFrame written to file: {file_name}")
        else:
            self.logme(f"Dataframe is empty for pair {pair} and directory {direction}")

    def getPositionInBinance(self, pair, apikey, apisecret):
        positionFetcher = FuturesPositionsFetcher(apikey, apisecret)
        symbol=pair.split('/')[0]+"USDT"
        existing_position_on_exchange = positionFetcher.get_futures_position_information(symbol)

        return existing_position_on_exchange            

    # def getPositionInBinanceStoploss(self, pair, current_time, current_rate, current_profit):
    #     self.logme(f"Entering custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
    #     positionFetcher = FuturesPositionsFetcher(self.stoploss_apikey, self.stoploss_apisecret)
    #     symbol=pair.split('/')[0]+"USDT"
    #     self.existing_position_on_exchange = positionFetcher.get_futures_position_information(symbol)               
    
    def detectBullishOrBearishCandle(self, df: pd.DataFrame) -> Constants:
        self.logme(f"Start Detect Overall Trend")        
        self.logme(df)        
        short_window=6
        long_window=26
        signal_window=9
        # Calculate the short term exponential moving average (EMA)
        df['EMA_short'] = df['current_profit'].ewm(span=short_window, adjust=True).mean()   
        # Calculate the long term exponential moving average (EMA)
        df['EMA_long'] = df['current_profit'].ewm(span=long_window, adjust=True).mean()    
        # Calculate the MACD line
        df['MACD'] = df['EMA_short'] - df['EMA_long']   
        # Calculate the Signal line
        df['Signal_Line'] = df['MACD'].ewm(span=signal_window, adjust=False).mean()   
        # Determine the trend
        df['Trend'] = df.apply(lambda row: 'Bullish' if row['MACD'] > row['Signal_Line'] else 'Bearish', axis=1)
        # self.logme(df['Trend'])
        # Evaluate the trend based on 80% rule
        bullish_count = df['Trend'].value_counts().get('Bullish', 0)
        bearish_count = df['Trend'].value_counts().get('Bearish', 0)
        total_rows = len(df)
        # self.logme(f"bullish_count / total_rows={bullish_count / total_rows}")
        # self.logme(f"bearish_count / total_rows={bearish_count / total_rows}")
        # if bullish_count / total_rows >= 0.7:
        if bullish_count / total_rows >= self.bullish_threshold_pct:
            overall_result = Constants.BULLISH
        elif bearish_count / total_rows >= self.bearish_threshold_pct:
            overall_result = Constants.BEARISH
        else:
            overall_result = Constants.LINEAR_STABLE
        # self.logme(f"overall_result={overall_result}")
        # self.logme(f"bullish_count={bullish_count}, bearish_count={bearish_count}, total_rows={total_rows}")
        partial_length = round(float(total_rows) // self.candle_divisor)
        if partial_length > 0 and len(df) > partial_length:
            last_partial_df = df[-partial_length:]
            # Evaluate the trend in the last third
            last_partial_bullish_count = last_partial_df['Trend'].value_counts().get('Bullish', 0)
            last_partial_bearish_count = last_partial_df['Trend'].value_counts().get('Bearish', 0)
            # self.logme(f"last_partial_bullish_count={last_partial_bullish_count}")
            # self.logme(f"last_partial_bearish_count={last_partial_bearish_count}")
            # self.logme(f"partial_length={partial_length}")
            # self.logme(f"last_partial_bullish_count / partial_length={last_partial_bullish_count / partial_length}") 
            # self.logme(f"last_partial_bearish_count / partial_length={last_partial_bearish_count / partial_length}") 
            if last_partial_bullish_count / partial_length >= self.bullish_partial_threshold_pct or overall_result == Constants.BULLISH:
                last_partial_result = Constants.BULLISH
            elif last_partial_bearish_count / partial_length >= self.bearish_partial_threshold_pct or overall_result == Constants.BEARISH:
                last_partial_result = Constants.BEARISH
            else:
                last_partial_result = Constants.LINEAR_STABLE
            self.logme(f"last_partial_result={last_partial_result}")
            # Check the last 3 rows
            if self.last_trend_entries > len(df):
                self.logme(f"Last trends entries {self.last_trend_entries} is greater than candle length {len(df)} adjusting to candle length")            
                self.last_trend_entries = len(df)
            last_trends = df['Trend'].tail(self.last_trend_entries)
            if all(last_trends == 'Bullish') and overall_result == Constants.BULLISH and last_partial_result == Constants.BULLISH:
                overall_result = Constants.BULLISH
            elif all(last_trends == 'Bearish') and overall_result == Constants.BEARISH and last_partial_result == Constants.BEARISH:
                overall_result = Constants.BEARISH
            else:
                overall_result = Constants.LINEAR_STABLE
            self.logme(f"End Detect Overall Trend: overall_result={overall_result}")        
            return overall_result    
        else:
            return Constants.LINEAR_STABLE   

    def detectLinearRegression(self, df: DataFrame):
        # Step 2: Perform linear regression using scipy.stats.linregress
        if len(df) > 1:
            trend = self.detectBullishOrBearishCandle(df)
            if trend == Constants.BULLISH:
                self.logme('Values are increasing')
                return Constants.LINEAR_INCREASING
            elif trend == Constants.BEARISH:
                self.logme('Values are decreasing')
                return Constants.LINEAR_DECREASING
        else:
            self.logme(f"Cannot calculate trend for dataframe, cause must be more than one row in dataframe")
        return Constants.LINEAR_STABLE

    
