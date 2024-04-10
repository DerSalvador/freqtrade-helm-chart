# --- Do not remove these libs ---
# --- Do not remove these libs ---
from logging import FATAL
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------
import talib.abstract as ta
import numpy as np
import freqtrade.vendor.qtpylib.indicators as qtpylib
import datetime
from technical.util import resample_to_interval, resampled_merge
from datetime import datetime, timedelta
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open, merge_informative_pair, DecimalParameter, IntParameter, CategoricalParameter
import technical.indicators as ftt
# @Rallipanos
# @pluxury
# with help from @stash86 and @Perkmeister
# Buy hyperspace params:
entry_params = {'base_nb_candles_entry': 8, 'ewo_high': 2.675, 'ewo_high_2': 4.516, 'ewo_low': -9.263, 'lookback_candles': 22, 'low_offset': 0.988, 'low_offset_2': 0.915, 'profit_threshold': 1.0408, 'rsi_entry': 57, 'rsi_fast_entry': 49}
# Sell hyperspace params:
exit_params = {'base_nb_candles_exit': 24, 'high_offset': 0.998, 'high_offset_2': 1, 'exit_rsi_main': 87.43}

def zlema2(dataframe, fast):
    df = dataframe.copy()
    zema1 = ta.EMA(df['close'], fast)
    zema2 = ta.EMA(zema1, fast)
    d1 = zema1 - zema2
    df['zlema2'] = zema1 + d1
    return df['zlema2']

def EWO(dataframe, ema_length=5, ema2_length=35):
    df = dataframe.copy()
    ema1 = ta.EMA(df, timeperiod=ema_length)
    ema2 = ta.EMA(df, timeperiod=ema2_length)
    emadif = (ema1 - ema2) / df['low'] * 100
    return emadif

