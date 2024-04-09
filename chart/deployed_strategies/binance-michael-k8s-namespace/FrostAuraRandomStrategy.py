from pandas import DataFrame
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IntParameter, IStrategy, CategoricalParameter
from random import random
import numpy as np

class FrostAuraRandomStrategy(IStrategy):
    """
    This is FrostAura's random strategy powered by nature.

    Last Optimization:
        Profit %        : 10-30%
        Optimized for   : Last 45 days, 1h
        Avg             : 2d - 5d
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3
    # Minimal ROI designed for the strategy.
    minimal_roi = {'0': 0.347, '450': 0.106, '1169': 0.032, '1624': 0}
    # Optimal stoploss designed for the strategy.
    stoploss = -0.231
    # Trailing stoploss
    trailing_stop = False
    # Optimal ticker interval for the strategy.
    timeframe = '1h'
    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False
    # These values can be overridden in the "ask_strategy" section in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    # Number of candles the strategy requires before producing valid signals.
    startup_candle_count: int = 30
    # Optional order type mapping.
    order_types = {'entry': 'market', 'exit': 'market', 'stoploss': 'market', 'stoploss_on_exchange': False}
    # Optional order time in force.
    order_time_in_force = {'entry': 'gtc', 'exit': 'gtc'}
    plot_config = {'main_plot': {'tema': {}, 'sar': {'color': 'white'}}, 'subplots': {'MACD': {'macd': {'color': 'blue'}, 'macdsignal': {'color': 'orange'}}, 'RSI': {'rsi': {'color': 'red'}}}}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['random_number'] = np.random.randint(0, 100, dataframe.shape[0])
        return dataframe
    entry_prediction_delta_direction = CategoricalParameter(['<', '>'], default='>', space='entry')
    entry_probability = IntParameter([0, 100], default=76, space='entry')

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        random_number = dataframe['random_number']
        dataframe.loc[random_number < self.entry_probability.value if self.entry_prediction_delta_direction.value == '<' else random_number > self.entry_probability.value, 'entry'] = 1
        return dataframe
    exit_prediction_delta_direction = CategoricalParameter(['<', '>'], default='<', space='exit')
    exit_probability = IntParameter([0, 100], default=0, space='exit')

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        random_number = dataframe['random_number']
        dataframe.loc[random_number < self.exit_probability.value if self.exit_prediction_delta_direction.value == '<' else random_number > self.exit_probability.value, 'exit'] = 1
        return dataframe