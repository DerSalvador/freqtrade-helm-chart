# --- Do not remove these libs ---
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
# --------------------------------
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter
from abc import ABC, abstractmethod
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_prev_date, timeframe_to_seconds
from datetime import datetime, timedelta
import math

class CombinedBinHAndClucHyperV0(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '1m'
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    # ----------------------------------------------------------------
    # Hyper Params
    # 
    # # Buy 
    entry_a_bbdelta_rate = DecimalParameter(0.004, 0.016, default=0.016, decimals=3)
    entry_a_closedelta_rate = DecimalParameter(0.0, 0.01, default=0.0087, decimals=4)
    entry_a_tail_rate = DecimalParameter(0.12, 0.5, default=0.28, decimals=2)
    entry_a_time_window = IntParameter(40, 100, default=30)
    entry_a_min_exit_rate = DecimalParameter(1.004, 1.1, default=0.004, decimals=3)
    entry_b_close_rate = DecimalParameter(0.4, 1.8, default=0.979, decimals=3)
    entry_b_volume_mean_slow_window = IntParameter(100, 300, default=30)
    entry_b_ema_slow = IntParameter(40, 100, default=50)
    entry_b_time_window = IntParameter(100, 300, default=20)
    entry_b_volume_mean_slow_num = IntParameter(10, 100, default=20)
    # Sell
    exit_bb_middleband_window = IntParameter(50, 200, default=20)
    exit_trailing_stop_positive_offset = DecimalParameter(0.01, 0.03, default=0.008, decimals=3)
    exit_trailing_stop_positive = 0.001
    # ----------------------------------------------------------------
    # Buy hyperspace params:
    entry_params = {'entry_a_bbdelta_rate': 0.016, 'entry_a_closedelta_rate': 0.0088, 'entry_a_tail_rate': 0.9, 'entry_a_time_window': 21, 'entry_a_min_exit_rate': 1.03, 'entry_b_close_rate': 0.979, 'entry_b_time_window': 20, 'entry_b_ema_slow': 50, 'entry_b_volume_mean_slow_num': 20, 'entry_b_volume_mean_slow_window': 30}
    # Sell hyperspace params:
    exit_params = {'exit_bb_middleband_window': 91, 'exit_trailing_stop_positive_offset': 0.008}
    # ROI table:
    minimal_roi = {'0': 100}
    # Stoploss:
    stoploss = -0.1
    trailing_stop = False
    trailing_only_offset_is_reached = False
    use_custom_stoploss = True

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        exit_trailing_stop_positive_offset = self.exit_trailing_stop_positive_offset.value if isinstance(self.exit_trailing_stop_positive_offset, ABC) else self.exit_trailing_stop_positive_offset
        exit_trailing_stop_positive = self.exit_trailing_stop_positive.value if isinstance(self.exit_trailing_stop_positive, ABC) else self.exit_trailing_stop_positive
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        if last_candle is None:
            return -1
        trade_date = timeframe_to_prev_date(self.timeframe, trade.open_date_utc - timedelta(seconds=timeframe_to_seconds(self.timeframe)))
        trade_candle = dataframe.loc[dataframe['date'] == trade_date]
        if trade_candle.empty:
            return -1
        trade_candle = trade_candle.squeeze()
        slippage_ratio = trade.open_rate / trade_candle['close'] - 1
        slippage_ratio = slippage_ratio if slippage_ratio > 0 else 0
        current_profit_comp = current_profit + slippage_ratio
        if current_profit_comp < exit_trailing_stop_positive_offset:
            return -1
        else:
            return exit_trailing_stop_positive

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # strategy BinHV45
        for x in self.entry_a_time_window.range if isinstance(self.entry_a_time_window, ABC) else [self.entry_a_time_window]:
            entry_bollinger = qtpylib.bollinger_bands(dataframe['close'], window=x, stds=2)
            dataframe[f'lower_{x}'] = entry_bollinger['lower']
            dataframe[f'bbdelta_{x}'] = (entry_bollinger['mid'] - dataframe[f'lower_{x}']).abs()
            dataframe[f'closedelta_{x}'] = (dataframe['close'] - dataframe['close'].shift()).abs()
            dataframe[f'tail_{x}'] = (dataframe['close'] - dataframe['low']).abs()
        # strategy ClucMay72018
        for x in self.entry_b_time_window.range if isinstance(self.entry_b_time_window, ABC) else [self.entry_b_time_window]:
            bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=x, stds=2)
            dataframe[f'bb_lowerband_{x}'] = bollinger['lower']
        for x in self.entry_b_ema_slow.range if isinstance(self.entry_b_ema_slow, ABC) else [self.entry_b_ema_slow]:
            dataframe[f'ema_slow_{x}'] = ta.EMA(dataframe, timeperiod=x)
        for x in self.entry_b_volume_mean_slow_window.range if isinstance(self.entry_b_volume_mean_slow_window, ABC) else [self.entry_b_volume_mean_slow_window]:
            dataframe[f'volume_mean_slow_{x}'] = dataframe['volume'].rolling(window=x).mean()
        for x in self.exit_bb_middleband_window.range if isinstance(self.exit_bb_middleband_window, ABC) else [self.exit_bb_middleband_window]:
            exit_bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=x, stds=2)
            dataframe[f'bb_middleband_{x}'] = exit_bollinger['mid']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        entry_a_time_window = self.entry_a_time_window.value if isinstance(self.entry_a_time_window, ABC) else self.entry_a_time_window
        entry_a_bbdelta_rate = self.entry_a_bbdelta_rate.value if isinstance(self.entry_a_bbdelta_rate, ABC) else self.entry_a_bbdelta_rate
        entry_a_closedelta_rate = self.entry_a_closedelta_rate.value if isinstance(self.entry_a_closedelta_rate, ABC) else self.entry_a_closedelta_rate
        entry_a_tail_rate = self.entry_a_tail_rate.value if isinstance(self.entry_a_tail_rate, ABC) else self.entry_a_tail_rate
        entry_a_min_exit_rate = self.entry_a_min_exit_rate.value if isinstance(self.entry_a_min_exit_rate, ABC) else self.entry_a_min_exit_rate
        entry_b_ema_slow = self.entry_b_ema_slow.value if isinstance(self.entry_b_ema_slow, ABC) else self.entry_b_ema_slow
        entry_b_close_rate = self.entry_b_close_rate.value if isinstance(self.entry_b_close_rate, ABC) else self.entry_b_close_rate
        entry_b_time_window = self.entry_b_time_window.value if isinstance(self.entry_b_time_window, ABC) else self.entry_b_time_window
        entry_b_volume_mean_slow_window = self.entry_b_volume_mean_slow_window.value if isinstance(self.entry_b_volume_mean_slow_window, ABC) else self.entry_b_volume_mean_slow_window
        entry_b_volume_mean_slow_num = self.entry_b_volume_mean_slow_num.value if isinstance(self.entry_b_volume_mean_slow_num, ABC) else self.entry_b_volume_mean_slow_num
        exit_bb_middleband_window = self.exit_bb_middleband_window.value if isinstance(self.exit_bb_middleband_window, ABC) else self.exit_bb_middleband_window  # strategy BinHV45
        # strategy ClucMay72018
        dataframe.loc[dataframe[f'lower_{entry_a_time_window}'].shift().gt(0) & dataframe[f'bbdelta_{entry_a_time_window}'].gt(dataframe['close'] * entry_a_bbdelta_rate) & dataframe[f'closedelta_{entry_a_time_window}'].gt(dataframe['close'] * entry_a_closedelta_rate) & dataframe[f'tail_{entry_a_time_window}'].lt(dataframe[f'bbdelta_{entry_a_time_window}'] * entry_a_tail_rate) & dataframe['close'].lt(dataframe[f'lower_{entry_a_time_window}'].shift()) & dataframe['close'].le(dataframe['close'].shift()) & dataframe[f'bb_middleband_{exit_bb_middleband_window}'].gt(dataframe['close'] * entry_a_min_exit_rate) | (dataframe['close'] < dataframe[f'ema_slow_{entry_b_ema_slow}']) & (dataframe['close'] < entry_b_close_rate * dataframe[f'bb_lowerband_{entry_b_time_window}']) & (dataframe['volume'] < dataframe[f'volume_mean_slow_{entry_b_volume_mean_slow_window}'].shift(1) * entry_b_volume_mean_slow_num), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exit_bb_middleband_window = self.exit_bb_middleband_window.value if isinstance(self.exit_bb_middleband_window, ABC) else self.exit_bb_middleband_window
        dataframe.loc[dataframe['close'] > dataframe[f'bb_middleband_{exit_bb_middleband_window}'], 'exit'] = 1
        return dataframe