class tesla4(IStrategy):
    INTERFACE_VERSION = 3
    # ROI table:
    minimal_roi = {'0': 0.215, '40': 0.032, '64': 0.03, '87': 0.016, '201': 0}
    # Stoploss:
    stoploss = -0.15
    # SMAOffset
    base_nb_candles_entry = IntParameter(2, 20, default=entry_params['base_nb_candles_entry'], space='entry', optimize=False)
    base_nb_candles_exit = IntParameter(2, 25, default=exit_params['base_nb_candles_exit'], space='exit', optimize=False)
    low_offset = DecimalParameter(0.9, 0.99, default=entry_params['low_offset'], space='entry', optimize=False)
    low_offset_2 = DecimalParameter(0.9, 0.99, default=entry_params['low_offset_2'], space='entry', optimize=False)
    high_offset = DecimalParameter(0.95, 1.1, default=exit_params['high_offset'], space='exit', optimize=False)
    high_offset_2 = DecimalParameter(0.99, 1.5, default=exit_params['high_offset_2'], space='exit', optimize=False)
    exit_rsi_main = DecimalParameter(72.0, 90.0, default=exit_params['exit_rsi_main'], space='exit', decimals=2, optimize=False, load=True)
    # Protection
    fast_ewo = 50
    slow_ewo = 200
    lookback_candles = IntParameter(1, 36, default=entry_params['lookback_candles'], space='entry', optimize=False)
    profit_threshold = DecimalParameter(0.99, 1.05, default=entry_params['profit_threshold'], space='entry', optimize=False)
    ewo_low = DecimalParameter(-20.0, -8.0, default=entry_params['ewo_low'], space='entry', optimize=False)
    ewo_high = DecimalParameter(2.0, 12.0, default=entry_params['ewo_high'], space='entry', optimize=False)
    ewo_high_2 = DecimalParameter(-6.0, 12.0, default=entry_params['ewo_high_2'], space='entry', optimize=False)
    rsi_entry = IntParameter(10, 80, default=entry_params['rsi_entry'], space='entry', optimize=False)
    rsi_fast_entry = IntParameter(10, 50, default=entry_params['rsi_fast_entry'], space='entry', optimize=False)
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.001
    trailing_stop_positive_offset = 0.01
    trailing_only_offset_is_reached = True
    # Sell signal
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.001
    ignore_roi_if_entry_signal = False
    # Optional order time in force.
    order_time_in_force = {'entry': 'gtc', 'exit': 'ioc'}
    # Optimal timeframe for the strategy
    timeframe = '5m'
    inf_15m = '15m'
    inf_1h = '1h'
    process_only_new_candles = True
    startup_candle_count = 200
    use_custom_stoploss = False
    plot_config = {'main_plot': {'ma_entry': {'color': 'orange'}, 'ma_exit': {'color': 'orange'}}, 'subplots': {'rsi': {'rsi': {'color': 'orange'}, 'rsi_fast': {'color': 'red'}, 'rsi_slow': {'color': 'green'}}, 'ewo': {'EWO': {'color': 'orange'}}}}
    slippage_protection = {'retries': 3, 'max_slippage': -0.02}

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float, rate: float, time_in_force: str, exit_reason: str, **kwargs) -> bool:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1]
        current_profit = trade.calc_profit_ratio(rate)
        if 'bb_bull' in trade.entry_tag and current_profit > 0.01:
            return True
        if last_candle is not None:
            if exit_reason in ['exit_signal']:
                if last_candle['hma_50'] > last_candle['ema_100'] and last_candle['rsi'] < 45:  # *1.2
                    return False
        if last_candle is not None:
            if exit_reason in ['exit_signal']:
                if last_candle['hma_50'] * 1.149 > last_candle['ema_100'] and last_candle['close'] < last_candle['ema_100'] * 0.951:  # *1.2
                    return False
        if trade.entry_tag == 'bb_bull':
            if exit_reason in ['exit_signal'] or exit_reason in ['roi']:
                return False
        # slippage
        try:
            state = self.slippage_protection['__pair_retries']
        except KeyError:
            state = self.slippage_protection['__pair_retries'] = {}
        candle = dataframe.iloc[-1].squeeze()
        slippage = rate / candle['close'] - 1
        if slippage < self.slippage_protection['max_slippage']:
            pair_retries = state.get(pair, 0)
            if pair_retries < self.slippage_protection['retries']:
                state[pair] = pair_retries + 1
                return False
        state[pair] = 0
        return True

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, '15m') for pair in pairs]
        return informative_pairs

    def informative_1h_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        assert self.dp, 'DataProvider is required for multiple timeframes.'
        # Get the informative pair
        informative_1h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_1h)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        dataframe['sma_200_dec'] = dataframe['sma_200'] < dataframe['sma_200'].shift(20)
        # EMA
        # informative_1h['ema_50'] = ta.EMA(informative_1h, timeperiod=50)
        # informative_1h['ema_200'] = ta.EMA(informative_1h, timeperiod=200)
        # # RSI
        # informative_1h['rsi'] = ta.RSI(informative_1h, timeperiod=14)
        # bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        # informative_1h['bb_lowerband'] = bollinger['lower']
        # informative_1h['bb_middleband'] = bollinger['mid']
        # informative_1h['bb_upperband'] = bollinger['upper']
        return informative_1h

    def informative_15m_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        assert self.dp, 'DataProvider is required for multiple timeframes.'
        # Get the informative pair
        informative_15m = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_15m)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        dataframe['sma_200_dec'] = dataframe['sma_200'] < dataframe['sma_200'].shift(20)
        # EMA
        # informative_1h['ema_50'] = ta.EMA(informative_1h, timeperiod=50)
        # informative_1h['ema_200'] = ta.EMA(informative_1h, timeperiod=200)
        # # RSI
        # informative_1h['rsi'] = ta.RSI(informative_1h, timeperiod=14)
        # bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        # informative_1h['bb_lowerband'] = bollinger['lower']
        # informative_1h['bb_middleband'] = bollinger['mid']
        # informative_1h['bb_upperband'] = bollinger['upper']
        return informative_15m

    def normal_tf_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Calculate all ma_entry values
        for val in self.base_nb_candles_entry.range:
            dataframe[f'ma_entry_{val}'] = ta.EMA(dataframe, timeperiod=val)
        # Calculate all ma_exit values
        for val in self.base_nb_candles_exit.range:
            dataframe[f'ma_exit_{val}'] = ta.EMA(dataframe, timeperiod=val)
        dataframe['hma_50'] = qtpylib.hull_moving_average(dataframe['close'], window=50)
        dataframe['ema_100'] = ta.EMA(dataframe, timeperiod=100)
        dataframe['ema_10'] = zlema2(dataframe, 10)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        dataframe['sma_200_dec'] = dataframe['sma_200'] < dataframe['sma_200'].shift(20)
        dataframe['sma_9'] = ta.SMA(dataframe, timeperiod=9)
        # Elliot
        dataframe['EWO'] = EWO(dataframe, self.fast_ewo, self.slow_ewo)
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=20)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        bb_40 = qtpylib.bollinger_bands(dataframe['close'], window=40, stds=2)
        dataframe['lower'] = bb_40['lower']
        dataframe['mid'] = bb_40['mid']
        dataframe['bbdelta'] = (bb_40['mid'] - dataframe['lower']).abs()
        dataframe['closedelta'] = (dataframe['close'] - dataframe['close'].shift()).abs()
        dataframe['tail'] = (dataframe['close'] - dataframe['low']).abs()
        # strategy ClucMay72018
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['volume_mean_slow'] = dataframe['volume'].rolling(window=30).mean()
        dataframe['vol_7_max'] = dataframe['volume'].rolling(window=20).max()
        dataframe['vol_14_max'] = dataframe['volume'].rolling(window=14).max()
        dataframe['vol_7_min'] = dataframe['volume'].rolling(window=20).min()
        dataframe['vol_14_min'] = dataframe['volume'].rolling(window=14).min()
        dataframe['roll_7'] = 100 * ((dataframe['volume'] - dataframe['vol_7_max']) / (dataframe['vol_7_max'] - dataframe['vol_7_min']))
        dataframe['vol_base'] = ta.SMA(dataframe['roll_7'], timeperiod=5)
        dataframe['vol_ma_26'] = ta.EMA(dataframe['volume'], timeperiod=26)
        dataframe['vol_ma_200'] = ta.EMA(dataframe['volume'], timeperiod=200)
        dataframe['vol_ma_26_front'] = (ta.EMA(dataframe['volume'], timeperiod=26).max() - ta.EMA(dataframe['volume'], timeperiod=26).min()) / 2
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # informative_1h = self.informative_1h_indicators(dataframe, metadata)
        informative_15m = self.informative_15m_indicators(dataframe, metadata)
        dataframe = merge_informative_pair(dataframe, informative_15m, self.timeframe, self.inf_15m, ffill=True)
        # The indicators for the normal (5m) timeframe
        dataframe = self.normal_tf_indicators(dataframe, metadata)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dont_entry_conditions = []
        # don't entry if there isn't 3% profit to be made
        dont_entry_conditions.append(dataframe['close_15m'].rolling(self.lookback_candles.value).max() < dataframe['close'] * self.profit_threshold.value)
        dataframe.loc[(dataframe['vol_base'] < -80) & (dataframe['rsi_fast'] < self.rsi_fast_entry.value) & (dataframe['close'] < dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset.value) & (dataframe['EWO'] > self.ewo_high.value) & (dataframe['rsi'] < self.rsi_entry.value) & (dataframe['volume'] > 0) & (dataframe['close'] < dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value), ['enter_long', 'enter_tag']] = (1, 'ewo1')
        dataframe.loc[(dataframe['vol_base'] < -80) & (dataframe['rsi_fast'] < self.rsi_fast_entry.value) & (dataframe['close'] < dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset_2.value) & (dataframe['EWO'] > self.ewo_high_2.value) & (dataframe['rsi'] < self.rsi_entry.value) & (dataframe['volume'] > 0) & (dataframe['close'] < dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value) & (dataframe['rsi'] < 25), ['enter_long', 'enter_tag']] = (1, 'ewo2')
        dataframe.loc[(dataframe['vol_base'] > -96) & (dataframe['vol_base'] > -20) & (dataframe['rsi_fast'] < self.rsi_fast_entry.value) & (dataframe['close'] < dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset.value) & (dataframe['EWO'] > self.ewo_high.value) & (dataframe['rsi'] < self.rsi_entry.value) & (dataframe['volume'] > 0) & (dataframe['close'] < dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value), ['enter_long', 'enter_tag']] = (1, 'ewo3')
        dataframe.loc[(dataframe['vol_base'] < -80) & (dataframe['rsi_fast'] < self.rsi_fast_entry.value) & (dataframe['close'] < dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset.value) & (dataframe['EWO'] < self.ewo_low.value) & (dataframe['volume'] > 0) & (dataframe['close'] < dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value), ['enter_long', 'enter_tag']] = (1, 'ewolow')
        # entry in bull market
        dataframe.loc[(dataframe['vol_base'] < -80) & (dataframe['ema_10'].rolling(10).mean() > dataframe['ema_100'].rolling(10).mean()) & dataframe['lower'].shift().gt(0) & dataframe['bbdelta'].gt(dataframe['close'] * 0.031) & dataframe['closedelta'].gt(dataframe['close'] * 0.018) & dataframe['tail'].lt(dataframe['bbdelta'] * 0.233) & dataframe['close'].lt(dataframe['lower'].shift()) & dataframe['close'].le(dataframe['close'].shift()) & (dataframe['volume'] > 0) | (dataframe['vol_base'] < -80) & (dataframe['ema_10'].rolling(10).mean() > dataframe['ema_100'].rolling(10).mean()) & (dataframe['close'] > dataframe['ema_100']) & (dataframe['close'] < dataframe['ema_slow']) & (dataframe['close'] < 0.993 * dataframe['bb_lowerband']) & (dataframe['volume'] < dataframe['volume_mean_slow'].shift(1) * 21) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'bb_bull')
        if dont_entry_conditions:
            for condition in dont_entry_conditions:
                dataframe.loc[condition, 'enter_long'] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append((dataframe['close'] > dataframe['sma_9']) & (dataframe['close'] > dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset_2.value) & (dataframe['rsi'] > 50) & (dataframe['volume'] > 0) & (dataframe['rsi_fast'] > dataframe['rsi_slow']) | (dataframe['close'] < dataframe['hma_50']) & (dataframe['close'] > dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value) & (dataframe['volume'] > 0) & (dataframe['rsi_fast'] > dataframe['rsi_slow']))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_long'] = 1
        return dataframe