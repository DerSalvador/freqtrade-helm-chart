from functools import reduce
import freqtrade.vendor.qtpylib.indicators as qtpylib
import talib.abstract as ta
from freqtrade.strategy import merge_informative_pair
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class LookaheadStrategy(IStrategy):
    INTERFACE_VERSION = 3
    # Buy hyperspace params:
    entry_params = {'entry_fast': 2, 'entry_push': 1.022, 'entry_shift': -8, 'entry_slow': 16}
    # Sell hyperspace params:
    exit_params = {'exit_fast': 34, 'exit_push': 0.458, 'exit_shift': -8, 'exit_slow': 44}
    # ROI table:
    # fmt: off
    minimal_roi = {'0': 0.166, '44': 0.012, '59': 0}
    # fmt: on
    # Stoploss:
    stoploss = -0.194
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    # Buy hypers
    timeframe = '5m'
    # #################### END OF RESULT PLACE ####################

    def informative_1h_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        assert self.dp, 'DataProvider is required for multiple timeframes.'
        # Get the informative pair
        informative_1h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1h')
        # EMA
        informative_1h['ema_50'] = ta.EMA(informative_1h, timeperiod=50)
        return informative_1h

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        informative_1h = self.informative_1h_indicators(dataframe, metadata)
        dataframe = merge_informative_pair(dataframe, informative_1h, self.timeframe, '1h', ffill=True)
        dataframe['entry_ema_fast'] = ta.SMA(dataframe, timeperiod=self.entry_params['entry_fast'])
        dataframe['entry_ema_slow'] = ta.SMA(dataframe, timeperiod=self.entry_params['entry_slow'])
        dataframe['exit_ema_fast'] = ta.SMA(dataframe, timeperiod=self.exit_params['exit_fast'])
        dataframe['exit_ema_slow'] = ta.SMA(dataframe, timeperiod=self.exit_params['exit_slow'])
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(qtpylib.crossed_above(dataframe['entry_ema_fast'].shift(self.entry_params['entry_shift']), dataframe['entry_ema_slow'].shift(self.entry_params['entry_shift']) * self.entry_params['entry_push']) & (dataframe['close'] > dataframe['ema_50_1h']))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), ['enter_long', 'enter_tag']] = (1, 'entry_reason')
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(qtpylib.crossed_below(dataframe['exit_ema_fast'].shift(self.exit_params['exit_shift']), dataframe['exit_ema_slow'].shift(self.exit_params['exit_shift']) * self.exit_params['exit_push']))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), ['exit_long', 'exit_tag']] = (1, 'some_exit_tag')
        return dataframe