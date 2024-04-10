import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative
from freqtrade.strategy import merge_informative_pair, DecimalParameter, IntParameter, BooleanParameter, CategoricalParameter, stoploss_from_open
from pandas import DataFrame, Series
from typing import Dict, List, Optional, Tuple
from functools import reduce
from freqtrade.persistence import Trade
from datetime import datetime, timedelta, timezone
from freqtrade.exchange import timeframe_to_prev_date
import talib.abstract as ta
import math
import pandas_ta as pta
import logging
from logging import FATAL
import time
import requests
import threading
logger = logging.getLogger(__name__)
###########################################################################################################
##               DONATIONS for stash86                                                                   ##
##                                                                                                       ##
##   Real-life money : https://patreon.com/stash86                                                       ##
##   BTC: 1FghqtgGLpD9F21BNDMje4iyj4cSzVPZPb                                                             ##
##   ETH (ERC20): 0x689c16451889824d3d3a79ad6fc867909dc8874d                                             ##
##   BEP20/BSC (USDT): 0x689c16451889824d3d3a79ad6fc867909dc8874d                                        ##
##   TRC20/TRON (USDT): TKMuRHJppPok3ik2siZp2SYRdBdfdSWxrt                                               ##
##                                                                                                       ##
##               REFERRAL LINKS                                                                          ##
##                                                                                                       ##
##  Binance: https://accounts.binance.com/en/register?ref=143744527                                      ##
##  Kucoin: https://www.kucoin.com/ucenter/signup?rcode=r3BWY2T                                          ##
##  Vultr (you get $100 credit that expires in 14 days) : https://www.vultr.com/?ref=8944192-8H          ##
###########################################################################################################

