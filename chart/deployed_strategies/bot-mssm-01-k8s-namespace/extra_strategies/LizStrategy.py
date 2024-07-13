kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-mssm-01 exec -it pod/freqtrade-bot-mssm-01-5f5bdfb5b4-kbc7z -c freqtrade -- cat /extra_strategies/LizStrategy.py
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
from pandas import DataFrame, Series
import scipy
# --------------------------------
import talib.abstract as ta
import ta as taa
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy  # noqa
import talib

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

class Constants(Enum):
    LINEAR_INCREASING = 1
    LINEAR_DECREASING = 2
    LINEAR_STABLE = 3
    
class LizStrategy(IStrategy):
    rpc: RPCManager = None
    # DerSalvador Hedging
    hedging_url = ""
    hedging_leverage = 1
    hedging_stake_amount = 0
    hedging_apikey = ""
    hedging_apisecret = ""
    hedging_analyse_timeframe = "1h"  
    stoploss_apikey = ""
    stoploss_apisecret = ""    
    spot_bot_api_status = ""
    bot_username = ""
    bot_password = ""
    hedging_trigger_timeout_seconds = 0
    hedging_profits_check_array_length = 0
    hedging_aggregated_profits_check_array_length = 0
    hedging_market_profits_check_array_length = 0
    
    existing_position_on_exchange = None    
    trade_start_times = {}  
    aggregated_dataframe_dict = {}
    market_aggregated_dataframe_dict = {}
    stoploss_dataframe_dict = {}
    linearRegressionIncreasingThreshold_Start = 0.004
    linearRegressionIncreasingThreshold_End = 0.1
    linearRegressionDecreasingThreshold_Start = -0.002
    linearRegressionDecreasingThreshold_End = -0.1
    start_profit_abs_positiv = 0.1
    start_profit_abs_negative = -0.1
    stoploss_bot_api = ""
    market_rising_count = 0
    market_falling_count = 0
    market_stable_count = 0
    market_threshold_pct = 0.8

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
        self.hedging_url = config['dersalvador']['hedging']['hedge_bot_api']
        self.hedging_leverage = config['dersalvador']['hedging']['leverage']
        self.hedging_stake_amount = config['dersalvador']['hedging']['stake_amount']
        self.hedging_apikey = config['dersalvador']['hedging']['apikey']
        self.hedging_apisecret = config['dersalvador']['hedging']['apisecret']
        self.stoploss_apikey = config['dersalvador']['hedging']['stoploss_apikey']
        self.stoploss_apisecret = config['dersalvador']['hedging']['stoploss_apisecret']
        self.hedging_trigger_timeout_seconds = config['dersalvador']['hedging']['trigger_timeout_seconds']
        self.hedging_profits_check_array_length = config['dersalvador']['hedging']['profits_check_array_length']
        self.hedging_aggregated_profits_check_array_length = config['dersalvador']['hedging']['aggregated_profits_check_array_length']
        self.hedging_market_profits_check_array_length = config['dersalvador']['hedging']['market_profits_check_array_length']
        self.spot_bot_api_status = config['dersalvador']['hedging']['spot_bot_api_status']
        self.hedge_bot_api_status = config['dersalvador']['hedging']['hedge_bot_api_status']
        self.hedge_bot_api_profit = config['dersalvador']['hedging']['hedge_bot_api_profit']
        self.bot_username =  config['api_server']['username']
        self.bot_password =  config['api_server']['password']
        self.linearRegressionIncreasingThreshold_Start = config['dersalvador']['hedging']['linearRegressionIncreasingThreshold_Start']
        self.linearRegressionIncreasingThreshold_End = config['dersalvador']['hedging']['linearRegressionIncreasingThreshold_End']
        self.linearRegressionDecreasingThreshold_Start = config['dersalvador']['hedging']['linearRegressionDecreasingThreshold_Start']
        self.linearRegressionDecreasingThreshold_End = config['dersalvador']['hedging']['linearRegressionDecreasingThreshold_End']
        self.start_profit_abs_positiv = config['dersalvador']['hedging']['start_profit_abs_positiv']
        self.start_profit_abs_negative = config['dersalvador']['hedging']['start_profit_abs_negative']
        self.stoploss_bot_api  = config['dersalvador']['hedging']['stoploss_bot_api']
        self.market_threshold_pct  = config['dersalvador']['hedging']['market_threshold_pct']
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
            self.hedging_config(self.config)
            msg=f'*Found Hedging section in config*\n'
            msg+=f'*API:* {self.hedging_url}\n'
            msg+=f'*Amount:* {self.hedging_stake_amount}\n' 
            msg+=f'*Leverage:* {self.hedging_leverage}\n'
            msg+=f'*profits_check_array_length:* {self.hedging_profits_check_array_length}\n'
            msg+=f'*aggregated_profits_check_array_length:* {self.hedging_aggregated_profits_check_array_length}\n'
            msg+=f'*market_profits_check_array_length:* {self.hedging_market_profits_check_array_length}\n'
            msg+=f'*trigger_timeout_seconds:* {self.hedging_trigger_timeout_seconds}\n'
            msg+=f'*bot_api_status:* {self.spot_bot_api_status}\n'
            msg+=f'*bot_username:* {self.bot_username}\n'
            msg+=f'*bot_password:* {self.bot_password}\n'
            msg+=f'*linearRegressionIncreasingThreshold_Start:* {self.linearRegressionIncreasingThreshold_Start}\n'
            msg+=f'*linearRegressionIncreasingThreshold_End:* {self.linearRegressionIncreasingThreshold_End}\n'
            msg+=f'*linearRegressionDecreasingThreshold_Start:* {self.linearRegressionDecreasingThreshold_Start}\n'
            msg+=f'*linearRegressionDecreasingThreshold_End:* {self.linearRegressionDecreasingThreshold_End}\n'
            msg+=f'*start_profit_abs_positiv:* {self.start_profit_abs_positiv}\n'
            msg+=f'*start_profit_abs_negative:* {self.start_profit_abs_negative}\n'
            msg+=f'*stoploss_bot_api:* {self.stoploss_bot_api}\n'
            msg+=f'*market_threshold_pct:* {self.market_threshold_pct}\n'
            
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
        dataframe.loc[(dataframe['close'] > 2e-06) & (dataframe['volume'] > dataframe['volume'].rolling(self.entry_volumeAVG.value).mean() * 4) & (dataframe['close'] < dataframe['sma']) & (dataframe['fastd'] > dataframe['fastk']) & (dataframe['rsi'] > self.entry_rsi.value) & (dataframe['fastd'] > self.entry_fastd.value) & (dataframe['fisher_rsi_norma'] < self.entry_fishRsiNorma.value), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with entry column
        """ 
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
        self.logme(f"----------------------------------------------------------")
        self.logme(f"Entering custom stoploss for pair {pair}")
        stoploss_distance_to_zero = trade.amount*trade.open_rate*trade.stop_loss_pct-current_profit
        self.logme(f"Stoploss distance for pair {pair}: {stoploss_distance_to_zero}")
        json = self.getJsonFromAPI(self.hedge_bot_api_profit)
        profit_all_coin = json['profit_all_coin']
        self.logme(f"Profit in hedgebot {self.hedge_bot_api_profit} for all coins is: {profit_all_coin}" )
        config_stoploss = float(self.config['stoploss'])
        bot_name = self.config['bot_name']
        if profit_all_coin < 0:
            newstoploss = config_stoploss - 0.01
        else:
            newstoploss = config_stoploss + 0.01
        # Stoploss passed 100%
        if newstoploss < -0.99:
            newstoploss = -0.99
        # Stoploss in direction positive
        if newstoploss > -0.05:
            newstoploss = -0.1
        self.logme(f"Setting new stoploss pct to {newstoploss} for pair {pair} in bot {bot_name}")
            
        # try:
        #     jsonTrade = self.getJsonTrade(pair, self.spot_bot_api_status)
        #     if jsonTrade is not None:
        #         stoploss_entry_dist = jsonTrade.get('stoploss_entry_dist')
        #         profit_abs = jsonTrade.get('profit_abs')
        #         leverage = jsonTrade.get('leverage')
        #         is_short = jsonTrade.get('is_short')
        #         trade.is_short = is_short
        #         self.logme(f"Stoploss Distance = {stoploss_entry_dist}")
        #         stoploss_distance_abs = stoploss_entry_dist-profit_abs
        #         self.logme(f"set new stop loss because stoploss_entry_distance_abs {stoploss_distance_abs} close to zero")
        #         if abs(stoploss_distance_abs) - 50 <= 0:
        #             self.logme(f"Getting closer to zero {stoploss_distance_abs - 50}, stop loss with be increased with 1%")
        #             newstoploss = config_stoploss + 0.01
        #         new_stoploss_row = { 
        #             'timestamp': current_time, 
        #             'stoploss_distance_abs': stoploss_distance_abs,
        #             'current_profit': current_profit,
        #             'profit_abs': profit_abs,
        #             'stoploss_entry_dist': stoploss_entry_dist,
        #             'pair': pair 
        #         }
        #         self.logme(f"Stoploss distance absolut = {stoploss_distance_abs}, when getting close to zero stoploss triggers...")
        #         stoploss_df = self.get_stoploss_dataframe_from_dict(pair)
        #         stoploss_df = stoploss_df._append(new_stoploss_row, ignore_index=True)                
        #         self.set_stoploss_dataframe_from_dict(pair, stoploss_df)
        #         self.logme(f"Stoploss Dataframe = {stoploss_df}")
        #         positionInBinance = self.getPositionInBinance(pair, self.stoploss_apikey, self.stoploss_apisecret)
        #         if len(stoploss_df) >= self.hedging_current_profits_check_array_length:
        #             trend, slope = self.detectLinearRegression(stoploss_df,"stoploss_distance_abs")        
        #             if trend == Constants.LINEAR_DECREASING: 
        #                 self.writeDataframeToFile(pair, stoploss_df, "is_short=" +  trade.is_short + "_stoploss_LINEAR_DECREASING", trade, slope)  
        #                 # the more distance moves away from zero the greater is distance to stoploss (stoploss_distance_abs converges to zero)
        #                 # Stoploss is reached when stoploss_distance_abs converge to zero, meaning increasing
        #                 self.logme(f"Distance to stoploss/liquidation diverging negative {stoploss_distance_abs} from 0, profit_abs={profit_abs}, stoploss_distance_abs={stoploss_distance_abs}")
        #                 if float(positionInBinance[0]['positionAmt']) == 0.0:
        #                     market_trend = self.detectMarketTrend()
        #                     if market_trend == Constants.LINEAR_DECREASING:
        #                         hedged = dsHedging.hedge_me(self, trade, pair, self.existing_position_on_exchange, self.stoploss_bot_api)
        #                     else:
        #                         self.logme("Market is not decreasing, so not going short")                            
        #             if trend == Constants.LINEAR_INCREASING: 
        #                 self.writeDataframeToFile(pair, stoploss_df, "is_short=" + trade.is_short + "_stoploss_LINEAR_INCREASING", trade, slope)  
        #                 # the closer to zero (increasing) the closer distance to stoploss
        #                 # Stoploss is reached when stoploss_distance_abs converge to zero, meaning increasing
        #                 self.logme(f"Distance to stoploss/liquidation converging {stoploss_distance_abs} to 0, profit_abs={profit_abs}, stoploss_distance_abs={stoploss_distance_abs}")
        #                 if float(positionInBinance[0]['positionAmt']) == 0.0:
        #                     market_trend = self.detectMarketTrend()
        #                     if market_trend == Constants.LINEAR_DECREASING:
        #                         hedged = dsHedging.hedge_me(self, trade, pair, self.existing_position_on_exchange, self.stoploss_bot_api)
        #                     else:
        #                         self.logme("Market is not decreasing, so not going short")                            
        #             self.set_stoploss_dataframe_from_dict(pair, pd.DataFrame())
        #     else:
        #         self.logme("Pair {pair} not found in bot {self.spot_bot_api_status}")              
        # except Exception as e:
        #     print(f"Stoploss distance not found for pair {pair}")
        #     print(f"{e}")
        # finally:
        #     print('Continuing after exception with next pair')
        # self.logme(f"Leaving custom stoploss for pair {pair}")
        # self.logme(f"----------------------------------------------------------")

        return newstoploss
    
    def custom_exit(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
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
        print(f"{msg}")
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
            new_row = { 'timestamp': open_timestamp, 'current_profit': current_profit, 'pair': pair, "trade_id": tradeid, "stop_loss_pct": stop_loss_pct}
            if self.market_status_df.empty:
                new_rows_df = pd.DataFrame(new_row, index=[0])
            else:
                new_rows_df = pd.DataFrame(new_row, index=[len(self.market_status_df['timestamp'])])
            self.market_status_df = self.market_status_df._append(new_rows_df)
        return self.market_status_df

    def hedgeMe(self, pair: str, trade: Trade, current_time: 'datetime', current_rate: float,
                    current_profit: float, dataframe: DataFrame, **kwargs): 
        hedged = False;
        self.logme(f"MSSM: Entering Hedging Logic for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}") 
        t = self.getJsonTrade(pair)
        if t is not None:
            profit_abs = t.get('profit_abs')
            # self.logme(dataframe)
            # Exit the trade if it has been more than 5 minutes with a negative profit
            if profit_abs > self.start_profit_abs_positiv or profit_abs < self.start_profit_abs_negative: 
                existing_position_on_exchange = self.getPositionInBinance(pair, self.hedging_apikey, self.hedging_apisecret)
                # dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
                # current_profit = self.remove_decimal_digits(profit_abs)
                hedged = self.hedgeMeCore(pair, trade, current_time, current_rate, profit_abs, existing_position_on_exchange)
            else:
                self.logme(f"Filtering profit abs {profit_abs} because is inside range start_profit_abs_negative-start_profit_abs_positiv: {self.start_profit_abs_negative}-{self.start_profit_abs_positiv}")
        return hedged

    def get_aggregated_dataframe_from_dict(self, key):
        if key in self.aggregated_dataframe_dict:
            return self.aggregated_dataframe_dict[key]
        else:
            empty_df = pd.DataFrame()
            self.aggregated_dataframe_dict[key] = empty_df
            return empty_df

    def set_aggregated_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        self.aggregated_dataframe_dict[key] = dataframe
    
    def get_market_aggregated_dataframe_from_dict(self, key):
        if key in self.market_aggregated_dataframe_dict:
            return self.market_aggregated_dataframe_dict[key]
        else:
            empty_df = pd.DataFrame()
            self.market_aggregated_dataframe_dict[key] = empty_df
            return empty_df

    def set_market_aggregated_dataframe_from_dict(self, key: str, dataframe: pd.DataFrame):
        self.market_aggregated_dataframe_dict[key] = dataframe
    
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
        current_profit = profit_abs
        if trade.id not in self.trade_start_times:
            self.trade_start_times[trade.id] = current_time
        hedged: bool = False
        if  self.hedging_trigger_timeout_seconds > 0: 
            self.logme(f"Triggering Hedging after {self.hedging_trigger_timeout_seconds} seconds, now: {(current_time - self.trade_start_times[trade.id]).total_seconds()}")
        if (current_time - self.trade_start_times[trade.id]).total_seconds() >= int(self.hedging_trigger_timeout_seconds):
            # aggregate market status dataframe to one aggregated dataframe
            self.populateAggregatedMarketDataframe()            
            # aggregate pair dataframes to on aggregated dataframe
            new_row = { 'timestamp': current_time, 'current_profit': current_profit, 'pair': pair, "trade_id": trade.id}
            self.trade_start_times[trade.id] = current_time
            if self.trade_profit_dataframe.empty:
                new_rows_df = pd.DataFrame(new_row, index=[0])
            else:
                new_rows_df = pd.DataFrame(new_row, index=[len(self.trade_profit_dataframe['timestamp'])])            
            self.trade_profit_dataframe = self.trade_profit_dataframe._append(new_rows_df)     
            pair_dataframe: pd.DataFrame = None           
            filtered_df: pd.DataFrame = None
            aggregate_df: pd.DataFrame = None
            pair_dataframe = self.trade_profit_dataframe[self.trade_profit_dataframe['pair'] == pair]
            pair_dataframe = pair_dataframe.reset_index(drop=True)
            filtered_df = self.trade_profit_dataframe[self.trade_profit_dataframe['pair'] != pair]
            filtered_df = filtered_df.reset_index(drop=True)
            self.logme(f"Extracting pair {pair} from dataframe until {self.hedging_profits_check_array_length} elements are reached, now: {len(pair_dataframe)} ")
            self.dumpCurrentProfitAsArray(pair_dataframe) 
            if len(pair_dataframe) >= self.hedging_profits_check_array_length:
                self.populateAggregatedPairDataframe(pair, pair_dataframe)         
                self.logme(f"++++ Start Profit Abs Dataframe Check Trends ++++++++++++++++++++++")
                self.logme(f"Checking now profit abs trends for pair {pair}")
                hedged = self.checkTrends(pair, trade, current_time, current_rate, current_profit, pair_dataframe, existing_position_on_exchange) 
                self.trade_profit_dataframe = filtered_df
                self.logCheckEnd(pair, filtered_df)
                self.logme(f"++++ End Profit Abs Check Trends ++++++++++++++++++++++")
                self.logme(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            aggregate_df = self.get_aggregated_dataframe_from_dict(pair)
            if not hedged and len(aggregate_df) >= self.hedging_aggregated_profits_check_array_length:
                self.logme(f"#### Start AGGREGATED Dataframe Check Trends ############")
                self.logme(f"Checking Aggregated trends for {pair} in following aggregated dataframe") 
                self.logme(f"{aggregate_df}")
                self.set_aggregated_dataframe_from_dict(pair, pd.DataFrame())
                hedged = self.checkTrends(pair, trade, current_time, current_rate, current_profit, aggregate_df, existing_position_on_exchange) 
                self.logCheckEnd(pair, aggregate_df)
                self.logme(f"#### End AGGREGATED Check Trends ############")
                self.logme(f"#################################################################################################")
        self.logme(f"Leaving Hedging Modus for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
        return hedged

    def populateAggregatedPairDataframe(self, pair, pair_dataframe):
        cumulated_current_profit = pair_dataframe['current_profit'].sum()
        new_aggregate_row = { 
                    'timestamp': pair_dataframe.iloc[0]['timestamp'], 
                    'current_profit': cumulated_current_profit,
                    'pair': pair_dataframe.iloc[0]['pair'] 
                }
        aggregate_df = self.get_aggregated_dataframe_from_dict(pair_dataframe.iloc[0]['pair'])
        aggregate_df = aggregate_df._append(new_aggregate_row, ignore_index=True)                
        self.set_aggregated_dataframe_from_dict(pair_dataframe.iloc[0]['pair'], aggregate_df)
        self.logme(f"Aggregated Dataframe Length for pair {pair}: {len(aggregate_df)}")

    def populateAggregatedMarketDataframe(self):
        status_df = self.getStatusTableAsDataframe()
        cumulated_market_profit = status_df['current_profit'].sum()
        new_market_aggregate_row = { 
                'timestamp': status_df.iloc[0]['timestamp'], 
                'current_profit': cumulated_market_profit 
            }
        market_aggregate_df = self.get_market_aggregated_dataframe_from_dict("market")
        market_aggregate_df = market_aggregate_df._append(new_market_aggregate_row, ignore_index=True)                
        self.set_market_aggregated_dataframe_from_dict("market", market_aggregate_df)

    def logCheckEnd(self, pair, filtered_df):
        self.logme(f"END of Checking trends for pair {pair}")
        self.logme(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        self.logme(f"Filtered out {pair}, remaining dataframe {filtered_df}")
        self.logme(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    
    def checkTrends(self, pair, trade, current_time, current_rate, current_profit, pair_dataframe, existing_position_on_exchange):
        hedged: bool = False
        trend: bool = False
        trend, slope = self.detectLinearRegression(pair_dataframe)        
        if trend == Constants.LINEAR_DECREASING:            
            log.info(f"Found subsequent decreases in current profit, hedging now short for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
            self.logme(f"Analysed pair dataframe going short:")
            self.logme(f"{pair_dataframe}")
            hedging_direction = "short"
            trade.is_short = False # hedge_me goes now short (opposite)
            market_trend = self.detectMarketTrend()
            if market_trend == Constants.LINEAR_DECREASING:
                hedged = dsHedging.hedge_me(self, trade, pair, existing_position_on_exchange)
                self.writeDataframeToFile(pair, pair_dataframe, hedging_direction + "_LINEAR_DECREASING", trade, slope)  
            else:
                self.logme("Market is not decreasing, so not going short")
        if trend == Constants.LINEAR_INCREASING:
            log.info(f"Found subsequent rises in current profit, hedging now long for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
            self.logme(f"Analysed pair dataframe going long:")
            self.logme(f"{pair_dataframe}")
            hedging_direction = "long"
            trade.is_short = True # hedge_me goes now long (opposite) 
            market_trend = self.detectMarketTrend()
            if market_trend == Constants.LINEAR_INCREASING:
                hedged = dsHedging.hedge_me(self, trade, pair, existing_position_on_exchange)
                self.writeDataframeToFile(pair, pair_dataframe, hedging_direction + "_LINEAR_INCREASING", trade, slope)  
            else:
                self.logme("Market is not increasing, so not going long")
        if trend == Constants.LINEAR_STABLE:
            self.logme(f"Not hedging {pair}, because no patterns found")
            self.dumpCurrentProfitAsArray(pair_dataframe) 
            hedged = False
        self.set_market_aggregated_dataframe_from_dict("market", pd.DataFrame())
        return hedged

    def detectMarketTrend(self):
        market_aggregate_df = self.get_market_aggregated_dataframe_from_dict("market") 
        self.logme("Checking Global Market Trend on spot bot with following aggregated status dataframe")
        self.logme(f"{market_aggregate_df}")
        # self.logme(f"{status_df}")
        # market_trend = self.check_market_trend(status_df)
        market_trend, _ = self.detectLinearRegression(market_aggregate_df)
        self.logme(f"Found following market trend in bot status={market_trend}")
        return market_trend

    def dumpCurrentProfitAsArray(self, dataframe: pd.DataFrame):
        self.logme(dataframe)
        result = dataframe['current_profit'].to_string(header=False, index=False).replace('\n', ',')
        print("[" + result + "]")

    def writeDataframeToFile(self, pair: str, dataframe: DataFrame, direction: str, trade: Trade, slope):      
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pair = pair.replace("/USDT:USDT", "")
        pair = pair.replace("/USDT", "")
        # Define the file name with timestamp
        slope = "{:.3f}".format(slope)
        file_name = f"hedged_{pair}_id_{trade.id}_slope_{slope}_{direction}_{timestamp}.csv"
        file_name_market = f"hedged_{pair}_id_{trade.id}_slope_{slope}_{direction}_{timestamp}_market.csv"
        file_name_aggregated_market = f"hedged_{pair}_id_{trade.id}_slope_{slope}_{direction}_{timestamp}_aggregated_market.csv"
        # Write DataFrame to file
        dataframe.to_csv(file_name, index=True)
        self.logme(f"Saving market trends as status table to {file_name_market}")
        status_df = self.getStatusTableAsDataframe()
        status_df.to_csv(file_name_market, index=True)
        market_aggregate_df = self.get_market_aggregated_dataframe_from_dict("market")
        market_aggregate_df.to_csv(file_name_aggregated_market, index=True)
        self.logme("Found following market trend in bot status={market_trend}")
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
                
    def detectLinearRegression(self, df: DataFrame, column: str = "current_profit"):
        # Step 2: Perform linear regression using scipy.stats.linregress
        slope, intercept, r_value, p_value, std_err = linregress(df.index, df[column])

        # Output the slope of the regression line
        self.logme(f'Slope of the regression line: {slope}')

        # Step 3: Check if the values are decreasing or increasing based on the slope
        if slope > self.linearRegressionIncreasingThreshold_Start and slope < self.linearRegressionIncreasingThreshold_End:
            self.logme('Values are increasing')
            return Constants.LINEAR_INCREASING, slope
        elif slope < self.linearRegressionDecreasingThreshold_Start and slope > self.linearRegressionDecreasingThreshold_End:
            self.logme('Values are decreasing')
            return Constants.LINEAR_DECREASING, slope
        self.logme(f"detectLinearRegression: No Linear Regression found for pair {df['pair']}")
        self.logme(f"detectLinearRegression: Current Slope Value: {slope},")
        self.logme(f"detectLinearRegression: Increase Linear Threshold between: {self.linearRegressionIncreasingThreshold_Start}-{self.linearRegressionIncreasingThreshold_End}")
        self.logme(f"detectLinearRegression: Decrease Linear Threshold between: {self.linearRegressionDecreasingThreshold_Start}-{self.linearRegressionDecreasingThreshold_End}")
        self.dumpCurrentProfitAsArray(df)
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

    
