# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class Roth03(IStrategy):
    INTERFACE_VERSION = 3
    #  7205/10000:    499 trades. 251/240/8 Wins/Draws/Losses. Avg profit   0.51%. Median profit   0.01%. Total profit  0.00137449 BTC ( 254.47Î£%). Avg duration 746.7 min. Objective: 0.15177
    # Buy hyperspace params:
    entry_params = {'adx-enabled': False, 'adx-value': 50, 'cci-enabled': False, 'cci-value': -196, 'fastd-enabled': True, 'fastd-value': 37, 'mfi-enabled': True, 'mfi-value': 20, 'rsi-enabled': False, 'rsi-value': 26, 'trigger': 'bb_lower'}
    # Sell hyperspace params:
    exit_params = {'exit-adx-enabled': False, 'exit-adx-value': 73, 'exit-cci-enabled': False, 'exit-cci-value': 189, 'exit-fastd-enabled': True, 'exit-fastd-value': 79, 'exit-mfi-enabled': True, 'exit-mfi-value': 86, 'exit-rsi-enabled': True, 'exit-rsi-value': 69, 'exit-trigger': 'exit-sar_reversal'}
    # ROI table:
    minimal_roi = {'0': 0.24553, '33': 0.07203, '90': 0.01452, '111': 0}
    # Stoploss:
    stoploss = -0.31939
    # Optimal timeframe for the strategy
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['cci'] = ta.CCI(dataframe)
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_low'] = bollinger['lower']
        dataframe['bb_mid'] = bollinger['mid']
        dataframe['bb_upper'] = bollinger['upper']
        dataframe['bb_perc'] = (dataframe['close'] - dataframe['bb_low']) / (dataframe['bb_upper'] - dataframe['bb_low'])
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['sar'] = ta.SAR(dataframe)
        dataframe['mfi'] = ta.MFI(dataframe)
        # Stoch fast
        stoch_fast = ta.STOCHF(dataframe)
        dataframe['fastd'] = stoch_fast['fastd']
        dataframe['fastk'] = stoch_fast['fastk']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with entry column
        """
        # (dataframe['cci'] <= -57.0)
        dataframe.loc[(dataframe['close'] < dataframe['bb_low']) & (dataframe['fastd'] > 37) & (dataframe['mfi'] < 20.0), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with entry column
        """
        # (dataframe['adx'] > 52) &
        # (dataframe['cci'] >= 50.0) &
        # (dataframe['close'] > dataframe['bb_upper'])
        dataframe.loc[(dataframe['sar'] > dataframe['close']) & (dataframe['rsi'] > 69) & (dataframe['mfi'] > 86) & (dataframe['fastd'] > 79), 'exit'] = 1
        return dataframe