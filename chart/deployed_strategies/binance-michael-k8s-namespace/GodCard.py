from freqtrade.strategy import IStrategy
from freqtrade.strategy import BooleanParameter, CategoricalParameter, DecimalParameter, IStrategy, IntParameter
from functools import reduce
from pandas import DataFrame
# --------------------------------
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy  # noqa

class GodCard(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    # Define the parameter spaces
    cooldown_lookback = IntParameter(2, 48, default=5, space='protection', optimize=True)
    stop_duration = IntParameter(12, 200, default=5, space='protection', optimize=True)
    use_stop_protection = BooleanParameter(default=True, space='protection', optimize=True)

    @property
    def protections(self):
        prot = []
        prot.append({'method': 'CooldownPeriod', 'stop_duration_candles': self.cooldown_lookback.value})
        if self.use_stop_protection.value:
            prot.append({'method': 'StoplossGuard', 'lookback_period_candles': 24, 'trade_limit': 4, 'stop_duration_candles': self.stop_duration.value, 'only_per_pair': False})
        return prot
    # run "populate_indicators" only for new candle
    process_only_new_candles = False
    # Experimental settings (configuration will overide these if set)
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = False
    # Optional order type mapping
    order_types = {'entry': 'limit', 'exit': 'limit', 'stoploss': 'market', 'stoploss_on_exchange': False}
    # Hyperopt parameters
    entry_rsi = IntParameter(low=1, high=100, default=30, space='entry', optimize=True)
    entry_rsi_enabled = CategoricalParameter([True, False], default=False, space='entry', optimize=True)
    entry_trigger = CategoricalParameter(['bb_one', 'bb_two', 'bb_three'], default='bb_one', space='entry', optimize=True)
    exit_rsi = IntParameter(low=1, high=100, default=70, space='exit', optimize=True)
    exit_rsi_enabled = CategoricalParameter([True, False], default=False, space='exit', optimize=True)
    exit_trigger = CategoricalParameter(['bb_low_exit', 'bb_mid_exit', 'bb_up_exit', 'sarBoi'], default='bb_two_exit', space='exit', optimize=True)
    # Buy hyperspace params:
    entry_params = {'entry_rsi': 56, 'entry_rsi_enabled': False, 'entry_trigger': 'bb_two'}
    # Sell hyperspace params:
    exit_params = {'exit_rsi': 9, 'exit_rsi_enabled': True, 'exit_trigger': 'bb_mid_exit'}
    # Protection hyperspace params:
    protection_params = {'cooldown_lookback': 0, 'stop_duration': 39, 'use_stop_protection': False}
    # ROI table:
    minimal_roi = {'0': 0.344, '32': 0.09, '120': 0.041, '447': 0}
    # Stoploss:
    stoploss = -0.087
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.043
    trailing_only_offset_is_reached = True

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)
        # SAR Parabol
        dataframe['sar'] = ta.SAR(dataframe)
        # Bollinger bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=1)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        bollinger2 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband2'] = bollinger2['lower']
        dataframe['bb_middleband2'] = bollinger2['mid']
        dataframe['bb_upperband2'] = bollinger2['upper']
        bollinger3 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=3)
        dataframe['bb_lowerband3'] = bollinger3['lower']
        dataframe['bb_middleband3'] = bollinger3['mid']
        dataframe['bb_upperband3'] = bollinger3['upper']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        # GUARDS AND TRENDS
        if self.entry_rsi_enabled.value:
            conditions.append(dataframe['rsi'] > self.entry_rsi.value)
        # TRIGGERS
        if self.entry_trigger.value == 'bb_one':
            conditions.append(dataframe['close'] < dataframe['bb_lowerband'])
        if self.entry_trigger.value == 'bb_two':
            conditions.append(dataframe['close'] < dataframe['bb_lowerband2'])
        if self.entry_trigger.value == 'bb_three':
            conditions.append(dataframe['close'] < dataframe['bb_lowerband3'])
        # Check that volume is not 0
        conditions.append(dataframe['volume'] > 0)
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        # GUARDS AND TRENDS
        if self.exit_rsi_enabled.value:
            conditions.append(dataframe['rsi'] > self.exit_rsi.value)
        # TRIGGERS
        if self.exit_trigger.value == 'sarBoi':
            conditions.append(dataframe['sar'] > dataframe['close'])
        if self.entry_trigger.value == 'bb_low_exit':
            conditions.append(dataframe['close'] > dataframe['bb_lowerband'])
        if self.entry_trigger.value == 'bb_mid_exit':
            conditions.append(dataframe['close'] > dataframe['bb_middleband'])
        if self.entry_trigger.value == 'bb_up_exit':
            conditions.append(dataframe['close'] > dataframe['bb_upperband'])
        # Check that volume is not 0
        conditions.append(dataframe['volume'] > 0)
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit'] = 1
        return dataframe