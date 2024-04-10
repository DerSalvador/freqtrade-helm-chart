# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class BBRSI2(IStrategy):
    INTERFACE_VERSION = 3
    minimal_roi = {'0': 0.3, '120': 0.2, '360': 0.15, '720': 0}
    stoploss = -0.2
    timeframe = '1m'
    trailing_stop = True
    order_types = {'entry': 'limit', 'exit': 'limit', 'emergencyexit': 'market', 'forceentry': 'market', 'forceexit': 'market', 'stoploss': 'market', 'stoploss_on_exchange': True, 'stoploss_on_exchange_interval': 60, 'stoploss_on_exchange_limit_ratio': 0.99}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        # dataframe['bb_upperband'] = bollinger['upper']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] > 35) & (dataframe['close'] < dataframe['bb_lowerband']), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] > 75) & (dataframe['close'] > dataframe['bb_middleband']), 'exit'] = 1
        return dataframe