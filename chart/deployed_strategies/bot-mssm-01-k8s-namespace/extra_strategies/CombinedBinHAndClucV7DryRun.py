kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-mssm-01 exec -it pod/freqtrade-bot-mssm-01-858b999f6c-pf26r -c freqtrade -- cat /extra_strategies/CombinedBinHAndClucV7DryRun.py
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
from freqtrade.strategy import merge_informative_pair
from freqtrade.strategy import DecimalParameter, IntParameter
from freqtrade.strategy.interface import IStrategy
from freqtrade.persistence import Trade
from pandas import DataFrame
from datetime import datetime, timedelta
from functools import reduce

from collections import defaultdict
from datetime import timedelta
import numpy as np
import pandas as pd
from freqtrade.mixins.logging_mixin import LoggingMixin
import os
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, CategoricalParameter
from pandas import DataFrame, Series
import talib.abstract as ta
from datetime import datetime, timedelta
import scipy
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from functools import reduce
# from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import RobustScaler
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from utils.FuturesPositionsFetcher import FuturesPositionFetcher
from typing import Dict, List, Optional, Tuple, Union
# import freqtrade.vendor.qtpylib.indicators as qtpylib

from freqtrade.strategy import (IStrategy, DecimalParameter, CategoricalParameter)
from freqtrade.persistence import Trade

# Strategy specific imports, files must reside in same folder as strategy
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import logging
import warnings

log = logging.getLogger(__name__)

logging.disable(logging.NOTSET)
print("Log enabled: ",log.isEnabledFor(logging.INFO))

LoggingMixin.show_output = True
    
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
###########################################################################################################
##                CombinedBinHAndClucV7 by iterativ                                                      ##
##                                                                                                       ##
##    Freqtrade https://github.com/freqtrade/freqtrade                                                   ##
##    The authors of the original CombinedBinHAndCluc https://github.com/freqtrade/freqtrade-strategies  ##
##    V7 by iterativ.                                                                                    ##
##                                                                                                       ##
###########################################################################################################
##               GENERAL RECOMMENDATIONS                                                                 ##
##                                                                                                       ##
##   For optimal performance, suggested to use between 4 and 6 open trades, with unlimited stake.        ##
##   A pairlist with 20 to 60 pairs. Volume pairlist works well.                                         ##
##   Prefer stable coin (USDT, BUSDT etc) pairs, instead of BTC or ETH pairs.                            ##
##   Highly recommended to blacklist leveraged tokens (*BULL, *BEAR, *UP, *DOWN etc).                    ##
##   Ensure that you don't override any variables in you config.json. Especially                         ##
##   the timeframe (must be 5m) & exit_profit_only (must be true).                                       ##
##                                                                                                       ##
###########################################################################################################
##               DONATIONS                                                                               ##
##                                                                                                       ##
##   Absolutely not required. However, will be accepted as a token of appreciation.                      ##
##                                                                                                       ##
##   BTC: bc1qvflsvddkmxh7eqhc4jyu5z5k6xcw3ay8jl49sk                                                     ##
##   ETH: 0x83D3cFb8001BDC5d2211cBeBB8cB3461E5f7Ec91                                                     ##
##                                                                                                       ##
###########################################################################################################
# SSL Channels

def SSLChannels(dataframe, length=7):
    df = dataframe.copy()
    df['ATR'] = ta.ATR(df, timeperiod=14)
    df['smaHigh'] = df['high'].rolling(length).mean() + df['ATR']
    df['smaLow'] = df['low'].rolling(length).mean() - df['ATR']
    df['hlv'] = np.where(df['close'] > df['smaHigh'], 1, np.where(df['close'] < df['smaLow'], -1, np.NAN))
    df['hlv'] = df['hlv'].ffill()
    df['sslDown'] = np.where(df['hlv'] < 0, df['smaHigh'], df['smaLow'])
    df['sslUp'] = np.where(df['hlv'] < 0, df['smaLow'], df['smaHigh'])
    return (df['sslDown'], df['sslUp'])

