# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
import talib.abstract as ta
import pandas
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.interface import IStrategy
pandas.set_option('display.precision', 8)

class BBRSIoriginal(IStrategy):
    INTERFACE_VERSION = 3
    '\n    Default Strategy provided by freqtrade bot.\n    You can override it with your own strategy\n    '
    # Minimal ROI designed for the strategy
    minimal_roi = {'0': 0.09638, '19': 0.03643, '69': 0.01923, '120': 0}
    # Optimal stoploss designed for the strategy
    stoploss = -0.36828
    # Optimal ticker interval for the strategy
    timeframe = '1h'
    # Optional order type mapping
    order_types = {'entry': 'limit', 'exit': 'limit', 'stoploss': 'limit', 'stoploss_on_exchange': False}
    # Optional time in force for orders
    order_time_in_force = {'entry': 'gtc', 'exit': 'gtc'}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Raw data from the exchange and parsed by parse_ticker_dataframe()
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """
        # Momentum Indicator
        # ------------------------------------
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)
        # Overlap Studies
        # ------------------------------------
        # Bollinger bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=4)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        bollinger3 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=3)
        dataframe['bb_lowerband3'] = bollinger3['lower']
        dataframe['bb_middleband3'] = bollinger3['mid']
        dataframe['bb_upperband3'] = bollinger3['upper']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry column
        """
        #(dataframe['rsi'] > 12) &
        dataframe.loc[dataframe['close'] < dataframe['bb_lowerband3'], 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry column
        """
        dataframe.loc[(dataframe['rsi'] > 75) & (dataframe['close'] > dataframe['bb_middleband']), 'exit'] = 1
        return dataframe