class MultiMA_TSL5(IStrategy):

    def version(self) -> str:
        return 'v5'
    INTERFACE_VERSION = 3
    # ROI table:
    minimal_roi = {'0': 100.0}
    # Buy hyperspace params:
    # value loaded from strategy
    # value loaded from strategy
    # value loaded from strategy
    # value loaded from strategy
    entry_params = {'base_nb_candles_entry_hma': 95, 'low_offset_hma': 0.92, 'base_nb_candles_entry_hma2': 59, 'low_offset_hma2': 0.92, 'base_nb_candles_entry_hma3': 62, 'low_offset_hma3': 0.89, 'base_nb_candles_entry_ema': 7, 'low_offset_ema': 0.988, 'base_nb_candles_entry_ema_hma': 41, 'low_offset_ema_hma': 0.985, 'base_nb_candles_entry_ema_2': 13, 'low_offset_ema_2': 0.986, 'base_nb_candles_entry_ema2': 20, 'low_offset_ema2': 0.953, 'base_nb_candles_entry_ema3': 36, 'low_offset_ema3': 0.955, 'entry_rsx_1': 59, 'entry_rsx_fast_1': 70, 'entry_rsx_2': 42, 'entry_rsx_fast_2': 68, 'entry_rsx_fast_hma': 69, 'entry_rsx_hma': 38, 'entry_ema_fast_length_15m': 15, 'entry_ema_fast_length_1h': 15, 'entry_ema_slow_length_15m': 30, 'entry_ema_slow_length_1h': 30, 'entry_length_volume': 15, 'entry_volume_volatility': 2.29, 'entry_length_volume2': 21, 'entry_volume_volatility2': 1.67}
    # Sell hyperspace params:
    exit_params = {'base_nb_candles_exit_ema': 88, 'high_offset_ema': 1.05, 'base_nb_candles_exit_ema2': 38, 'high_offset_ema2': 1.018, 'base_nb_candles_exit_ema3': 39, 'high_offset_ema3': 0.957, 'base_nb_candles_exit_ema4': 71, 'high_offset_ema4': 0.941, 'base_nb_candles_exit_ema5': 22, 'high_offset_ema5': 0.948, 'base_nb_candles_exit_ema6': 40, 'high_offset_ema6': 0.861}
    # Protection hyperspace params:
    protection_params = {'low_profit_lookback': 60, 'low_profit_min_req': 0.04, 'low_profit_stop_duration': 28, 'low_profit_trade_limit': 2, 'low_profit_lookback2': 45, 'low_profit_min_req2': -0.01, 'low_profit_stop_duration2': 9, 'low_profit_trade_limit2': 1, 'max_drawdown_allowed': 1, 'max_drawdown_lookback': 56, 'max_drawdown_stop_duration': 10, 'max_drawdown_trade_limit': 6, 'stoploss_guard_lookback': 28, 'stoploss_guard_stop_duration': 20}
    low_profit_optimize = False
    low_profit_lookback = IntParameter(2, 60, default=20, space='protection', optimize=low_profit_optimize)
    low_profit_trade_limit = IntParameter(2, 40, default=3, space='protection', optimize=low_profit_optimize)
    low_profit_stop_duration = IntParameter(2, 40, default=20, space='protection', optimize=low_profit_optimize)
    low_profit_min_req = DecimalParameter(-0.05, 0.05, default=-0.05, space='protection', decimals=2, optimize=low_profit_optimize)
    low_profit_optimize2 = False
    low_profit_lookback2 = IntParameter(2, 60, default=20, space='protection', optimize=low_profit_optimize2)
    low_profit_trade_limit2 = IntParameter(1, 5, default=3, space='protection', optimize=low_profit_optimize2)
    low_profit_stop_duration2 = IntParameter(2, 30, default=20, space='protection', optimize=low_profit_optimize2)
    low_profit_min_req2 = DecimalParameter(-0.05, 0.05, default=-0.05, space='protection', decimals=2, optimize=low_profit_optimize2)
    max_drawdown_optimize = False
    max_drawdown_lookback = IntParameter(2, 60, default=20, space='protection', optimize=max_drawdown_optimize)
    max_drawdown_trade_limit = IntParameter(2, 10, default=3, space='protection', optimize=max_drawdown_optimize)
    max_drawdown_stop_duration = IntParameter(2, 60, default=20, space='protection', optimize=max_drawdown_optimize)
    max_drawdown_allowed = IntParameter(1, 4, default=4, space='protection', optimize=max_drawdown_optimize)
    stoploss_guard_optimize = False
    stoploss_guard_lookback = IntParameter(1, 40, default=20, space='protection', optimize=stoploss_guard_optimize)
    stoploss_guard_trade_limit = IntParameter(1, 4, default=1, space='protection', optimize=False)
    stoploss_guard_stop_duration = IntParameter(1, 40, default=20, space='protection', optimize=stoploss_guard_optimize)

    @property
    def protections(self):
        prot = []
        prot.append({'method': 'LowProfitPairs', 'lookback_period_candles': self.low_profit_lookback.value, 'trade_limit': self.low_profit_trade_limit.value, 'stop_duration_candles': int(self.low_profit_stop_duration.value), 'required_profit': self.low_profit_min_req.value, 'only_per_pair': True})
        prot.append({'method': 'LowProfitPairs', 'lookback_period_candles': self.low_profit_lookback2.value, 'trade_limit': self.low_profit_trade_limit2.value, 'stop_duration_candles': int(self.low_profit_stop_duration2.value), 'required_profit': self.low_profit_min_req2.value, 'only_per_pair': False})
        prot.append({'method': 'MaxDrawdown', 'lookback_period_candles': self.max_drawdown_lookback.value, 'trade_limit': self.max_drawdown_trade_limit.value, 'stop_duration_candles': self.max_drawdown_stop_duration.value, 'max_allowed_drawdown': 0.05 * self.max_drawdown_allowed.value})
        prot.append({'method': 'StoplossGuard', 'lookback_period_candles': self.stoploss_guard_lookback.value, 'trade_limit': self.stoploss_guard_trade_limit.value, 'stop_duration_candles': self.stoploss_guard_stop_duration.value, 'only_per_pair': True, 'only_per_side': True})
        return prot
    dummy = IntParameter(20, 70, default=61, space='entry', optimize=False)
    entry_rsx_hma = IntParameter(10, 70, default=50, space='entry', optimize=False)
    entry_rsx_fast_hma = IntParameter(10, 70, default=50, space='entry', optimize=False)
    entry_rsx_1 = IntParameter(10, 70, default=50, space='entry', optimize=False)
    entry_rsx_fast_1 = IntParameter(10, 70, default=50, space='entry', optimize=False)
    entry_rsx_2 = IntParameter(10, 70, default=50, space='entry', optimize=False)
    entry_rsx_fast_2 = IntParameter(10, 70, default=50, space='entry', optimize=False)
    optimize_entry_hma = False
    base_nb_candles_entry_hma = IntParameter(5, 100, default=6, space='entry', optimize=optimize_entry_hma)
    low_offset_hma = DecimalParameter(0.7, 0.99, default=0.95, decimals=2, space='entry', optimize=optimize_entry_hma)
    optimize_entry_hma2 = False
    base_nb_candles_entry_hma2 = IntParameter(5, 100, default=6, space='entry', optimize=optimize_entry_hma2)
    low_offset_hma2 = DecimalParameter(0.7, 0.99, default=0.95, decimals=2, space='entry', optimize=optimize_entry_hma2)
    optimize_entry_hma3 = False
    base_nb_candles_entry_hma3 = IntParameter(5, 100, default=6, space='entry', optimize=optimize_entry_hma3)
    low_offset_hma3 = DecimalParameter(0.7, 0.99, default=0.95, decimals=2, space='entry', optimize=optimize_entry_hma3)
    optimize_entry_ema = False
    base_nb_candles_entry_ema = IntParameter(5, 100, default=6, space='entry', optimize=optimize_entry_ema)
    low_offset_ema = DecimalParameter(0.7, 0.99, default=0.9, space='entry', optimize=optimize_entry_ema)
    optimize_entry_ema_hma = False
    base_nb_candles_entry_ema_hma = IntParameter(5, 100, default=6, space='entry', optimize=optimize_entry_ema_hma)
    low_offset_ema_hma = DecimalParameter(0.7, 0.99, default=0.9, space='entry', optimize=optimize_entry_ema_hma)
    optimize_entry_ema_2 = False
    base_nb_candles_entry_ema_2 = IntParameter(5, 100, default=6, space='entry', optimize=optimize_entry_ema_2)
    low_offset_ema_2 = DecimalParameter(0.7, 0.99, default=0.9, space='entry', optimize=optimize_entry_ema_2)
    optimize_entry_ema2 = False
    base_nb_candles_entry_ema2 = IntParameter(5, 100, default=6, space='entry', optimize=optimize_entry_ema2)
    low_offset_ema2 = DecimalParameter(0.7, 0.99, default=0.9, space='entry', optimize=optimize_entry_ema2)
    optimize_entry_ema3 = False
    base_nb_candles_entry_ema3 = IntParameter(5, 100, default=6, space='entry', optimize=optimize_entry_ema3)
    low_offset_ema3 = DecimalParameter(0.7, 0.99, default=0.9, space='entry', optimize=optimize_entry_ema3)
    length_ema_15m = [5, 10, 15, 20, 25, 30, 35]
    optimize_entry_ema_length_15m = False
    entry_ema_fast_length_15m = CategoricalParameter([5, 10, 15, 20, 25, 30], default=15, optimize=optimize_entry_ema_length_15m)
    entry_ema_slow_length_15m = CategoricalParameter([10, 15, 20, 25, 30, 35], default=30, optimize=optimize_entry_ema_length_15m)
    length_ema_1h = [5, 10, 15, 20, 25, 30, 35]
    optimize_entry_ema_length_1h = False
    entry_ema_fast_length_1h = CategoricalParameter([5, 10, 15, 20, 25, 30], default=15, optimize=optimize_entry_ema_length_1h)
    entry_ema_slow_length_1h = CategoricalParameter([10, 15, 20, 25, 30, 35], default=30, optimize=optimize_entry_ema_length_1h)
    optimize_entry_volume = False
    entry_length_volume = IntParameter(5, 100, default=6, optimize=optimize_entry_volume)
    entry_volume_volatility = DecimalParameter(0.5, 3, default=1, decimals=2, optimize=optimize_entry_volume)
    optimize_entry_volume2 = False
    entry_length_volume2 = IntParameter(5, 100, default=6, optimize=optimize_entry_volume2)
    entry_volume_volatility2 = DecimalParameter(0.5, 3, default=1, decimals=2, optimize=optimize_entry_volume2)
    # Sell
    optimize_exit_ema = False
    base_nb_candles_exit_ema = IntParameter(5, 100, default=6, space='exit', optimize=optimize_exit_ema)
    high_offset_ema = DecimalParameter(1, 1.2, default=1, decimals=2, space='exit', optimize=optimize_exit_ema)
    optimize_exit_ema2 = False
    base_nb_candles_exit_ema2 = IntParameter(5, 100, default=6, space='exit', optimize=optimize_exit_ema2)
    high_offset_ema2 = DecimalParameter(0.9, 1.1, default=0.95, space='exit', optimize=optimize_exit_ema2)
    optimize_exit_ema3 = False
    base_nb_candles_exit_ema3 = IntParameter(5, 100, default=6, space='exit', optimize=optimize_exit_ema3)
    high_offset_ema3 = DecimalParameter(0.8, 0.99, default=0.95, space='exit', optimize=optimize_exit_ema3)
    optimize_exit_ema4 = False
    base_nb_candles_exit_ema4 = IntParameter(5, 100, default=6, space='exit', optimize=optimize_exit_ema4)
    high_offset_ema4 = DecimalParameter(0.8, 0.99, default=0.95, space='exit', optimize=optimize_exit_ema4)
    optimize_exit_ema5 = False
    base_nb_candles_exit_ema5 = IntParameter(5, 100, default=6, space='exit', optimize=optimize_exit_ema5)
    high_offset_ema5 = DecimalParameter(0.8, 0.99, default=0.95, space='exit', optimize=optimize_exit_ema5)
    optimize_exit_ema6 = False
    base_nb_candles_exit_ema6 = IntParameter(5, 100, default=6, space='exit', optimize=optimize_exit_ema6)
    high_offset_ema6 = DecimalParameter(0.8, 0.99, default=0.95, space='exit', optimize=optimize_exit_ema6)
    # Stoploss:
    stoploss = -0.1
    # Trailing stop:
    trailing_stop = False
    trailing_stop_positive = 0.001
    trailing_stop_positive_offset = 0.01
    trailing_only_offset_is_reached = True
    # Sell signal
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.01
    ignore_roi_if_entry_signal = False
    timeframe = '5m'
    process_only_new_candles = True
    startup_candle_count = 200
    age_filter = 30

    @informative('1d')
    def populate_indicators_1d(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['age_filter_ok'] = dataframe['volume'].rolling(window=self.age_filter, min_periods=self.age_filter).min() > 0
        if not self.config['runmode'].value in ('dry_run', 'live'):
            drop_columns = ['open', 'high', 'low', 'close', 'volume']
            dataframe.drop(columns=dataframe.columns.intersection(drop_columns), inplace=True)
        return dataframe

    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.config['runmode'].value in 'hyperopt' and self.optimize_entry_ema_length_1h:
            for val in self.length_ema_1h:
                dataframe[f'ema_{val}'] = ta.EMA(dataframe, timeperiod=int(val))
        else:
            dataframe[f'ema_{self.entry_ema_fast_length_1h.value}'] = ta.EMA(dataframe, timeperiod=int(self.entry_ema_fast_length_1h.value))
            dataframe[f'ema_{self.entry_ema_slow_length_1h.value}'] = ta.EMA(dataframe, timeperiod=int(self.entry_ema_slow_length_1h.value))
        if not self.config['runmode'].value in ('dry_run', 'live'):
            drop_columns = ['open', 'high', 'low', 'close', 'volume']
            dataframe.drop(columns=dataframe.columns.intersection(drop_columns), inplace=True)
        return dataframe

    @informative('15m')
    def populate_indicators_15m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.config['runmode'].value in 'hyperopt' and self.optimize_entry_ema_length_15m:
            for val in self.length_ema_15m:
                dataframe[f'ema_{val}'] = ta.EMA(dataframe, timeperiod=int(val))
        else:
            dataframe[f'ema_{self.entry_ema_fast_length_15m.value}'] = ta.EMA(dataframe, timeperiod=int(self.entry_ema_fast_length_15m.value))
            dataframe[f'ema_{self.entry_ema_slow_length_15m.value}'] = ta.EMA(dataframe, timeperiod=int(self.entry_ema_slow_length_15m.value))
        if not self.config['runmode'].value in ('dry_run', 'live'):
            drop_columns = ['open', 'high', 'low', 'close', 'volume']
            dataframe.drop(columns=dataframe.columns.intersection(drop_columns), inplace=True)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Heiken Ashi
        heikinashi = qtpylib.heikinashi(dataframe)
        heikinashi['volume'] = dataframe['volume']
        # Profit Maximizer - PMAX
        dataframe['pm'], df_pmx = pmax(heikinashi, MAtype=1, length=9, multiplier=27, period=10, src=3)
        df_source = (dataframe['high'] + dataframe['low'] + dataframe['open'] + dataframe['close']) / 4
        dataframe['pmax_thresh'] = ta.EMA(df_source, timeperiod=9)
        dataframe['rsx_14'] = pta.rsx(dataframe['close'], 14)
        dataframe['rsx_4'] = pta.rsx(dataframe['close'], 4)
        dataframe['live_data_ok'] = dataframe['volume'].rolling(window=72, min_periods=72).min() > 0
        if not self.optimize_entry_hma:
            dataframe['hma_offset_entry'] = tv_hma(dataframe, int(self.base_nb_candles_entry_hma.value)) * self.low_offset_hma.value
        if not self.optimize_entry_hma2:
            dataframe['hma_offset_entry2'] = tv_hma(dataframe, int(self.base_nb_candles_entry_hma2.value)) * self.low_offset_hma2.value
        if not self.optimize_entry_hma3:
            dataframe['hma_offset_entry3'] = tv_hma(dataframe, int(self.base_nb_candles_entry_hma3.value)) * self.low_offset_hma3.value
        if not self.optimize_entry_ema:
            dataframe['ema_offset_entry'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema.value)) * self.low_offset_ema.value
        if not self.optimize_entry_ema_hma:
            dataframe['ema_offset_entry_hma'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema_hma.value)) * self.low_offset_ema_hma.value
        if not self.optimize_entry_ema_2:
            dataframe['ema_offset_entry_2'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema_2.value)) * self.low_offset_ema_2.value
        if not self.optimize_entry_ema2:
            dataframe['ema_offset_entry2'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema2.value)) * self.low_offset_ema2.value
        if not self.optimize_entry_ema3:
            dataframe['ema_offset_entry3'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema3.value)) * self.low_offset_ema3.value
        if not self.optimize_entry_volume:
            df_rvol = rvol(dataframe, int(self.entry_length_volume.value))
            dataframe['volume_volatility'] = df_rvol < self.entry_volume_volatility.value
        if not self.optimize_entry_volume2:
            df_rvol = rvol(dataframe, int(self.entry_length_volume2.value))
            dataframe['volume_volatility2'] = df_rvol < self.entry_volume_volatility2.value
        if not self.optimize_exit_ema:
            dataframe['ema_offset_exit'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema.value)) * self.high_offset_ema.value
        if not self.optimize_exit_ema2:
            dataframe['ema_offset_exit2'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema2.value)) * self.high_offset_ema2.value
        if not self.optimize_exit_ema3:
            dataframe['ema_offset_exit3'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema3.value)) * self.high_offset_ema3.value
        if not self.optimize_exit_ema4:
            dataframe['ema_offset_exit4'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema4.value)) * self.high_offset_ema4.value
        if not self.optimize_exit_ema5:
            dataframe['ema_offset_exit5'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema5.value)) * self.high_offset_ema5.value
        if not self.optimize_exit_ema6:
            dataframe['ema_offset_exit6'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema6.value)) * self.high_offset_ema6.value
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        if self.optimize_entry_hma:
            dataframe['hma_offset_entry'] = tv_hma(dataframe, int(self.base_nb_candles_entry_hma.value)) * self.low_offset_hma.value
        if self.optimize_entry_hma2:
            dataframe['hma_offset_entry2'] = tv_hma(dataframe, int(self.base_nb_candles_entry_hma2.value)) * self.low_offset_hma2.value
        if self.optimize_entry_hma3:
            dataframe['hma_offset_entry3'] = tv_hma(dataframe, int(self.base_nb_candles_entry_hma3.value)) * self.low_offset_hma3.value
        if self.optimize_entry_ema:
            dataframe['ema_offset_entry'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema.value)) * self.low_offset_ema.value
        if self.optimize_entry_ema_hma:
            dataframe['ema_offset_entry_hma'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema_hma.value)) * self.low_offset_ema_hma.value
        if self.optimize_entry_ema_2:
            dataframe['ema_offset_entry_2'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema_2.value)) * self.low_offset_ema_2.value
        if self.optimize_entry_ema2:
            dataframe['ema_offset_entry2'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema2.value)) * self.low_offset_ema2.value
        if self.optimize_entry_ema3:
            dataframe['ema_offset_entry3'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema3.value)) * self.low_offset_ema3.value
        if self.optimize_entry_volume:
            df_rvol = rvol(dataframe, int(self.entry_length_volume.value))
            dataframe['volume_volatility'] = df_rvol < self.entry_volume_volatility.value
        if self.optimize_entry_volume2:
            df_rvol = rvol(dataframe, int(self.entry_length_volume2.value))
            dataframe['volume_volatility2'] = df_rvol < self.entry_volume_volatility2.value
        dataframe.loc[:, 'enter_tag'] = ''
        dataframe.loc[:, 'enter_long'] = 0
        go_long_1h = ((self.entry_ema_fast_length_1h.value < self.entry_ema_slow_length_1h.value) & (dataframe[f'ema_{self.entry_ema_fast_length_1h.value}_1h'] > dataframe[f'ema_{self.entry_ema_slow_length_1h.value}_1h'])).astype('int') * 2
        go_long_15m = ((self.entry_ema_fast_length_15m.value < self.entry_ema_slow_length_15m.value) & (dataframe[f'ema_{self.entry_ema_fast_length_15m.value}_15m'] > dataframe[f'ema_{self.entry_ema_slow_length_15m.value}_15m'])).astype('int') * 2
        # &
        # dataframe["volatility"]
        add_check = dataframe['live_data_ok'] & dataframe['age_filter_ok_1d'] & (dataframe['open'] > dataframe['close']) & (go_long_1h > 0) & (go_long_15m > 0) & ((dataframe['close'] < dataframe['ema_offset_entry']) & (dataframe['pm'] <= dataframe['pmax_thresh']) & (dataframe['rsx_14'] < self.entry_rsx_1.value) & (dataframe['rsx_4'] < self.entry_rsx_fast_1.value) & dataframe['volume_volatility'] | (dataframe['close'] < dataframe['ema_offset_entry_2']) & (dataframe['pm'] > dataframe['pmax_thresh']) & (dataframe['rsx_14'] < self.entry_rsx_2.value) & (dataframe['rsx_4'] < self.entry_rsx_fast_2.value) & dataframe['volume_volatility2'])
        entry_offset_hma = (dataframe['close'] < dataframe['hma_offset_entry']) & (dataframe['pm'] <= dataframe['pmax_thresh']) & (dataframe['rsx_14'] < self.entry_rsx_hma.value) & (dataframe['rsx_4'] < self.entry_rsx_fast_hma.value) & (dataframe['close'] < dataframe['ema_offset_entry_hma'])
        dataframe.loc[entry_offset_hma, 'enter_tag'] += 'hma '
        conditions.append(entry_offset_hma)
        entry_offset_hma2 = (dataframe['close'] < dataframe['hma_offset_entry2']) & (dataframe['pm'] > dataframe['pmax_thresh'])
        dataframe.loc[entry_offset_hma2, 'enter_tag'] += 'hma_2 '
        conditions.append(entry_offset_hma2)
        entry_offset_hma3 = ((dataframe['close'] < dataframe['hma_offset_entry3']).rolling(2).min() > 0) & (dataframe['pm'] <= dataframe['pmax_thresh'])
        dataframe.loc[entry_offset_hma3, 'enter_tag'] += 'hma_3 '
        conditions.append(entry_offset_hma3)
        entry_offset_ema2 = ((dataframe['close'] < dataframe['ema_offset_entry2']).rolling(2).min() > 0) & (dataframe['pm'] <= dataframe['pmax_thresh'])
        dataframe.loc[entry_offset_ema2, 'enter_tag'] += 'ema_2 '
        conditions.append(entry_offset_ema2)
        entry_offset_ema3 = ((dataframe['close'] < dataframe['ema_offset_entry3']).rolling(3).min() > 0) & (dataframe['pm'] <= dataframe['pmax_thresh'])
        dataframe.loc[entry_offset_ema3, 'enter_tag'] += 'ema_3 '
        conditions.append(entry_offset_ema3)
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions) & add_check, 'enter_long'] = 1
            dataframe.loc[entry_offset_hma & entry_offset_ema2 & np.invert(entry_offset_hma3), 'enter_long'] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.optimize_exit_ema:
            dataframe['ema_offset_exit'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema.value)) * self.high_offset_ema.value
        if self.optimize_exit_ema2:
            dataframe['ema_offset_exit2'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema2.value)) * self.high_offset_ema2.value
        if self.optimize_exit_ema3:
            dataframe['ema_offset_exit3'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema3.value)) * self.high_offset_ema3.value
        if self.optimize_exit_ema4:
            dataframe['ema_offset_exit4'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema4.value)) * self.high_offset_ema4.value
        if self.optimize_exit_ema5:
            dataframe['ema_offset_exit5'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema5.value)) * self.high_offset_ema5.value
        if self.optimize_exit_ema6:
            dataframe['ema_offset_exit6'] = ta.EMA(dataframe, int(self.base_nb_candles_exit_ema6.value)) * self.high_offset_ema6.value
        dataframe.loc[:, 'exit_tag'] = ''
        conditions = []
        exit_ema_1 = (dataframe['close'] > dataframe['ema_offset_exit']) & (dataframe['pm'] <= dataframe['pmax_thresh'])
        conditions.append(exit_ema_1)
        dataframe.loc[exit_ema_1, 'exit_tag'] += 'EMA_1 '
        exit_ema_2 = (dataframe['close'] > dataframe['ema_offset_exit2']) & (dataframe['pm'] > dataframe['pmax_thresh'])
        conditions.append(exit_ema_2)
        dataframe.loc[exit_ema_2, 'exit_tag'] += 'EMA_2 '
        exit_ema_3 = (dataframe['close'] < dataframe['ema_offset_exit3']) & (dataframe['pm'] <= dataframe['pmax_thresh'])
        conditions.append(exit_ema_3)
        dataframe.loc[exit_ema_3, 'exit_tag'] += 'EMA_3 '
        exit_ema_4 = (dataframe['close'] < dataframe['ema_offset_exit4']) & (dataframe['pm'] > dataframe['pmax_thresh'])
        conditions.append(exit_ema_4)
        dataframe.loc[exit_ema_4, 'exit_tag'] += 'EMA_4 '
        add_check = dataframe['volume'] > 0
        exit_ema_5 = ((dataframe['close'] < dataframe['ema_offset_exit5']).rolling(2).min() > 0) & (dataframe['pm'] <= dataframe['pmax_thresh'])
        conditions.append(exit_ema_5)
        dataframe.loc[exit_ema_5, 'exit_tag'] += 'EMA_5 '
        exit_ema_6 = ((dataframe['close'] < dataframe['ema_offset_exit6']).rolling(2).min() > 0) & (dataframe['pm'] > dataframe['pmax_thresh'])
        conditions.append(exit_ema_6)
        dataframe.loc[exit_ema_6, 'exit_tag'] += 'EMA_6 '
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions) & add_check, 'exit_long'] = 1
        return dataframe

