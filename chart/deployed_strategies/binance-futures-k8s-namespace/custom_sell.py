# --- Do not remove these libs ---
import freqtrade.vendor.qtpylib.indicators as qtpylib
from datetime import datetime, timedelta, timezone

from functools import reduce
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter
#from technical.indicators import vwma, Rmi, WTO, IIIX, PMAX, vwmacd

import numpy as np
import sys
# --------------------------------
import talib.abstract as ta
#from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IStrategy, merge_informative_pair, informative
from pandas import DataFrame, Series, DatetimeIndex, merge, to_numeric
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_prev_date
import pandas as pd

from warnings import simplefilter
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)

import arrow
from freqtrade.exchange import timeframe_to_minutes
import time

class custom_exit(IStrategy):
    custom_info = {}

    entry_signal_entry6 = CategoricalParameter([True, False], default=True, space="entry", optimize=False)

    order_types = {
        "entry": 'limit',
        "exit": 'market',
        "stoploss": 'market',
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_interval": 60,
        "stoploss_on_exchange_limit_ratio": 0.99,
    }


    protections = [
    {
        "method": "StoplossGuard",
        "lookback_period_candles": 300,
        "trade_limit": 2,
        "stop_duration_candles": 300,
        "only_per_pair": "true"
    },
    {
        "method": "LowProfitPairs",
        "lookback_period_candles": 24,
        "trade_limit": 1,
        "stop_duration": 300,
        "required_profit": 0.001
    },
    {
        "method": "CooldownPeriod",
        "stop_duration_candles": 2
    },
    {
        "method": "MaxDrawdown",
        "lookback_period_candles": 96,
        "trade_limit": 5,
        "stop_duration_candles": 48,
        "max_allowed_drawdown": 0.2
    }
    ]

    # ROI table:
    minimal_roi = {
        "0": 0.034,
        "35": 0.024,
        "92": 0.011,
        "170": 0
    }

    # Trailing stop:
    trailing_stop = False
    trailing_stop_positive = 0.098
    trailing_stop_positive_offset = 0.193
    trailing_only_offset_is_reached = True

    # Stoploss:
    stoploss = -0.347

    timeframe = '5m'
    startup_candle_count = 450
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Custom stoploss
    use_custom_stoploss = False

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        if trade.entry_tag:
           entry_tag = trade.entry_tag

        if entry_tag == 'entry6':

           if current_profit > 0:
              #print("exiting " + str(current_profit))
              return 'plus0percent' + '_' + entry_tag
           elif current_profit < 0:
              #print("exiting " + str(current_profit))
              return 'minus0percent' + '_' + entry_tag

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                           rate: float, time_in_force: str, exit_reason: str, **kwargs) -> bool:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        #last_candle = dataframe.iloc[-1].squeeze()


        if (exit_reason == 'roi') & (trade.entry_tag == "entry6"):
            #print("REJECTED: " + trade.entry_tag + "/" + exit_reason)
            return False

        #print("SOLD: " + trade.entry_tag + "/" + exit_reason)
        return True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.normal_tf_indicators(dataframe, metadata)

        return dataframe

    def normal_tf_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Informative
        if not self.dp:
            # Don't do anything if DataProvider is not available.
            return dataframe

        # Keltner
        keltner = qtpylib.keltner_channel(dataframe, window=17, atrs=2)
        dataframe['keltner_lower'] = keltner['lower']
        dataframe['keltner_middle'] = keltner['mid']
        dataframe['keltner_upper'] = keltner['upper']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # BUY6
        if (self.entry_signal_entry6.value):
          dataframe.loc[
           (
             (
               (dataframe['close'] > dataframe['keltner_middle'])
             )
           ),
           ['entry', 'entry_tag']] = (1, 'entry6')


        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit'] = 0
        return dataframe