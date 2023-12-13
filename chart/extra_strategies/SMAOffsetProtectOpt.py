# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------
import talib.abstract as ta
import numpy as np
import freqtrade.vendor.qtpylib.indicators as qtpylib
import datetime
from technical.util import resample_to_interval, resampled_merge
from datetime import datetime, timedelta
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open, merge_informative_pair, DecimalParameter, IntParameter, CategoricalParameter
import technical.indicators as ftt
# Buy hyperspace params: orginal
# entry_params = {
#     "base_nb_candles_entry": 16,
#     "ewo_high": 5.638,
#     "ewo_low": -19.993,
#     "low_offset": 0.978,
#     "rsi_entry": 61,
#    "fast_ewo": 50,  # value loaded from strategy
#    "slow_ewo": 200,  # value loaded from strategy
# }
# Buy hyperspace params: from v0
# value loaded from strategy
# value loaded from strategy
entry_params = {'base_nb_candles_entry': 20, 'ewo_high': 5.499, 'ewo_low': -19.881, 'low_offset': 0.975, 'rsi_entry': 50, 'fast_ewo': 50, 'slow_ewo': 200}
# Sell hyperspace params:orginal
# exit_params = {
#     "base_nb_candles_exit": 49,
#     "high_offset": 1.006,
# }
# Sell hyperspace params:  from v0
exit_params = {'base_nb_candles_exit': 24, 'high_offset': 1.012}

def EWO(dataframe, ema_length=5, ema2_length=35):
    df = dataframe.copy()
    ema1 = ta.EMA(df, timeperiod=ema_length)
    ema2 = ta.EMA(df, timeperiod=ema2_length)
    emadif = (ema1 - ema2) / df['close'] * 100
    return emadif

class SMAOffsetProtectOpt(IStrategy):
    INTERFACE_VERSION = 3
    # ROI table:
    minimal_roi = {'0': 0.2, '38': 0.074, '78': 0.025, '194': 0}
    # Stoploss:
    stoploss = -0.228
    # SMAOffset
    base_nb_candles_entry = IntParameter(5, 80, default=entry_params['base_nb_candles_entry'], space='entry', optimize=True)
    base_nb_candles_exit = IntParameter(5, 80, default=exit_params['base_nb_candles_exit'], space='exit', optimize=True)
    low_offset = DecimalParameter(0.9, 0.99, default=entry_params['low_offset'], space='entry', optimize=True)
    high_offset = DecimalParameter(0.99, 1.1, default=exit_params['high_offset'], space='exit', optimize=True)
    # Protection
    fast_ewo = IntParameter(10, 50, default=entry_params['fast_ewo'], space='entry', optimize=False)
    slow_ewo = IntParameter(100, 200, default=entry_params['slow_ewo'], space='entry', optimize=False)
    # fast_ewo = 50
    # slow_ewo = 200
    ewo_low = DecimalParameter(-20.0, -8.0, default=entry_params['ewo_low'], space='entry', optimize=True)
    ewo_high = DecimalParameter(2.0, 12.0, default=entry_params['ewo_high'], space='entry', optimize=True)
    rsi_entry = IntParameter(30, 70, default=entry_params['rsi_entry'], space='entry', optimize=True)
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.049
    trailing_only_offset_is_reached = True
    # Sell signal
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.01
    ignore_roi_if_entry_signal = True
    ## Optional order time in force.
    order_time_in_force = {'entry': 'gtc', 'exit': 'ioc'}
    # Optimal timeframe for the strategy
    timeframe = '5m'
    informative_timeframe = '1h'
    process_only_new_candles = True
    startup_candle_count = 50
    plot_config = {'main_plot': {'ma_entry': {'color': 'green'}, 'ma_exit': {'color': 'red'}}, 'subplots': {'RSI': {'rsi': {'color': '#fe2e34', 'type': 'line'}}, 'EWO': {'EWO': {'color': '#c7d729', 'type': 'line'}}}}
    use_custom_stoploss = False

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs

    def get_informative_indicators(self, metadata: dict):
        dataframe = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.informative_timeframe)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Calculate all ma_entry values
        for val in self.base_nb_candles_entry.range:
            dataframe[f'ma_entry_{val}'] = ta.EMA(dataframe, timeperiod=val)
        # Calculate all ma_exit values
        for val in self.base_nb_candles_exit.range:
            dataframe[f'ma_exit_{val}'] = ta.EMA(dataframe, timeperiod=val)
        # Elliot
        dataframe['EWO'] = EWO(dataframe, self.fast_ewo.value, self.slow_ewo.value)
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        dataframe['ma_entry'] = dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset.value
        # (dataframe['close'].shift(1) < dataframe['ma_entry']) &
        # (dataframe['low'] < dataframe['ma_entry']) &
        # (dataframe['close'] > dataframe['ma_entry']) &
        # (qtpylib.crossed_above(dataframe['close'], dataframe['ma_entry'])) &
        conditions.append((dataframe['close'] < dataframe['ma_entry']) & (dataframe['EWO'] > self.ewo_high.value) & (dataframe['rsi'] < self.rsi_entry.value) & (dataframe['volume'] > 0))
        # (dataframe['close'].shift(1) < dataframe['ma_entry']) &
        # (dataframe['low'] < dataframe['ma_entry']) &
        # (dataframe['close'] > dataframe['ma_entry']) &
        # (qtpylib.crossed_above(dataframe['close'], dataframe['ma_entry'])) &
        conditions.append((dataframe['close'] < dataframe['ma_entry']) & (dataframe['EWO'] < self.ewo_low.value) & (dataframe['volume'] > 0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        dataframe['ma_exit'] = dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value
        # (dataframe['close'] > (dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value)) &
        conditions.append(qtpylib.crossed_below(dataframe['close'], dataframe['ma_exit']) & (dataframe['volume'] > 0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_long'] = 1
        return dataframe