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
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter, 
                                IStrategy, IntParameter, RealParameter, merge_informative_pair)
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
    pc = ((in2-in1)/in1) * 100
    return pc

class eltoro(IStrategy):

    ### Strategy parameters ###
    exit_profit_only = True ### No exiting at a loss
    use_custom_stoploss = True
    trailing_stop = False # True
    ignore_roi_if_entry_signal = True
    use_exit_signal = True
    stoploss = -0.25
    # DCA Parameters
    position_adjustment_enable = True
    max_entry_position_adjustment = 0
    max_dca_multiplier = 1
    market_status = 0
    minimal_roi = {
        "0": 0.215,

    }

    # fast ewo
    fastest_ewo = 5
    faster_ewo = 35

    # slow ewo
    fast_ewo = 35
    slow_ewo = 200

    ### Hyperoptable parameters ###

    # protections
    cooldown_lookback = IntParameter(24, 48, default=46, space="protection", optimize=True)
    stop_duration = IntParameter(12, 200, default=5, space="protection", optimize=True)
    use_stop_protection = BooleanParameter(default=True, space="protection", optimize=True)

    # SMAOffset
    base_nb_candles_entry = IntParameter(5, 60, default=25, space='entry', optimize=True)
    base_nb_candles_exit = IntParameter(5, 60, default=49, space='exit', optimize=True)
    low_offset = DecimalParameter(0.9, 0.99, default=0.97, decimals=2, space='entry', optimize=True)
    high_offset = DecimalParameter(1.0, 1.1, default=1.00,  decimals=2, space='exit', optimize=True)
    high_offset_2 = DecimalParameter(1.1, 1.5, default=1.3, decimals=2, space='exit', optimize=True)   
    filterlength = IntParameter(low=15, high=35, default=25, space='exit', optimize=True)
    max_length = CategoricalParameter([24, 48, 72, 96, 144, 192, 240], default=48, space="entry", optimize=False)

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
    auto_entry = IntParameter(5, 10, default=8, space='entry', optimize=True)
    auto_entry_bearzzz = IntParameter(1, 15, default=2, space='entry', optimize=True)

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
    auto_exit = IntParameter(3, 10, default=4, space='exit', optimize=True)

    ### BTC and Pair EWO values
    bull = DecimalParameter(-0.25, 0.25, default=0, space='entry',decimals=2, optimize=True)
    estop = DecimalParameter(-0.5, 0, default=-0.5, space='exit',decimals=2, optimize=True)

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
    tsl_target3 = DecimalParameter(low=0.08, high=0.15, default=0.15, space='exit', optimize=True, load=True)
    ts3 = DecimalParameter(low=0.025, high=0.04, default=0.035, space='exit', optimize=True, load=True)
    tsl_target2 = DecimalParameter(low=0.06, high=0.08, default=0.1, space='exit', optimize=True, load=True)
    ts2 = DecimalParameter(low=0.015, high=0.03, default=0.02, space='exit', optimize=True, load=True)
    tsl_target1 = DecimalParameter(low=0.04, high=0.06, default=0.06, space='exit', optimize=True, load=True)
    ts1 = DecimalParameter(low=0.01, high=0.016, default=0.013, space='exit', optimize=True, load=True)
    tsl_target0 = DecimalParameter(low=0.02, high=0.04, default=0.03, space='exit', optimize=True, load=True)
    ts0 = DecimalParameter(low=0.008, high=0.015, default=0.01, space='exit', optimize=True, load=True)

    ## Optional order time in force.
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'ioc'
    }

    # Optimal timeframe for the strategy
    timeframe = '15m'
    informative_timeframe = '1h'

    process_only_new_candles = True
    startup_candle_count = 79
    
    ### protections ###
    @property
    def protections(self):
        prot = []

        prot.append({
            "method": "CooldownPeriod",
            "stop_duration_candles": self.cooldown_lookback.value
        })
        if self.use_stop_protection.value:
            prot.append({
                "method": "StoplossGuard",
                "lookback_period_candles": 24 * 3,
                "trade_limit": 2,
                "stop_duration_candles": self.stop_duration.value,
                "only_per_pair": False
            })

        return prot

    def informative_pairs(self):

        pairs = self.dp.current_whitelist()
        pairs += ['BTC/USDT']
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs

    def get_informative_indicators(self, metadata: dict):

        dataframe = self.dp.get_pair_dataframe(
            pair=metadata['pair'], timeframe=self.informative_timeframe)

        return dataframe

    ### Dollar Cost Averaging ###
    # This is called when placing the initial order (opening trade)
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:

        # We need to leave most of the funds for possible further DCA orders
        # This also applies to fixed stakes
        return proposed_stake / self.max_dca_multiplier 

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:

        if current_profit > 0.10 and trade.nr_of_successful_exits == 0:
            # Take half of the profit at +5%
            return -(trade.stake_amount / 2)

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:

        for stop5 in self.tsl_target5.range:
            if (current_profit > stop5):
                for stop5a in self.ts5.range:
                    self.dp.send_msg(f'*** {pair} *** Profit: {current_profit} - lvl5 {stop5}/{stop5a} activated')
                    return stop5a 
        for stop4 in self.tsl_target4.range:
            if (current_profit > stop4):
                for stop4a in self.ts4.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl4 {stop4}/{stop4a} activated')
                    return stop4a 
        for stop3 in self.tsl_target3.range:
            if (current_profit > stop3):
                for stop3a in self.ts3.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl3 {stop3}/{stop3a} activated')
                    return stop3a 
        for stop2 in self.tsl_target2.range:
            if (current_profit > stop2):
                for stop2a in self.ts2.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl2 {stop2}/{stop2a} activated')
                    return stop2a 
        for stop1 in self.tsl_target1.range:
            if (current_profit > stop1):
                for stop1a in self.ts1.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl1 {stop1}/{stop1a} activated')
                    return stop1a 
        for stop0 in self.tsl_target0.range:
            if (current_profit > stop0):
                for stop0a in self.ts0.range:
                    self.dp.send_msg(f'*** {pair} *** Profit {current_profit} - lvl0 {stop0}/{stop0a} activated')
                    return stop0a 

        return self.stoploss

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        if self.dp:
            inf_tf = '1h'
            informative = self.dp.get_pair_dataframe(pair=f"BTC/USDT", timeframe=inf_tf)
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
        dataframe['r2.50'] = dataframe['r2'] + (dataframe['r3-dif'] * 2) 
        dataframe['r2.75'] = dataframe['r2'] + (dataframe['r3-dif'] * 3)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_ma'] = ta.SMA(dataframe['rsi'], timeperiod=10)
        dataframe['rsi_ma_pcnt'] = PC(dataframe, dataframe['rsi_ma'], dataframe['rsi_ma'].shift(1))

        # HMA
        dataframe['hma_50'] = qtpylib.hull_moving_average(dataframe['close'], window=50)
        dataframe['hma_50_pc'] = PC(dataframe, dataframe['hma_50'], dataframe['hma_50'].shift(1))

        # SMA
        dataframe['200_SMA'] = ta.SMA(dataframe["close"], timeperiod = 200)
        dataframe['200_SMAPC'] = PC(dataframe, dataframe['200_SMA'], dataframe['200_SMA'].shift(1) )

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
        dataframe['i2'] = dataframe['lema'] + ta.EMA(dataframe['close']  - dataframe['lema'], timeperiod=18)
        dataframe['macdlead'] = dataframe['i1'] - dataframe['i2']
        dataframe['macdl'] = dataframe['sema'] - dataframe['lema']
        dataframe['macdl_sig'] = ta.SMA(dataframe['macdl'], period=5)
        dataframe["macdlead_pc"] = round((dataframe["macdlead"].shift() - dataframe["macdlead"]) / abs(dataframe["macdlead"].shift()) * -100, 2)
        

        # Elliot
        dataframe['EWO'] = EWO(dataframe, self.fast_ewo, self.slow_ewo)
        dataframe['FEWO'] = EWO(dataframe, self.fastest_ewo, self.faster_ewo)
        dataframe['EWO_PC'] = PC(dataframe, dataframe['EWO'], dataframe['EWO'].shift(1))
        dataframe['FEWO_PC'] = PC(dataframe, dataframe['FEWO'], dataframe['FEWO'].shift(1))

        # Williams R%
        dataframe['willr14'] = pta.willr(dataframe['high'], dataframe['low'], dataframe['close'])
        dataframe['willr14PC'] = PC(dataframe, dataframe['willr14'], dataframe['willr14'].shift(1) )

        for l in self.max_length.range:
            dataframe['min'] = dataframe['open'].rolling(l).min()
            dataframe['max'] = dataframe['close'].rolling(l).max()

        # distance from the rolling max in percent
        dataframe['from_200'] = ta.SMA(((((dataframe['close'] + dataframe['open']) / 2) - dataframe['200_SMA']) / dataframe['close']) * 100, timeperiod=5)

        ### Buying Weights ###
        dataframe.loc[(dataframe['rsi']<self.rsi_entry.value), 'rsi_entry1'] = 1
        dataframe.loc[(dataframe['rsi']>self.rsi_entry.value), 'rsi_entry1'] = -1

        dataframe.loc[(dataframe['rsi']>dataframe['rsi_ma']), 'rsi_entry2'] = 1
        dataframe.loc[(dataframe['rsi']<dataframe['rsi_ma']), 'rsi_entry2'] = -1
        
        dataframe.loc[(dataframe['rsi_ma_pcnt']>self.rsi_ma_entrypc.value), 'rsi_entry3'] = 1
        dataframe.loc[(dataframe['rsi_ma_pcnt']<self.rsi_ma_entrypc.value), 'rsi_entry3'] = -1
        
        dataframe.loc[(dataframe['rsi']<self.rsi_entry_safe.value), 'rsi_entry4'] = 2
        dataframe.loc[(dataframe['rsi']>self.rsi_entry_safe.value), 'rsi_entry4'] = 0

        dataframe['rsi_weight'] = (
            (dataframe['rsi_entry1']+dataframe['rsi_entry2']+dataframe['rsi_entry3']+dataframe['rsi_entry4'])/4) * self.x1.value


        dataframe.loc[((dataframe['FEWO'] > dataframe['EWO']) & (dataframe['FEWO'].shift(1) < dataframe['EWO'].shift(1))), 'ewo_entry1'] = 1
        dataframe.loc[((dataframe['FEWO'] < dataframe['EWO']) & (dataframe['FEWO'].shift(1) > dataframe['EWO'].shift(1))), 'ewo_entry1'] = -1

        dataframe.loc[(dataframe['FEWO_PC'] > self.FEWO_entrypc.value), 'ewo_entry2'] = 2
        dataframe.loc[(dataframe['FEWO_PC'] < self.FEWO_entrypc.value), 'ewo_entry2'] = -2

        dataframe.loc[((dataframe['FEWO'] > self.bull.value) & (dataframe['FEWO'] < self.ewo_high.value)), 'ewo_entry3'] = 2
        dataframe.loc[((dataframe['FEWO'] < self.bull.value) & (dataframe['FEWO'] > self.ewo_high.value)), 'ewo_entry3'] = -1

        dataframe.loc[((dataframe['FEWO'] > self.ewo_low.value) & (dataframe['FEWO'] < self.bull.value)), 'ewo_entry4'] = 1
        dataframe.loc[(dataframe['FEWO'] < self.ewo_low.value), 'ewo_entry4'] = 0

        dataframe.loc[(dataframe['FEWO'] < self.ewo_low.value), 'ewo_entry5'] = 1
        dataframe.loc[(dataframe['FEWO'] > self.ewo_low.value), 'ewo_entry5'] = 0

        dataframe.loc[((dataframe['EWO'] > self.bull.value) & (dataframe['EWO'] < self.ewo_high.value)), 'ewo_entry6'] = 1
        dataframe.loc[((dataframe['EWO'] < self.bull.value) & (dataframe['EWO'] > self.ewo_high.value)), 'ewo_entry6'] = 0

        dataframe.loc[((dataframe['EWO'] < self.ewo_high.value) & (dataframe['EWO'] > self.bull.value)), 'ewo_entry7'] = 1
        dataframe.loc[(dataframe['EWO'] > self.ewo_high.value), 'ewo_entry7'] = 0

        dataframe.loc[(dataframe['EWO'] < self.ewo_low.value) & (dataframe['EWO_PC'] > self.EWO_entrypc.value), 'ewo_entry8'] = 2
        dataframe.loc[(dataframe['EWO'] > self.ewo_low.value) & (dataframe['EWO_PC'] > self.EWO_entrypc.value), 'ewo_entry8'] = 0

        dataframe.loc[(dataframe['EWO_PC'] > self.EWO_entrypc.value), 'ewo_entry9'] = 1
        dataframe.loc[(dataframe['EWO_PC'] < self.EWO_entrypc.value), 'ewo_entry9'] = -1

        dataframe['fewo_weight'] = ((dataframe['ewo_entry1']+dataframe['ewo_entry2']+dataframe['ewo_entry3']+dataframe['ewo_entry4']+dataframe['ewo_entry5'])/5) * self.x2.value
        dataframe['ewo_weight'] = ((dataframe['ewo_entry6']+dataframe['ewo_entry7']+dataframe['ewo_entry8']+dataframe['ewo_entry9'])/4) * self.x3.value

        dataframe.loc[((dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_entry_pc.value)), 'sma_entry1'] = 1
        dataframe.loc[((dataframe['close'] < dataframe['200_SMA'])& (dataframe['200_SMAPC'] > self.sma200_entry_pc.value)), 'sma_entry1'] = 2
        dataframe.loc[((dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_entry_pc.value)), 'sma_entry1'] = -1
        dataframe.loc[((dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_entry_pc.value)), 'sma_entry1'] = -1

        dataframe.loc[(dataframe['200_SMAPC'] > self.sma200_entry_pc.value), 'sma_entry2'] = 1
        dataframe.loc[(dataframe['200_SMAPC'] < self.sma200_entry_pc.value), 'sma_entry2'] = -1
        
        dataframe.loc[(dataframe['hma_50'] > dataframe['200_SMA']) & (dataframe['hma_50'].shift(1) < dataframe['200_SMA'].shift(1)), 'sma_entry3'] = 2
        dataframe.loc[(dataframe['hma_50'] > dataframe['200_SMA']) & (dataframe['hma_50'] > self.hma_entry_pc.value) , 'sma_entry3'] = 1

        dataframe['200SMA_weight'] = ((dataframe['sma_entry1']+dataframe['sma_entry2']+dataframe['sma_entry3'])/3) * self.x4.value

        dataframe.loc[(dataframe['willr14'] < self.willr_entry.value), 'willr_entry1'] = 1
        dataframe.loc[(dataframe['willr14'] > self.willr_entry.value), 'willr_entry1'] = -1

        dataframe.loc[(dataframe['willr14'] > -80), 'willr_entry2'] = 1
        dataframe.loc[(dataframe['willr14'] < -80), 'willr_entry2'] = -1
        
        dataframe.loc[(dataframe['willr14PC'] > 0), 'willr_entry3'] = 1
        dataframe.loc[(dataframe['willr14PC'] < 0), 'willr_entry3'] = -1

        dataframe['willr_weight'] = ((dataframe['willr_entry1']+dataframe['willr_entry2']+dataframe['willr_entry3'])/3) * self.x5.value

        dataframe.loc[(dataframe['close'] > dataframe['hma_50']), 'hma_entry1'] = -1
        dataframe.loc[(dataframe['close'] < dataframe['hma_50']), 'hma_entry1'] = 1

        dataframe.loc[(dataframe['hma_50_pc'] > self.hma_entry_pc.value) & (dataframe['hma_50'] > dataframe['200_SMA']), 'hma_entry2'] = 1
        dataframe.loc[(dataframe['hma_50_pc'] < self.hma_entry_pc.value) & (dataframe['hma_50'] > dataframe['200_SMA']), 'hma_entry2'] = -1

        dataframe['hma_weight'] = ((dataframe['hma_entry1']+dataframe['hma_entry2'])/2) * self.x6.value

        dataframe.loc[(dataframe['close'] < (dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset.value)), 'base_ma_entry1'] = 1
        dataframe.loc[(dataframe['close'] > (dataframe[f'ma_entry_{self.base_nb_candles_entry.value}'] * self.low_offset.value)), 'base_ma_entry'] = -1

        dataframe.loc[(dataframe['close'] < dataframe[f'ma_entry_{self.base_nb_candles_entry.value}']), 'base_ma_entry2'] = 1
        dataframe.loc[(dataframe['close'] > dataframe[f'ma_entry_{self.base_nb_candles_entry.value}']), 'base_ma_entry2'] = -1

        dataframe['base_ma_entry_weight'] = ((dataframe['base_ma_entry1'] + dataframe['base_ma_entry2'])/2) * self.x7.value

        dataframe.loc[(dataframe['macdl'] > dataframe['macdl_sig']), 'macdl_entry1'] = 1
        dataframe.loc[(dataframe['macdl'] < dataframe['macdl_sig']), 'macdl_entry1'] = -1

        dataframe.loc[(dataframe['macdlead'] > -(self.macdl_entry_range.value * dataframe['close'])), 'macdl_entry2'] = 1
        dataframe.loc[(dataframe['macdlead'] < -(self.macdl_entry_range.value * dataframe['close'])), 'macdl_entry2'] = -1

        dataframe.loc[(dataframe['macdlead'] < (self.macdl_entry_range.value * dataframe['close'])), 'macdl_entry3'] = 1
        dataframe.loc[(dataframe['macdlead'] > (self.macdl_entry_range.value * dataframe['close'])), 'macdl_entry3'] = -1

        dataframe.loc[(dataframe['macdlead_pc'] > self.macdl_entry_pc.value), 'macdl_entry4'] = 1
        dataframe.loc[(dataframe['macdlead_pc'] < self.macdl_entry_pc.value), 'macdl_entry4'] = -1

        dataframe['macdl_weight'] = ((dataframe['macdl_entry1']+dataframe['macdl_entry2']+dataframe['macdl_entry3']+dataframe['macdl_entry4'])/4) * self.x8.value

        dataframe.loc[(dataframe['s2'] > dataframe['close']), 'pivot_entry1'] = 1
        dataframe.loc[(dataframe['s2'] < dataframe['close']), 'pivot_entry1'] = 0

        dataframe.loc[(dataframe['s3'] > dataframe['close']), 'pivot_entry2'] = 2
        dataframe.loc[(dataframe['s3'] < dataframe['close']), 'pivot_entry2'] = 0

        dataframe.loc[(dataframe['s2'] < dataframe['hma_50']), 'pivot_entry3'] = 0
        dataframe.loc[(dataframe['s2'] > dataframe['hma_50']), 'pivot_entry3'] = 1

        dataframe.loc[(dataframe['s3'] < dataframe['hma_50']), 'pivot_entry4'] = 0
        dataframe.loc[(dataframe['s3'] > dataframe['hma_50']), 'pivot_entry4'] = 2

        dataframe.loc[(dataframe['r2'] < dataframe['hma_50']) & (dataframe['r3'] > dataframe['hma_50']) & (dataframe['hma_50'] > self.hma_entry_pc.value), 'pivot_entry5'] = 2
        dataframe.loc[(dataframe['r2'] < dataframe['hma_50']) & (dataframe['r3'] > dataframe['hma_50']) & (dataframe['hma_50'] < self.hma_entry_pc.value), 'pivot_entry5'] = 0

        dataframe.loc[(dataframe['r3'] < dataframe['hma_50']), 'pivot_entry6'] = -3
        dataframe.loc[(dataframe['r3'] > dataframe['hma_50']), 'pivot_entry6'] = 0

        dataframe['pivot_weight'] = ((dataframe['pivot_entry1']+dataframe['pivot_entry2']+dataframe['pivot_entry3']+dataframe['pivot_entry4']+dataframe['pivot_entry5']+dataframe['pivot_entry6'])/4) * self.x9.value

        dataframe['from_weight'] = -(dataframe['from_200'] * self.x10.value)

        dataframe['auto_entry'] = dataframe[['rsi_weight', 'fewo_weight', 'ewo_weight', 'willr_weight', 'hma_weight', 'base_ma_entry_weight', 'macdl_weight','200SMA_weight', 'pivot_weight', 'from_weight']].sum(axis=1)

        ### SELLING ###

        dataframe.loc[(dataframe['rsi']<self.rsi_exit.value), 'rsi_exit1'] = 1
        dataframe.loc[(dataframe['rsi']>self.rsi_exit.value), 'rsi_exit1'] = -1

        dataframe.loc[(dataframe['rsi']>dataframe['rsi_ma']), 'rsi_exit2'] = -1
        dataframe.loc[(dataframe['rsi']<dataframe['rsi_ma']), 'rsi_exit2'] = 1
        
        dataframe.loc[(dataframe['rsi_ma_pcnt']>self.rsi_ma_exitpc.value), 'rsi_exit3'] = -1
        dataframe.loc[(dataframe['rsi_ma_pcnt']<self.rsi_ma_exitpc.value), 'rsi_exit3'] = 1
        
        dataframe.loc[(dataframe['rsi']<self.rsi_exit_safe.value), 'rsi_exit4'] = -1
        dataframe.loc[(dataframe['rsi']>self.rsi_exit_safe.value), 'rsi_exit4'] = 1

        dataframe['rsi_weight_exit'] = (
            (dataframe['rsi_exit1']+dataframe['rsi_exit2']+dataframe['rsi_exit3']+dataframe['rsi_exit4'])/4) * self.y1.value

        dataframe.loc[((dataframe['FEWO'] > dataframe['EWO']) & (dataframe['FEWO'].shift(1) < dataframe['EWO'].shift(1))), 'ewo_exit1'] = -1
        dataframe.loc[((dataframe['FEWO'] < dataframe['EWO']) & (dataframe['FEWO'].shift(1) > dataframe['EWO'].shift(1))), 'ewo_exit1'] = 1

        dataframe.loc[(dataframe['FEWO_PC'] > self.FEWO_exitpc.value), 'ewo_exit2'] = -2
        dataframe.loc[(dataframe['FEWO_PC'] < self.FEWO_exitpc.value), 'ewo_exit2'] = 2

        dataframe.loc[((dataframe['FEWO'] > self.bull.value) & (dataframe['FEWO'] < self.ewo_high.value)), 'ewo_exit3'] = -1
        dataframe.loc[((dataframe['FEWO'] < self.bull.value) & (dataframe['FEWO'] > self.ewo_high.value)), 'ewo_exit3'] = 1

        dataframe.loc[((dataframe['FEWO'] > self.ewo_low.value) & (dataframe['FEWO'] < self.bull.value)), 'ewo_exit4'] = 1
        dataframe.loc[(dataframe['FEWO'] < self.ewo_low.value), 'ewo_exit4'] = -1

        dataframe.loc[(dataframe['FEWO'] < self.ewo_low.value), 'ewo_exit5'] = 1
        dataframe.loc[(dataframe['FEWO'] > self.ewo_low.value), 'ewo_exit5'] = 0

        dataframe.loc[((dataframe['EWO'] > self.bull.value) & (dataframe['EWO'] < self.ewo_high.value)), 'ewo_exit6'] = 1
        dataframe.loc[((dataframe['EWO'] < self.bull.value) & (dataframe['EWO'] > self.ewo_high.value)), 'ewo_exit6'] = 1

        dataframe.loc[(dataframe['EWO'] < self.ewo_high.value), 'ewo_exit7'] = 1
        dataframe.loc[(dataframe['EWO'] > self.ewo_high.value), 'ewo_exit7'] = 0

        dataframe.loc[(dataframe['EWO'] < self.ewo_low.value) & (dataframe['EWO_PC'] > self.EWO_exitpc.value), 'ewo_exit8'] = 0
        dataframe.loc[(dataframe['EWO'] > self.ewo_low.value) & (dataframe['EWO_PC'] > self.EWO_exitpc.value), 'ewo_exit8'] = 1

        dataframe.loc[(dataframe['EWO_PC'] > self.EWO_exitpc.value), 'ewo_exit9'] = -1
        dataframe.loc[(dataframe['EWO_PC'] < self.EWO_exitpc.value), 'ewo_exit9'] = 1

        dataframe['fewo_weight_exit'] = ((dataframe['ewo_exit1']+dataframe['ewo_exit2']+dataframe['ewo_exit3']+dataframe['ewo_exit4']+dataframe['ewo_exit5'])/5) * self.y2.value
        dataframe['ewo_weight_exit'] = ((dataframe['ewo_exit6']+dataframe['ewo_exit7']+dataframe['ewo_exit8']+dataframe['ewo_exit9'])/4) * self.y3.value

        dataframe.loc[((dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] > self.sma200_exit_pc.value)), 'sma_exit1'] = -1
        dataframe.loc[((dataframe['close'] < dataframe['200_SMA'])& (dataframe['200_SMAPC'] > self.sma200_exit_pc.value)), 'sma_exit1'] = -2
        dataframe.loc[((dataframe['close'] > dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_exit_pc.value)), 'sma_exit1'] = 2
        dataframe.loc[((dataframe['close'] < dataframe['200_SMA']) & (dataframe['200_SMAPC'] < self.sma200_exit_pc.value)), 'sma_exit1'] = 1

        dataframe.loc[(dataframe['200_SMAPC'] > self.sma200_exit_pc.value), 'sma_exit2'] = -1
        dataframe.loc[(dataframe['200_SMAPC'] < self.sma200_exit_pc.value), 'sma_exit2'] = 1
        
        dataframe.loc[(dataframe['hma_50'] < dataframe['200_SMA']) & (dataframe['hma_50'].shift(1) > dataframe['200_SMA'].shift(1)), 'sma_exit3'] = 1
        dataframe.loc[(dataframe['hma_50'] > dataframe['200_SMA']) & (dataframe['hma_50'] < self.hma_exit_pc.value) , 'sma_exit3'] = 2

        dataframe['200SMA_weight_exit'] = ((dataframe['sma_exit1']+dataframe['sma_exit2']+dataframe['sma_exit3'])/3) * self.y4.value

        dataframe.loc[(dataframe['willr14'] < self.willr_exit.value), 'willr_exit1'] = -1
        dataframe.loc[(dataframe['willr14'] > self.willr_exit.value), 'willr_exit1'] = 1

        dataframe.loc[(dataframe['willr14'] > -10), 'willr_exit2'] = 1
        dataframe.loc[(dataframe['willr14'] < -10), 'willr_exit2'] = -1
        
        dataframe.loc[(dataframe['willr14PC'] > 0), 'willr_exit3'] = -1
        dataframe.loc[(dataframe['willr14PC'] < 0), 'willr_exit3'] = 1

        dataframe['willr_weight_exit'] = ((dataframe['willr_exit1']+dataframe['willr_exit2']+dataframe['willr_exit3'])/3) * self.y5.value

        dataframe.loc[(dataframe['close'] > dataframe['hma_50']), 'hma_exit1'] = 1
        dataframe.loc[(dataframe['close'] < dataframe['hma_50']), 'hma_exit1'] = -1

        dataframe.loc[(dataframe['hma_50_pc'] > self.hma_exit_pc.value), 'hma_exit2'] = -1
        dataframe.loc[(dataframe['hma_50_pc'] < self.hma_exit_pc.value), 'hma_exit2'] = 1

        dataframe['hma_weight_exit'] = ((dataframe['hma_exit1']+dataframe['hma_exit2'])/2) * self.y6.value

        dataframe.loc[(dataframe['close'] < (dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value)), 'base_ma_exit1'] = -1
        dataframe.loc[(dataframe['close'] > (dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset.value)), 'base_ma_exit'] = 1

        dataframe.loc[(dataframe['close'] < (dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset_2.value)), 'base_ma_exit2'] = -1
        dataframe.loc[(dataframe['close'] > (dataframe[f'ma_exit_{self.base_nb_candles_exit.value}'] * self.high_offset_2.value)), 'base_ma_exit2'] = 1

        dataframe['base_ma_exit_weight'] = ((dataframe['base_ma_exit1'] + dataframe['base_ma_exit2'])/2) * self.y7.value


        dataframe.loc[(dataframe['macdl'] > dataframe['macdl_sig']), 'macdl_exit1'] = -1
        dataframe.loc[(dataframe['macdl'] < dataframe['macdl_sig']), 'macdl_exit1'] = 1

        dataframe.loc[(dataframe['macdlead'] > -(self.macdl_exit_range.value * dataframe['close'])), 'macdl_exit2'] = 1
        dataframe.loc[(dataframe['macdlead'] < -(self.macdl_exit_range.value * dataframe['close'])), 'macdl_exit2'] = -1

        dataframe.loc[(dataframe['macdlead'] < (self.macdl_exit_range.value * dataframe['close'])), 'macdl_exit3'] = 1
        dataframe.loc[(dataframe['macdlead'] > (self.macdl_exit_range.value * dataframe['close'])), 'macdl_exit3'] = -1

        dataframe.loc[(dataframe['macdlead_pc'] > self.macdl_exit_pc.value), 'macdl_exit4'] = -1
        dataframe.loc[(dataframe['macdlead_pc'] < self.macdl_exit_pc.value), 'macdl_exit4'] = 1

        dataframe['macdl_weight_exit'] = ((dataframe['macdl_exit1']+dataframe['macdl_exit2']+dataframe['macdl_exit3']+dataframe['macdl_exit4'])/4) * self.y8.value

        dataframe.loc[(dataframe['r1'] > dataframe['close']), 'pivot_exit1'] = 0
        dataframe.loc[(dataframe['r1'] < dataframe['close']), 'pivot_exit1'] = 0.5

        dataframe.loc[(dataframe['r2'] > dataframe['close']), 'pivot_exit2'] = 0
        dataframe.loc[(dataframe['r2'] < dataframe['close']), 'pivot_exit2'] = 0.5

        dataframe.loc[(dataframe['r2.50'] < dataframe['hma_50']), 'pivot_exit3'] = -0.5
        dataframe.loc[(dataframe['r2.50'] > dataframe['hma_50']), 'pivot_exit3'] = 0.5

        dataframe.loc[(dataframe['r2.75'] < dataframe['hma_50']), 'pivot_exit4'] = -0.5
        dataframe.loc[(dataframe['r2.75'] > dataframe['hma_50']), 'pivot_exit4'] = 0.5

        dataframe.loc[(dataframe['r2'] < dataframe['hma_50']) & (dataframe['r3'] > dataframe['hma_50']) & (dataframe['hma_50'] > self.hma_exit_pc.value), 'pivot_exit5'] = 0
        dataframe.loc[(dataframe['r2'] < dataframe['hma_50']) & (dataframe['r3'] > dataframe['hma_50']) & (dataframe['hma_50'] < self.hma_exit_pc.value), 'pivot_exit5'] = 1

        dataframe.loc[(dataframe['r3'] < dataframe['hma_50']), 'pivot_exit6'] = 0
        dataframe.loc[(dataframe['r3'] > dataframe['hma_50']), 'pivot_exit6'] = 1

        dataframe['pivot_weight_exit'] = ((dataframe['pivot_exit1']+dataframe['pivot_exit2']+dataframe['pivot_exit3']+dataframe['pivot_exit4']+dataframe['pivot_exit5']+dataframe['pivot_exit6'])/4) * self.y9.value

        dataframe['from_weight_exit'] = (dataframe['from_200'] * self.y10.value)

        dataframe['auto_exit'] = dataframe[['rsi_weight_exit', 'fewo_weight_exit', 'ewo_weight_exit', 'willr_weight_exit', 'hma_weight_exit', 'base_ma_exit_weight', 'macdl_weight_exit', '200SMA_weight_exit', 'pivot_weight_exit', 'from_weight_exit']].sum(axis=1)

        dataframe['auto_entry_decision'] = ta.SMA((dataframe['auto_entry'] - dataframe['auto_exit']), timeperiod=2)
        dataframe['auto_exit_decision'] = ta.SMA((dataframe['auto_exit'] - dataframe['auto_entry']), timeperiod=2)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:


        dataframe.loc[
            (
                # (dataframe['auto_entry_decision'] >= self.auto_entry.value) &
                (qtpylib.crossed_above(dataframe['auto_entry_decision'], self.auto_entry.value)) &
                (dataframe['BTC_EWO_Fast_1h'] >= self.bull.value) &
                # (dataframe['BTC_EWO_Fast_1h'] > dataframe['BTC_EWO_Fast_1h'].shift(1)) &
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']] = (1, 'auto entry bullzzz')

        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe['auto_entry_decision'], (self.auto_entry.value + self.auto_entry_bearzzz.value))) &
                (dataframe['BTC_EWO_Fast_1h'] < self.bull.value) &
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']] = (1, 'auto entry bearzzz')

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        ### possibly change exit signals?

        # dataframe.loc[
        #     (
        #         (qtpylib.crossed_below(dataframe[f'zema_{self.filterlength.value}'], dataframe['r3'])) &
        #         (dataframe['rsi'] > 50)&
        #         (dataframe['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     ['exit_long', 'exit_tag']] = (1, 'R3 - XO')

        # dataframe.loc[
        #     (
        #         (qtpylib.crossed_below(dataframe[f'zema_{self.filterlength.value}'], dataframe['r2.75'])) &
        #         (dataframe['rsi'] > 50)&
        #         (dataframe['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     ['exit_long', 'exit_tag']] = (1, 'R2.75 - XO')

        # dataframe.loc[
        #     (
        #         (qtpylib.crossed_below(dataframe[f'zema_{self.filterlength.value}'], dataframe['r2.50'])) &
        #         (dataframe['rsi'] > 50)&
        #         (dataframe['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     ['exit_long', 'exit_tag']] = (1, 'R2.5 - XO')

        # dataframe.loc[
        #     (
        #         (qtpylib.crossed_below(dataframe[f'zema_{self.filterlength.value}'], dataframe['r2.25'])) &
        #         (dataframe['rsi'] > 50)&
        #         (dataframe['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     ['exit_long', 'exit_tag']] = (1, 'R2.25 - XO')

        dataframe.loc[
            (
            
                (dataframe['auto_exit_decision'] >= self.auto_exit.value) &
                (dataframe['volume'] > 0)

            ),
            ['exit_long', 'exit_tag']] = (1, 'auto_exit')


        # dataframe.loc[
        #     (
        #         (dataframe['BTC_EWO_Fast_1h'] <= self.estop.value) &
        #         (dataframe['volume'] > 0)
        #     ),
        #     ['exit_long', 'exit_tag']] = (1, 'fucking bearzzz')

        return dataframe

