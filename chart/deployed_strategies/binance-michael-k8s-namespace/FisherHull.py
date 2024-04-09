import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame, DatetimeIndex, merge, Series
from technical.indicators import hull_moving_average
'\nAutor: https://github.com/werkkrew/freqtrade-strategies\n'

class FisherHull(IStrategy):
    INTERFACE_VERSION = 3
    # Buy hyperspace params:
    entry_params = {}
    # Sell hyperspace params:
    exit_params = {}
    # ROI table:
    minimal_roi = {'0': 1000}
    # Stoploss:
    stoploss = -0.27654
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.32606
    trailing_stop_positive_offset = 0.33314
    trailing_only_offset_is_reached = True
    timeframe = '1m'
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['hma'] = hull_moving_average(dataframe, 14, 'close')
        dataframe['cci'] = ta.CCI(dataframe, timeperiod=14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        rsi = 0.1 * (dataframe['rsi'] - 50)
        dataframe['fisher_rsi'] = (np.exp(2 * rsi) - 1) / (np.exp(2 * rsi) + 1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['hma'] < dataframe['hma'].shift()) & (dataframe['cci'] <= -50.0) & (dataframe['fisher_rsi'] < -0.5) & (dataframe['volume'] > 0), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['hma'] > dataframe['hma'].shift()) & (dataframe['cci'] >= 100.0) & (dataframe['fisher_rsi'] > 0.5) & (dataframe['volume'] > 0), 'exit_long'] = 1
        return dataframe