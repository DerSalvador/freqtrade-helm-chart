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
# C.T. 3-9-23
# adding bull/bear detect of 1hr fast ewo
### Change log ###

def EWO(dataframe, ema_length=5, ema2_length=35):
    df = dataframe.copy()
    ema1 = ta.EMA(df, timeperiod=ema_length)
    ema2 = ta.EMA(df, timeperiod=ema2_length)
    emadif = (ema1 - ema2) / df['close'] * 100
    return emadif

def PC(dataframe, in1, in2):
    df = dataframe.copy()
    pc = (in2 - in1) / in1 * 100
    return pc

class eltoro1_4(IStrategy):
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
    # fast ewo
    fastest_ewo = 5
    faster_ewo = 35
    # slow ewo
    fast_ewo = 35
    slow_ewo = 200
    ### Hyperoptable parameters ###
    # protections
    cooldown_lookback = IntParameter(24, 48, default=46, space='protection', optimize=True)
    stop_duration = IntParameter(12, 200, default=5, space='protection', optimize=True)
    use_stop_protection = BooleanParameter(default=True, space='protection', optimize=True)
    # SMAOffset
    base_nb_candles_entry = IntParameter(5, 60, default=25, space='entry', optimize=True)
    base_nb_candles_exit = IntParameter(5, 60, default=49, space='exit', optimize=True)
    low_offset = DecimalParameter(0.9, 0.99, default=0.97, decimals=2, space='entry', optimize=True)
    high_offset = DecimalParameter(1.0, 1.1, default=1.0, decimals=2, space='exit', optimize=True)
    high_offset_2 = DecimalParameter(1.1, 1.5, default=1.3, decimals=2, space='exit', optimize=True)
    filterlength = IntParameter(low=15, high=35, default=25, space='exit', optimize=True)
    max_length = CategoricalParameter([24, 48, 72, 96, 144, 192, 240], default=48, space='entry', optimize=False)
    # Buy Parameters
    ewo_low = IntParameter(-4, -1, default=--1, space='entry', optimize=True)
    ewo_high = IntParameter(0, 4, default=1, space='entry', optimize=True)
    rsi_entry = IntParameter(55, 70, default=65, space='entry', optimize=True)
    rsi_entry_safe = IntParameter(40, 55, default=50, space='entry', optimize=True)
    rsi_ma_entrypc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    EWO_entrypc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    FEWO_entrypc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    sma200_entry_pc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    willr_entry = IntParameter(-50, -20, default=-50, space='entry', optimize=True)
    hma_entry_pc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    macdl_entry_range = DecimalParameter(0.01, 0.03, default=0.01, decimals=2, space='entry', optimize=True)
    macdl_entry_pc = IntParameter(-5, 5, default=0, space='entry', optimize=True)
    auto_entry = IntParameter(5, 15, default=10, space='entry', optimize=True)
    auto_entry_down = IntParameter(5, 15, default=10, space='entry', optimize=True)
    auto_entry_bearzzz = IntParameter(5, 15, default=5, space='entry', optimize=True)
    auto_entry_bearzzz_down = IntParameter(5, 15, default=5, space='entry', optimize=True)
    # Buy Parameters
    rsi_exit = IntParameter(55, 70, default=50, space='exit', optimize=True)
    rsi_exit_safe = IntParameter(60, 80, default=70, space='exit', optimize=True)
    rsi_ma_exitpc = IntParameter(-5, 5, default=0, space='exit', optimize=True)
    EWO_exitpc = IntParameter(-5, 5, default=0, space='exit', optimize=True)
    FEWO_exitpc = IntParameter(-5, 5, default=0, space='exit', optimize=True)
    sma200_exit_pc = IntParameter(-5, 5, default=0, space='exit', optimize=True)
    willr_exit = IntParameter(-50, -20, default=-20, space='exit', optimize=True)
    hma_exit_pc = IntParameter(-5, 5, default=0, space='exit', optimize=True)
    macdl_exit_range = DecimalParameter(0.01, 0.04, default=0.01, decimals=2, space='exit', optimize=True)
    macdl_exit_pc = IntParameter(-5, 5, default=0, space='exit', optimize=True)
    auto_exit_bull = IntParameter(3, 15, default=4, space='exit', optimize=True)
    auto_exit_bear = IntParameter(3, 15, default=4, space='exit', optimize=True)
    ### BTC and Pair EWO values
    bull = DecimalParameter(-0.25, 0.25, default=0, space='entry', decimals=2, optimize=True)
    estop = DecimalParameter(-0.5, 0, default=-0.5, space='exit', decimals=2, optimize=True)
    ###  Buy Weight Mulitpliers ###
    x1 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x2 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x3 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x4 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x5 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x6 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x7 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x8 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x9 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    x10 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='entry', optimize=True)
    ###  Sell Weight Mulitpliers ###
    y1 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y2 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y3 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y4 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y5 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y6 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y7 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y8 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y9 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
    y10 = DecimalParameter(0.3, 5.0, default=1, decimals=1, space='exit', optimize=True)
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
    timeframe = '1h'
    informative_timeframe = '4h'
    process_only_new_candles = True
    startup_candle_count = 79
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
        pairs += ['BTC/USDT']
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
            # Take half of the profit at +5%
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
            inf_tf = '4h'
            pair = metadata['pair']
            print(pair)
            informative = self.dp.get_pair_dataframe(pair=f'BTC/USDT', timeframe=inf_tf)
            informative_pair = self.dp.get_pair_dataframe(pair=pair, timeframe=inf_tf)
            informative['INFEWO'] = EWO(informative_pair, 5, 35)
            # BTC EWO 5/35
            informative['BTC_EWO_Fast'] = EWO(informative, 5, 35)
            informative['BTC_EWO_ PC'] = PC(informative, informative['BTC_EWO_Fast'], informative['BTC_EWO_Fast'].shift(1))
        ### Changed this part ###
        # if np.where(informative['BTC_EWO_Fast'] > self.bull.value and informative['BTC_EWO_Fast'].shift(1) < self.bull.value, 1, 0) == 1:
        #     self.dp.send_msg(f"MARKET STATUS: Bear is gone! Lets F00kInG GOOOOO!!!", always_send=True)
        #     print("MARKET STATUS: Bear is gone! Lets F00kInG GOOOOO!!!")
        # elif np.where(informative['BTC_EWO_Fast'] < self.bull.value and informative['BTC_EWO_Fast'].shift(1) > self.bull.value, 1, 0) == 1:
        #     self.dp.send_msg(f"MARKET STATUS: Bear Lurking! Grab the Lube, This could hurt...", always_send=True)
        #     print("MARKET STATUS: Bear Lurking! Grab the Lube, This could hurt...")
        # elif np.where(informative['BTC_EWO_Fast'] < self.estop.value and informative['BTC_EWO_Fast'].shift(1) > self.estop.value, 1, 0) == 1:
        #     self.dp.send_msg(f"MARKET STATUS: ABANDON SHIP!!!", always_send=True)
        #     print("MARKET STATUS: ABANDON SHIP!!!")
        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, inf_tf, ffill=True)
        ### 5m indicators ###
        # Filter ZEMA
        for length in self.filterlength.range:
            dataframe[f'ema_1{length}'] = ta.EMA(dataframe['close'], timeperiod=length)
            dataframe[f'ema_2{length}'] = ta.EMA(dataframe[f'ema_1{length}'], timeperiod=length)
            dataframe[f'ema_dif{length}'] = dataframe[f'ema_1{length}'] - dataframe[f'ema_2{length}']
            dataframe[f'zema_{length}'] = dataframe[f'ema_1{length}'] + dataframe[f'ema_dif{length}']
        # Pivot Points
        pivots = pivots_points.pivots_points(dataframe)
        dataframe['pivot'] = pivots['pivot']
        dataframe['s1'] = pivots['s1']
        dataframe['r1'] = pivots['r1']
        dataframe['s2'] = pivots['s2']
        dataframe['r2'] = pivots['r2']
        dataframe['s3'] = pivots['s3']
        dataframe['r3'] = pivots['r3']
        dataframe['r3-dif'] = (dataframe['r3'] - dataframe['r2']) / 4
        dataframe['r2.25'] = dataframe['r2'] + dataframe['r3-dif']
        dataframe['r2.50'] = dataframe['r2'] + dataframe['r3-dif'] * 2
        dataframe['r2.75'] = dataframe['r2'] + dataframe['r3-dif'] * 3
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_ma'] = ta.SMA(dataframe['rsi'], timeperiod=10)
        dataframe['rsi_ma_pcnt'] = PC(dataframe, dataframe['rsi_ma'], dataframe['rsi_ma'].shift(1))
        # HMA
        dataframe['hma_50'] = qtpylib.hull_moving_average(dataframe['close'], window=50)
        dataframe['hma_50_pc'] = PC(dataframe, dataframe['hma_50'], dataframe['hma_50'].shift(1))
        # SMA
        dataframe['200_SMA'] = ta.SMA(dataframe['close'], timeperiod=200)
        dataframe['200_SMAPC'] = PC(dataframe, dataframe['200_SMA'], dataframe['200_SMA'].shift(1))
        # Plot 0
        dataframe['zero'] = 0
        # Calculate all ma_entry values
        for val in self.base_nb_candles_entry.range:
            dataframe[f'ma_entry_{val}'] = ta.EMA(dataframe, timeperiod=val)
        # Calculate all ma_exit values
        for val in self.base_nb_candles_exit.range:
            dataframe[f'ma_exit_{val}'] = ta.EMA(dataframe, timeperiod=val)
        # Lazy Bear's Macd Lead
        dataframe['sema'] = ta.EMA(dataframe['close'], timeperiod=8)
        dataframe['lema'] = ta.EMA(dataframe['close'], timeperiod=18)
        dataframe['i1'] = dataframe['sema'] + ta.EMA(dataframe['close'] - dataframe['sema'], timeperiod=8)
        dataframe['i2'] = dataframe['lema'] + ta.EMA(dataframe['close'] - dataframe['lema'], timeperiod=18)
        dataframe['macdlead'] = dataframe['i1'] - dataframe['i2']
        dataframe['macdl'] = dataframe['sema'] - dataframe['lema']
        dataframe['macdl_sig'] = ta.SMA(dataframe['macdl'], period=5)
        dataframe['macdlead_pc'] = round((dataframe['macdlead'].shift() - dataframe['macdlead']) / abs(dataframe['macdlead'].shift()) * -100, 2)
        # Elliot
        dataframe['EWO'] = EWO(dataframe, self.fast_ewo, self.slow_ewo)
        dataframe['FEWO'] = EWO(dataframe, self.fastest_ewo, self.faster_ewo)
        dataframe['EWO_PC'] = PC(dataframe, dataframe['EWO'], dataframe['EWO'].shift(1))
        dataframe['FEWO_PC'] = PC(dataframe, dataframe['FEWO'], dataframe['FEWO'].shift(1))
        # Williams R%
        dataframe['willr14'] = pta.willr(dataframe['high'], dataframe['low'], dataframe['close'])
        dataframe['willr14PC'] = PC(dataframe, dataframe['willr14'], dataframe['willr14'].shift(1))
        for l in self.max_length.range:
            dataframe['min'] = dataframe['open'].rolling(l).min()
            dataframe['max'] = dataframe['close'].rolling(l).max()
        # distance from the rolling max in percent
        dataframe['from_200'] = ta.SMA(((dataframe['close'] + dataframe['open']) / 2 - dataframe['200_SMA']) / dataframe['close'] * 100, timeperiod=5)
        ### Buying Weights ###
        dataframe.loc[dataframe['rsi'] < self.rsi_entry.value, 'rsi_entry1'] = 1
        dataframe.loc[dataframe['rsi'] > self.rsi_entry.value, 'rsi_entry1'] = -1
        dataframe.loc[dataframe['rsi'] > dataframe['rsi_ma'], 'rsi_entry2'] = 1
        dataframe.loc[dataframe['rsi'] < dataframe['rsi_ma'], 'rsi_entry2'] = -1
        dataframe.loc[dataframe['rsi_ma_pcnt'] > self.rsi_ma_entrypc.value, 'rsi_entry3'] = 1
        dataframe.loc[dataframe['rsi_ma_pcnt'] < self.rsi_ma_entrypc.value, 'rsi_entry3'] = -1
        dataframe.loc[dataframe['rsi'] < self.rsi_entry_safe.value, 'rsi_entry4'] = 2
        dataframe.loc[dataframe['rsi'] > self.rsi_entry_safe.value, 'rsi_entry4'] = 0
        dataframe['rsi_weight'] = (dataframe['rsi_entry1'] + dataframe['rsi_entry2'] + dataframe['rsi_entry3'] + dataframe['rsi_entry4']) / 4 * self.x1.value
        dataframe.loc[(dataframe['FEWO'] > dataframe['EWO']) & (dataframe['FEWO'].shift(1) < dataframe['EWO'].shift(1)), 'ewo_entry1'] = 1
        dataframe.loc[(dataframe['FEWO'] < dataframe['EWO']) & (dataframe['FEWO'].shift(1) > dataframe['EWO'].shift(1)), 'ewo_entry1'] = -1
        dataframe.loc[dataframe['FEWO_PC'] > self.FEWO_entrypc.value, 'ewo_entry2'] = 2
        dataframe.loc[dataframe['FEWO_PC'] < self.FEWO_entrypc.value, 'ewo_entry2'] = -2
        dataframe.loc[(dataframe['FEWO'] > self.bull.value) & (dataframe['FEWO'] < self.ewo_high.value), 'ewo_entry3'] = 2
        dataframe.loc[(dataframe['FEWO'] < self.bull.value) & (dataframe['FEWO'] > self.ewo_high.value), 'ewo_entry3'] = -1
        dataframe.loc[(dataframe['FEWO'] > self.ewo_low.value) & (dataframe['FEWO'] < self.bull.value), 'ewo_entry4'] = 1
        dataframe.loc[dataframe['FEWO'] < self.ewo_low.value, 'ewo_entry4'] = 0
        dataframe.loc[dataframe['FEWO'] < self.ewo_low.value, 'ewo_entry5'] = 1
        dataframe.loc[dataframe['FEWO'] > self.ewo_low.value, 'ewo_entry5'] = 0
        dataframe.loc[(dataframe['EWO'] > self.bull.value) & (dataframe['EWO'] < self.ewo_high.value), 'ewo_entry6'] = 1
        dataframe.loc[(dataframe['EWO'] < self.bull.value) & (dataframe['EWO'] > self.ewo_high.value), 'ewo_entry6'] = 0
        dataframe.loc[(dataframe['EWO'] < self.ewo_high.value) & (dataframe['EWO'] > self.bull.value), 'ewo_entry7'] = 1
        dataframe.loc[dataframe['EWO'] > self.ewo_high.value, 'ewo_entry7'] = 0
        dataframe.loc[(dataframe['EWO'] < self.ewo_low.value) & (dataframe['EWO_PC'] > self.EWO_entrypc.value), 'ewo_entry8'] = 2
        dataframe.loc[(dataframe['EWO'] > self.ewo_low.value) & (dataframe['EWO_PC'] > self.EWO_entrypc.value), 'ewo_entry8'] = 0
        dataframe.loc[dataframe['EWO_PC'] > self.EWO_entrypc.value, 'ewo_entry9'] = 1
        dataframe.loc[dataframe['EWO_PC'] < self.EWO_entrypc.value, 'ewo_entry9'] = -1
        dataframe['fewo_weight'] = (dataframe['ewo_entry1'] + dataframe['ewo_entry2'] + dataframe['ewo_entry3'] + dataframe['ewo_entry4'] + dataframe['ewo_entry5']) / 5 * self.x2.value
        dataframe['ewo_weight'] = (dataframe['ewo_entry6'] + dataframe['ewo_entry7'] + dataframe['ewo_entry8'] + dataframe['ewo_entry9']) / 4 * self.x3.value
        dataframe.loc[(dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_entry_pc.value), 'sma_entry1'] = 1
        dataframe.loc[(dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_entry_pc.value), 'sma_entry1'] = 2
        dataframe.loc[(dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_entry_pc.value), 'sma_entry1'] = -1
        dataframe.loc[(dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_entry_pc.value), 'sma_entry1'] = -1
        dataframe.loc[dataframe['200_SMAPC'] > self.sma200_entry_pc.value, 'sma_entry2'] = 1
        dataframe.loc[dataframe['200_SMAPC'] < self.sma200_entry_pc.value, 'sma_entry2'] = -1
        dataframe.loc[(dataframe['hma_50'] > dataframe['200_SMA']) & (dataframe['hma_50'].shift(1) < dataframe['200_SMA'].shift(1)), 'sma_entry3'] = 2
        dataframe.loc[(dataframe['hma_50'] > dataframe['200_SMA']) & (dataframe['hma_50'] > self.hma_entry_pc.value), 'sma_entry3'] = 1
        dataframe['200SMA_weight'] = (dataframe['sma_entry1'] + dataframe['sma_entry2'] + dataframe['sma_entry3']) / 3 * self.x4.value
        dataframe.loc[dataframe['willr14'] < self.willr_entry.value, 'willr_entry1'] = 1
        dataframe.loc[dataframe['willr14'] > self.willr_entry.value, 'willr_entry1'] = -1
        dataframe.loc[dataframe['willr14'] > -80, 'willr_entry2'] = 1
        dataframe.loc[dataframe['willr14'] < -80, 'willr_entry2'] = -1
        dataframe.loc[dataframe['willr14PC'] > 0, 'willr_entry3'] = 1
        dataframe.loc[dataframe['willr14PC'] < 0, 'willr_entry3'] = -1
        dataframe['willr_weight'] = (dataframe['willr_entry1'] + dataframe['willr_entry2'] + dataframe['willr_entry3']) / 3 * self.x5.value
        dataframe.loc[dataframe['close'] > dataframe['hma_50'], 'hma_entry1'] = 1
        dataframe.loc[dataframe['close'] < dataframe['hma_50'], 'hma_entry1'] = -1
        dataframe.loc[(dataframe['hma_50_pc'] > self.hma_entry_pc.value) & (dataframe['hma_50'] > dataframe['200_SMA']), 'hma_entry2'] = 1
        dataframe.loc[(dataframe['hma_50_pc'] < self.hma_entry_pc.value) & (dataframe['hma_50'] > dataframe['200_SMA']), 'hma_entry2'] = -1
        dataframe['hma_weight'] = (dataframe['hma_entry1'] + dataframe['hma_entry2']) / 2 * self.x6.value
        dataframe.loc[dataframe['close'] < dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset.value, 'base_ma_entry1'] = 1
        dataframe.loc[dataframe['close'] > dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset.value, 'base_ma_entry'] = -1
        dataframe.loc[dataframe['close'] < dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'], 'base_ma_entry2'] = 1
        dataframe.loc[dataframe['close'] > dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'], 'base_ma_entry2'] = -1
        dataframe['base_ma_entry_weight'] = (dataframe['base_ma_entry1'] + dataframe['base_ma_entry2']) / 2 * self.x7.value
        dataframe.loc[dataframe['macdl'] > dataframe['macdl_sig'], 'macdl_entry1'] = 1
        dataframe.loc[dataframe['macdl'] < dataframe['macdl_sig'], 'macdl_entry1'] = -1
        dataframe.loc[dataframe['macdlead'] > -(self.macdl_entry_range.value * dataframe['close']), 'macdl_entry2'] = 1
        dataframe.loc[dataframe['macdlead'] < -(self.macdl_entry_range.value * dataframe['close']), 'macdl_entry2'] = -1
        dataframe.loc[dataframe['macdlead'] < self.macdl_entry_range.value * dataframe['close'], 'macdl_entry3'] = 1
        dataframe.loc[dataframe['macdlead'] > self.macdl_entry_range.value * dataframe['close'], 'macdl_entry3'] = -1
        dataframe.loc[dataframe['macdlead_pc'] > self.macdl_entry_pc.value, 'macdl_entry4'] = 1
        dataframe.loc[dataframe['macdlead_pc'] < self.macdl_entry_pc.value, 'macdl_entry4'] = -1
        dataframe['macdl_weight'] = (dataframe['macdl_entry1'] + dataframe['macdl_entry2'] + dataframe['macdl_entry3'] + dataframe['macdl_entry4']) / 4 * self.x8.value
        dataframe.loc[dataframe['s2'] > dataframe['close'], 'pivot_entry1'] = 1
        dataframe.loc[dataframe['s2'] < dataframe['close'], 'pivot_entry1'] = 0
        dataframe.loc[dataframe['s3'] > dataframe['close'], 'pivot_entry2'] = 2
        dataframe.loc[dataframe['s3'] < dataframe['close'], 'pivot_entry2'] = 0
        dataframe.loc[dataframe['s2'] < dataframe['hma_50'], 'pivot_entry3'] = 0
        dataframe.loc[dataframe['s2'] > dataframe['hma_50'], 'pivot_entry3'] = 1
        dataframe.loc[dataframe['s3'] < dataframe['hma_50'], 'pivot_entry4'] = 0
        dataframe.loc[dataframe['s3'] > dataframe['hma_50'], 'pivot_entry4'] = 2
        dataframe.loc[(dataframe['r2'] < dataframe['hma_50']) & (dataframe['r3'] > dataframe['hma_50']) & (dataframe['hma_50'] > self.hma_entry_pc.value), 'pivot_entry5'] = 2
        dataframe.loc[(dataframe['r2'] < dataframe['hma_50']) & (dataframe['r3'] > dataframe['hma_50']) & (dataframe['hma_50'] < self.hma_entry_pc.value), 'pivot_entry5'] = 0
        dataframe.loc[dataframe['r3'] < dataframe['hma_50'], 'pivot_entry6'] = -3
        dataframe.loc[dataframe['r3'] > dataframe['hma_50'], 'pivot_entry6'] = 0
        dataframe['pivot_weight'] = (dataframe['pivot_entry1'] + dataframe['pivot_entry2'] + dataframe['pivot_entry3'] + dataframe['pivot_entry4'] + dataframe['pivot_entry5'] + dataframe['pivot_entry6']) / 4 * self.x9.value
        dataframe['from_weight'] = -(dataframe['from_200'] * self.x10.value)
        dataframe['auto_entry'] = dataframe[['rsi_weight', 'fewo_weight', 'ewo_weight', 'willr_weight', 'hma_weight', 'base_ma_entry_weight', 'macdl_weight', '200SMA_weight', 'pivot_weight', 'from_weight']].sum(axis=1)
        ### SELLING ###
        dataframe.loc[dataframe['rsi'] < self.rsi_exit.value, 'rsi_exit1'] = 1
        dataframe.loc[dataframe['rsi'] > self.rsi_exit.value, 'rsi_exit1'] = -1
        dataframe.loc[dataframe['rsi'] > dataframe['rsi_ma'], 'rsi_exit2'] = -1
        dataframe.loc[dataframe['rsi'] < dataframe['rsi_ma'], 'rsi_exit2'] = 1
        dataframe.loc[dataframe['rsi_ma_pcnt'] > self.rsi_ma_exitpc.value, 'rsi_exit3'] = -1
        dataframe.loc[dataframe['rsi_ma_pcnt'] < self.rsi_ma_exitpc.value, 'rsi_exit3'] = 1
        dataframe.loc[dataframe['rsi'] < self.rsi_exit_safe.value, 'rsi_exit4'] = -1
        dataframe.loc[dataframe['rsi'] > self.rsi_exit_safe.value, 'rsi_exit4'] = 1
        dataframe['rsi_weight_exit'] = (dataframe['rsi_exit1'] + dataframe['rsi_exit2'] + dataframe['rsi_exit3'] + dataframe['rsi_exit4']) / 4 * self.y1.value
        dataframe.loc[(dataframe['FEWO'] > dataframe['EWO']) & (dataframe['FEWO'].shift(1) < dataframe['EWO'].shift(1)), 'ewo_exit1'] = -1
        dataframe.loc[(dataframe['FEWO'] < dataframe['EWO']) & (dataframe['FEWO'].shift(1) > dataframe['EWO'].shift(1)), 'ewo_exit1'] = 1
        dataframe.loc[dataframe['FEWO_PC'] > self.FEWO_exitpc.value, 'ewo_exit2'] = -2
        dataframe.loc[dataframe['FEWO_PC'] < self.FEWO_exitpc.value, 'ewo_exit2'] = 2
        dataframe.loc[(dataframe['FEWO'] > self.bull.value) & (dataframe['FEWO'] < self.ewo_high.value), 'ewo_exit3'] = -1
        dataframe.loc[(dataframe['FEWO'] < self.bull.value) & (dataframe['FEWO'] > self.ewo_high.value), 'ewo_exit3'] = 1
        dataframe.loc[(dataframe['FEWO'] > self.ewo_low.value) & (dataframe['FEWO'] < self.bull.value), 'ewo_exit4'] = 1
        dataframe.loc[dataframe['FEWO'] < self.ewo_low.value, 'ewo_exit4'] = -1
        dataframe.loc[dataframe['FEWO'] < self.ewo_low.value, 'ewo_exit5'] = 1
        dataframe.loc[dataframe['FEWO'] > self.ewo_low.value, 'ewo_exit5'] = 0
        dataframe.loc[(dataframe['EWO'] > self.bull.value) & (dataframe['EWO'] < self.ewo_high.value), 'ewo_exit6'] = 1
        dataframe.loc[(dataframe['EWO'] < self.bull.value) & (dataframe['EWO'] > self.ewo_high.value), 'ewo_exit6'] = 1
        dataframe.loc[dataframe['EWO'] < self.ewo_high.value, 'ewo_exit7'] = 1
        dataframe.loc[dataframe['EWO'] > self.ewo_high.value, 'ewo_exit7'] = 0
        dataframe.loc[(dataframe['EWO'] < self.ewo_low.value) & (dataframe['EWO_PC'] > self.EWO_exitpc.value), 'ewo_exit8'] = 0
        dataframe.loc[(dataframe['EWO'] > self.ewo_low.value) & (dataframe['EWO_PC'] > self.EWO_exitpc.value), 'ewo_exit8'] = 1
        dataframe.loc[dataframe['EWO_PC'] > self.EWO_exitpc.value, 'ewo_exit9'] = -1
        dataframe.loc[dataframe['EWO_PC'] < self.EWO_exitpc.value, 'ewo_exit9'] = 1
        dataframe['fewo_weight_exit'] = (dataframe['ewo_exit1'] + dataframe['ewo_exit2'] + dataframe['ewo_exit3'] + dataframe['ewo_exit4'] + dataframe['ewo_exit5']) / 5 * self.y2.value
        dataframe['ewo_weight_exit'] = (dataframe['ewo_exit6'] + dataframe['ewo_exit7'] + dataframe['ewo_exit8'] + dataframe['ewo_exit9']) / 4 * self.y3.value
        dataframe.loc[(dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_exit_pc.value), 'sma_exit1'] = -1
        dataframe.loc[(dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_exit_pc.value), 'sma_exit1'] = -2
        dataframe.loc[(dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_exit_pc.value), 'sma_exit1'] = 2
        dataframe.loc[(dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_exit_pc.value), 'sma_exit1'] = 1
        dataframe.loc[dataframe['200_SMAPC'] > self.sma200_exit_pc.value, 'sma_exit2'] = -1
        dataframe.loc[dataframe['200_SMAPC'] < self.sma200_exit_pc.value, 'sma_exit2'] = 1
        dataframe.loc[(dataframe['hma_50'] < dataframe['200_SMA']) & (dataframe['hma_50'].shift(1) > dataframe['200_SMA'].shift(1)), 'sma_exit3'] = 1
        dataframe.loc[(dataframe['hma_50'] > dataframe['200_SMA']) & (dataframe['hma_50'] < self.hma_exit_pc.value), 'sma_exit3'] = 2
        dataframe['200SMA_weight_exit'] = (dataframe['sma_exit1'] + dataframe['sma_exit2'] + dataframe['sma_exit3']) / 3 * self.y4.value
        dataframe.loc[dataframe['willr14'] < self.willr_exit.value, 'willr_exit1'] = -1
        dataframe.loc[dataframe['willr14'] > self.willr_exit.value, 'willr_exit1'] = 1
        dataframe.loc[dataframe['willr14'] > -10, 'willr_exit2'] = 1
        dataframe.loc[dataframe['willr14'] < -10, 'willr_exit2'] = -1
        dataframe.loc[dataframe['willr14PC'] > 0, 'willr_exit3'] = -1
        dataframe.loc[dataframe['willr14PC'] < 0, 'willr_exit3'] = 1
        dataframe['willr_weight_exit'] = (dataframe['willr_exit1'] + dataframe['willr_exit2'] + dataframe['willr_exit3']) / 3 * self.y5.value
        dataframe.loc[dataframe['close'] > dataframe['hma_50'], 'hma_exit1'] = -2
        dataframe.loc[dataframe['close'] < dataframe['hma_50'], 'hma_exit1'] = 2
        dataframe.loc[dataframe['hma_50_pc'] > self.hma_exit_pc.value, 'hma_exit2'] = -1
        dataframe.loc[dataframe['hma_50_pc'] < self.hma_exit_pc.value, 'hma_exit2'] = 1
        dataframe['hma_weight_exit'] = (dataframe['hma_exit1'] + dataframe['hma_exit2']) / 2 * self.y6.value
        dataframe.loc[dataframe['close'] < dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value, 'base_ma_exit1'] = -1
        dataframe.loc[dataframe['close'] > dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value, 'base_ma_exit'] = 1
        dataframe.loc[dataframe['close'] < dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset_2.value, 'base_ma_exit2'] = -1
        dataframe.loc[dataframe['close'] > dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset_2.value, 'base_ma_exit2'] = 1
        dataframe['base_ma_exit_weight'] = (dataframe['base_ma_exit1'] + dataframe['base_ma_exit2']) / 2 * self.y7.value
        dataframe.loc[dataframe['macdl'] > dataframe['macdl_sig'], 'macdl_exit1'] = -1
        dataframe.loc[dataframe['macdl'] < dataframe['macdl_sig'], 'macdl_exit1'] = 1
        dataframe.loc[dataframe['macdlead'] > -(self.macdl_exit_range.value * dataframe['close']), 'macdl_exit2'] = 1
        dataframe.loc[dataframe['macdlead'] < -(self.macdl_exit_range.value * dataframe['close']), 'macdl_exit2'] = -1
        dataframe.loc[dataframe['macdlead'] < self.macdl_exit_range.value * dataframe['close'], 'macdl_exit3'] = 1
        dataframe.loc[dataframe['macdlead'] > self.macdl_exit_range.value * dataframe['close'], 'macdl_exit3'] = -1
        dataframe.loc[dataframe['macdlead_pc'] > self.macdl_exit_pc.value, 'macdl_exit4'] = -1
        dataframe.loc[dataframe['macdlead_pc'] < self.macdl_exit_pc.value, 'macdl_exit4'] = 1
        dataframe['macdl_weight_exit'] = (dataframe['macdl_exit1'] + dataframe['macdl_exit2'] + dataframe['macdl_exit3'] + dataframe['macdl_exit4']) / 4 * self.y8.value
        dataframe.loc[dataframe['r1'] > dataframe['close'], 'pivot_exit1'] = 0
        dataframe.loc[dataframe['r1'] < dataframe['close'], 'pivot_exit1'] = 0.5
        dataframe.loc[dataframe['r2'] > dataframe['close'], 'pivot_exit2'] = 0
        dataframe.loc[dataframe['r2'] < dataframe['close'], 'pivot_exit2'] = 0.5
        dataframe.loc[dataframe['r2.50'] < dataframe['hma_50'], 'pivot_exit3'] = -0.5
        dataframe.loc[dataframe['r2.50'] > dataframe['hma_50'], 'pivot_exit3'] = 0.5
        dataframe.loc[dataframe['r2.75'] < dataframe['hma_50'], 'pivot_exit4'] = -0.5
        dataframe.loc[dataframe['r2.75'] > dataframe['hma_50'], 'pivot_exit4'] = 0.5
        dataframe.loc[(dataframe['r2'] < dataframe['hma_50']) & (dataframe['r3'] > dataframe['hma_50']) & (dataframe['hma_50'] > self.hma_exit_pc.value), 'pivot_exit5'] = 0
        dataframe.loc[(dataframe['r2'] < dataframe['hma_50']) & (dataframe['r3'] > dataframe['hma_50']) & (dataframe['hma_50'] < self.hma_exit_pc.value), 'pivot_exit5'] = 1
        dataframe.loc[dataframe['r3'] < dataframe['hma_50'], 'pivot_exit6'] = 0
        dataframe.loc[dataframe['r3'] > dataframe['hma_50'], 'pivot_exit6'] = 1
        dataframe['pivot_weight_exit'] = (dataframe['pivot_exit1'] + dataframe['pivot_exit2'] + dataframe['pivot_exit3'] + dataframe['pivot_exit4'] + dataframe['pivot_exit5'] + dataframe['pivot_exit6']) / 4 * self.y9.value
        dataframe['from_weight_exit'] = dataframe['from_200'] * self.y10.value
        dataframe['auto_exit'] = dataframe[['rsi_weight_exit', 'fewo_weight_exit', 'ewo_weight_exit', 'willr_weight_exit', 'hma_weight_exit', 'base_ma_exit_weight', 'macdl_weight_exit', '200SMA_weight_exit', 'pivot_weight_exit', 'from_weight_exit']].sum(axis=1)
        dataframe['auto_entry_decision'] = ta.SMA(dataframe['auto_entry'] - dataframe['auto_exit'], timeperiod=2)
        dataframe['auto_exit_decision'] = ta.SMA(dataframe['auto_exit'] - dataframe['auto_entry'], timeperiod=2)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # (qtpylib.crossed_above(dataframe['auto_entry_decision'], self.auto_entry.value)) &
        dataframe.loc[(dataframe['auto_entry_decision'] >= self.auto_entry.value) & (dataframe['BTC_EWO_Fast_4h'] >= self.bull.value) & (dataframe['BTC_EWO_Fast_4h'] > dataframe['BTC_EWO_Fast_4h'].shift(1)) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'auto entry bullzzz up')
        # (qtpylib.crossed_above(dataframe['auto_entry_decision'], (self.auto_entry.value + self.auto_entry_down.value))) &
        dataframe.loc[(dataframe['auto_entry_decision'] >= self.auto_entry.value + self.auto_entry_down.value) & (dataframe['BTC_EWO_Fast_4h'] >= self.bull.value) & (dataframe['BTC_EWO_Fast_4h'] <= dataframe['BTC_EWO_Fast_4h'].shift(1)) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'auto entry bullzzz down')
        # (qtpylib.crossed_above(dataframe['auto_entry_decision'], (self.auto_entry.value + self.auto_entry_bearzzz.value))) &
        dataframe.loc[(dataframe['auto_entry_decision'] >= self.auto_entry.value + self.auto_entry_bearzzz.value) & (dataframe['BTC_EWO_Fast_4h'] < self.bull.value) & (dataframe['BTC_EWO_Fast_4h'] > dataframe['BTC_EWO_Fast_4h'].shift(1)) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'auto entry bearzzz up')
        # (qtpylib.crossed_above(dataframe['auto_entry_decision'], (self.auto_entry.value + self.auto_entry_bearzzz.value + self.auto_entry_bearzzz_down.value))) &
        dataframe.loc[(dataframe['auto_entry_decision'] >= self.auto_entry.value + self.auto_entry_bearzzz.value + self.auto_entry_bearzzz_down.value) & (dataframe['BTC_EWO_Fast_4h'] < self.bull.value) & (dataframe['BTC_EWO_Fast_4h'] <= dataframe['BTC_EWO_Fast_4h'].shift(1)) & (dataframe['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'auto entry bearzzz down')
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['auto_exit_decision'] >= self.auto_exit_bull.value + self.auto_exit_bear.value) & (dataframe['close'] < dataframe['hma_50']) & (dataframe['BTC_EWO_Fast_4h'] < self.bull.value) & (dataframe['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'auto_exit_bull')
        dataframe.loc[(dataframe['auto_exit_decision'] >= self.auto_exit_bear.value) & (dataframe['close'] < dataframe['hma_50']) & (dataframe['BTC_EWO_Fast_4h'] > self.bull.value) & (dataframe['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'auto_exit_bear')
        return dataframe
# ============================================================== BACKTESTING REPORT =============================================================
# |       Pair |   Entries |   Avg Profit % |   Cum Profit % |   Tot Profit USDT |   Tot Profit % |      Avg Duration |   Win  Draw  Loss  Win% |
# |------------+-----------+----------------+----------------+-------------------+----------------+-------------------+-------------------------|
# | YFDAI/USDT |         8 |           6.22 |          49.79 |           196.096 |          19.61 |  3 days, 18:52:00 |     8     0     0   100 |
# |  EOSC/USDT |         5 |           9.47 |          47.33 |           157.313 |          15.73 |    1 day, 2:48:00 |     5     0     0   100 |
# |  CSPR/USDT |         6 |           5.36 |          32.16 |           110.362 |          11.04 |   1 day, 18:20:00 |     6     0     0   100 |
# |   TRU/USDT |         2 |          10.75 |          21.49 |            91.047 |           9.10 |   7 days, 3:00:00 |     2     0     0   100 |
# |  OSMO/USDT |         5 |           4.16 |          20.79 |            83.699 |           8.37 |  3 days, 14:48:00 |     4     0     1  80.0 |
# |   LDO/USDT |         5 |           3.75 |          18.75 |            69.986 |           7.00 |   3 days, 9:12:00 |     5     0     0   100 |
# |  VELO/USDT |         5 |           5.13 |          25.64 |            66.246 |           6.62 |          12:24:00 |     5     0     0   100 |
# |  OPUL/USDT |         4 |           5.36 |          21.45 |            61.578 |           6.16 |    1 day, 2:30:00 |     4     0     0   100 |
# |   ENJ/USDT |         2 |           7.10 |          14.20 |            60.915 |           6.09 |          21:30:00 |     2     0     0   100 |
# |  KLAY/USDT |         3 |           5.39 |          16.17 |            60.073 |           6.01 |   4 days, 8:00:00 |     3     0     0   100 |
# |  ORAI/USDT |         3 |           5.55 |          16.66 |            56.659 |           5.67 |          23:20:00 |     3     0     0   100 |
# |    OP/USDT |         2 |           5.60 |          11.21 |            53.396 |           5.34 |    1 day, 0:00:00 |     2     0     0   100 |
# | GALAX/USDT |         3 |           5.03 |          15.09 |            52.418 |           5.24 |           8:40:00 |     3     0     0   100 |
# |  ATOM/USDT |         4 |           2.37 |           9.47 |            50.111 |           5.01 |  4 days, 18:30:00 |     3     0     1  75.0 |
# |  DYDX/USDT |         3 |           3.91 |          11.73 |            49.893 |           4.99 |   3 days, 9:20:00 |     3     0     0   100 |
# |  AGIX/USDT |         3 |           4.40 |          13.21 |            49.035 |           4.90 |   4 days, 7:00:00 |     3     0     0   100 |
# | JASMY/USDT |         3 |           4.60 |          13.80 |            45.034 |           4.50 |   4 days, 0:20:00 |     3     0     0   100 |
# |   XDC/USDT |         5 |           2.23 |          11.13 |            39.592 |           3.96 |   1 day, 23:12:00 |     5     0     0   100 |
# |   AKT/USDT |         6 |           3.41 |          20.48 |            37.443 |           3.74 |  3 days, 14:20:00 |     5     0     1  83.3 |
# |  LUNC/USDT |         2 |           4.74 |           9.48 |            36.080 |           3.61 |   4 days, 3:30:00 |     2     0     0   100 |
# |   APT/USDT |         3 |           2.79 |           8.38 |            35.385 |           3.54 |  3 days, 12:00:00 |     3     0     0   100 |
# |   FIL/USDT |         2 |           3.63 |           7.27 |            33.453 |           3.35 |           5:00:00 |     2     0     0   100 |
# |  LINK/USDT |         3 |           2.61 |           7.83 |            32.468 |           3.25 |   8 days, 0:40:00 |     3     0     0   100 |
# |   ETC/USDT |         2 |           5.75 |          11.50 |            32.347 |           3.23 |          20:00:00 |     2     0     0   100 |
# |  COMP/USDT |         2 |           4.56 |           9.12 |            31.862 |           3.19 |  2 days, 23:00:00 |     2     0     0   100 |
# |   ETH/USDT |         2 |           3.25 |           6.50 |            31.230 |           3.12 |   6 days, 8:30:00 |     2     0     0   100 |
# |   GMX/USDT |         2 |           5.82 |          11.64 |            31.221 |           3.12 |    1 day, 6:00:00 |     2     0     0   100 |
# |   XRP/USDT |         3 |           3.07 |           9.21 |            28.977 |           2.90 |          16:00:00 |     3     0     0   100 |
# |  RNDR/USDT |         1 |           5.80 |           5.80 |            28.858 |           2.89 |           5:00:00 |     1     0     0   100 |
# |   ZEC/USDT |         3 |           2.84 |           8.51 |            26.970 |           2.70 |   1 day, 21:40:00 |     3     0     0   100 |
# |  HBAR/USDT |         2 |           2.81 |           5.62 |            25.982 |           2.60 |   1 day, 16:30:00 |     2     0     0   100 |
# |  SCRT/USDT |         2 |           3.55 |           7.09 |            25.207 |           2.52 |  2 days, 11:30:00 |     2     0     0   100 |
# |   IMX/USDT |         4 |           1.94 |           7.78 |            24.663 |           2.47 |  3 days, 16:45:00 |     4     0     0   100 |
# |  KAVA/USDT |         1 |           5.16 |           5.16 |            23.317 |           2.33 |           9:00:00 |     1     0     0   100 |
# |  EGLD/USDT |         1 |           4.74 |           4.74 |            21.670 |           2.17 |           7:00:00 |     1     0     0   100 |
# |   QNT/USDT |         4 |           1.64 |           6.56 |            18.340 |           1.83 | 15 days, 17:00:00 |     3     0     1  75.0 |
# |   VET/USDT |         1 |           4.54 |           4.54 |            17.988 |           1.80 |          10:00:00 |     1     0     0   100 |
# | THETA/USDT |         1 |           5.11 |           5.11 |            17.533 |           1.75 |          23:00:00 |     1     0     0   100 |
# |   ADA/USDT |         2 |           3.01 |           6.01 |            16.461 |           1.65 |  5 days, 23:30:00 |     2     0     0   100 |
# |  AVAX/USDT |         1 |           5.66 |           5.66 |            15.738 |           1.57 |          17:00:00 |     1     0     0   100 |
# |  DOGE/USDT |         1 |           5.60 |           5.60 |            15.316 |           1.53 |   1 day, 23:00:00 |     1     0     0   100 |
# |   TRX/USDT |         2 |           1.86 |           3.72 |            11.669 |           1.17 |  6 days, 23:00:00 |     2     0     0   100 |
# |  IOTA/USDT |         1 |           1.94 |           1.94 |            11.413 |           1.14 |   2 days, 3:00:00 |     1     0     0   100 |
# |   UNI/USDT |         1 |           2.17 |           2.17 |            11.105 |           1.11 |   1 day, 10:00:00 |     1     0     0   100 |
# |  AGLD/USDT |         1 |           4.67 |           4.67 |            10.974 |           1.10 |    1 day, 2:00:00 |     1     0     0   100 |
# |   APE/USDT |         2 |           1.25 |           2.51 |            10.320 |           1.03 |   2 days, 2:30:00 |     2     0     0   100 |
# | MATIC/USDT |         2 |           1.42 |           2.83 |             9.626 |           0.96 |  4 days, 21:00:00 |     2     0     0   100 |
# |   XTZ/USDT |         1 |           1.82 |           1.82 |             9.397 |           0.94 |  3 days, 16:00:00 |     1     0     0   100 |
# |   XLM/USDT |         1 |           1.07 |           1.07 |             4.525 |           0.45 |   8 days, 9:00:00 |     1     0     0   100 |
# |   FTM/USDT |         1 |           0.66 |           0.66 |             2.712 |           0.27 |  6 days, 21:00:00 |     1     0     0   100 |
# |   BTC/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |   INJ/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |   DOT/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |   GRT/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |   SOL/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |  ANKR/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |   FET/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |   BAT/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |   YFI/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# | SUSHI/USDT |         0 |           0.00 |           0.00 |             0.000 |           0.00 |              0:00 |     0     0     0     0 |
# |  ALGO/USDT |         1 |          -0.46 |          -0.46 |            -2.258 |          -0.23 |   1 day, 19:00:00 |     0     0     1     0 |
# |   FLR/USDT |         7 |           0.88 |           6.18 |            -6.514 |          -0.65 |  7 days, 22:34:00 |     5     0     2  71.4 |
# |   EWT/USDT |         6 |           0.73 |           4.39 |           -15.501 |          -1.55 |  3 days, 23:10:00 |     5     0     1  83.3 |
# |   CTI/USDT |         5 |           0.29 |           1.47 |           -17.998 |          -1.80 |  3 days, 10:48:00 |     4     0     1  80.0 |
# |  ROSE/USDT |         1 |         -11.40 |         -11.40 |           -65.481 |          -6.55 |  25 days, 7:00:00 |     0     0     1     0 |
# |   RLY/USDT |         6 |          -1.36 |          -8.17 |           -83.647 |          -8.36 |   4 days, 8:20:00 |     5     0     1  83.3 |
# | OCEAN/USDT |         2 |         -10.46 |         -20.92 |           -94.414 |          -9.44 |  5 days, 18:30:00 |     1     0     1  50.0 |
# |   EOS/USDT |         3 |          -6.51 |         -19.54 |          -126.953 |         -12.70 |   7 days, 4:20:00 |     2     0     1  66.7 |
# |  NEAR/USDT |         3 |         -10.73 |         -32.20 |          -149.278 |         -14.93 | 14 days, 11:40:00 |     1     0     2  33.3 |
# |      TOTAL |       168 |           2.92 |         490.40 |          1481.657 |         148.17 |  3 days, 22:47:00 |   153     0    15  91.1 |
# ==================================================================== ENTER TAG STATS ====================================================================
# |                   TAG |   Entries |   Avg Profit % |   Cum Profit % |   Tot Profit USDT |   Tot Profit % |     Avg Duration |   Win  Draw  Loss  Win% |
# |-----------------------+-----------+----------------+----------------+-------------------+----------------+------------------+-------------------------|
# | auto entry bullzzz down |       111 |           3.04 |         337.23 |          1016.378 |         101.64 | 3 days, 19:39:00 |   100     0    11  90.1 |
# |   auto entry bullzzz up |        31 |           4.22 |         130.95 |           374.487 |          37.45 |  3 days, 6:04:00 |    30     0     1  96.8 |
# |   auto entry bearzzz up |         5 |           6.30 |          31.51 |           132.902 |          13.29 |  2 days, 0:36:00 |     5     0     0   100 |
# | auto entry bearzzz down |        21 |          -0.44 |          -9.30 |           -42.111 |          -4.21 |  6 days, 2:57:00 |    18     0     3  85.7 |
# |                 TOTAL |       168 |           2.92 |         490.40 |          1481.657 |         148.17 | 3 days, 22:47:00 |   153     0    15  91.1 |
# ======================================================= EXIT REASON STATS ========================================================
# |        Exit Reason |   Exits |   Win  Draws  Loss  Win% |   Avg Profit % |   Cum Profit % |   Tot Profit USDT |   Tot Profit % |
# |--------------------+---------+--------------------------+----------------+----------------+-------------------+----------------|
# | trailing_stop_loss |      92 |     82     0    10  89.1 |           3.41 |         313.46 |           844.302 |          62.69 |
# |     auto_exit_bear |      61 |     61     0     0   100 |           2.08 |         126.82 |           475.353 |          25.36 |
# |     auto_exit_bull |       7 |      7     0     0   100 |           2.47 |          17.26 |            73.632 |           3.45 |
# |         force_exit |       5 |      0     0     5     0 |          -6.32 |         -31.58 |          -163.778 |          -6.32 |
# |                roi |       3 |      3     0     0   100 |          21.48 |          64.44 |           252.148 |          12.89 |
# ========================================================== LEFT OPEN TRADES REPORT ===========================================================
# |      Pair |   Entries |   Avg Profit % |   Cum Profit % |   Tot Profit USDT |   Tot Profit % |      Avg Duration |   Win  Draw  Loss  Win% |
# |-----------+-----------+----------------+----------------+-------------------+----------------+-------------------+-------------------------|
# | ALGO/USDT |         1 |          -0.46 |          -0.46 |            -2.258 |          -0.23 |   1 day, 19:00:00 |     0     0     1     0 |
# | ATOM/USDT |         1 |          -1.56 |          -1.56 |            -7.898 |          -0.79 | 12 days, 20:00:00 |     0     0     1     0 |
# |  QNT/USDT |         1 |          -2.79 |          -2.79 |           -16.350 |          -1.63 | 46 days, 17:00:00 |     0     0     1     0 |
# | ROSE/USDT |         1 |         -11.40 |         -11.40 |           -65.481 |          -6.55 |  25 days, 7:00:00 |     0     0     1     0 |
# | NEAR/USDT |         1 |         -15.36 |         -15.36 |           -71.792 |          -7.18 | 29 days, 18:00:00 |     0     0     1     0 |
# |     TOTAL |         5 |          -6.32 |         -31.58 |          -163.778 |         -16.38 |  23 days, 6:36:00 |     0     0     5     0 |
# ================== SUMMARY METRICS ==================
# | Metric                      | Value               |
# |-----------------------------+---------------------|
# | Backtesting from            | 2023-01-01 00:00:00 |
# | Backtesting to              | 2023-05-31 00:00:00 |
# | Max open trades             | 5                   |
# |                             |                     |
# | Total/Daily Avg Trades      | 168 / 1.12          |
# | Starting balance            | 1000 USDT           |
# | Final balance               | 2481.657 USDT       |
# | Absolute profit             | 1481.657 USDT       |
# | Total profit %              | 148.17%             |
# | CAGR %                      | 813.14%             |
# | Profit factor               | 2.23                |
# | Trades per day              | 1.12                |
# | Avg. daily profit %         | 0.99%               |
# | Avg. stake amount           | 391.806 USDT        |
# | Total trade volume          | 65823.426 USDT      |
# |                             |                     |
# | Best Pair                   | YFDAI/USDT 49.79%   |
# | Worst Pair                  | NEAR/USDT -32.20%   |
# | Best trade                  | TRU/USDT 21.48%     |
# | Worst trade                 | EOS/USDT -24.47%    |
# | Best day                    | 154.86 USDT         |
# | Worst day                   | -163.778 USDT       |
# | Days win/draw/lose          | 70 / 70 / 10        |
# | Avg. Duration Winners       | 2 days, 14:46:00    |
# | Avg. Duration Loser         | 17 days, 13:20:00   |
# | Rejected Entry signals      | 174472              |
# | Entry/Exit Timeouts         | 0 / 0               |
# |                             |                     |
# | Min balance                 | 1013.404 USDT       |
# | Max balance                 | 3030.23 USDT        |
# | Max % of account underwater | 18.10%              |
# | Absolute Drawdown (Account) | 18.10%              |
# | Absolute Drawdown           | 548.573 USDT        |
# | Drawdown high               | 2030.23 USDT        |
# | Drawdown low                | 1481.657 USDT       |
# | Drawdown Start              | 2023-04-16 21:00:00 |
# | Drawdown End                | 2023-05-31 00:00:00 |
# | Market change               | 71.41%              |
# =====================================================
# 2023-06-20 16:41:50,933 - freqtrade.resolvers.iresolver - WARNING - Could not import /home/jared/freq/user_data/strategies/EWOGPT.py due to 'name 'DataFrame' is not defined'
# 2023-06-20 16:41:50,942 - freqtrade.resolvers.iresolver - WARNING - Could not import /home/jared/freq/user_data/strategies/nveztr.py due to 'invalid syntax (nveztr.py, line 386)'
# 2023-06-20 16:41:50,943 - freqtrade.resolvers.iresolver - WARNING - Could not import /home/jared/freq/user_data/strategies/NASOSv5.py due to 'name 'TrailingBuySellStrat' is not defined'
# 2023-06-20 16:41:50,958 - NFIX - INFO - pandas_ta successfully imported
# 2023-06-20 16:41:50,979 - freqtrade.optimize.hyperopt_tools - INFO - Dumping parameters to /home/jared/freq/user_data/strategies/eltoro1_4.json
# Epoch details:
#    934/1000:    168 trades. 153/0/15 Wins/Draws/Losses. Avg profit   2.92%. Median profit   4.55%. Total profit 1481.65664574 USDT ( 148.17%). Avg duration 3 days, 22:47:00 min. Objective: -1481.65665
#     # Buy hyperspace params:
#     entry_params = {
#         "EWO_entrypc": 4,
#         "FEWO_entrypc": 4,
#         "auto_entry": 6,
#         "auto_entry_bearzzz": 12,
#         "auto_entry_bearzzz_down": 8,
#         "auto_entry_down": 8,
#         "base_nb_candles_entry": 16,
#         "bull": 0.15,
#         "ewo_high": 2,
#         "ewo_low": -3,
#         "hma_entry_pc": 4,
#         "low_offset": 0.94,
#         "macdl_entry_pc": 4,
#         "macdl_entry_range": 0.02,
#         "rsi_entry": 67,
#         "rsi_entry_safe": 48,
#         "rsi_ma_entrypc": 2,
#         "sma200_entry_pc": 1,
#         "willr_entry": -34,
#         "x1": 3.1,
#         "x10": 1.9,
#         "x2": 3.8,
#         "x3": 1.6,
#         "x4": 3.7,
#         "x5": 0.6,
#         "x6": 1.7,
#         "x7": 0.9,
#         "x8": 3.3,
#         "x9": 1.8,
#         "max_length": 48,  # value loaded from strategy
#     }
#     # Sell hyperspace params:
#     exit_params = {
#         "EWO_exitpc": -5,
#         "FEWO_exitpc": -5,
#         "auto_exit_bear": 6,
#         "auto_exit_bull": 3,
#         "base_nb_candles_exit": 35,
#         "estop": -0.3,
#         "filterlength": 25,
#         "high_offset": 1.0,
#         "high_offset_2": 1.17,
#         "hma_exit_pc": -3,
#         "macdl_exit_pc": 2,
#         "macdl_exit_range": 0.02,
#         "rsi_ma_exitpc": 0,
#         "rsi_exit": 60,
#         "rsi_exit_safe": 70,
#         "sma200_exit_pc": 3,
#         "ts0": 0.013,
#         "ts1": 0.011,
#         "ts2": 0.028,
#         "ts3": 0.028,
#         "ts4": 0.03,
#         "ts5": 0.041,
#         "tsl_target0": 0.058,
#         "tsl_target1": 0.062,
#         "tsl_target2": 0.094,
#         "tsl_target3": 0.133,
#         "tsl_target4": 0.206,
#         "tsl_target5": 0.4,
#         "willr_exit": -23,
#         "y1": 3.8,
#         "y10": 0.4,
#         "y2": 2.2,
#         "y3": 4.3,
#         "y4": 1.4,
#         "y5": 4.1,
#         "y6": 0.8,
#         "y7": 3.8,
#         "y8": 4.4,
#         "y9": 3.5,
#     }
#     # Protection hyperspace params:
#     protection_params = {
#         "cooldown_lookback": 46,  # value loaded from strategy
#         "stop_duration": 5,  # value loaded from strategy
#         "use_stop_protection": True,  # value loaded from strategy
#     }
#     # ROI table:  # value loaded from strategy
#     minimal_roi = {
#         "0": 0.215
#     }
#     # Stoploss:
#     stoploss = -0.25  # value loaded from strategy
#     # Trailing stop:
#     trailing_stop = False  # value loaded from strategy
#     trailing_stop_positive = None  # value loaded from strategy
#     trailing_stop_positive_offset = 0.0  # value loaded from strategy
#     trailing_only_offset_is_reached = False  # value loaded from strategy
#  