def zema(dataframe, period, field='close'):
    """
    Source: https://github.com/freqtrade/technical/blob/master/technical/indicators/overlap_studies.py#L79
    Modified slightly to use ta.EMA instead of technical ema
    """
    df = dataframe.copy()
    df['ema1'] = ta.EMA(df[field], timeperiod=period)
    df['ema2'] = ta.EMA(df['ema1'], timeperiod=period)
    df['d'] = df['ema1'] - df['ema2']
    df['zema'] = df['ema1'] + df['d']
    return df['zema']

def tv_wma(df, length=9) -> DataFrame:
    """
    Source: Tradingview "Moving Average Weighted"
    Pinescript Author: Unknown
    Args :
        dataframe : Pandas Dataframe
        length : WMA length
        field : Field to use for the calculation
    Returns :
        dataframe : Pandas DataFrame with new columns 'tv_wma'
    """
    norm = 0
    sum = 0
    for i in range(1, length - 1):
        weight = (length - i) * length
        norm = norm + weight
        sum = sum + df.shift(i) * weight
    tv_wma = sum / norm if norm > 0 else 0
    return tv_wma

def tv_hma(dataframe, length=9, field='close') -> DataFrame:
    """
    Source: Tradingview "Hull Moving Average"
    Pinescript Author: Unknown
    Args :
        dataframe : Pandas Dataframe
        length : HMA length
        field : Field to use for the calculation
    Returns :
        dataframe : Pandas DataFrame with new columns 'tv_hma'
    """
    h = 2 * tv_wma(dataframe[field], math.floor(length / 2)) - tv_wma(dataframe[field], length)
    tv_hma = tv_wma(h, math.floor(math.sqrt(length)))
    # dataframe.drop("h", inplace=True, axis=1)
    return tv_hma

