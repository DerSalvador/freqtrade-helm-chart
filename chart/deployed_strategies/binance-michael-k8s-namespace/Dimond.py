# 𝐼𝓉 𝒾𝓈 𝒟𝒾𝓂𝑜𝓃𝒹 𝒮𝓉𝓇𝒶𝓉𝑒𝑔𝓎.
# 𝒯𝒽𝒶𝓉 𝓉𝒶𝓀𝑒𝓈 𝒽𝑒𝓇 𝑜𝓌𝓃 𝓇𝒾𝑔𝒽𝓉𝓈 𝓁𝒾𝓀𝑒 𝒜𝒻𝑔𝒽𝒶𝓃𝒾𝓈𝓉𝒶𝓃 𝓌𝑜𝓂𝑒𝓃
# 𝒯𝒽𝑜𝓈𝑒 𝓌𝒽𝑜 𝓈𝓉𝒾𝓁𝓁 𝓅𝓇𝑜𝓊𝒹 𝒶𝓃𝒹 𝒽𝑜𝓅𝑒𝒻𝓊𝓁.
# 𝒯𝒽𝑜𝓈𝑒 𝓌𝒽𝑜 𝓉𝒽𝑒 𝓂𝑜𝓈𝓉 𝒷𝑒𝒶𝓊𝓉𝒾𝒻𝓊𝓁 𝒸𝓇𝑒𝒶𝓉𝓊𝓇𝑒𝓈 𝒾𝓃 𝓉𝒽𝑒 𝒹𝑒𝓅𝓉𝒽𝓈 𝑜𝒻 𝓉𝒽𝑒 𝒹𝒶𝓇𝓀𝑒𝓈𝓉.
# 𝒯𝒽𝑜𝓈𝑒 𝓌𝒽𝑜 𝓈𝒽𝒾𝓃𝑒 𝓁𝒾𝓀𝑒 𝒹𝒾𝒶𝓂𝑜𝓃𝒹𝓈 𝒷𝓊𝓇𝒾𝑒𝒹 𝒾𝓃 𝓉𝒽𝑒 𝒽𝑒𝒶𝓇𝓉 𝑜𝒻 𝓉𝒽𝑒 𝒹𝑒𝓈𝑒𝓇𝓉 ...
# 𝒲𝒽𝓎 𝓃𝑜𝓉 𝒽𝑒𝓁𝓅 𝓌𝒽𝑒𝓃 𝓌𝑒 𝒸𝒶𝓃?
# 𝐼𝒻 𝓌𝑒 𝒷𝑒𝓁𝒾𝑒𝓋𝑒 𝓉𝒽𝑒𝓇𝑒 𝒾𝓈 𝓃𝑜 𝓂𝒶𝓃 𝓁𝑒𝒻𝓉 𝓌𝒾𝓉𝒽 𝓉𝒽𝑒𝓂
# (𝒲𝒽𝒾𝒸𝒽 𝒾𝓈 𝓅𝓇𝑜𝒷𝒶𝒷𝓁𝓎 𝓉𝒽𝑒 𝓅𝓇𝑜𝒹𝓊𝒸𝓉 𝑜𝒻 𝓉𝒽𝑒 𝓉𝒽𝑜𝓊𝑔𝒽𝓉 𝑜𝒻 𝓅𝒶𝒾𝓃𝓁𝑒𝓈𝓈 𝒸𝑜𝓇𝓅𝓈𝑒𝓈)
# 𝒲𝒽𝑒𝓇𝑒 𝒽𝒶𝓈 𝑜𝓊𝓇 𝒽𝓊𝓂𝒶𝓃𝒾𝓉𝓎 𝑔𝑜𝓃𝑒?
# 𝒲𝒽𝑒𝓇𝑒 𝒽𝒶𝓈 𝒽𝓊𝓂𝒶𝓃𝒾𝓉𝓎 𝑔𝑜𝓃𝑒?
# 𝒲𝒽𝓎 𝓃𝑜𝓉 𝒽𝑒𝓁𝓅 𝓌𝒽𝑒𝓃 𝓌𝑒 𝒸𝒶𝓃?
# IMPORTANT: This strategy
# designed for "ZERO" loss and "UNDER"
# 15 minuts avg duration.So if you have more
# loss and more avg, Its "NOT" normal result, and
# you will change config.json variables and hyperoption commands
# Thanks To @xmatthias if he was approve the last version of This strategy
# That just a lazy code. I never can reach to this strategy(Now its really a dimond.)
# * freqtrade hyperopt --hyperopt-loss ShortTradeDurHyperOptLoss --spaces all --strategy Dimond -e 700 -j 2 --timerange 20210810-20210813
# * freqtrade backtesting --strategy Dimond
# Author: @Mablue (Masoud Azizi)
# github: https://github.com/mablue/
# (First Hyperopt it.A hyperopt file is available)
# --- Do not remove these libs ---
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from functools import reduce
import freqtrade.vendor.qtpylib.indicators as qtpylib
##### SETINGS #####
# It hyperopt just one set of params for all entry and exit strategies if true.
DUALFIT = False
COUNT = 10
GAP = 3
### END SETINGS ###