class CombinedBinHAndClucV7DryRun(IStrategy):
    rpc: RPCManager = None
    # DerSalvador Hedging
    dry_run = True
    dry_run_wallet = 50000
    hedging_url = ""
    hedging_leverage = 1
    hedging_stake_amount = 0
    hedging_apikey = ""
    hedging_apisecret = ""    
    existing_position_on_exchange = None
    
    INTERFACE_VERSION = 3
    minimal_roi = {'0': 0.0181}
    stoploss = -0.99  # effectively disabled.
    timeframe = '5m'
    inf_1h = '1h'  # informative tf
    # Sell signal
    use_exit_signal = True
    exit_profit_only = True
    exit_profit_offset = 0.001  # it doesn't meant anything, just to guarantee there is a minimal profit.
    ignore_roi_if_entry_signal = True
    # Trailing stoploss
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03
    # Custom stoploss
    use_custom_stoploss = True
    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True
    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 200
    # Optional order type mapping.
    order_types = {'entry': 'limit', 'exit': 'limit', 'stoploss': 'market', 'stoploss_on_exchange': False}
    # Buy Hyperopt params
    entry_dip_threshold_1 = DecimalParameter(0.08, 0.2, default=0.14, space='entry', decimals=2, optimize=False, load=True)
    entry_dip_threshold_2 = DecimalParameter(0.02, 0.4, default=0.34, space='entry', decimals=2, optimize=False, load=True)
    entry_dip_threshold_3 = DecimalParameter(0.25, 0.44, default=0.38, space='entry', decimals=2, optimize=False, load=True)
    entry_bb40_bbdelta_close = DecimalParameter(0.005, 0.04, default=0.031, space='entry', optimize=True, load=True)
    entry_bb40_closedelta_close = DecimalParameter(0.01, 0.03, default=0.021, space='entry', optimize=True, load=True)
    entry_bb40_tail_bbdelta = DecimalParameter(0.2, 0.4, default=0.264, space='entry', optimize=True, load=True)
    entry_bb20_close_bblowerband = DecimalParameter(0.8, 1.1, default=0.992, space='entry', optimize=True, load=True)
    entry_bb20_volume = IntParameter(18, 36, default=29, space='entry', optimize=True, load=True)
    entry_rsi_diff = DecimalParameter(34.0, 60.0, default=50.48, space='entry', decimals=2, optimize=True, load=True)
    entry_min_inc = DecimalParameter(0.005, 0.05, default=0.01, space='entry', decimals=2, optimize=True, load=True)
    entry_rsi_1h = DecimalParameter(40.0, 70.0, default=67.0, space='entry', decimals=2, optimize=True, load=True)
    entry_rsi = DecimalParameter(30.0, 40.0, default=38.5, space='entry', decimals=2, optimize=True, load=True)
    entry_mfi = DecimalParameter(36.0, 65.0, default=36.0, space='entry', decimals=2, optimize=True, load=True)
    # Sell Hyperopt params
    exit_roi_profit_1 = DecimalParameter(0.08, 0.16, default=0.1, space='exit', decimals=2, optimize=False, load=True)
    exit_roi_rsi_1 = DecimalParameter(30.0, 38.0, default=34, space='exit', decimals=2, optimize=False, load=True)
    exit_roi_profit_2 = DecimalParameter(0.02, 0.05, default=0.03, space='exit', decimals=2, optimize=False, load=True)
    exit_roi_rsi_2 = DecimalParameter(34.0, 44.0, default=38, space='exit', decimals=2, optimize=False, load=True)
    exit_roi_profit_3 = DecimalParameter(0.0, 0.0, default=0.0, space='exit', decimals=2, optimize=False, load=True)
    exit_roi_rsi_3 = DecimalParameter(48.0, 56.0, default=50, space='exit', decimals=2, optimize=False, load=True)
    exit_rsi_main = DecimalParameter(72.0, 90.0, default=77, space='exit', decimals=2, optimize=True, load=True)


    @staticmethod
    def setRPCManager(rpc: RPCManager):
        CombinedBinHAndClucV7DryRun.rpc = rpc

    def hedge(self, pair, direction):
        dsHedging.hedge(self, pair, direction)
        
    @staticmethod
    def sendMessageToTelegram(msg: str):
        msg = {
            'type': RPCMessageType.STARTUP,
            'status': f"{msg}"
        }
        if CombinedBinHAndClucV7DryRun.rpc is not None: 
            CombinedBinHAndClucV7DryRun.rpc.send_msg(msg)
        else:
            log.warning("RPC Telegram object not initialized in Strategy")
                    
    ############################################
    def hedging_config(self, config) -> None:
        self.hedging_url = config['dersalvador']['hedging']['hedge_bot_api']
        self.hedging_leverage = config['dersalvador']['hedging']['leverage']
        self.hedging_stake_amount = config['dersalvador']['hedging']['stake_amount']
        self.hedging_apikey = config['dersalvador']['hedging']['apikey']
        self.hedging_apisecret = config['dersalvador']['hedging']['apisecret']
        
    def bot_start(self, **kwargs) -> None:
        
        if self.config['dersalvador']['hedging'] is not None:
            self.hedging_config(self.config)
            msg=f'*Found Hedging section in config*\n'
            msg+=f'*API:* {self.hedging_url}\n'
            msg+=f'*Amount:* {self.hedging_stake_amount}\n' 
            msg+=f'*Leverage:* {self.hedging_leverage}\n'
            log.info(msg)
            CombinedBinHAndClucV7DryRun.sendMessageToTelegram(msg)
        else:
            msg="No Hedging section found in config file"
            log.info(msg)
            CombinedBinHAndClucV7DryRun.sendMessageToTelegram(msg)
            
        return
    
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        # Manage losing trades and open room for better ones.
        if (current_profit < 0) & (current_time - timedelta(minutes=280) > trade.open_date_utc):
            return 0.01
        return 0.99

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float, rate: float, time_in_force: str, exit_reason: str, **kwargs) -> bool:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        # Prevent exit, if there is more potential, in order to maximize profit
        if last_candle is not None:
            current_profit = trade.calc_profit_ratio(rate)
            if exit_reason == 'roi':
                if current_profit > self.exit_roi_profit_1.value:
                    if last_candle['rsi'] > self.exit_roi_rsi_1.value:
                        return False
                elif current_profit > self.exit_roi_profit_2.value:
                    if last_candle['rsi'] > self.exit_roi_rsi_2.value:
                        return False
                elif current_profit > self.exit_roi_profit_3.value:
                    if last_candle['rsi'] > self.exit_roi_rsi_3.value:
                        return False
        return True

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.inf_1h) for pair in pairs]
        return informative_pairs

    def informative_1h_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        assert self.dp, 'DataProvider is required for multiple timeframes.'
        # Get the informative pair
        informative_1h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_1h)
        # EMA
        informative_1h['ema_50'] = ta.EMA(informative_1h, timeperiod=50)
        informative_1h['ema_200'] = ta.EMA(informative_1h, timeperiod=200)
        # SMA
        informative_1h['sma_200'] = ta.SMA(informative_1h, timeperiod=200)
        # RSI
        informative_1h['rsi'] = ta.RSI(informative_1h, timeperiod=14)
        # SSL Channels
        ssl_down_1h, ssl_up_1h = SSLChannels(informative_1h, 20)
        informative_1h['ssl_down'] = ssl_down_1h
        informative_1h['ssl_up'] = ssl_up_1h
        return informative_1h

    def normal_tf_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # strategy BinHV45
        bb_40 = qtpylib.bollinger_bands(dataframe['close'], window=40, stds=2)
        dataframe['lower'] = bb_40['lower']
        dataframe['mid'] = bb_40['mid']
        dataframe['bbdelta'] = (bb_40['mid'] - dataframe['lower']).abs()
        dataframe['closedelta'] = (dataframe['close'] - dataframe['close'].shift()).abs()
        dataframe['tail'] = (dataframe['close'] - dataframe['low']).abs()
        # strategy ClucMay72018
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['volume_mean_slow'] = dataframe['volume'].rolling(window=30).mean()
        # EMA
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        # SMA
        dataframe['sma_5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['sma_200'] = ta.EMA(dataframe, timeperiod=200)
        # MFI
        dataframe['mfi'] = ta.MFI(dataframe, timeperiod=14)
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # The indicators for the 1h informative timeframe
        informative_1h = self.informative_1h_indicators(dataframe, metadata)
        dataframe = merge_informative_pair(dataframe, informative_1h, self.timeframe, self.inf_1h, ffill=True)
        # The indicators for the normal (5m) timeframe
        dataframe = self.normal_tf_indicators(dataframe, metadata)
        # Calculate the 12-period EMA
        dataframe['ema12'] = dataframe['close'].ewm(span=12, adjust=False).mean()
        # Calculate the 26-period EMA
        dataframe['ema26'] = dataframe['close'].ewm(span=26, adjust=False).mean()
        # Calculate the MACD line
        dataframe['macd'] = dataframe['ema12'] - dataframe['ema26']
        # Calculate the Signal line (9-period EMA of the MACD line)
        dataframe['signal'] = dataframe['macd'].ewm(span=9, adjust=False).mean()
        # Calculate the Histogram
        dataframe['histogram'] = dataframe['macd'] - dataframe['signal']
        # Calculate MACD differences to detect rapid rises/falls
        dataframe['macd_diff'] = dataframe['macd'].diff()        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append((dataframe['close'] > dataframe['ema_200_1h']) & (dataframe['ema_50'] > dataframe['ema_200']) & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_1.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_2.value) & dataframe['lower'].shift().gt(0) & dataframe['bbdelta'].gt(dataframe['close'] * self.entry_bb40_bbdelta_close.value) & dataframe['closedelta'].gt(dataframe['close'] * self.entry_bb40_closedelta_close.value) & dataframe['tail'].lt(dataframe['bbdelta'] * self.entry_bb40_tail_bbdelta.value) & dataframe['close'].lt(dataframe['lower'].shift()) & dataframe['close'].le(dataframe['close'].shift()) & (dataframe['volume'] > 0))
        conditions.append((dataframe['close'] > dataframe['ema_200']) & (dataframe['close'] > dataframe['ema_200_1h']) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_1.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_2.value) & (dataframe['close'] < dataframe['ema_slow']) & (dataframe['close'] < self.entry_bb20_close_bblowerband.value * dataframe['bb_lowerband']) & (dataframe['volume'] < dataframe['volume_mean_slow'].shift(1) * self.entry_bb20_volume.value))
        conditions.append((dataframe['close'] < dataframe['sma_5']) & (dataframe['ssl_up_1h'] > dataframe['ssl_down_1h']) & (dataframe['ema_50'] > dataframe['ema_200']) & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_1.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_2.value) & (dataframe['rsi'] < dataframe['rsi_1h'] - self.entry_rsi_diff.value) & (dataframe['volume'] > 0))
        conditions.append((dataframe['sma_200'] > dataframe['sma_200'].shift(20)) & (dataframe['sma_200_1h'] > dataframe['sma_200_1h'].shift(16)) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_1.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_2.value) & ((dataframe['open'].rolling(144).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_3.value) & ((dataframe['open'].rolling(24).min() - dataframe['close']) / dataframe['close'] > self.entry_min_inc.value) & (dataframe['rsi_1h'] > self.entry_rsi_1h.value) & (dataframe['rsi'] < self.entry_rsi.value) & (dataframe['mfi'] < self.entry_mfi.value) & (dataframe['volume'] > 0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append((dataframe['close'] > dataframe['bb_upperband']) & (dataframe['close'].shift(1) > dataframe['bb_upperband'].shift(1)) & (dataframe['close'].shift(2) > dataframe['bb_upperband'].shift(2)) & (dataframe['volume'] > 0))
        conditions.append((dataframe['rsi'] > self.exit_rsi_main.value) & (dataframe['volume'] > 0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_long'] = 1
        return dataframe

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> bool:
        
        # Check MACD for rapid rise or fall every 5 minutes since trade entry
        print(f"Entering custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
        log.info(f"Entering custom_exit for {pair}, current_profit: {current_profit}, current_rate: {current_rate}, timestamp: {current_time}")
        positionFetcher = FuturesPositionFetcher(self.hedging_apikey, self.hedging_apisecret)
        symbolBinance=pair.split('/')[0]+"USDT"
        symbol=symbolBinance.replace("USDT", "")
        CombinedBinHAndClucV7DryRun.existing_position_on_exchange = positionFetcher.get_futures_position_information(symbolBinance)        
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        trade_entry_time = trade.open_date_utc
        exfile=f"./user_data/csv/{symbol}"
        os.makedirs(exfile, exist_ok=True)  
        dataframe.to_csv(exfile + f"/dataframe-{self.config['timeframe']}-{symbol}.csv")  
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        last_candles = dataframe.iloc[-10:]  # Get the last 4 candles
        print(last_candles)

        # Define thresholds for rapid rise and fall
        rapid_rise_threshold = 0.1
        rapid_fall_threshold = -0.1

        # Check for 4 consecutive rapid rises or falls
        rapid_rises = (last_candles['macd_diff'] > rapid_rise_threshold).all()
        rapid_falls = (last_candles['macd_diff'] < rapid_fall_threshold).all()

        if rapid_rises:
            log.info(f"Entering long trading macd_diff={last_candles['macd_diff']} greater than threshold={rapid_rise_threshold}")
            trade.is_short = True # hedge_me goes the opposite
            pair = pair.replace("USDT","/USDT:USDT")
            log.info(f"Market is rising for {pair}. Hedging short={trade.is_short } pair {pair} with leverage {self.hedging_leverage} and amount {self.hedging_stake_amount}")
            dsHedging.hedge_me(self, trade, pair, CombinedBinHAndClucV7DryRun.existing_position_on_exchange)                
            log.info(f"Market is rising for {pair}. Hedged short={trade.is_short } successfully pair {pair} with leverage {self.hedging_leverage} and amount {self.hedging_stake_amount}")

        if rapid_falls:
            log.info(f"Entering long trading macd_diff={last_candles['macd_diff']} less than threshold={rapid_fall_threshold}")
            trade.is_short = False # hedge_me goes the opposite
            pair = pair.replace("USDT","/USDT:USDT")
            log.info(f"Market is falling for {pair}. Hedging short={trade.is_short } now pair {pair} with leverage {self.hedging_leverage} and amount {self.hedging_stake_amount}")
            dsHedging.hedge_me(self, trade, pair, CombinedBinHAndClucV7DryRun.existing_position_on_exchange)                
            log.info(f"Market is falling for {pair}. Hedged short={trade.is_short } successfully pair {pair} with leverage {self.hedging_leverage} and amount {self.hedging_stake_amount}")
        
        log.info(f"Leaving custom_exit: Hedging Config: short={trade.is_short } pair {pair} with leverage {self.hedging_leverage} and amount {self.hedging_stake_amount}")
            
        return None