def rvol(dataframe, window=24):
    av = ta.SMA(dataframe['volume'], timeperiod=int(window))
    rvol = dataframe['volume'] / av
    return rvol

def pmax(df, period, multiplier, length, MAtype, src):
    period = int(period)
    multiplier = int(multiplier)
    length = int(length)
    MAtype = int(MAtype)
    src = int(src)
    mavalue = f'MA_{MAtype}_{length}'
    atr = f'ATR_{period}'
    pm = f'pm_{period}_{multiplier}_{length}_{MAtype}'
    pmx = f'pmX_{period}_{multiplier}_{length}_{MAtype}'
    # MAtype==1 --> EMA
    # MAtype==2 --> DEMA
    # MAtype==3 --> T3
    # MAtype==4 --> SMA
    # MAtype==5 --> VIDYA
    # MAtype==6 --> TEMA
    # MAtype==7 --> WMA
    # MAtype==8 --> VWMA
    # MAtype==9 --> zema
    if src == 1:
        masrc = df['close']
    elif src == 2:
        masrc = (df['high'] + df['low']) / 2
    elif src == 3:
        masrc = (df['high'] + df['low'] + df['close'] + df['open']) / 4
    if MAtype == 1:
        mavalue = ta.EMA(masrc, timeperiod=length)
    elif MAtype == 2:
        mavalue = ta.DEMA(masrc, timeperiod=length)
    elif MAtype == 3:
        mavalue = ta.T3(masrc, timeperiod=length)
    elif MAtype == 4:
        mavalue = ta.SMA(masrc, timeperiod=length)
    elif MAtype == 5:
        mavalue = VIDYA(df, length=length)
    elif MAtype == 6:
        mavalue = ta.TEMA(masrc, timeperiod=length)
    elif MAtype == 7:
        mavalue = ta.WMA(df, timeperiod=length)
    elif MAtype == 8:
        mavalue = vwma(df, length)
    elif MAtype == 9:
        mavalue = zema(df, period=length)
    df[atr] = ta.ATR(df, timeperiod=period)
    df['basic_ub'] = mavalue + multiplier / 10 * df[atr]
    df['basic_lb'] = mavalue - multiplier / 10 * df[atr]
    basic_ub = df['basic_ub'].values
    final_ub = np.full(len(df), 0.0)
    basic_lb = df['basic_lb'].values
    final_lb = np.full(len(df), 0.0)
    for i in range(period, len(df)):
        final_ub[i] = basic_ub[i] if basic_ub[i] < final_ub[i - 1] or mavalue[i - 1] > final_ub[i - 1] else final_ub[i - 1]
        final_lb[i] = basic_lb[i] if basic_lb[i] > final_lb[i - 1] or mavalue[i - 1] < final_lb[i - 1] else final_lb[i - 1]
    df['final_ub'] = final_ub
    df['final_lb'] = final_lb
    pm_arr = np.full(len(df), 0.0)
    for i in range(period, len(df)):
        pm_arr[i] = final_ub[i] if pm_arr[i - 1] == final_ub[i - 1] and mavalue[i] <= final_ub[i] else final_lb[i] if pm_arr[i - 1] == final_ub[i - 1] and mavalue[i] > final_ub[i] else final_lb[i] if pm_arr[i - 1] == final_lb[i - 1] and mavalue[i] >= final_lb[i] else final_ub[i] if pm_arr[i - 1] == final_lb[i - 1] and mavalue[i] < final_lb[i] else 0.0
    pm = Series(pm_arr)
    # Mark the trend direction up/down
    pmx = np.where(pm_arr > 0.0, np.where(mavalue < pm_arr, 'down', 'up'), np.NaN)
    return (pm, pmx)