class Dimond(IStrategy):
    INTERFACE_VERSION = 3
    # ###################### RESULT PLACE ######################
    # *    6/700:      1 trades. 1/0/0 Wins/Draws/Losses. Avg profit  17.68%. Median profit  17.68%. Total profit  58.94100000 USDT (   5.89Σ%). Avg duration 0:00:00 min. Objective: 1.79949
    # Buy hyperspace params:
    entry_params = {'entry_fast': 31, 'entry_push': 0.72, 'entry_shift': -7, 'entry_slow': 2}
    # Sell hyperspace params:
    exit_params = {'exit_fast': 17, 'exit_push': 1.493, 'exit_shift': -7, 'exit_slow': 28}
    # ROI table:
    minimal_roi = {'0': 0.177, '31': 0.059, '61': 0.021, '170': 0}
    # Stoploss:
    stoploss = -0.241
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.13
    trailing_stop_positive_offset = 0.189
    trailing_only_offset_is_reached = True
    # Buy hypers
    timeframe = '5m'
    # #################### END OF RESULT PLACE ####################
    entry_push = DecimalParameter(0, 2, decimals=3, default=1, space='entry')
    entry_shift = IntParameter(-10, 0, default=-6, space='entry')
    entry_fast = IntParameter(2, 50, default=9, space='entry')
    entry_slow = IntParameter(2, 50, default=18, space='entry')
    if not DUALFIT:
        exit_push = DecimalParameter(0, 2, decimals=3, default=1, space='exit')
        exit_shift = IntParameter(-10, 0, default=-6, space='exit')
        exit_fast = IntParameter(2, 50, default=9, space='exit')
        exit_slow = IntParameter(2, 50, default=18, space='exit')

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['entry_ema_fast'] = ta.SMA(dataframe, timeperiod=int(self.entry_fast.value))
        dataframe['entry_ema_slow'] = ta.SMA(dataframe, timeperiod=int(self.entry_slow.value))
        conditions = []
        conditions.append(qtpylib.crossed_above(dataframe['entry_ema_fast'].shift(self.entry_shift.value), dataframe['entry_ema_slow'].shift(self.entry_shift.value) * self.entry_push.value))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        push = self.entry_push.value
        shift = self.entry_shift.value
        ema_fast = dataframe['entry_ema_fast']
        ema_slow = dataframe['entry_ema_slow']
        if not DUALFIT:
            push = self.exit_push.value
            shift = self.exit_shift.value
            ema_fast = dataframe['exit_ema_fast'] = ta.SMA(dataframe, timeperiod=int(self.entry_fast.value))
            ema_slow = dataframe['exit_ema_slow'] = ta.SMA(dataframe, timeperiod=int(self.entry_slow.value))
        conditions = []
        conditions.append(qtpylib.crossed_below(ema_fast.shift(shift), ema_slow.shift(shift) * push))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        return dataframe