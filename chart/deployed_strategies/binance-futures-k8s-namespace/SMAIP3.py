# --- Do not remove these libs ---
# --------------------------------
from datetime import datetime, timedelta
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import CategoricalParameter
from freqtrade.strategy import DecimalParameter, IntParameter
from freqtrade.strategy.interface import IStrategy
# author @tirail
ma_types = {'SMA': ta.SMA, 'EMA': ta.EMA}

class SMAIP3(IStrategy):
    INTERFACE_VERSION = 3
    # hyperopt and paste results here
    # Buy hyperspace params:
    entry_params = {'base_nb_candles_entry': 18, 'entry_trigger': 'SMA', 'low_offset': 0.968, 'pair_is_bad_1_threshold': 0.13, 'pair_is_bad_2_threshold': 0.075}
    # #########################################################
    # Sell hyperspace params:
    exit_params = {'base_nb_candles_exit': 55, 'high_offset': 1.07, 'exit_trigger': 'EMA'}
    # ROI table:
    minimal_roi = {'0': 0.135, '35': 0.061, '86': 0.037, '167': 0}
    # Stoploss:
    stoploss = -0.331
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.098
    trailing_stop_positive_offset = 0.159
    trailing_only_offset_is_reached = True
    base_nb_candles_entry = IntParameter(16, 60, default=entry_params['base_nb_candles_entry'], space='entry')
    base_nb_candles_exit = IntParameter(16, 60, default=exit_params['base_nb_candles_exit'], space='exit')
    low_offset = DecimalParameter(0.8, 0.99, default=entry_params['low_offset'], space='entry')
    high_offset = DecimalParameter(0.8, 1.1, default=exit_params['high_offset'], space='exit')
    entry_trigger = CategoricalParameter(ma_types.keys(), default=entry_params['entry_trigger'], space='entry')
    exit_trigger = CategoricalParameter(ma_types.keys(), default=exit_params['exit_trigger'], space='exit')
    pair_is_bad_1_threshold = DecimalParameter(0.0, 0.3, default=0.2, space='entry')
    pair_is_bad_2_threshold = DecimalParameter(0.0, 0.25, default=0.072, space='entry')
    # Optimal timeframe for the strategy
    timeframe = '5m'
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    process_only_new_candles = True
    startup_candle_count = 30
    plot_config = {'main_plot': {'ma_offset_entry': {'color': 'orange'}, 'ma_offset_exit': {'color': 'orange'}}}
    use_custom_stoploss = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not self.config['runmode'].value == 'hyperopt':
            dataframe['ma_offset_entry'] = ma_types[self.entry_trigger.value](dataframe, int(self.base_nb_candles_entry.value)) * self.low_offset.value
            dataframe['ma_offset_exit'] = ma_types[self.exit_trigger.value](dataframe, int(self.base_nb_candles_exit.value)) * self.high_offset.value
            dataframe['pair_is_bad'] = (((dataframe['open'].shift(12) - dataframe['close']) / dataframe['close'] >= self.pair_is_bad_1_threshold.value) | ((dataframe['open'].shift(6) - dataframe['close']) / dataframe['close'] >= self.pair_is_bad_2_threshold.value)).astype('int')
            dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
            dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.config['runmode'].value == 'hyperopt':
            dataframe['ma_offset_entry'] = ma_types[self.entry_trigger.value](dataframe, int(self.base_nb_candles_entry.value)) * self.low_offset.value
            dataframe['pair_is_bad'] = (((dataframe['open'].shift(12) - dataframe['close']) / dataframe['close'] >= self.pair_is_bad_1_threshold.value) | ((dataframe['open'].shift(6) - dataframe['close']) / dataframe['close'] >= self.pair_is_bad_2_threshold.value)).astype('int')
            dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
            dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe.loc[(dataframe['ema_50'] > dataframe['ema_200']) & (dataframe['close'] > dataframe['ema_200']) & (dataframe['pair_is_bad'] < 1) & (dataframe['close'] < dataframe['ma_offset_entry']) & (dataframe['volume'] > 0), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.config['runmode'].value == 'hyperopt':
            dataframe['ma_offset_exit'] = ma_types[self.exit_trigger.value](dataframe, int(self.base_nb_candles_exit.value)) * self.high_offset.value
        dataframe.loc[(dataframe['close'] > dataframe['ma_offset_exit']) & (dataframe['volume'] > 0), 'exit'] = 1
        return dataframe