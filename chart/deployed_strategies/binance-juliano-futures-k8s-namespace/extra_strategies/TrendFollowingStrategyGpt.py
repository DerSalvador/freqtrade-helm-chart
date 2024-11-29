kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n binance-juliano-futures exec -it pod/freqtrade-binance-juliano-futures-64f97687bf-wn6d6 -c freqtrade -- cat /extra_strategies/TrendFollowingStrategyGpt.py
from functools import reduce
from pandas import DataFrame
from freqtrade.strategy import IStrategy
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy

class TrendFollowingStrategyGpt(IStrategy):
    INTERFACE_VERSION = 3
    # ROI table:
    minimal_roi = {'0': 0.15, '30': 0.1, '60': 0.05}
    # Stoploss:
    stoploss = -0.265
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.1
    trailing_only_offset_is_reached = False
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Calculate OBV
        dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])
        
        # Calculate EMA
        dataframe['trend'] = dataframe['close'].ewm(span=20, adjust=False).mean()
        
        # Calculate SMA
        dataframe['sma'] = ta.SMA(dataframe, timeperiod=20)
        
        # Calculate ADX
        dataframe['adx'] = ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        
        # Calculate MACD
        macd = ta.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Entry long
        dataframe.loc[
            (dataframe['close'] > dataframe['trend']) &
            (dataframe['close'].shift(1) <= dataframe['trend'].shift(1)) &
            (dataframe['obv'] > dataframe['obv'].shift(1)) &
            (dataframe['adx'] > 25) &
            (dataframe['macd'] > dataframe['macdsignal']),
            'enter_long'] = 1

        # Entry short
        dataframe.loc[
            (dataframe['close'] < dataframe['trend']) &
            (dataframe['close'].shift(1) >= dataframe['trend'].shift(1)) &
            (dataframe['obv'] < dataframe['obv'].shift(1)) &
            (dataframe['adx'] > 25) &
            (dataframe['macd'] < dataframe['macdsignal']),
            'enter_short'] = -1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit long
        dataframe.loc[
            (dataframe['close'] < dataframe['trend']) &
            (dataframe['close'].shift(1) >= dataframe['trend'].shift(1)) &
            (dataframe['obv'] > dataframe['obv'].shift(1)),
            'exit_long'] = 1

        # Exit short
        dataframe.loc[
            (dataframe['close'] > dataframe['trend']) &
            (dataframe['close'].shift(1) <= dataframe['trend'].shift(1)) &
            (dataframe['obv'] < dataframe['obv'].shift(1)),
            'exit_short'] = 1
        
        return dataframe
