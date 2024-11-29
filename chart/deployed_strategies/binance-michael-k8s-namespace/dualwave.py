from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
import talib.abstract as ta
from technical import qtpylib, pivots_points
import numpy as np
import logging
import pandas as pd
import pandas_ta as pta
import datetime
from datetime import datetime, timedelta, timezone
from typing import Optional
import talib.abstract as ta
from technical.util import resample_to_interval, resampled_merge
from freqtrade.strategy import BooleanParameter, CategoricalParameter, DecimalParameter, IStrategy, IntParameter, RealParameter, merge_informative_pair
from freqtrade.strategy import stoploss_from_open
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.persistence import Trade
import technical.indicators as ftt
logger = logging.getLogger('freqtrade')
### Change log ###
### Change log ###

def PC(dataframe, in1, in2):
    df = dataframe.copy()
    pc = (in2 - in1) / in1 * 100
    return pc

class dualwave(IStrategy):
    INTERFACE_VERSION = 3
    ### Strategy parameters ###
    exit_profit_only = True  ### No exiting at a loss
    use_custom_stoploss = True
    trailing_stop = False  # True
    ignore_roi_if_entry_signal = True
    use_exit_signal = True
    stoploss = -0.25
    # DCA Parameters
    position_adjustment_enable = True
    max_entry_position_adjustment = 0
    max_dca_multiplier = 1
    market_status = 0
    minimal_roi = {'0': 0.215}
    ### Hyperoptable parameters ###
    # protections
    cooldown_lookback = IntParameter(24, 48, default=46, space='protection', optimize=True)
    stop_duration = IntParameter(12, 200, default=5, space='protection', optimize=True)
    use_stop_protection = BooleanParameter(default=True, space='protection', optimize=True)
    # SMA   
    filterlength = IntParameter(low=15, high=35, default=25, space='exit', optimize=True)
    max_length = CategoricalParameter([24, 48, 72, 96, 144, 192, 240], default=48, space='entry', optimize=False)
    from15 = IntParameter(low=5, high=35, default=25, space='entry', optimize=True)
    from2 = IntParameter(low=2, high=10, default=5, space='entry', optimize=True)
    # Buy Parameters
    rsi_entry = IntParameter(55, 70, default=65, space='entry', optimize=True)
    rsi_entry_safe = IntParameter(40, 55, default=50, space='entry', optimize=True)
    rsi_ma_entrypc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    sma200_entry_pc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    willr_entry = IntParameter(-50, -20, default=-50, space='entry', optimize=True)
    auto_entry = IntParameter(3, 13, default=3, space='entry', optimize=True)
    auto_entry_down = IntParameter(3, 13, default=3, space='entry', optimize=True)
    auto_entry_bearzzz = IntParameter(3, 13, default=3, space='entry', optimize=True)
    auto_entry_bearzzz_down = IntParameter(3, 10, default=3, space='entry', optimize=True)
    auto_entry_2 = IntParameter(3, 10, default=3, space='entry', optimize=True)
    auto_entry_down_2 = IntParameter(3, 10, default=3, space='entry', optimize=True)
    auto_entry_bearzzz_2 = IntParameter(3, 10, default=3, space='entry', optimize=True)
    auto_entry_bearzzz_down_2 = IntParameter(3, 10, default=3, space='entry', optimize=True)
    fast_wave_entry = IntParameter(-20, 0, default=-20, space='entry', optimize=True)
    slow_wave_entry = IntParameter(-20, 0, default=-20, space='entry', optimize=True)
    fast_wave_entry_pc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    slow_wave_entry_pc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    entry_smoothing = IntParameter(low=3, high=35, default=15, space='entry', optimize=True)
    # Sell Parameters
    rsi_exit = IntParameter(55, 70, default=50, space='exit', optimize=True)
    rsi_exit_safe = IntParameter(60, 80, default=70, space='exit', optimize=True)
    rsi_ma_exitpc = IntParameter(-5, 5, default=0, space='exit', optimize=True)
    sma200_exit_pc = IntParameter(-5, 5, default=0, space='exit', optimize=True)
    willr_exit = IntParameter(-50, -20, default=-20, space='exit', optimize=True)
    auto_exit_bull = IntParameter(3, 15, default=4, space='exit', optimize=True)
    auto_exit_bear = IntParameter(3, 15, default=4, space='exit', optimize=True)
    fast_wave_exit = IntParameter(-20, 10, default=0, space='exit', optimize=True)
    slow_wave_exit = IntParameter(-20, 10, default=0, space='exit', optimize=True)
    exit_smoothing = IntParameter(low=5, high=35, default=15, space='exit', optimize=True)
    ###  Buy Weight Mulitpliers ###
    x01 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x02 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x03 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x04 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x05 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x06 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x07 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x08 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x09 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    x10 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='entry', optimize=True)
    ###  Sell Weight Mulitpliers ###
    y01 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y02 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y03 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y04 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y05 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y06 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y07 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y08 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y09 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    y10 = DecimalParameter(1.0, 5.0, default=2.5, decimals=1, space='exit', optimize=True)
    #trailing stop loss optimiziation
    tsl_target5 = DecimalParameter(low=0.25, high=0.4, decimals=1, default=0.3, space='exit', optimize=True, load=True)
    ts5 = DecimalParameter(low=0.04, high=0.06, default=0.05, space='exit', optimize=True, load=True)
    tsl_target4 = DecimalParameter(low=0.15, high=0.25, default=0.2, space='exit', optimize=True, load=True)
    ts4 = DecimalParameter(low=0.03, high=0.05, default=0.045, space='exit', optimize=True, load=True)
    tsl_target3 = DecimalParameter(low=0.1, high=0.15, default=0.15, space='exit', optimize=True, load=True)
    ts3 = DecimalParameter(low=0.025, high=0.04, default=0.035, space='exit', optimize=True, load=True)
    tsl_target2 = DecimalParameter(low=0.08, high=0.1, default=0.1, space='exit', optimize=True, load=True)
    ts2 = DecimalParameter(low=0.015, high=0.03, default=0.02, space='exit', optimize=True, load=True)
    tsl_target1 = DecimalParameter(low=0.06, high=0.08, default=0.06, space='exit', optimize=True, load=True)
    ts1 = DecimalParameter(low=0.01, high=0.016, default=0.013, space='exit', optimize=True, load=True)
    tsl_target0 = DecimalParameter(low=0.04, high=0.06, default=0.03, space='exit', optimize=True, load=True)
    ts0 = DecimalParameter(low=0.008, high=0.015, default=0.01, space='exit', optimize=True, load=True)
    ## Optional order time in force.
    order_time_in_force = {'entry': 'gtc', 'exit': 'ioc'}
    # Optimal timeframe for the strategy
    timeframe = '15m'
    informative_timeframe = '2h'
    process_only_new_candles = True
    startup_candle_count = 30
    ### protections ###

    @property
    def protections(self):
        prot = []
        prot.append({'method': 'CooldownPeriod', 'stop_duration_candles': self.cooldown_lookback.value})
        if self.use_stop_protection.value:
            prot.append({'method': 'StoplossGuard', 'lookback_period_candles': 24 * 3, 'trade_limit': 2, 'stop_duration_candles': self.stop_duration.value, 'only_per_pair': False})
        return prot

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs

    def get_informative_indicators(self, metadata: dict):
        dataframe = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.informative_timeframe)
        return dataframe
    ### Dollar Cost Averaging ###
    # This is called when placing the initial order (opening trade)

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float, min_stake: Optional[float], max_stake: float, leverage: float, entry_tag: Optional[str], side: str, **kwargs) -> float:
        # We need to leave most of the funds for possible further DCA orders
        # This also applies to fixed stakes
        return proposed_stake / self.max_dca_multiplier

    def adjust_trade_position(self, trade: Trade, current_time: datetime, current_rate: float, current_profit: float, min_stake: Optional[float], max_stake: float, current_entry_rate: float, current_exit_rate: float, current_entry_profit: float, current_exit_profit: float, **kwargs) -> Optional[float]:
        if current_profit > 0.1 and trade.nr_of_successful_exits == 0:
            # Take half of the profit at +10%
            return -(trade.stake_amount / 2)

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        for stop5 in self.tsl_target5.range:
            if current_profit > stop5:
                for stop5a in self.ts5.range:
                    self.dp.send_msg(f'*** {pair} *** Profit: {current_profit} - lvl5 {stop5}/{stop5a} activated')
                    return stop5a
        for stop4 in self.tsl_target4.range:
            if current_profit > stop4:
                for stop4a in self.ts4.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl4 {stop4}/{stop4a} activated')
                    return stop4a
        for stop3 in self.tsl_target3.range:
            if current_profit > stop3:
                for stop3a in self.ts3.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl3 {stop3}/{stop3a} activated')
                    return stop3a
        for stop2 in self.tsl_target2.range:
            if current_profit > stop2:
                for stop2a in self.ts2.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl2 {stop2}/{stop2a} activated')
                    return stop2a
        for stop1 in self.tsl_target1.range:
            if current_profit > stop1:
                for stop1a in self.ts1.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl1 {stop1}/{stop1a} activated')
                    return stop1a
        for stop0 in self.tsl_target0.range:
            if current_profit > stop0:
                for stop0a in self.ts0.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl0 {stop0}/{stop0a} activated')
                    return stop0a
        return self.stoploss

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.dp:
            inf_tf = '2h'
            pair = metadata['pair']
            informative = self.dp.get_pair_dataframe(pair=pair, timeframe=inf_tf)
            # RSI
            informative['rsi'] = ta.RSI(informative)
            informative['rsi_ma'] = ta.SMA(informative['rsi'], timeperiod=10)
            informative['rsi_ma_pcnt'] = PC(informative, informative['rsi_ma'], informative['rsi_ma'].shift(1))
            # WaveTrend using OHLC4 or HA close - 3/21
            ap = 0.25 * (informative['high'] + informative['low'] + informative['close'] + informative['open'])
            informative['esa'] = ta.EMA(ap, timeperiod=3)
            informative['d'] = ta.EMA(abs(ap - informative['esa']), timeperiod=3)
            informative['wave_ci'] = (ap - informative['esa']) / (0.015 * informative['d'])
            informative['wave_t1'] = ta.EMA(informative['wave_ci'], timeperiod=21)
            informative['wave_t2'] = ta.SMA(informative['wave_t1'], timeperiod=3)
            informative['t1_pc'] = PC(informative, informative['wave_t1'], informative['wave_t1'].shift(1))
            # SMA
            informative['200_SMA'] = ta.SMA(informative['close'], timeperiod=200)
            informative['200_SMAPC'] = PC(informative, informative['200_SMA'], informative['200_SMA'].shift(1))
            informative['from_200'] = ta.SMA(((informative['close'] + informative['open']) / 2 - informative['200_SMA']) / informative['close'] * 100, timeperiod=self.from2.value)
            ### BUYING WEIGHTS ###
            informative.loc[informative['rsi'] < self.rsi_entry.value, 'rsi_entry1'] = 1
            informative.loc[informative['rsi'] > self.rsi_entry.value, 'rsi_entry1'] = -1
            informative.loc[informative['rsi'] > informative['rsi_ma'], 'rsi_entry2'] = 1
            informative.loc[informative['rsi'] < informative['rsi_ma'], 'rsi_entry2'] = -1
            informative.loc[informative['rsi_ma_pcnt'] > self.rsi_ma_entrypc.value, 'rsi_entry3'] = 1
            informative.loc[informative['rsi_ma_pcnt'] < self.rsi_ma_entrypc.value, 'rsi_entry3'] = -1
            informative.loc[informative['rsi'] < self.rsi_entry_safe.value, 'rsi_entry4'] = 1
            informative.loc[informative['rsi'] > self.rsi_entry_safe.value, 'rsi_entry4'] = 0
            informative['rsi_weight'] = (informative['rsi_entry1'] + informative['rsi_entry2'] + informative['rsi_entry3'] + informative['rsi_entry4']) / 4 * self.x01.value
            informative.loc[(informative['close'] > informative['200_SMA']) & (informative['200_SMAPC'] > self.sma200_entry_pc.value), 'sma_entry1'] = 1
            informative.loc[(informative['close'] < informative['200_SMA']) & (informative['200_SMAPC'] > self.sma200_entry_pc.value), 'sma_entry1'] = 1
            informative.loc[(informative['close'] > informative['200_SMA']) & (informative['200_SMAPC'] < self.sma200_entry_pc.value), 'sma_entry1'] = -1
            informative.loc[(informative['close'] < informative['200_SMA']) & (informative['200_SMAPC'] < self.sma200_entry_pc.value), 'sma_entry1'] = -1
            informative.loc[informative['200_SMAPC'] > self.sma200_entry_pc.value, 'sma_entry2'] = 1
            informative.loc[informative['200_SMAPC'] < self.sma200_entry_pc.value, 'sma_entry2'] = -1
            informative['200SMA_weight'] = (informative['sma_entry1'] + informative['sma_entry2']) / 2 * self.x02.value
            informative['from_weight'] = 0  #-((informative['from_200']) * self.x03.value)
            informative.loc[informative['wave_t1'] < self.slow_wave_entry.value, 'wave_entry1'] = 1
            informative.loc[informative['wave_t1'] > self.slow_wave_entry.value, 'wave_entry1'] = -1
            informative.loc[informative['wave_t1'] > informative['wave_t1'].shift(1), 'wave_entry2'] = 1
            informative.loc[informative['wave_t1'] < informative['wave_t1'].shift(1), 'wave_entry2'] = -1
            informative.loc[informative['wave_t1'] > informative['wave_t2'], 'wave_entry3'] = 1
            informative.loc[informative['wave_t1'] < informative['wave_t2'], 'wave_entry3'] = -1
            informative['wave_weight'] = (informative['wave_entry1'] + informative['wave_entry2'] + informative['wave_entry3']) / 3 * self.x04.value
            informative['auto_entry'] = informative[['rsi_weight', 'wave_weight', '200SMA_weight', 'from_weight']].sum(axis=1)
            ### SELLING WEIGHTS ###
            informative.loc[informative['rsi'] > self.rsi_exit.value, 'rsi_exit1'] = 1
            informative.loc[informative['rsi'] < self.rsi_exit.value, 'rsi_exit1'] = -1
            informative.loc[informative['rsi'] < informative['rsi_ma'], 'rsi_exit2'] = 1
            informative.loc[informative['rsi'] > informative['rsi_ma'], 'rsi_exit2'] = -1
            informative.loc[informative['rsi_ma_pcnt'] < self.rsi_ma_exitpc.value, 'rsi_exit3'] = 1
            informative.loc[informative['rsi_ma_pcnt'] > self.rsi_ma_exitpc.value, 'rsi_exit3'] = -1
            informative.loc[informative['rsi'] > self.rsi_exit_safe.value, 'rsi_exit4'] = 1
            informative.loc[informative['rsi'] < self.rsi_exit_safe.value, 'rsi_exit4'] = 0
            informative['rsi_weight'] = (informative['rsi_exit1'] + informative['rsi_exit2'] + informative['rsi_exit3'] + informative['rsi_exit4']) / 4 * self.y01.value
            informative.loc[(informative['close'] > informative['200_SMA']) & (informative['200_SMAPC'] > self.sma200_exit_pc.value), 'sma_exit1'] = -1
            informative.loc[(informative['close'] < informative['200_SMA']) & (informative['200_SMAPC'] > self.sma200_exit_pc.value), 'sma_exit1'] = -1
            informative.loc[(informative['close'] > informative['200_SMA']) & (informative['200_SMAPC'] < self.sma200_exit_pc.value), 'sma_exit1'] = 1
            informative.loc[(informative['close'] < informative['200_SMA']) & (informative['200_SMAPC'] < self.sma200_exit_pc.value), 'sma_exit1'] = 1
            informative.loc[informative['200_SMAPC'] > self.sma200_exit_pc.value, 'sma_exit2'] = -1
            informative.loc[informative['200_SMAPC'] < self.sma200_exit_pc.value, 'sma_exit2'] = 1
            informative['200SMA_weight'] = (informative['sma_exit1'] + informative['sma_exit2']) / 2 * self.y02.value
            informative['from_weight_exit'] = 0  #((informative['from_200']) * self.y03.value)
            informative.loc[informative['wave_t1'] < self.slow_wave_exit.value, 'wave_exit1'] = -1
            informative.loc[informative['wave_t1'] > self.slow_wave_exit.value, 'wave_exit1'] = 1
            informative.loc[informative['wave_t1'] > informative['wave_t1'].shift(1), 'wave_exit2'] = -1
            informative.loc[informative['wave_t1'] < informative['wave_t1'].shift(1), 'wave_exit2'] = 1
            informative.loc[informative['wave_t1'] > informative['wave_t2'], 'wave_exit3'] = -1
            informative.loc[informative['wave_t1'] < informative['wave_t2'], 'wave_exit3'] = 1
            informative['wave_weight'] = (informative['wave_exit1'] + informative['wave_exit2'] + informative['wave_exit3']) / 3 * self.y04.value
            informative['auto_exit'] = informative[['rsi_weight', 'wave_weight', '200SMA_weight', 'from_weight_exit']].sum(axis=1)
            informative['auto_entry_decision'] = informative['auto_entry'] - informative['auto_exit']
            informative['auto_exit_decision'] = informative['auto_exit'] - informative['auto_entry']
        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, inf_tf, ffill=True)
        ### 15m indicators ###
        # WaveTrend using OHLC4 or HA close - 3/21
        ap = 0.25 * (dataframe['high'] + dataframe['low'] + dataframe['close'] + dataframe['open'])
        dataframe['esa'] = ta.EMA(ap, timeperiod=3)
        dataframe['d'] = ta.EMA(abs(ap - dataframe['esa']), timeperiod=3)
        dataframe['wave_ci'] = (ap - dataframe['esa']) / (0.015 * dataframe['d'])
        dataframe['wave_t1'] = ta.EMA(dataframe['wave_ci'], timeperiod=21)
        dataframe['wave_t2'] = ta.SMA(dataframe['wave_t1'], timeperiod=3)
        dataframe['t1_pc'] = PC(dataframe, dataframe['wave_t1'], dataframe['wave_t1'].shift(1))
        # Filter ZEMA
        for length in self.filterlength.range:
            dataframe[f'ema_1{length}'] = ta.EMA(dataframe['close'], timeperiod=length)
            dataframe[f'ema_2{length}'] = ta.EMA(dataframe[f'ema_1{length}'], timeperiod=length)
            dataframe[f'ema_dif{length}'] = dataframe[f'ema_1{length}'] - dataframe[f'ema_2{length}']
            dataframe[f'zema_{length}'] = dataframe[f'ema_1{length}'] + dataframe[f'ema_dif{length}']
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_ma'] = ta.SMA(dataframe['rsi'], timeperiod=10)
        dataframe['rsi_ma_pcnt'] = PC(dataframe, dataframe['rsi_ma'], dataframe['rsi_ma'].shift(1))
        # SMA
        dataframe['200_SMA'] = ta.SMA(dataframe['close'], timeperiod=200)
        dataframe['200_SMAPC'] = PC(dataframe, dataframe['200_SMA'], dataframe['200_SMA'].shift(1))
        # Plot 0
        dataframe['zero'] = 0
        # Williams R%
        dataframe['willr14'] = pta.willr(dataframe['high'], dataframe['low'], dataframe['close'])
        dataframe['willr14PC'] = PC(dataframe, dataframe['willr14'], dataframe['willr14'].shift(1))
        for l in self.max_length.range:
            dataframe['min'] = dataframe['open'].rolling(l).min()
            dataframe['max'] = dataframe['close'].rolling(l).max()
        # distance from 200SMA max
        dataframe['from_200'] = ta.SMA(((dataframe['close'] + dataframe['open']) / 2 - dataframe['200_SMA']) / dataframe['close'] * 100, timeperiod=self.from15.value)
        ### Buying Weights ###
        dataframe.loc[dataframe['rsi'] < self.rsi_entry.value, 'rsi_entry1'] = 1
        dataframe.loc[dataframe['rsi'] > self.rsi_entry.value, 'rsi_entry1'] = -1
        dataframe.loc[dataframe['rsi'] > dataframe['rsi_ma'], 'rsi_entry2'] = 1
        dataframe.loc[dataframe['rsi'] < dataframe['rsi_ma'], 'rsi_entry2'] = -1
        dataframe.loc[dataframe['rsi_ma_pcnt'] > self.rsi_ma_entrypc.value, 'rsi_entry3'] = 1
        dataframe.loc[dataframe['rsi_ma_pcnt'] < self.rsi_ma_entrypc.value, 'rsi_entry3'] = -1
        dataframe.loc[dataframe['rsi'] < self.rsi_entry_safe.value, 'rsi_entry4'] = 1
        dataframe.loc[dataframe['rsi'] > self.rsi_entry_safe.value, 'rsi_entry4'] = 0
        dataframe['rsi_weight'] = (dataframe['rsi_entry1'] + dataframe['rsi_entry2'] + dataframe['rsi_entry3'] + dataframe['rsi_entry4']) / 4 * self.x05.value
        dataframe.loc[(dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_entry_pc.value), 'sma_entry1'] = 1
        dataframe.loc[(dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_entry_pc.value), 'sma_entry1'] = 1
        dataframe.loc[(dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_entry_pc.value), 'sma_entry1'] = -1
        dataframe.loc[(dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_entry_pc.value), 'sma_entry1'] = -1
        dataframe.loc[dataframe['200_SMAPC'] > self.sma200_entry_pc.value, 'sma_entry2'] = 1
        dataframe.loc[dataframe['200_SMAPC'] < self.sma200_entry_pc.value, 'sma_entry2'] = -1
        dataframe['200SMA_weight'] = (dataframe['sma_entry1'] + dataframe['sma_entry2']) / 2 * self.x06.value
        dataframe.loc[dataframe['willr14'] < self.willr_entry.value, 'willr_entry1'] = 1
        dataframe.loc[dataframe['willr14'] > self.willr_entry.value, 'willr_entry1'] = -1
        dataframe.loc[dataframe['willr14'] > -80, 'willr_entry2'] = 1
        dataframe.loc[dataframe['willr14'] < -80, 'willr_entry2'] = -1
        dataframe.loc[dataframe['willr14PC'] > 0, 'willr_entry3'] = 1
        dataframe.loc[dataframe['willr14PC'] < 0, 'willr_entry3'] = -1
        dataframe['willr_weight'] = (dataframe['willr_entry1'] + dataframe['willr_entry2'] + dataframe['willr_entry3']) / 3 * self.x07.value
        dataframe['from_weight'] = -(dataframe['from_200'] * self.x08.value)
        dataframe.loc[dataframe['wave_t1'] < self.fast_wave_entry.value, 'wave_entry1'] = 1
        dataframe.loc[dataframe['wave_t1'] > self.fast_wave_entry.value, 'wave_entry1'] = -1
        dataframe.loc[dataframe['wave_t1'] > dataframe['wave_t1'].shift(1), 'wave_entry2'] = 1
        dataframe.loc[dataframe['wave_t1'] < dataframe['wave_t1'].shift(1), 'wave_entry2'] = -1
        dataframe.loc[dataframe['wave_t1'] > dataframe['wave_t2'], 'wave_entry3'] = 1
        dataframe.loc[dataframe['wave_t1'] < dataframe['wave_t2'], 'wave_entry3'] = -1
        dataframe.loc[(dataframe['wave_t1'] > dataframe['wave_t1_2h']) & (dataframe['wave_t1_2h'] < self.slow_wave_entry.value), 'wave_entry4'] = 1
        dataframe.loc[(dataframe['wave_t1'] < dataframe['wave_t1_2h']) & (dataframe['wave_t1_2h'] < self.slow_wave_entry.value), 'wave_entry4'] = 2
        dataframe['wave_weight'] = (dataframe['wave_entry1'] + dataframe['wave_entry2'] + dataframe['wave_entry3'] + dataframe['wave_entry4']) / 4 * self.x09.value
        dataframe['auto_entry'] = dataframe[['rsi_weight', 'willr_weight', '200SMA_weight', 'from_weight', 'wave_weight']].sum(axis=1)
        ### SELLING ###
        dataframe.loc[dataframe['rsi'] > self.rsi_exit.value, 'rsi_exit1'] = 1
        dataframe.loc[dataframe['rsi'] < self.rsi_exit.value, 'rsi_exit1'] = -1
        dataframe.loc[dataframe['rsi'] > dataframe['rsi_ma'], 'rsi_exit2'] = -1
        dataframe.loc[dataframe['rsi'] < dataframe['rsi_ma'], 'rsi_exit2'] = 1
        dataframe.loc[dataframe['rsi_ma_pcnt'] > self.rsi_ma_exitpc.value, 'rsi_exit3'] = -1
        dataframe.loc[dataframe['rsi_ma_pcnt'] < self.rsi_ma_exitpc.value, 'rsi_exit3'] = 1
        dataframe.loc[dataframe['rsi'] < self.rsi_exit_safe.value, 'rsi_exit4'] = 0
        dataframe.loc[dataframe['rsi'] > self.rsi_exit_safe.value, 'rsi_exit4'] = 1
        dataframe['rsi_weight_exit'] = (dataframe['rsi_exit1'] + dataframe['rsi_exit2'] + dataframe['rsi_exit3'] + dataframe['rsi_exit4']) / 4 * self.y05.value
        dataframe.loc[(dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_exit_pc.value), 'sma_exit1'] = 1
        dataframe.loc[(dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_exit_pc.value), 'sma_exit1'] = 2
        dataframe.loc[(dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_exit_pc.value), 'sma_exit1'] = -2
        dataframe.loc[(dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_exit_pc.value), 'sma_exit1'] = -1
        dataframe.loc[dataframe['200_SMAPC'] > self.sma200_exit_pc.value, 'sma_exit2'] = 1
        dataframe.loc[dataframe['200_SMAPC'] < self.sma200_exit_pc.value, 'sma_exit2'] = -1
        dataframe['200SMA_weight_exit'] = (dataframe['sma_exit1'] + dataframe['sma_exit2']) / 2 * self.y06.value
        dataframe.loc[dataframe['willr14'] < self.willr_exit.value, 'willr_exit1'] = -1
        dataframe.loc[dataframe['willr14'] > self.willr_exit.value, 'willr_exit1'] = 1
        dataframe.loc[dataframe['willr14'] > -10, 'willr_exit2'] = 1
        dataframe.loc[dataframe['willr14'] < -10, 'willr_exit2'] = -1
        dataframe.loc[dataframe['willr14PC'] > 0, 'willr_exit3'] = -1
        dataframe.loc[dataframe['willr14PC'] < 0, 'willr_exit3'] = 1
        dataframe['willr_weight_exit'] = (dataframe['willr_exit1'] + dataframe['willr_exit2'] + dataframe['willr_exit3']) / 3 * self.y07.value
        dataframe['from_weight_exit'] = dataframe['from_200'] * self.y08.value
        dataframe.loc[dataframe['wave_t1'] < self.slow_wave_exit.value, 'wave_exit1'] = -1
        dataframe.loc[dataframe['wave_t1'] > self.slow_wave_exit.value, 'wave_exit1'] = 1
        dataframe.loc[dataframe['wave_t1'] > dataframe['wave_t1'].shift(1), 'wave_exit2'] = -1
        dataframe.loc[dataframe['wave_t1'] < dataframe['wave_t1'].shift(1), 'wave_exit2'] = 1
        dataframe.loc[dataframe['wave_t1'] > dataframe['wave_t2'], 'wave_exit3'] = -1
        dataframe.loc[dataframe['wave_t1'] < dataframe['wave_t2'], 'wave_exit3'] = 1
        dataframe.loc[(dataframe['wave_t1'] > dataframe['wave_t1_2h']) & (dataframe['wave_t1_2h'] > self.slow_wave_exit.value), 'wave_exit4'] = 1
        dataframe.loc[(dataframe['wave_t1'] < dataframe['wave_t1_2h']) & (dataframe['wave_t1_2h'] > self.slow_wave_exit.value), 'wave_exit4'] = 2
        dataframe['wave_weight'] = (dataframe['wave_exit1'] + dataframe['wave_exit2'] + dataframe['wave_exit3'] + dataframe['wave_exit4']) / 4 * self.y09.value
        dataframe['auto_exit'] = dataframe[['rsi_weight_exit', 'willr_weight_exit', '200SMA_weight_exit', 'from_weight_exit']].sum(axis=1)
        # dataframe['auto_entry_decision'] = ta.SMA((dataframe['auto_entry'] - dataframe['auto_exit']), timeperiod=self.entry_smoothing.value)
        # dataframe['auto_exit_decision'] = ta.SMA((dataframe['auto_exit'] - dataframe['auto_entry']), timeperiod=self.exit_smoothing.value)
        dataframe['auto_entry_decision'] = dataframe['auto_entry'] - dataframe['auto_exit']
        dataframe['auto_exit_decision'] = dataframe['auto_exit'] - dataframe['auto_entry']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['auto_entry_decision'] >= self.auto_entry.value) & (dataframe['auto_entry_decision_2h'] >= self.auto_entry_2.value) & (dataframe['auto_entry_decision'] >= dataframe['auto_entry_decision'].shift(1)) & (dataframe['200_SMA_2h'] > dataframe['200_SMA_2h'].shift(8)) & (dataframe['200_SMA'] > dataframe['200_SMA'].shift(1)) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'auto entry bullzzz up')
        dataframe.loc[(dataframe['auto_entry_decision'] >= self.auto_entry.value + self.auto_entry_down.value) & (dataframe['auto_entry_decision_2h'] >= self.auto_entry_2.value + self.auto_entry_down_2.value) & (dataframe['auto_entry_decision'] >= dataframe['auto_entry_decision'].shift(1)) & (dataframe['200_SMA_2h'] > dataframe['200_SMA_2h'].shift(8)) & (dataframe['200_SMA'] < dataframe['200_SMA'].shift(1)) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'auto entry bullzzz down')
        dataframe.loc[(dataframe['auto_entry_decision'] >= self.auto_entry.value + self.auto_entry_bearzzz.value) & (dataframe['auto_entry_decision_2h'] >= self.auto_entry_2.value + self.auto_entry_bearzzz_2.value) & (dataframe['auto_entry_decision'] >= dataframe['auto_entry_decision'].shift(1)) & (dataframe['200_SMA_2h'] < dataframe['200_SMA_2h'].shift(8)) & (dataframe['200_SMA'] > dataframe['200_SMA'].shift(1)) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'auto entry bearzzz up')
        dataframe.loc[(dataframe['auto_entry_decision'] >= self.auto_entry.value + self.auto_entry_bearzzz.value + self.auto_entry_bearzzz_down.value) & (dataframe['auto_entry_decision_2h'] >= self.auto_entry_2.value + self.auto_entry_bearzzz_down_2.value) & (dataframe['auto_entry_decision'] >= dataframe['auto_entry_decision'].shift(1)) & (dataframe['200_SMA_2h'] < dataframe['200_SMA_2h'].shift(8)) & (dataframe['200_SMA'] < dataframe['200_SMA'].shift(1)) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'auto entry bearzzz down')
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['auto_exit_decision'] >= self.auto_exit_bull.value + self.auto_exit_bear.value) & (dataframe['200_SMA_2h'] > dataframe['200_SMA_2h'].shift(8)) & (dataframe['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'auto_exit_bull')
        dataframe.loc[(dataframe['auto_exit_decision'] >= self.auto_exit_bear.value) & (dataframe['200_SMA_2h'] < dataframe['200_SMA_2h'].shift(8)) & (dataframe['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'auto_exit_bear')
        return dataframe