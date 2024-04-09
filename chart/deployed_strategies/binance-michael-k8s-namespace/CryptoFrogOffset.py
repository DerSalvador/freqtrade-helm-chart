from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from cachetools import TTLCache
from functools import reduce
## I hope you know what these are already
from pandas import DataFrame
import numpy as np
## Indicator libs
import talib.abstract as ta
from finta import TA as fta
## FT stuffs
from freqtrade.strategy import IStrategy, merge_informative_pair, stoploss_from_open, IntParameter, DecimalParameter, CategoricalParameter
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.exchange import timeframe_to_minutes
from freqtrade.persistence import Trade
from skopt.space import Dimension

class CryptoFrogOffset(IStrategy):
    INTERFACE_VERSION = 3
    # ROI table - this strat REALLY benefits from roi and trailing hyperopt:
    minimal_roi = {'0': 0.213, '39': 0.103, '96': 0.037, '166': 0}
    # Stoploss:
    stoploss = -0.085
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.047
    trailing_only_offset_is_reached = False
    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 400
    use_custom_stoploss = False
    # Linear Decay Parameters
    # minutes to reach end, I find it works well to match this to the final ROI value - default 1080
    # minutes to wait before decay starts
    # -0.32118, # -0.07163,     # starting value: should be the same or smaller than initial stoploss - default -0.30
    # ending value - default -0.03
    # Profit and TA  
    # diff between current and minimum profit to move stoploss up to min profit point
    # how far negative should current profit be before we consider moving it up based on cur/min or roc
    # value for roc to use for dynamic bailout
    # rmi-slow value to pause stoploss decay
    # set the stoploss to the atr offset below current price, or immediate
    # Positive Trailing
    # enable trailing once positive  
    # trail after how far positive
    # how far behind to place the trail
    custom_stop = {'decay-time': 166, 'decay-delay': 0, 'decay-start': -0.085, 'decay-end': -0.02, 'cur-min-diff': 0.03, 'cur-threshold': -0.02, 'roc-bail': -0.03, 'rmi-trend': 50, 'bail-how': 'immediate', 'pos-trail': True, 'pos-threshold': 0.005, 'pos-trail-dist': 0.015}
    # Dynamic ROI
    droi_trend_type = CategoricalParameter(['rmi', 'ssl', 'candle', 'any'], default='any', space='exit', optimize=True)
    droi_pullback = CategoricalParameter([True, False], default=True, space='exit', optimize=True)
    droi_pullback_amount = DecimalParameter(0.005, 0.02, default=0.005, space='exit')
    droi_pullback_respect_table = CategoricalParameter([True, False], default=False, space='exit', optimize=True)
    # Custom Stoploss
    cstp_threshold = DecimalParameter(-0.05, 0, default=-0.03, space='exit')
    cstp_bail_how = CategoricalParameter(['roc', 'time', 'any'], default='roc', space='exit', optimize=True)
    cstp_bail_roc = DecimalParameter(-0.05, -0.01, default=-0.03, space='exit')
    cstp_bail_time = IntParameter(720, 1440, default=720, space='exit')
    stoploss = custom_stop['decay-start']
    custom_trade_info = {}
    custom_current_price_cache: TTLCache = TTLCache(maxsize=100, ttl=300)  # 5 minutes
    # run "populate_indicators" only for new candle
    process_only_new_candles = True
    # Experimental settings (configuration will overide these if set)
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.01
    ignore_roi_if_entry_signal = False
    use_dynamic_roi = True
    timeframe = '5m'
    informative_timeframe = '1h'
    # Optional order type mapping
    order_types = {'entry': 'limit', 'exit': 'limit', 'stoploss': 'market', 'stoploss_on_exchange': False}
    plot_config = {'main_plot': {'Smooth_HA_H': {'color': 'orange'}, 'Smooth_HA_L': {'color': 'yellow'}}, 'subplots': {'StochRSI': {'srsi_k': {'color': 'blue'}, 'srsi_d': {'color': 'red'}}, 'MFI': {'mfi': {'color': 'green'}}, 'BBEXP': {'bbw_expansion': {'color': 'orange'}}, 'FAST': {'fastd': {'color': 'red'}, 'fastk': {'color': 'blue'}}, 'SQZMI': {'sqzmi': {'color': 'lightgreen'}}, 'VFI': {'vfi': {'color': 'lightblue'}}, 'DMI': {'dmi_plus': {'color': 'orange'}, 'dmi_minus': {'color': 'yellow'}}, 'EMACO': {'emac_1h': {'color': 'red'}, 'emao_1h': {'color': 'blue'}}}}
    #############
    # Enable/Disable conditions
    #-------------------------------------------------------------
    # Buy signal 1 - RSI/MFI/INC
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 2 - RSI diff
    #-------------------------------------------------------------
    #"entry_volume_2": 2.6, # removed
    #-------------------------------------------------------------
    # Buy signal 3 BHV
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 4 - Cluc
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 5 - MACD/BB/more checks
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 6 - MACD/BB/less checks
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    #"entry_volume_7": 2.0,
    #"entry_ema_rel_7": 0.986, # Not used
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    #"entry_volume_9": 1.0, #removed
    #-------------------------------------------------------------
    # Buy signal 10 - BB/SMA/Less checks
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 11 - INC/RSI/MFI/SMA
    #-------------------------------------------------------------
    #0.939
    # lower can have losses
    #-------------------------------------------------------------
    # Buy signal 12 - EWO high/MA offset/RSI
    #-------------------------------------------------------------
    #"entry_volume_12": 1.7, # removed
    #-------------------------------------------------------------
    # Buy signal 13 - EWO low/MA Offset
    #-------------------------------------------------------------
    #"entry_volume_13": 1.6, # Removed
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    #"entry_volume_14": 2.0, # Removed
    #-------------------------------------------------------------
    # Buy signal 15 - MACD/MA Offset/RSI
    #-------------------------------------------------------------
    #"entry_volume_15": 2.0, # Removed
    #-------------------------------------------------------------
    # Buy signal 16 - EWO/EMA/RSI
    #-------------------------------------------------------------
    #"entry_volume_16": 2.0, # removed
    #-------------------------------------------------------------
    # Buy signal 17 - EWO low/EMA Offset
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    #"entry_volume_18": 2.0, # removed
    #-------------------------------------------------------------
    # Buy signal 19 - Chopiness/RSI
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 20 - Double RSI
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 21 - Double RSI
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 22
    #-------------------------------------------------------------
    #-------------------------------------------------------------
    # Buy signal 23 - Over EMA200/2001h/RSI/BB/EWO
    #-------------------------------------------------------------
    entry_params = {'entry_condition_1_enable': True, 'entry_01_protection__close_above_ema_fast': True, 'entry_01_protection__close_above_ema_fast_len': '200', 'entry_01_protection__close_above_ema_slow': False, 'entry_01_protection__close_above_ema_slow_len': '50', 'entry_01_protection__ema_fast': False, 'entry_01_protection__ema_fast_len': '26', 'entry_01_protection__ema_slow': True, 'entry_01_protection__ema_slow_len': '100', 'entry_01_protection__safe_dips': True, 'entry_01_protection__safe_dips_type': 'normal', 'entry_01_protection__safe_pump': True, 'entry_01_protection__safe_pump_period': '36', 'entry_01_protection__safe_pump_type': 'loose', 'entry_01_protection__sma200_1h_rising': False, 'entry_01_protection__sma200_1h_rising_val': '36', 'entry_01_protection__sma200_rising': True, 'entry_01_protection__sma200_rising_val': '36', 'entry_mfi_1': 36.0, 'entry_min_inc_1': 0.022, 'entry_rsi_1': 36.0, 'entry_rsi_1h_max_1': 84.0, 'entry_rsi_1h_min_1': 30.0, 'entry_condition_2_enable': True, 'entry_02_protection__close_above_ema_slow': False, 'entry_02_protection__close_above_ema_slow_len': '15', 'entry_02_protection__close_above_ema_fast': False, 'entry_02_protection__close_above_ema_fast_len': '200', 'entry_02_protection__ema_fast': False, 'entry_02_protection__ema_fast_len': '50', 'entry_02_protection__ema_slow': False, 'entry_02_protection__ema_slow_len': '50', 'entry_02_protection__safe_dips': True, 'entry_02_protection__safe_dips_type': 'normal', 'entry_02_protection__safe_pump': False, 'entry_02_protection__safe_pump_period': '48', 'entry_02_protection__safe_pump_type': 'loose', 'entry_02_protection__sma200_rising': False, 'entry_02_protection__sma200_rising_val': '50', 'entry_02_protection__sma200_1h_rising': True, 'entry_02_protection__sma200_1h_rising_val': '50', 'entry_bb_offset_2': 0.983, 'entry_mfi_2': 49.0, 'entry_rsi_1h_diff_2': 39.0, 'entry_rsi_1h_max_2': 84.0, 'entry_rsi_1h_min_2': 32.0, 'entry_condition_3_enable': True, 'entry_03_protection__close_above_ema_slow': False, 'entry_03_protection__close_above_ema_slow_len': '15', 'entry_03_protection__close_above_ema_fast': False, 'entry_03_protection__close_above_ema_fast_len': '5', 'entry_03_protection__ema_fast': True, 'entry_03_protection__ema_fast_len': '100', 'entry_03_protection__ema_slow': True, 'entry_03_protection__ema_slow_len': '100', 'entry_03_protection__safe_dips': False, 'entry_03_protection__safe_dips_type': 'loose', 'entry_03_protection__safe_pump': True, 'entry_03_protection__safe_pump_period': '36', 'entry_03_protection__safe_pump_type': 'loose', 'entry_03_protection__sma200_rising': False, 'entry_03_protection__sma200_rising_val': '50', 'entry_03_protection__sma200_1h_rising': False, 'entry_03_protection__sma200_1h_rising_val': '50', 'entry_condition_4_enable': True, 'entry_04_protection__close_above_ema_slow': False, 'entry_04_protection__close_above_ema_slow_len': '200', 'entry_04_protection__close_above_ema_fast': False, 'entry_04_protection__close_above_ema_fast_len': '30', 'entry_04_protection__ema_fast': False, 'entry_04_protection__ema_fast_len': '50', 'entry_04_protection__ema_slow': False, 'entry_04_protection__ema_slow_len': '50', 'entry_04_protection__safe_dips': True, 'entry_04_protection__safe_dips_type': 'normal', 'entry_04_protection__safe_pump': True, 'entry_04_protection__safe_pump_period': '48', 'entry_04_protection__safe_pump_type': 'normal', 'entry_04_protection__sma200_1h_rising': True, 'entry_04_protection__sma200_1h_rising_val': '20', 'entry_04_protection__sma200_rising': True, 'entry_04_protection__sma200_rising_val': '50', 'entry_condition_5_enable': True, 'entry_05_protection__close_above_ema_fast': False, 'entry_05_protection__close_above_ema_fast_len': '200', 'entry_05_protection__close_above_ema_slow': False, 'entry_05_protection__close_above_ema_slow_len': '15', 'entry_05_protection__ema_fast': True, 'entry_05_protection__ema_fast_len': '100', 'entry_05_protection__ema_slow': False, 'entry_05_protection__ema_slow_len': '50', 'entry_05_protection__safe_dips': True, 'entry_05_protection__safe_dips_type': 'loose', 'entry_05_protection__safe_pump': True, 'entry_05_protection__safe_pump_period': '36', 'entry_05_protection__safe_pump_type': 'strict', 'entry_05_protection__sma200_rising': False, 'entry_05_protection__sma200_rising_val': '50', 'entry_05_protection__sma200_1h_rising': False, 'entry_05_protection__sma200_1h_rising_val': '50', 'entry_condition_6_enable': True, 'entry_06_protection__close_above_ema_slow': False, 'entry_06_protection__close_above_ema_slow_len': '15', 'entry_06_protection__close_above_ema_fast': False, 'entry_06_protection__close_above_ema_fast_len': '200', 'entry_06_protection__ema_fast': False, 'entry_06_protection__ema_fast_len': '50', 'entry_06_protection__ema_slow': True, 'entry_06_protection__ema_slow_len': '100', 'entry_06_protection__safe_dips': True, 'entry_06_protection__safe_dips_type': 'normal', 'entry_06_protection__safe_pump': True, 'entry_06_protection__safe_pump_period': '36', 'entry_06_protection__safe_pump_type': 'strict', 'entry_06_protection__sma200_rising': False, 'entry_06_protection__sma200_rising_val': '50', 'entry_06_protection__sma200_1h_rising': False, 'entry_06_protection__sma200_1h_rising_val': '50', 'entry_condition_7_enable': True, 'entry_07_protection__close_above_ema_slow': False, 'entry_07_protection__close_above_ema_slow_len': '15', 'entry_07_protection__close_above_ema_fast': False, 'entry_07_protection__close_above_ema_fast_len': '200', 'entry_07_protection__ema_fast': True, 'entry_07_protection__ema_fast_len': '100', 'entry_07_protection__ema_slow': True, 'entry_07_protection__ema_slow_len': '50', 'entry_07_protection__safe_dips': True, 'entry_07_protection__safe_dips_type': 'normal', 'entry_07_protection__safe_pump': False, 'entry_07_protection__safe_pump_period': '36', 'entry_07_protection__safe_pump_type': 'loose', 'entry_07_protection__sma200_rising': False, 'entry_07_protection__sma200_rising_val': '50', 'entry_07_protection__sma200_1h_rising': False, 'entry_07_protection__sma200_1h_rising_val': '50', 'entry_ema_open_mult_7': 0.03, 'entry_rsi_7': 36.0, 'entry_condition_8_enable': True, 'entry_08_protection__close_above_ema_slow': False, 'entry_08_protection__close_above_ema_slow_len': '15', 'entry_08_protection__close_above_ema_fast': False, 'entry_08_protection__close_above_ema_fast_len': '200', 'entry_08_protection__ema_fast': False, 'entry_08_protection__ema_fast_len': '50', 'entry_08_protection__ema_slow': True, 'entry_08_protection__ema_slow_len': '50', 'entry_08_protection__safe_dips': True, 'entry_08_protection__safe_dips_type': 'loose', 'entry_08_protection__safe_pump': True, 'entry_08_protection__safe_pump_period': '24', 'entry_08_protection__safe_pump_type': 'loose', 'entry_08_protection__sma200_rising': False, 'entry_08_protection__sma200_rising_val': '50', 'entry_08_protection__sma200_1h_rising': False, 'entry_08_protection__sma200_1h_rising_val': '50', 'entry_condition_9_enable': True, 'entry_09_protection__close_above_ema_slow': False, 'entry_09_protection__close_above_ema_slow_len': '15', 'entry_09_protection__close_above_ema_fast': False, 'entry_09_protection__close_above_ema_fast_len': '200', 'entry_09_protection__ema_fast': True, 'entry_09_protection__ema_fast_len': '100', 'entry_09_protection__ema_slow': False, 'entry_09_protection__ema_slow_len': '50', 'entry_09_protection__safe_dips': False, 'entry_09_protection__safe_dips_type': 'strict', 'entry_09_protection__safe_pump': False, 'entry_09_protection__safe_pump_period': '24', 'entry_09_protection__safe_pump_type': 'loose', 'entry_09_protection__sma200_rising': False, 'entry_09_protection__sma200_rising_val': '50', 'entry_09_protection__sma200_1h_rising': False, 'entry_09_protection__sma200_1h_rising_val': '50', 'entry_bb_offset_9': 0.985, 'entry_ma_offset_9': 0.97, 'entry_mfi_9': 30.0, 'entry_rsi_1h_max_9': 88.0, 'entry_rsi_1h_min_9': 30.0, 'entry_volume_9': 1.0, 'entry_bb_offset_9': 0.96, 'entry_ma_offset_9': 0.96, 'entry_mfi_9': 36.0, 'entry_rsi_1h_max_9': 88.0, 'entry_rsi_1h_min_9': 30.0, 'entry_volume_9': 1.0, 'entry_bb_offset_9': 0.965, 'entry_ma_offset_9': 0.922, 'entry_mfi_9': 50.0, 'entry_rsi_1h_max_9': 88.0, 'entry_rsi_1h_min_9': 30.0, 'entry_condition_10_enable': True, 'entry_10_protection__close_above_ema_slow': False, 'entry_10_protection__close_above_ema_slow_len': '15', 'entry_10_protection__close_above_ema_fast': False, 'entry_10_protection__close_above_ema_fast_len': '200', 'entry_10_protection__ema_fast': False, 'entry_10_protection__ema_fast_len': '50', 'entry_10_protection__ema_slow': False, 'entry_10_protection__ema_slow_len': '50', 'entry_10_protection__safe_dips': True, 'entry_10_protection__safe_dips_type': 'loose', 'entry_10_protection__safe_pump': False, 'entry_10_protection__safe_pump_period': '24', 'entry_10_protection__safe_pump_type': 'loose', 'entry_10_protection__sma200_rising': False, 'entry_10_protection__sma200_rising_val': '50', 'entry_10_protection__sma200_1h_rising': True, 'entry_10_protection__sma200_1h_rising_val': '24', 'entry_bb_offset_10': 0.994, 'entry_ma_offset_10': 0.948, 'entry_rsi_1h_10': 37.0, 'entry_volume_10': 2.4, 'entry_condition_11_enable': True, 'entry_11_protection__close_above_ema_slow': False, 'entry_11_protection__close_above_ema_slow_len': '15', 'entry_11_protection__close_above_ema_fast': False, 'entry_11_protection__close_above_ema_fast_len': '200', 'entry_11_protection__ema_fast': False, 'entry_11_protection__ema_fast_len': '50', 'entry_11_protection__ema_slow': False, 'entry_11_protection__ema_slow_len': '50', 'entry_11_protection__safe_dips': True, 'entry_11_protection__safe_dips_type': 'loose', 'entry_11_protection__safe_pump': True, 'entry_11_protection__safe_pump_period': '24', 'entry_11_protection__safe_pump_type': 'loose', 'entry_11_protection__sma200_rising': False, 'entry_11_protection__sma200_rising_val': '50', 'entry_11_protection__sma200_1h_rising': False, 'entry_11_protection__sma200_1h_rising_val': '50', 'entry_ma_offset_11': 0.939, 'entry_mfi_11': 36.0, 'entry_min_inc_11': 0.01, 'entry_rsi_11': 48.0, 'entry_rsi_1h_max_11': 84.0, 'entry_rsi_1h_min_11': 56.0, 'entry_condition_12_enable': True, 'entry_12_protection__close_above_ema_slow': False, 'entry_12_protection__close_above_ema_slow_len': '15', 'entry_12_protection__close_above_ema_fast': False, 'entry_12_protection__close_above_ema_fast_len': '200', 'entry_12_protection__ema_fast': False, 'entry_12_protection__ema_fast_len': '50', 'entry_12_protection__ema_slow': False, 'entry_12_protection__ema_slow_len': '50', 'entry_12_protection__safe_dips': True, 'entry_12_protection__safe_dips_type': 'strict', 'entry_12_protection__safe_pump': False, 'entry_12_protection__safe_pump_period': '24', 'entry_12_protection__safe_pump_type': 'loose', 'entry_12_protection__sma200_rising': False, 'entry_12_protection__sma200_rising_val': '50', 'entry_12_protection__sma200_1h_rising': True, 'entry_12_protection__sma200_1h_rising_val': '24', 'entry_ewo_12': 1.8, 'entry_ma_offset_12': 0.922, 'entry_rsi_12': 30.0, 'entry_condition_13_enable': True, 'entry_13_protection__close_above_ema_slow': False, 'entry_13_protection__close_above_ema_slow_len': '15', 'entry_13_protection__close_above_ema_fast': False, 'entry_13_protection__close_above_ema_fast_len': '200', 'entry_13_protection__ema_fast': False, 'entry_13_protection__ema_fast_len': '50', 'entry_13_protection__ema_slow': False, 'entry_13_protection__ema_slow_len': '50', 'entry_13_protection__safe_dips': True, 'entry_13_protection__safe_dips_type': 'strict', 'entry_13_protection__safe_pump': False, 'entry_13_protection__safe_pump_period': '24', 'entry_13_protection__safe_pump_type': 'loose', 'entry_13_protection__sma200_rising': False, 'entry_13_protection__sma200_rising_val': '50', 'entry_13_protection__sma200_1h_rising': True, 'entry_13_protection__sma200_1h_rising_val': '24', 'entry_ewo_13': -11.8, 'entry_ma_offset_13': 0.99, 'entry_condition_14_enable': True, 'entry_14_protection__close_above_ema_slow': False, 'entry_14_protection__close_above_ema_slow_len': '15', 'entry_14_protection__close_above_ema_fast': False, 'entry_14_protection__close_above_ema_fast_len': '200', 'entry_14_protection__ema_fast': False, 'entry_14_protection__ema_fast_len': '50', 'entry_14_protection__ema_slow': False, 'entry_14_protection__ema_slow_len': '50', 'entry_14_protection__safe_dips': True, 'entry_14_protection__safe_dips_type': 'strict', 'entry_14_protection__safe_pump': True, 'entry_14_protection__safe_pump_period': '24', 'entry_14_protection__safe_pump_type': 'normal', 'entry_14_protection__sma200_rising': True, 'entry_14_protection__sma200_rising_val': '30', 'entry_14_protection__sma200_1h_rising': True, 'entry_14_protection__sma200_1h_rising_val': '50', 'entry_bb_offset_14': 0.988, 'entry_ema_open_mult_14': 0.014, 'entry_ma_offset_14': 0.98, 'entry_condition_15_enable': True, 'entry_15_protection__close_above_ema_slow': False, 'entry_15_protection__close_above_ema_slow_len': '15', 'entry_15_protection__close_above_ema_fast': False, 'entry_15_protection__close_above_ema_fast_len': '200', 'entry_15_protection__ema_fast': False, 'entry_15_protection__ema_fast_len': '50', 'entry_15_protection__ema_slow': True, 'entry_15_protection__ema_slow_len': '50', 'entry_15_protection__safe_dips': True, 'entry_15_protection__safe_dips_type': 'normal', 'entry_15_protection__safe_pump': True, 'entry_15_protection__safe_pump_period': '36', 'entry_15_protection__safe_pump_type': 'strict', 'entry_15_protection__sma200_rising': False, 'entry_15_protection__sma200_rising_val': '50', 'entry_15_protection__sma200_1h_rising': False, 'entry_15_protection__sma200_1h_rising_val': '50', 'entry_ema_open_mult_15': 0.018, 'entry_ma_offset_15': 0.954, 'entry_rsi_15': 28.0, 'entry_ema_rel_15': 0.988, 'entry_condition_16_enable': True, 'entry_16_protection__close_above_ema_slow': False, 'entry_16_protection__close_above_ema_slow_len': '15', 'entry_16_protection__close_above_ema_fast': False, 'entry_16_protection__close_above_ema_fast_len': '200', 'entry_16_protection__ema_fast': False, 'entry_16_protection__ema_fast_len': '50', 'entry_16_protection__ema_slow': True, 'entry_16_protection__ema_slow_len': '50', 'entry_16_protection__safe_dips': True, 'entry_16_protection__safe_dips_type': 'strict', 'entry_16_protection__safe_pump': True, 'entry_16_protection__safe_pump_period': '24', 'entry_16_protection__safe_pump_type': 'strict', 'entry_16_protection__sma200_rising': False, 'entry_16_protection__sma200_rising_val': '50', 'entry_16_protection__sma200_1h_rising': False, 'entry_16_protection__sma200_1h_rising_val': '50', 'entry_ewo_16': 2.8, 'entry_ma_offset_16': 0.952, 'entry_rsi_16': 31.0, 'entry_condition_17_enable': True, 'entry_17_protection__close_above_ema_slow': False, 'entry_17_protection__close_above_ema_slow_len': '15', 'entry_17_protection__close_above_ema_fast': False, 'entry_17_protection__close_above_ema_fast_len': '200', 'entry_17_protection__ema_fast': False, 'entry_17_protection__ema_fast_len': '50', 'entry_17_protection__ema_slow': False, 'entry_17_protection__ema_slow_len': '50', 'entry_17_protection__safe_dips': True, 'entry_17_protection__safe_dips_type': 'strict', 'entry_17_protection__safe_pump': True, 'entry_17_protection__safe_pump_period': '24', 'entry_17_protection__safe_pump_type': 'loose', 'entry_17_protection__sma200_rising': False, 'entry_17_protection__sma200_rising_val': '50', 'entry_17_protection__sma200_1h_rising': False, 'entry_17_protection__sma200_1h_rising_val': '50', 'entry_ewo_17': -12.0, 'entry_ma_offset_17': 0.952, 'entry_condition_18_enable': True, 'entry_18_protection__close_above_ema_slow': True, 'entry_18_protection__close_above_ema_slow_len': '200', 'entry_18_protection__close_above_ema_fast': False, 'entry_18_protection__close_above_ema_fast_len': '200', 'entry_18_protection__ema_fast': True, 'entry_18_protection__ema_fast_len': '100', 'entry_18_protection__ema_slow': True, 'entry_18_protection__ema_slow_len': '50', 'entry_18_protection__safe_dips': True, 'entry_18_protection__safe_dips_type': 'normal', 'entry_18_protection__safe_pump': True, 'entry_18_protection__safe_pump_period': '24', 'entry_18_protection__safe_pump_type': 'strict', 'entry_18_protection__sma200_rising': True, 'entry_18_protection__sma200_rising_val': '44', 'entry_18_protection__sma200_1h_rising': True, 'entry_18_protection__sma200_1h_rising_val': '72', 'entry_bb_offset_18': 0.982, 'entry_rsi_18': 26.0, 'entry_condition_19_enable': True, 'entry_19_protection__close_above_ema_slow': False, 'entry_19_protection__close_above_ema_slow_len': '15', 'entry_19_protection__close_above_ema_fast': False, 'entry_19_protection__close_above_ema_fast_len': '200', 'entry_19_protection__ema_fast': False, 'entry_19_protection__ema_fast_len': '50', 'entry_19_protection__ema_slow': True, 'entry_19_protection__ema_slow_len': '100', 'entry_19_protection__safe_dips': True, 'entry_19_protection__safe_dips_type': 'normal', 'entry_19_protection__safe_pump': True, 'entry_19_protection__safe_pump_period': '24', 'entry_19_protection__safe_pump_type': 'normal', 'entry_19_protection__sma200_rising': True, 'entry_19_protection__sma200_rising_val': '36', 'entry_19_protection__sma200_1h_rising': False, 'entry_19_protection__sma200_1h_rising_val': '50', 'entry_condition_20_enable': True, 'entry_20_protection__close_above_ema_slow': False, 'entry_20_protection__close_above_ema_slow_len': '15', 'entry_20_protection__close_above_ema_fast': False, 'entry_20_protection__close_above_ema_fast_len': '200', 'entry_20_protection__ema_fast': False, 'entry_20_protection__ema_fast_len': '50', 'entry_20_protection__ema_slow': True, 'entry_20_protection__ema_slow_len': '50', 'entry_20_protection__safe_dips': False, 'entry_20_protection__safe_dips_type': 'normal', 'entry_20_protection__safe_pump': False, 'entry_20_protection__safe_pump_period': '24', 'entry_20_protection__safe_pump_type': 'loose', 'entry_20_protection__sma200_rising': False, 'entry_20_protection__sma200_rising_val': '50', 'entry_20_protection__sma200_1h_rising': False, 'entry_20_protection__sma200_1h_rising_val': '50', 'entry_condition_21_enable': True, 'entry_21_protection__close_above_ema_slow': False, 'entry_21_protection__close_above_ema_slow_len': '15', 'entry_21_protection__close_above_ema_fast': False, 'entry_21_protection__close_above_ema_fast_len': '200', 'entry_21_protection__ema_fast': False, 'entry_21_protection__ema_fast_len': '50', 'entry_21_protection__ema_slow': True, 'entry_21_protection__ema_slow_len': '50', 'entry_21_protection__safe_dips': True, 'entry_21_protection__safe_dips_type': 'normal', 'entry_21_protection__safe_pump': False, 'entry_21_protection__safe_pump_period': '36', 'entry_21_protection__safe_pump_type': 'loose', 'entry_21_protection__sma200_rising': False, 'entry_21_protection__sma200_rising_val': '50', 'entry_21_protection__sma200_1h_rising': False, 'entry_21_protection__sma200_1h_rising_val': '50', 'entry_condition_22_enable': True, 'entry_22_protection__close_above_ema_slow': False, 'entry_22_protection__close_above_ema_slow_len': '15', 'entry_22_protection__close_above_ema_fast': False, 'entry_22_protection__close_above_ema_fast_len': '200', 'entry_22_protection__ema_fast': False, 'entry_22_protection__ema_fast_len': '50', 'entry_22_protection__ema_slow': False, 'entry_22_protection__ema_slow_len': '50', 'entry_22_protection__safe_dips': False, 'entry_22_protection__safe_dips_type': 'normal', 'entry_22_protection__safe_pump': False, 'entry_22_protection__safe_pump_period': '36', 'entry_22_protection__safe_pump_type': 'loose', 'entry_22_protection__sma200_rising': False, 'entry_22_protection__sma200_rising_val': '50', 'entry_22_protection__sma200_1h_rising': False, 'entry_22_protection__sma200_1h_rising_val': '50', 'entry_condition_23_enable': True, 'entry_23_protection__close_above_ema_slow': True, 'entry_23_protection__close_above_ema_slow_len': '200', 'entry_23_protection__close_above_ema_fast': True, 'entry_23_protection__close_above_ema_fast_len': '200', 'entry_23_protection__ema_fast': False, 'entry_23_protection__ema_fast_len': '50', 'entry_23_protection__ema_slow': False, 'entry_23_protection__ema_slow_len': '50', 'entry_23_protection__safe_dips': True, 'entry_23_protection__safe_dips_type': 'loose', 'entry_23_protection__safe_pump': False, 'entry_23_protection__safe_pump_period': '36', 'entry_23_protection__safe_pump_type': 'loose', 'entry_23_protection__sma200_rising': False, 'entry_23_protection__sma200_rising_val': '50', 'entry_23_protection__sma200_1h_rising': False, 'entry_23_protection__sma200_1h_rising_val': '50'}
    #############
    # Enable/Disable conditions
    #############
    exit_params = {'exit_condition_1_enable': True, 'exit_condition_2_enable': True, 'exit_condition_3_enable': True, 'exit_condition_4_enable': True, 'exit_condition_5_enable': True, 'exit_condition_6_enable': True, 'exit_condition_7_enable': True, 'exit_condition_8_enable': True}
    #############################################################
    entry_condition_1_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_01_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=True, load=True)
    entry_01_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=True, load=True)
    entry_01_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=True, load=True)
    entry_01_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=True, load=True)
    entry_01_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=True, load=True)
    entry_01_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_01_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=True, load=True)
    entry_01_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_01_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=True, load=True)
    entry_01_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=True, load=True)
    entry_01_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=True, load=True)
    entry_01_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=True, load=True)
    entry_01_protection__safe_dips = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_01_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=True, load=True)
    entry_01_protection__safe_pump = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_01_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=True, load=True)
    entry_01_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=True, load=True)
    entry_condition_2_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_02_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_02_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_02_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_02_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_02_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_02_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_02_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_02_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_02_protection__safe_dips = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_02_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_02_protection__safe_pump = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_02_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_02_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_02_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_02_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_02_protection__sma200_1h_rising = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_02_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_condition_3_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_03_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_03_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_03_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_03_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_03_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_03_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_03_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_03_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_03_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_03_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_03_protection__safe_pump = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_03_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_03_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='36', space='entry', optimize=False, load=True)
    entry_03_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_03_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_03_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_03_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_condition_4_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_04_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_04_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_04_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_04_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_04_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_04_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_04_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_04_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_04_protection__safe_dips = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_04_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_04_protection__safe_pump = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_04_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_04_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_04_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_04_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_04_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_04_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_condition_5_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_05_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_05_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_05_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_05_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_05_protection__ema_fast = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_05_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='100', space='entry', optimize=False, load=True)
    entry_05_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_05_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_05_protection__safe_dips = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_05_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_05_protection__safe_pump = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_05_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_05_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='36', space='entry', optimize=False, load=True)
    entry_05_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_05_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_05_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_05_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_condition_6_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_06_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_06_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_06_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_06_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_06_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_06_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_06_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_06_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_06_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_06_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_06_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_06_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_06_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_06_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_06_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_06_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_06_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_7_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_07_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_07_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_07_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_07_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_07_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_07_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_07_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_07_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_07_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_07_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_07_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_07_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_07_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_07_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_07_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_07_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_07_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_8_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_08_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_08_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_08_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_08_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_08_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_08_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_08_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_08_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_08_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_08_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_08_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_08_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_08_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_08_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_08_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_08_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_08_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_9_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_09_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_09_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_09_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_09_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_09_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_09_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_09_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_09_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_09_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_09_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_09_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_09_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_09_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_09_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_09_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_09_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_09_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_10_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_10_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_10_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_10_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_10_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_10_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_10_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_10_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_10_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_10_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_10_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_10_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_10_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_10_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_10_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_10_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_10_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_10_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_11_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_11_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_11_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_11_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_11_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_11_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_11_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_11_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_11_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_11_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_11_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_11_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_11_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_11_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_11_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_11_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_11_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_11_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_12_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_12_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_12_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_12_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_12_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_12_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_12_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_12_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_12_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_12_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_12_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_12_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_12_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_12_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_12_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_12_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_12_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_12_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_13_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_13_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_13_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_13_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_13_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_13_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_13_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_13_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_13_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_13_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_13_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_13_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_13_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_13_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_13_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_13_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_13_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_13_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_14_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_14_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_14_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_14_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_14_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_14_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_14_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_14_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_14_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_14_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_14_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_14_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_14_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_14_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_14_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_14_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_14_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_14_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_15_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_15_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_15_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_15_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_15_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_15_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_15_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_15_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_15_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_15_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_15_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_15_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_15_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_15_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_15_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_15_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_15_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_15_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_16_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_16_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_16_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_16_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_16_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_16_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_16_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_16_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_16_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_16_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_16_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_16_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_16_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_16_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_16_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_16_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_16_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_16_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_17_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_17_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_17_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_17_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_17_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_17_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_17_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_17_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_17_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_17_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_17_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_17_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_17_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_17_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_17_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_17_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_17_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_17_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_18_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_18_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_18_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_18_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_18_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_18_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_18_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_18_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_18_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_18_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_18_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_18_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_18_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_18_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_18_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_18_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_18_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_18_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_19_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_19_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_19_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_19_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_19_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_19_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_19_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_19_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_19_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_19_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_19_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_19_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_19_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_19_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_19_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_19_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_19_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_19_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_20_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_20_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_20_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_20_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_20_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_20_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_20_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_20_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_20_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_20_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_20_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_20_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_20_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_20_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_20_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_20_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_20_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_20_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_21_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_21_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_21_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_21_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_21_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_21_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_21_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_21_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_21_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_21_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_21_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_21_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_21_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_21_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_21_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_21_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_21_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_21_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_22_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_22_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_22_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_22_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_22_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_22_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_22_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_22_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_22_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_22_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_22_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_22_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_22_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_22_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_22_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_22_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_22_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_22_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    entry_condition_23_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=False, load=True)
    entry_23_protection__ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_23_protection__ema_fast_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_23_protection__ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_23_protection__ema_slow_len = CategoricalParameter(['26', '50', '100', '200'], default='50', space='entry', optimize=False, load=True)
    entry_23_protection__close_above_ema_fast = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_23_protection__close_above_ema_fast_len = CategoricalParameter(['12', '20', '26', '50', '100', '200'], default='200', space='entry', optimize=False, load=True)
    entry_23_protection__close_above_ema_slow = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_23_protection__close_above_ema_slow_len = CategoricalParameter(['15', '50', '200'], default='200', space='entry', optimize=False, load=True)
    entry_23_protection__sma200_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_23_protection__sma200_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_23_protection__sma200_1h_rising = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_23_protection__sma200_1h_rising_val = CategoricalParameter(['20', '30', '36', '44', '50'], default='50', space='entry', optimize=False, load=True)
    entry_23_protection__safe_dips = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_23_protection__safe_dips_type = CategoricalParameter(['strict', 'normal', 'loose'], default='strict', space='entry', optimize=False, load=True)
    entry_23_protection__safe_pump = CategoricalParameter([True, False], default=False, space='entry', optimize=False, load=True)
    entry_23_protection__safe_pump_type = CategoricalParameter(['strict', 'normal', 'loose'], default='normal', space='entry', optimize=False, load=True)
    entry_23_protection__safe_pump_period = CategoricalParameter(['24', '36', '48'], default='24', space='entry', optimize=False, load=True)
    # Normal dips
    entry_dip_threshold_1 = DecimalParameter(0.001, 0.05, default=0.02, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_2 = DecimalParameter(0.01, 0.2, default=0.14, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_3 = DecimalParameter(0.05, 0.4, default=0.32, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_4 = DecimalParameter(0.2, 0.5, default=0.5, space='entry', decimals=3, optimize=False, load=True)
    # Strict dips
    entry_dip_threshold_5 = DecimalParameter(0.001, 0.05, default=0.015, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_6 = DecimalParameter(0.01, 0.2, default=0.06, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_7 = DecimalParameter(0.05, 0.4, default=0.24, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_8 = DecimalParameter(0.2, 0.5, default=0.4, space='entry', decimals=3, optimize=False, load=True)
    # Loose dips
    entry_dip_threshold_9 = DecimalParameter(0.001, 0.05, default=0.026, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_10 = DecimalParameter(0.01, 0.2, default=0.24, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_11 = DecimalParameter(0.05, 0.4, default=0.42, space='entry', decimals=3, optimize=False, load=True)
    entry_dip_threshold_12 = DecimalParameter(0.2, 0.5, default=0.66, space='entry', decimals=3, optimize=False, load=True)
    # 24 hours
    entry_pump_pull_threshold_1 = DecimalParameter(1.5, 3.0, default=1.75, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_1 = DecimalParameter(0.4, 1.0, default=0.6, space='entry', decimals=3, optimize=False, load=True)
    # 36 hours
    entry_pump_pull_threshold_2 = DecimalParameter(1.5, 3.0, default=1.75, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_2 = DecimalParameter(0.4, 1.0, default=0.64, space='entry', decimals=3, optimize=False, load=True)
    # 48 hours
    entry_pump_pull_threshold_3 = DecimalParameter(1.5, 3.0, default=1.75, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_3 = DecimalParameter(0.4, 1.0, default=0.85, space='entry', decimals=3, optimize=False, load=True)
    # 24 hours strict
    entry_pump_pull_threshold_4 = DecimalParameter(1.5, 3.0, default=2.2, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_4 = DecimalParameter(0.4, 1.0, default=0.42, space='entry', decimals=3, optimize=False, load=True)
    # 36 hours strict
    entry_pump_pull_threshold_5 = DecimalParameter(1.5, 3.0, default=2.0, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_5 = DecimalParameter(0.4, 1.0, default=0.58, space='entry', decimals=3, optimize=False, load=True)
    # 48 hours strict
    entry_pump_pull_threshold_6 = DecimalParameter(1.5, 3.0, default=2.0, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_6 = DecimalParameter(0.4, 1.0, default=0.8, space='entry', decimals=3, optimize=False, load=True)
    # 24 hours loose
    entry_pump_pull_threshold_7 = DecimalParameter(1.5, 3.0, default=1.7, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_7 = DecimalParameter(0.4, 1.0, default=0.66, space='entry', decimals=3, optimize=False, load=True)
    # 36 hours loose
    entry_pump_pull_threshold_8 = DecimalParameter(1.5, 3.0, default=1.7, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_8 = DecimalParameter(0.4, 1.0, default=0.7, space='entry', decimals=3, optimize=False, load=True)
    # 48 hours loose
    entry_pump_pull_threshold_9 = DecimalParameter(1.3, 2.0, default=1.4, space='entry', decimals=2, optimize=False, load=True)
    entry_pump_threshold_9 = DecimalParameter(0.4, 1.8, default=1.6, space='entry', decimals=3, optimize=False, load=True)
    entry_min_inc_1 = DecimalParameter(0.01, 0.05, default=0.022, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_1h_min_1 = DecimalParameter(25.0, 40.0, default=30.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_max_1 = DecimalParameter(70.0, 90.0, default=84.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1 = DecimalParameter(20.0, 40.0, default=36.0, space='entry', decimals=1, optimize=False, load=True)
    entry_mfi_1 = DecimalParameter(20.0, 40.0, default=36.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_min_2 = DecimalParameter(30.0, 40.0, default=32.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_max_2 = DecimalParameter(70.0, 95.0, default=84.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_diff_2 = DecimalParameter(30.0, 50.0, default=39.0, space='entry', decimals=1, optimize=False, load=True)
    entry_mfi_2 = DecimalParameter(30.0, 56.0, default=49.0, space='entry', decimals=1, optimize=False, load=True)
    entry_bb_offset_2 = DecimalParameter(0.97, 0.999, default=0.983, space='entry', decimals=3, optimize=False, load=True)
    entry_bb40_bbdelta_close_3 = DecimalParameter(0.005, 0.06, default=0.057, space='entry', optimize=False, load=True)
    entry_bb40_closedelta_close_3 = DecimalParameter(0.01, 0.03, default=0.023, space='entry', optimize=False, load=True)
    entry_bb40_tail_bbdelta_3 = DecimalParameter(0.15, 0.45, default=0.418, space='entry', optimize=False, load=True)
    entry_ema_rel_3 = DecimalParameter(0.97, 0.999, default=0.986, space='entry', decimals=3, optimize=False, load=True)
    entry_bb20_close_bblowerband_4 = DecimalParameter(0.96, 0.99, default=0.979, space='entry', optimize=False, load=True)
    entry_bb20_volume_4 = DecimalParameter(1.0, 20.0, default=10.0, space='entry', decimals=2, optimize=False, load=True)
    entry_ema_open_mult_5 = DecimalParameter(0.016, 0.03, default=0.018, space='entry', decimals=3, optimize=False, load=True)
    entry_bb_offset_5 = DecimalParameter(0.98, 1.0, default=0.996, space='entry', decimals=3, optimize=False, load=True)
    entry_ema_rel_5 = DecimalParameter(0.97, 0.999, default=0.982, space='entry', decimals=3, optimize=False, load=True)
    entry_ema_open_mult_6 = DecimalParameter(0.02, 0.03, default=0.024, space='entry', decimals=3, optimize=False, load=True)
    entry_bb_offset_6 = DecimalParameter(0.98, 0.999, default=0.984, space='entry', decimals=3, optimize=False, load=True)
    entry_ema_open_mult_7 = DecimalParameter(0.02, 0.04, default=0.03, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_7 = DecimalParameter(24.0, 50.0, default=36.0, space='entry', decimals=1, optimize=False, load=True)
    entry_ema_rel_7 = DecimalParameter(0.97, 0.999, default=0.986, space='entry', decimals=3, optimize=False, load=True)
    entry_volume_8 = DecimalParameter(1.0, 6.0, default=2.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_8 = DecimalParameter(16.0, 30.0, default=20.0, space='entry', decimals=1, optimize=False, load=True)
    entry_tail_diff_8 = DecimalParameter(3.0, 10.0, default=3.5, space='entry', decimals=1, optimize=False, load=True)
    entry_ma_offset_9 = DecimalParameter(0.94, 0.99, default=0.97, space='entry', decimals=3, optimize=False, load=True)
    entry_bb_offset_9 = DecimalParameter(0.97, 0.99, default=0.985, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_1h_min_9 = DecimalParameter(26.0, 40.0, default=30.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_max_9 = DecimalParameter(70.0, 90.0, default=88.0, space='entry', decimals=1, optimize=False, load=True)
    entry_mfi_9 = DecimalParameter(26.0, 40.0, default=30.0, space='entry', decimals=1, optimize=False, load=True)
    entry_ma_offset_10 = DecimalParameter(0.93, 0.97, default=0.944, space='entry', decimals=3, optimize=False, load=True)
    entry_bb_offset_10 = DecimalParameter(0.97, 0.99, default=0.994, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_1h_10 = DecimalParameter(20.0, 40.0, default=37.0, space='entry', decimals=1, optimize=False, load=True)
    entry_ma_offset_11 = DecimalParameter(0.93, 0.99, default=0.939, space='entry', decimals=3, optimize=False, load=True)
    entry_min_inc_11 = DecimalParameter(0.005, 0.05, default=0.022, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_1h_min_11 = DecimalParameter(40.0, 60.0, default=56.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_max_11 = DecimalParameter(70.0, 90.0, default=84.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_11 = DecimalParameter(30.0, 48.0, default=48.0, space='entry', decimals=1, optimize=False, load=True)
    entry_mfi_11 = DecimalParameter(36.0, 56.0, default=38.0, space='entry', decimals=1, optimize=False, load=True)
    entry_ma_offset_12 = DecimalParameter(0.93, 0.97, default=0.936, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_12 = DecimalParameter(26.0, 40.0, default=30.0, space='entry', decimals=1, optimize=False, load=True)
    entry_ewo_12 = DecimalParameter(2.0, 6.0, default=2.0, space='entry', decimals=1, optimize=False, load=True)
    entry_ma_offset_13 = DecimalParameter(0.93, 0.98, default=0.978, space='entry', decimals=3, optimize=False, load=True)
    entry_ewo_13 = DecimalParameter(-14.0, -7.0, default=-10.4, space='entry', decimals=1, optimize=False, load=True)
    entry_ema_open_mult_14 = DecimalParameter(0.01, 0.03, default=0.014, space='entry', decimals=3, optimize=False, load=True)
    entry_bb_offset_14 = DecimalParameter(0.98, 1.0, default=0.986, space='entry', decimals=3, optimize=False, load=True)
    entry_ma_offset_14 = DecimalParameter(0.93, 0.99, default=0.97, space='entry', decimals=3, optimize=False, load=True)
    entry_ema_open_mult_15 = DecimalParameter(0.01, 0.03, default=0.018, space='entry', decimals=3, optimize=False, load=True)
    entry_ma_offset_15 = DecimalParameter(0.93, 0.99, default=0.954, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_15 = DecimalParameter(20.0, 36.0, default=28.0, space='entry', decimals=1, optimize=False, load=True)
    entry_ema_rel_15 = DecimalParameter(0.97, 0.999, default=0.988, space='entry', decimals=3, optimize=False, load=True)
    entry_ma_offset_16 = DecimalParameter(0.93, 0.97, default=0.952, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_16 = DecimalParameter(26.0, 50.0, default=31.0, space='entry', decimals=1, optimize=False, load=True)
    entry_ewo_16 = DecimalParameter(2.0, 6.0, default=2.8, space='entry', decimals=1, optimize=False, load=True)
    entry_ma_offset_17 = DecimalParameter(0.93, 0.98, default=0.958, space='entry', decimals=3, optimize=False, load=True)
    entry_ewo_17 = DecimalParameter(-18.0, -10.0, default=-12.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_18 = DecimalParameter(16.0, 32.0, default=26.0, space='entry', decimals=1, optimize=False, load=True)
    entry_bb_offset_18 = DecimalParameter(0.98, 1.0, default=0.982, space='entry', decimals=3, optimize=False, load=True)
    entry_rsi_1h_min_19 = DecimalParameter(40.0, 70.0, default=50.0, space='entry', decimals=1, optimize=False, load=True)
    entry_chop_min_19 = DecimalParameter(20.0, 60.0, default=24.1, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_20 = DecimalParameter(20.0, 36.0, default=27.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_20 = DecimalParameter(14.0, 30.0, default=20.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_21 = DecimalParameter(10.0, 28.0, default=23.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_21 = DecimalParameter(18.0, 40.0, default=24.0, space='entry', decimals=1, optimize=False, load=True)
    entry_volume_22 = DecimalParameter(0.5, 6.0, default=3.0, space='entry', decimals=1, optimize=False, load=True)
    entry_bb_offset_22 = DecimalParameter(0.98, 1.0, default=0.98, space='entry', decimals=3, optimize=False, load=True)
    entry_ma_offset_22 = DecimalParameter(0.93, 0.98, default=0.94, space='entry', decimals=3, optimize=False, load=True)
    entry_ewo_22 = DecimalParameter(2.0, 10.0, default=4.2, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_22 = DecimalParameter(26.0, 56.0, default=37.0, space='entry', decimals=1, optimize=False, load=True)
    entry_bb_offset_23 = DecimalParameter(0.97, 1.0, default=0.987, space='entry', decimals=3, optimize=False, load=True)
    entry_ewo_23 = DecimalParameter(2.0, 10.0, default=7.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_23 = DecimalParameter(20.0, 40.0, default=30.0, space='entry', decimals=1, optimize=False, load=True)
    entry_rsi_1h_23 = DecimalParameter(60.0, 80.0, default=70.0, space='entry', decimals=1, optimize=False, load=True)
    # Sell
    exit_condition_1_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=False, load=True)
    exit_condition_2_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=False, load=True)
    exit_condition_3_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=False, load=True)
    exit_condition_4_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=False, load=True)
    exit_condition_5_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=False, load=True)
    exit_condition_6_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=False, load=True)
    exit_condition_7_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=False, load=True)
    exit_condition_8_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=False, load=True)
    exit_rsi_bb_1 = DecimalParameter(60.0, 80.0, default=79.5, space='exit', decimals=1, optimize=False, load=True)
    exit_rsi_bb_2 = DecimalParameter(72.0, 90.0, default=81, space='exit', decimals=1, optimize=False, load=True)
    exit_rsi_main_3 = DecimalParameter(77.0, 90.0, default=82, space='exit', decimals=1, optimize=False, load=True)
    exit_dual_rsi_rsi_4 = DecimalParameter(72.0, 84.0, default=73.4, space='exit', decimals=1, optimize=False, load=True)
    exit_dual_rsi_rsi_1h_4 = DecimalParameter(78.0, 92.0, default=79.6, space='exit', decimals=1, optimize=False, load=True)
    exit_ema_relative_5 = DecimalParameter(0.005, 0.05, default=0.024, space='exit', optimize=False, load=True)
    exit_rsi_diff_5 = DecimalParameter(0.0, 20.0, default=4.4, space='exit', optimize=False, load=True)
    exit_rsi_under_6 = DecimalParameter(72.0, 90.0, default=79.0, space='exit', decimals=1, optimize=False, load=True)
    exit_rsi_1h_7 = DecimalParameter(80.0, 95.0, default=81.7, space='exit', decimals=1, optimize=False, load=True)
    exit_bb_relative_8 = DecimalParameter(1.05, 1.3, default=1.1, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_profit_0 = DecimalParameter(0.01, 0.1, default=0.01, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_rsi_0 = DecimalParameter(30.0, 40.0, default=33.0, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_profit_1 = DecimalParameter(0.01, 0.1, default=0.03, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_rsi_1 = DecimalParameter(30.0, 50.0, default=38.0, space='exit', decimals=2, optimize=False, load=True)
    exit_custom_profit_2 = DecimalParameter(0.01, 0.1, default=0.05, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_rsi_2 = DecimalParameter(34.0, 50.0, default=43.0, space='exit', decimals=2, optimize=False, load=True)
    exit_custom_profit_3 = DecimalParameter(0.06, 0.3, default=0.08, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_rsi_3 = DecimalParameter(38.0, 55.0, default=48.0, space='exit', decimals=2, optimize=False, load=True)
    exit_custom_profit_4 = DecimalParameter(0.06, 0.3, default=0.1, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_rsi_4 = DecimalParameter(38.0, 55.0, default=50.0, space='exit', decimals=2, optimize=False, load=True)
    exit_custom_profit_5 = DecimalParameter(0.2, 0.45, default=0.12, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_rsi_5 = DecimalParameter(40.0, 58.0, default=42.0, space='exit', decimals=2, optimize=False, load=True)
    exit_custom_profit_6 = DecimalParameter(0.16, 0.45, default=0.2, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_rsi_6 = DecimalParameter(20.0, 40.0, default=34.0, space='exit', decimals=2, optimize=False, load=True)
    # Profit under EMA200
    exit_custom_under_profit_0 = DecimalParameter(0.01, 0.4, default=0.01, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_under_rsi_0 = DecimalParameter(28.0, 40.0, default=33.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_under_profit_1 = DecimalParameter(0.01, 0.1, default=0.02, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_under_rsi_1 = DecimalParameter(36.0, 60.0, default=56.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_under_profit_2 = DecimalParameter(0.01, 0.1, default=0.04, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_under_rsi_2 = DecimalParameter(46.0, 66.0, default=60.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_under_profit_3 = DecimalParameter(0.01, 0.1, default=0.06, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_under_rsi_3 = DecimalParameter(50.0, 68.0, default=62.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_under_profit_4 = DecimalParameter(0.05, 0.12, default=0.08, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_under_rsi_4 = DecimalParameter(50.0, 68.0, default=56.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_under_profit_5 = DecimalParameter(0.06, 0.14, default=0.1, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_under_rsi_5 = DecimalParameter(36.0, 48.0, default=42.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_under_profit_6 = DecimalParameter(0.16, 0.3, default=0.2, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_under_rsi_6 = DecimalParameter(20.0, 40.0, default=34.0, space='exit', decimals=1, optimize=False, load=True)
    # Profit targets for pumped pairs 48h 1
    exit_custom_pump_profit_1_1 = DecimalParameter(0.01, 0.03, default=0.01, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_1_1 = DecimalParameter(26.0, 40.0, default=34.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_1_2 = DecimalParameter(0.01, 0.6, default=0.02, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_1_2 = DecimalParameter(36.0, 50.0, default=40.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_1_3 = DecimalParameter(0.02, 0.1, default=0.04, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_1_3 = DecimalParameter(38.0, 50.0, default=42.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_1_4 = DecimalParameter(0.06, 0.12, default=0.1, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_1_4 = DecimalParameter(36.0, 48.0, default=42.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_1_5 = DecimalParameter(0.14, 0.24, default=0.2, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_1_5 = DecimalParameter(20.0, 40.0, default=34.0, space='exit', decimals=1, optimize=False, load=True)
    # Profit targets for pumped pairs 36h 1
    exit_custom_pump_profit_2_1 = DecimalParameter(0.01, 0.03, default=0.01, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_2_1 = DecimalParameter(26.0, 40.0, default=34.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_2_2 = DecimalParameter(0.01, 0.6, default=0.02, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_2_2 = DecimalParameter(36.0, 50.0, default=40.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_2_3 = DecimalParameter(0.02, 0.1, default=0.04, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_2_3 = DecimalParameter(38.0, 50.0, default=40.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_2_4 = DecimalParameter(0.06, 0.12, default=0.1, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_2_4 = DecimalParameter(36.0, 48.0, default=42.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_2_5 = DecimalParameter(0.14, 0.24, default=0.2, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_2_5 = DecimalParameter(20.0, 40.0, default=34.0, space='exit', decimals=1, optimize=False, load=True)
    # Profit targets for pumped pairs 24h 1
    exit_custom_pump_profit_3_1 = DecimalParameter(0.01, 0.03, default=0.01, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_3_1 = DecimalParameter(26.0, 40.0, default=34.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_3_2 = DecimalParameter(0.01, 0.6, default=0.02, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_3_2 = DecimalParameter(34.0, 50.0, default=40.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_3_3 = DecimalParameter(0.02, 0.1, default=0.04, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_3_3 = DecimalParameter(38.0, 50.0, default=40.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_3_4 = DecimalParameter(0.06, 0.12, default=0.1, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_3_4 = DecimalParameter(36.0, 48.0, default=42.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_profit_3_5 = DecimalParameter(0.14, 0.24, default=0.2, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_rsi_3_5 = DecimalParameter(20.0, 40.0, default=34.0, space='exit', decimals=1, optimize=False, load=True)
    # SMA descending
    exit_custom_dec_profit_min_1 = DecimalParameter(0.01, 0.1, default=0.05, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_dec_profit_max_1 = DecimalParameter(0.06, 0.16, default=0.12, space='exit', decimals=3, optimize=False, load=True)
    # Under EMA100
    exit_custom_dec_profit_min_2 = DecimalParameter(0.05, 0.12, default=0.07, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_dec_profit_max_2 = DecimalParameter(0.06, 0.2, default=0.16, space='exit', decimals=3, optimize=False, load=True)
    # Trail 1
    exit_trail_profit_min_1 = DecimalParameter(0.1, 0.2, default=0.16, space='exit', decimals=2, optimize=False, load=True)
    exit_trail_profit_max_1 = DecimalParameter(0.4, 0.7, default=0.6, space='exit', decimals=2, optimize=False, load=True)
    exit_trail_down_1 = DecimalParameter(0.01, 0.08, default=0.03, space='exit', decimals=3, optimize=False, load=True)
    exit_trail_rsi_min_1 = DecimalParameter(16.0, 36.0, default=20.0, space='exit', decimals=1, optimize=False, load=True)
    exit_trail_rsi_max_1 = DecimalParameter(30.0, 50.0, default=50.0, space='exit', decimals=1, optimize=False, load=True)
    # Trail 2
    exit_trail_profit_min_2 = DecimalParameter(0.08, 0.16, default=0.1, space='exit', decimals=3, optimize=False, load=True)
    exit_trail_profit_max_2 = DecimalParameter(0.3, 0.5, default=0.4, space='exit', decimals=2, optimize=False, load=True)
    exit_trail_down_2 = DecimalParameter(0.02, 0.08, default=0.03, space='exit', decimals=3, optimize=False, load=True)
    exit_trail_rsi_min_2 = DecimalParameter(16.0, 36.0, default=20.0, space='exit', decimals=1, optimize=False, load=True)
    exit_trail_rsi_max_2 = DecimalParameter(30.0, 50.0, default=50.0, space='exit', decimals=1, optimize=False, load=True)
    # Trail 3
    exit_trail_profit_min_3 = DecimalParameter(0.01, 0.12, default=0.06, space='exit', decimals=3, optimize=False, load=True)
    exit_trail_profit_max_3 = DecimalParameter(0.1, 0.3, default=0.2, space='exit', decimals=2, optimize=False, load=True)
    exit_trail_down_3 = DecimalParameter(0.01, 0.06, default=0.05, space='exit', decimals=3, optimize=False, load=True)
    # Under & near EMA200, accept profit
    exit_custom_profit_under_rel_1 = DecimalParameter(0.01, 0.04, default=0.024, space='exit', optimize=False, load=True)
    exit_custom_profit_under_rsi_diff_1 = DecimalParameter(0.0, 20.0, default=4.4, space='exit', optimize=False, load=True)
    # Under & near EMA200, take the loss
    exit_custom_stoploss_under_rel_1 = DecimalParameter(0.001, 0.02, default=0.004, space='exit', optimize=False, load=True)
    exit_custom_stoploss_under_rsi_diff_1 = DecimalParameter(0.0, 20.0, default=8.0, space='exit', optimize=False, load=True)
    # 48h for pump exit checks
    exit_pump_threshold_1 = DecimalParameter(0.5, 1.2, default=0.9, space='exit', decimals=2, optimize=False, load=True)
    exit_pump_threshold_2 = DecimalParameter(0.4, 0.9, default=0.7, space='exit', decimals=2, optimize=False, load=True)
    exit_pump_threshold_3 = DecimalParameter(0.3, 0.7, default=0.5, space='exit', decimals=2, optimize=False, load=True)
    # 36h for pump exit checks
    exit_pump_threshold_4 = DecimalParameter(0.5, 0.9, default=0.72, space='exit', decimals=2, optimize=False, load=True)
    exit_pump_threshold_5 = DecimalParameter(3.0, 6.0, default=4.0, space='exit', decimals=2, optimize=False, load=True)
    exit_pump_threshold_6 = DecimalParameter(0.8, 1.6, default=1.0, space='exit', decimals=2, optimize=False, load=True)
    # 24h for pump exit checks
    exit_pump_threshold_7 = DecimalParameter(0.5, 0.9, default=0.68, space='exit', decimals=2, optimize=False, load=True)
    exit_pump_threshold_8 = DecimalParameter(0.3, 0.6, default=0.4, space='exit', decimals=2, optimize=False, load=True)
    exit_pump_threshold_9 = DecimalParameter(0.2, 0.5, default=0.3, space='exit', decimals=2, optimize=False, load=True)
    # Pumped, descending SMA
    exit_custom_pump_dec_profit_min_1 = DecimalParameter(0.001, 0.04, default=0.005, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_dec_profit_max_1 = DecimalParameter(0.03, 0.08, default=0.05, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_dec_profit_min_2 = DecimalParameter(0.01, 0.08, default=0.04, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_dec_profit_max_2 = DecimalParameter(0.04, 0.1, default=0.06, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_dec_profit_min_3 = DecimalParameter(0.02, 0.1, default=0.06, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_dec_profit_max_3 = DecimalParameter(0.06, 0.12, default=0.09, space='exit', decimals=3, optimize=False, load=True)
    # Pumped 48h 1, under EMA200
    exit_custom_pump_under_profit_min_1 = DecimalParameter(0.02, 0.06, default=0.04, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_under_profit_max_1 = DecimalParameter(0.04, 0.1, default=0.09, space='exit', decimals=3, optimize=False, load=True)
    # Pumped trail 1
    exit_custom_pump_trail_profit_min_1 = DecimalParameter(0.01, 0.12, default=0.05, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_trail_profit_max_1 = DecimalParameter(0.06, 0.16, default=0.07, space='exit', decimals=2, optimize=False, load=True)
    exit_custom_pump_trail_down_1 = DecimalParameter(0.01, 0.06, default=0.05, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_pump_trail_rsi_min_1 = DecimalParameter(16.0, 36.0, default=20.0, space='exit', decimals=1, optimize=False, load=True)
    exit_custom_pump_trail_rsi_max_1 = DecimalParameter(30.0, 50.0, default=70.0, space='exit', decimals=1, optimize=False, load=True)
    # Stoploss, pumped, 48h 1
    exit_custom_stoploss_pump_max_profit_1 = DecimalParameter(0.01, 0.04, default=0.025, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_stoploss_pump_min_1 = DecimalParameter(-0.1, -0.01, default=-0.02, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_stoploss_pump_max_1 = DecimalParameter(-0.1, -0.01, default=-0.01, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_stoploss_pump_ma_offset_1 = DecimalParameter(0.7, 0.99, default=0.94, space='exit', decimals=2, optimize=False, load=True)
    # Stoploss, pumped, 48h 1
    exit_custom_stoploss_pump_max_profit_2 = DecimalParameter(0.01, 0.04, default=0.025, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_stoploss_pump_loss_2 = DecimalParameter(-0.1, -0.01, default=-0.05, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_stoploss_pump_ma_offset_2 = DecimalParameter(0.7, 0.99, default=0.92, space='exit', decimals=2, optimize=False, load=True)
    # Stoploss, pumped, 36h 3
    exit_custom_stoploss_pump_max_profit_3 = DecimalParameter(0.01, 0.04, default=0.008, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_stoploss_pump_loss_3 = DecimalParameter(-0.16, -0.06, default=-0.12, space='exit', decimals=3, optimize=False, load=True)
    exit_custom_stoploss_pump_ma_offset_3 = DecimalParameter(0.7, 0.99, default=0.88, space='exit', decimals=2, optimize=False, load=True)

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        max_profit = (trade.max_rate - trade.open_rate) / trade.open_rate
        if last_candle is not None:
            if (current_profit > self.exit_custom_profit_6.value) & (last_candle['rsi'] < self.exit_custom_rsi_6.value):
                return 'signal_profit_6'
            if (self.exit_custom_profit_6.value > current_profit > self.exit_custom_profit_5.value) & (last_candle['rsi'] < self.exit_custom_rsi_5.value):
                return 'signal_profit_5'
            elif (self.exit_custom_profit_5.value > current_profit > self.exit_custom_profit_4.value) & (last_candle['rsi'] < self.exit_custom_rsi_4.value):
                return 'signal_profit_4'
            elif (self.exit_custom_profit_4.value > current_profit > self.exit_custom_profit_3.value) & (last_candle['rsi'] < self.exit_custom_rsi_3.value):
                return 'signal_profit_3'
            elif (self.exit_custom_profit_3.value > current_profit > self.exit_custom_profit_2.value) & (last_candle['rsi'] < self.exit_custom_rsi_2.value):
                return 'signal_profit_2'
            elif (self.exit_custom_profit_2.value > current_profit > self.exit_custom_profit_1.value) & (last_candle['rsi'] < self.exit_custom_rsi_1.value):
                return 'signal_profit_1'
            elif (self.exit_custom_profit_1.value > current_profit > self.exit_custom_profit_0.value) & (last_candle['rsi'] < self.exit_custom_rsi_0.value):
                return 'signal_profit_0'
            # check if close is under EMA200
            elif (current_profit > self.exit_custom_under_profit_6.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_6.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_6'
            elif (self.exit_custom_under_profit_6.value > current_profit > self.exit_custom_under_profit_5.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_5.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_5'
            elif (self.exit_custom_under_profit_5.value > current_profit > self.exit_custom_under_profit_4.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_4.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_4'
            elif (self.exit_custom_under_profit_4.value > current_profit > self.exit_custom_under_profit_3.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_3.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_3'
            elif (self.exit_custom_under_profit_3.value > current_profit > self.exit_custom_under_profit_2.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_2.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_2'
            elif (self.exit_custom_under_profit_2.value > current_profit > self.exit_custom_under_profit_1.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_1.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_1'
            elif (self.exit_custom_under_profit_1.value > current_profit > self.exit_custom_under_profit_0.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_0.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_0'
            # check if the pair is "pumped"
            elif last_candle['exit_pump_48_1_1h'] & (current_profit > self.exit_custom_pump_profit_1_5.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_1_5.value):
                return 'signal_profit_p_1_5'
            elif last_candle['exit_pump_48_1_1h'] & (self.exit_custom_pump_profit_1_5.value > current_profit > self.exit_custom_pump_profit_1_4.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_1_4.value):
                return 'signal_profit_p_1_4'
            elif last_candle['exit_pump_48_1_1h'] & (self.exit_custom_pump_profit_1_4.value > current_profit > self.exit_custom_pump_profit_1_3.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_1_3.value):
                return 'signal_profit_p_1_3'
            elif last_candle['exit_pump_48_1_1h'] & (self.exit_custom_pump_profit_1_3.value > current_profit > self.exit_custom_pump_profit_1_2.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_1_2.value):
                return 'signal_profit_p_1_2'
            elif last_candle['exit_pump_48_1_1h'] & (self.exit_custom_pump_profit_1_2.value > current_profit > self.exit_custom_pump_profit_1_1.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_1_1.value):
                return 'signal_profit_p_1_1'
            elif last_candle['exit_pump_36_1_1h'] & (current_profit > self.exit_custom_pump_profit_2_5.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_2_5.value):
                return 'signal_profit_p_2_5'
            elif last_candle['exit_pump_36_1_1h'] & (self.exit_custom_pump_profit_2_5.value > current_profit > self.exit_custom_pump_profit_2_4.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_2_4.value):
                return 'signal_profit_p_2_4'
            elif last_candle['exit_pump_36_1_1h'] & (self.exit_custom_pump_profit_2_4.value > current_profit > self.exit_custom_pump_profit_2_3.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_2_3.value):
                return 'signal_profit_p_2_3'
            elif last_candle['exit_pump_36_1_1h'] & (self.exit_custom_pump_profit_2_3.value > current_profit > self.exit_custom_pump_profit_2_2.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_2_2.value):
                return 'signal_profit_p_2_2'
            elif last_candle['exit_pump_36_1_1h'] & (self.exit_custom_pump_profit_2_2.value > current_profit > self.exit_custom_pump_profit_2_1.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_2_1.value):
                return 'signal_profit_p_2_1'
            elif last_candle['exit_pump_24_1_1h'] & (current_profit > self.exit_custom_pump_profit_3_5.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_3_5.value):
                return 'signal_profit_p_3_5'
            elif last_candle['exit_pump_24_1_1h'] & (self.exit_custom_pump_profit_3_5.value > current_profit > self.exit_custom_pump_profit_3_4.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_3_4.value):
                return 'signal_profit_p_3_4'
            elif last_candle['exit_pump_24_1_1h'] & (self.exit_custom_pump_profit_3_4.value > current_profit > self.exit_custom_pump_profit_3_3.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_3_3.value):
                return 'signal_profit_p_3_3'
            elif last_candle['exit_pump_24_1_1h'] & (self.exit_custom_pump_profit_3_3.value > current_profit > self.exit_custom_pump_profit_3_2.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_3_2.value):
                return 'signal_profit_p_3_2'
            elif last_candle['exit_pump_24_1_1h'] & (self.exit_custom_pump_profit_3_2.value > current_profit > self.exit_custom_pump_profit_3_1.value) & (last_candle['rsi'] < self.exit_custom_pump_rsi_3_1.value):
                return 'signal_profit_p_3_1'
            elif (self.exit_custom_dec_profit_max_1.value > current_profit > self.exit_custom_dec_profit_min_1.value) & last_candle['sma_200_dec']:
                return 'signal_profit_d_1'
            elif (self.exit_custom_dec_profit_max_2.value > current_profit > self.exit_custom_dec_profit_min_2.value) & (last_candle['close'] < last_candle['ema_100']):
                return 'signal_profit_d_2'
            # Trailing
            elif (self.exit_trail_profit_max_1.value > current_profit > self.exit_trail_profit_min_1.value) & (self.exit_trail_rsi_min_1.value < last_candle['rsi'] < self.exit_trail_rsi_max_1.value) & (max_profit > current_profit + self.exit_trail_down_1.value):
                return 'signal_profit_t_1'
            elif (self.exit_trail_profit_max_2.value > current_profit > self.exit_trail_profit_min_2.value) & (self.exit_trail_rsi_min_2.value < last_candle['rsi'] < self.exit_trail_rsi_max_2.value) & (max_profit > current_profit + self.exit_trail_down_2.value):
                return 'signal_profit_t_2'
            elif (self.exit_trail_profit_max_3.value > current_profit > self.exit_trail_profit_min_3.value) & (max_profit > current_profit + self.exit_trail_down_3.value) & last_candle['sma_200_dec_1h']:
                return 'signal_profit_t_3'
            elif (last_candle['close'] < last_candle['ema_200']) & (current_profit > self.exit_trail_profit_min_3.value) & (current_profit < self.exit_trail_profit_max_3.value) & (max_profit > current_profit + self.exit_trail_down_3.value):
                return 'signal_profit_u_t_1'
            elif (current_profit > 0.0) & (last_candle['close'] < last_candle['ema_200']) & ((last_candle['ema_200'] - last_candle['close']) / last_candle['close'] < self.exit_custom_profit_under_rel_1.value) & (last_candle['rsi'] > last_candle['rsi_1h'] + self.exit_custom_profit_under_rsi_diff_1.value):
                return 'signal_profit_u_e_1'
            elif (current_profit < -0.0) & (last_candle['close'] < last_candle['ema_200']) & ((last_candle['ema_200'] - last_candle['close']) / last_candle['close'] < self.exit_custom_stoploss_under_rel_1.value) & (last_candle['rsi'] > last_candle['rsi_1h'] + self.exit_custom_stoploss_under_rsi_diff_1.value):
                return 'signal_stoploss_u_1'
            elif (self.exit_custom_pump_dec_profit_max_1.value > current_profit > self.exit_custom_pump_dec_profit_min_1.value) & last_candle['exit_pump_48_1_1h'] & last_candle['sma_200_dec'] & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_p_d_1'
            elif (self.exit_custom_pump_dec_profit_max_2.value > current_profit > self.exit_custom_pump_dec_profit_min_2.value) & last_candle['exit_pump_48_2_1h'] & last_candle['sma_200_dec'] & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_p_d_2'
            elif (self.exit_custom_pump_dec_profit_max_3.value > current_profit > self.exit_custom_pump_dec_profit_min_3.value) & last_candle['exit_pump_48_3_1h'] & last_candle['sma_200_dec'] & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_p_d_3'
            # Pumped 48h 1, under EMA200
            elif (self.exit_custom_pump_under_profit_max_1.value > current_profit > self.exit_custom_pump_under_profit_min_1.value) & last_candle['exit_pump_48_1_1h'] & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_p_u_1'
            # Pumped 36h 2, trail 1
            elif last_candle['exit_pump_36_2_1h'] & (self.exit_custom_pump_trail_profit_max_1.value > current_profit > self.exit_custom_pump_trail_profit_min_1.value) & (self.exit_custom_pump_trail_rsi_min_1.value < last_candle['rsi'] < self.exit_custom_pump_trail_rsi_max_1.value) & (max_profit > current_profit + self.exit_custom_pump_trail_down_1.value):
                return 'signal_profit_p_t_1'
            elif (max_profit < self.exit_custom_stoploss_pump_max_profit_1.value) & (self.exit_custom_stoploss_pump_min_1.value < current_profit < self.exit_custom_stoploss_pump_max_1.value) & last_candle['exit_pump_48_1_1h'] & last_candle['sma_200_dec'] & (last_candle['close'] < last_candle['ema_200'] * self.exit_custom_stoploss_pump_ma_offset_1.value):
                return 'signal_stoploss_p_1'
            elif (max_profit < self.exit_custom_stoploss_pump_max_profit_2.value) & (current_profit < self.exit_custom_stoploss_pump_loss_2.value) & last_candle['exit_pump_48_1_1h'] & last_candle['sma_200_dec_1h'] & (last_candle['close'] < last_candle['ema_200'] * self.exit_custom_stoploss_pump_ma_offset_2.value):
                return 'signal_stoploss_p_2'
            elif (max_profit < self.exit_custom_stoploss_pump_max_profit_3.value) & (current_profit < self.exit_custom_stoploss_pump_loss_3.value) & last_candle['exit_pump_36_3_1h'] & (last_candle['close'] < last_candle['ema_200'] * self.exit_custom_stoploss_pump_ma_offset_3.value):
                return 'signal_stoploss_p_3'
        return None

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        #pairs.append("BTC/USDT")
        #pairs.append("ETH/USDT")
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs
    ## smoothed Heiken Ashi

    def HA(self, dataframe, smoothing=None):
        df = dataframe.copy()
        df['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        df.reset_index(inplace=True)
        ha_open = [(df['open'][0] + df['close'][0]) / 2]
        [ha_open.append((ha_open[i] + df['HA_Close'].values[i]) / 2) for i in range(0, len(df) - 1)]
        df['HA_Open'] = ha_open
        df.set_index('index', inplace=True)
        df['HA_High'] = df[['HA_Open', 'HA_Close', 'high']].max(axis=1)
        df['HA_Low'] = df[['HA_Open', 'HA_Close', 'low']].min(axis=1)
        if smoothing is not None:
            sml = abs(int(smoothing))
            if sml > 0:
                df['Smooth_HA_O'] = ta.EMA(df['HA_Open'], sml)
                df['Smooth_HA_C'] = ta.EMA(df['HA_Close'], sml)
                df['Smooth_HA_H'] = ta.EMA(df['HA_High'], sml)
                df['Smooth_HA_L'] = ta.EMA(df['HA_Low'], sml)
        return df

    def hansen_HA(self, informative_df, period=6):
        dataframe = informative_df.copy()
        dataframe['hhclose'] = (dataframe['open'] + dataframe['high'] + dataframe['low'] + dataframe['close']) / 4
        dataframe['hhopen'] = (dataframe['open'].shift(2) + dataframe['close'].shift(2)) / 2  #it is not the same as real heikin ashi since I found that this is better.
        dataframe['hhhigh'] = dataframe[['open', 'close', 'high']].max(axis=1)
        dataframe['hhlow'] = dataframe[['open', 'close', 'low']].min(axis=1)
        dataframe['emac'] = ta.SMA(dataframe['hhclose'], timeperiod=period)  #to smooth out the data and thus less noise.
        dataframe['emao'] = ta.SMA(dataframe['hhopen'], timeperiod=period)
        return {'emac': dataframe['emac'], 'emao': dataframe['emao']}
    ## detect BB width expansion to indicate possible volatility

    def bbw_expansion(self, bbw_rolling, mult=1.1):
        bbw = list(bbw_rolling)
        m = 0.0
        for i in range(len(bbw) - 1):
            if bbw[i] > m:
                m = bbw[i]
        if bbw[-1] > m * mult:
            return 1
        return 0
    ## do_indicator style a la Obelisk strategies

    def do_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Stoch fast - mainly due to 5m timeframes
        stoch_fast = ta.STOCHF(dataframe)
        dataframe['fastd'] = stoch_fast['fastd']
        dataframe['fastk'] = stoch_fast['fastk']
        #StochRSI for double checking things
        period = 14
        smoothD = 3
        SmoothK = 3
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        stochrsi = (dataframe['rsi'] - dataframe['rsi'].rolling(period).min()) / (dataframe['rsi'].rolling(period).max() - dataframe['rsi'].rolling(period).min())
        dataframe['srsi_k'] = stochrsi.rolling(SmoothK).mean() * 100
        dataframe['srsi_d'] = dataframe['srsi_k'].rolling(smoothD).mean()
        # Bollinger Bands because obviously
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=1)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        # SAR Parabol - probably don't need this
        dataframe['sar'] = ta.SAR(dataframe)
        ## confirm wideboi variance signal with bbw expansion
        dataframe['bb_width'] = (dataframe['bb_upperband'] - dataframe['bb_lowerband']) / dataframe['bb_middleband']
        dataframe['bbw_expansion'] = dataframe['bb_width'].rolling(window=4).apply(self.bbw_expansion)
        # confirm entry and exit on smoothed HA
        dataframe = self.HA(dataframe, 4)
        # thanks to Hansen_Khornelius for this idea that I apply to the 1hr informative
        # https://github.com/hansen1015/freqtrade_strategy
        hansencalc = self.hansen_HA(dataframe, 6)
        dataframe['emac'] = hansencalc['emac']
        dataframe['emao'] = hansencalc['emao']
        # money flow index (MFI) for in/outflow of money, like RSI adjusted for vol
        dataframe['mfi'] = fta.MFI(dataframe)
        ## sqzmi to detect quiet periods
        dataframe['sqzmi'] = fta.SQZMI(dataframe)  #, MA=hansencalc['emac'])
        # Volume Flow Indicator (MFI) for volume based on the direction of price movement
        dataframe['vfi'] = fta.VFI(dataframe, period=14)
        dmi = fta.DMI(dataframe, period=14)
        dataframe['dmi_plus'] = dmi['DI+']
        dataframe['dmi_minus'] = dmi['DI-']
        dataframe['adx'] = fta.ADX(dataframe, period=14)
        ## for stoploss - all from Solipsis4
        ## simple ATR and ROC for stoploss
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['roc'] = ta.ROC(dataframe, timeperiod=9)
        dataframe['rmi'] = RMI(dataframe, length=24, mom=5)
        ssldown, sslup = SSLChannels_ATR(dataframe, length=21)
        dataframe['sroc'] = SROC(dataframe, roclen=21, emalen=13, smooth=21)
        dataframe['ssl-dir'] = np.where(sslup > ssldown, 'up', 'down')
        dataframe['rmi-up'] = np.where(dataframe['rmi'] >= dataframe['rmi'].shift(), 1, 0)
        dataframe['rmi-up-trend'] = np.where(dataframe['rmi-up'].rolling(5).sum() >= 3, 1, 0)
        dataframe['candle-up'] = np.where(dataframe['close'] >= dataframe['close'].shift(), 1, 0)
        dataframe['candle-up-trend'] = np.where(dataframe['candle-up'].rolling(5).sum() >= 3, 1, 0)
        return dataframe

    def informative_1h_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        assert self.dp, 'DataProvider is required for multiple timeframes.'
        # Get the informative pair
        informative_1h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.informative_timeframe)
        # EMA
        informative_1h['ema_15'] = ta.EMA(informative_1h, timeperiod=15)
        informative_1h['ema_20'] = ta.EMA(informative_1h, timeperiod=20)
        informative_1h['ema_26'] = ta.EMA(informative_1h, timeperiod=26)
        informative_1h['ema_50'] = ta.EMA(informative_1h, timeperiod=50)
        informative_1h['ema_100'] = ta.EMA(informative_1h, timeperiod=100)
        informative_1h['ema_200'] = ta.EMA(informative_1h, timeperiod=200)
        # SMA
        informative_1h['sma_200'] = ta.SMA(informative_1h, timeperiod=200)
        informative_1h['sma_200_dec'] = informative_1h['sma_200'] < informative_1h['sma_200'].shift(20)
        # RSI
        informative_1h['rsi'] = ta.RSI(informative_1h, timeperiod=14)
        # BB
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(informative_1h), window=20, stds=2)
        informative_1h['bb_lowerband'] = bollinger['lower']
        informative_1h['bb_middleband'] = bollinger['mid']
        informative_1h['bb_upperband'] = bollinger['upper']
        # Pump protections
        informative_1h['safe_pump_24_normal'] = self.safe_pump(informative_1h, 24, self.entry_pump_threshold_1.value, self.entry_pump_pull_threshold_1.value)
        informative_1h['safe_pump_36_normal'] = self.safe_pump(informative_1h, 36, self.entry_pump_threshold_2.value, self.entry_pump_pull_threshold_2.value)
        informative_1h['safe_pump_48_normal'] = self.safe_pump(informative_1h, 48, self.entry_pump_threshold_3.value, self.entry_pump_pull_threshold_3.value)
        informative_1h['safe_pump_24_strict'] = self.safe_pump(informative_1h, 24, self.entry_pump_threshold_4.value, self.entry_pump_pull_threshold_4.value)
        informative_1h['safe_pump_36_strict'] = self.safe_pump(informative_1h, 36, self.entry_pump_threshold_5.value, self.entry_pump_pull_threshold_5.value)
        informative_1h['safe_pump_48_strict'] = self.safe_pump(informative_1h, 48, self.entry_pump_threshold_6.value, self.entry_pump_pull_threshold_6.value)
        informative_1h['safe_pump_24_loose'] = self.safe_pump(informative_1h, 24, self.entry_pump_threshold_7.value, self.entry_pump_pull_threshold_7.value)
        informative_1h['safe_pump_36_loose'] = self.safe_pump(informative_1h, 36, self.entry_pump_threshold_8.value, self.entry_pump_pull_threshold_8.value)
        informative_1h['safe_pump_48_loose'] = self.safe_pump(informative_1h, 48, self.entry_pump_threshold_9.value, self.entry_pump_pull_threshold_9.value)
        informative_1h['exit_pump_48_1'] = (informative_1h['high'].rolling(48).max() - informative_1h['low'].rolling(48).min()) / informative_1h['low'].rolling(48).min() > self.exit_pump_threshold_1.value
        informative_1h['exit_pump_48_2'] = (informative_1h['high'].rolling(48).max() - informative_1h['low'].rolling(48).min()) / informative_1h['low'].rolling(48).min() > self.exit_pump_threshold_2.value
        informative_1h['exit_pump_48_3'] = (informative_1h['high'].rolling(48).max() - informative_1h['low'].rolling(48).min()) / informative_1h['low'].rolling(48).min() > self.exit_pump_threshold_3.value
        informative_1h['exit_pump_36_1'] = (informative_1h['high'].rolling(36).max() - informative_1h['low'].rolling(36).min()) / informative_1h['low'].rolling(36).min() > self.exit_pump_threshold_4.value
        informative_1h['exit_pump_36_2'] = (informative_1h['high'].rolling(36).max() - informative_1h['low'].rolling(36).min()) / informative_1h['low'].rolling(36).min() > self.exit_pump_threshold_5.value
        informative_1h['exit_pump_36_3'] = (informative_1h['high'].rolling(36).max() - informative_1h['low'].rolling(36).min()) / informative_1h['low'].rolling(36).min() > self.exit_pump_threshold_6.value
        informative_1h['exit_pump_24_1'] = (informative_1h['high'].rolling(24).max() - informative_1h['low'].rolling(24).min()) / informative_1h['low'].rolling(24).min() > self.exit_pump_threshold_7.value
        informative_1h['exit_pump_24_2'] = (informative_1h['high'].rolling(24).max() - informative_1h['low'].rolling(24).min()) / informative_1h['low'].rolling(24).min() > self.exit_pump_threshold_8.value
        informative_1h['exit_pump_24_3'] = (informative_1h['high'].rolling(24).max() - informative_1h['low'].rolling(24).min()) / informative_1h['low'].rolling(24).min() > self.exit_pump_threshold_9.value
        return informative_1h

    def range_percent_change(self, dataframe: DataFrame, length: int) -> float:
        """
        Rolling Percentage Change Maximum across interval.

        :param dataframe: DataFrame The original OHLC dataframe
        :param length: int The length to look back
        """
        df = dataframe.copy()
        return (df['open'].rolling(length).max() - df['close'].rolling(length).min()) / df['close'].rolling(length).min()

    def range_maxgap(self, dataframe: DataFrame, length: int) -> float:
        """
        Maximum Price Gap across interval.

        :param dataframe: DataFrame The original OHLC dataframe
        :param length: int The length to look back
        """
        df = dataframe.copy()
        return df['open'].rolling(length).max() - df['close'].rolling(length).min()

    def range_maxgap_adjusted(self, dataframe: DataFrame, length: int, adjustment: float) -> float:
        """
        Maximum Price Gap across interval adjusted.

        :param dataframe: DataFrame The original OHLC dataframe
        :param length: int The length to look back
        :param adjustment: int The adjustment to be applied
        """
        return self.range_maxgap(dataframe, length) / adjustment

    def range_height(self, dataframe: DataFrame, length: int) -> float:
        """
        Current close distance to range bottom.

        :param dataframe: DataFrame The original OHLC dataframe
        :param length: int The length to look back
        """
        df = dataframe.copy()
        return df['close'] - df['close'].rolling(length).min()

    def safe_pump(self, dataframe: DataFrame, length: int, thresh: float, pull_thresh: float) -> bool:
        """
        Determine if entry after a pump is safe.

        :param dataframe: DataFrame The original OHLC dataframe
        :param length: int The length to look back
        :param thresh: int Maximum percentage change threshold
        :param pull_thresh: int Pullback from interval maximum threshold
        """
        df = dataframe.copy()
        return (self.range_percent_change(df, length) < thresh) | (self.range_maxgap_adjusted(df, length, pull_thresh) > self.range_height(df, length))

    def normal_tf_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # BB 40
        bb_40 = qtpylib.bollinger_bands(dataframe['close'], window=40, stds=2)
        dataframe['lower'] = bb_40['lower']
        dataframe['mid'] = bb_40['mid']
        dataframe['bbdelta'] = (bb_40['mid'] - dataframe['lower']).abs()
        dataframe['closedelta'] = (dataframe['close'] - dataframe['close'].shift()).abs()
        dataframe['tail'] = (dataframe['close'] - dataframe['low']).abs()
        # BB 20
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        # EMA 200
        dataframe['ema_12'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema_26'] = ta.EMA(dataframe, timeperiod=26)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_100'] = ta.EMA(dataframe, timeperiod=100)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        # SMA
        dataframe['sma_5'] = ta.SMA(dataframe, timeperiod=5)
        dataframe['sma_30'] = ta.SMA(dataframe, timeperiod=30)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        dataframe['sma_200_dec'] = dataframe['sma_200'] < dataframe['sma_200'].shift(20)
        # MFI
        dataframe['mfi'] = ta.MFI(dataframe)
        # EWO
        dataframe['ewo'] = EWO(dataframe, 50, 200)
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        # Chopiness
        dataframe['chop'] = qtpylib.chopiness(dataframe, 14)
        # Dip protection
        dataframe['safe_dips_normal'] = ((dataframe['open'] - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_1.value) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_2.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_3.value) & ((dataframe['open'].rolling(144).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_4.value)
        dataframe['safe_dips_strict'] = ((dataframe['open'] - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_5.value) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_6.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_7.value) & ((dataframe['open'].rolling(144).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_8.value)
        dataframe['safe_dips_loose'] = ((dataframe['open'] - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_9.value) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_10.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_11.value) & ((dataframe['open'].rolling(144).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_12.value)
        # Volume
        dataframe['volume_mean_4'] = dataframe['volume'].rolling(4).mean().shift(1)
        dataframe['volume_mean_30'] = dataframe['volume'].rolling(30).mean()
        return dataframe
    ## stolen from Obelisk's Ichi strat code and backtest blog post, and Solipsis4

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # The indicators for the 1h informative timeframe
        informative_1h = self.informative_1h_indicators(dataframe, metadata)
        # Populate/update the trade data if there is any, set trades to false if not live/dry
        self.custom_trade_info[metadata['pair']] = self.populate_trades(metadata['pair'])
        if self.config['runmode'].value in ('backtest', 'hyperopt'):
            assert timeframe_to_minutes(self.timeframe) <= 30, 'Backtest this strategy in 5m or 1m timeframe.'
        if self.timeframe == self.informative_timeframe:
            dataframe = self.do_indicators(dataframe, metadata)
        else:
            if not self.dp:
                return dataframe
            informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.informative_timeframe)
            informative = self.do_indicators(informative.copy(), metadata)
            dataframe = merge_informative_pair(dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True)
            skip_columns = [s + '_' + self.informative_timeframe for s in ['date', 'open', 'high', 'low', 'close', 'volume', 'emac', 'emao']]
            dataframe.rename(columns=lambda s: s.replace('_{}'.format(self.informative_timeframe), '') if not s in skip_columns else s, inplace=True)
        # Slam some indicators into the trade_info dict so we can dynamic roi and custom stoploss in backtest
        if self.dp.runmode.value in ('backtest', 'hyperopt'):
            self.custom_trade_info[metadata['pair']]['roc'] = dataframe[['date', 'roc']].copy().set_index('date')
            self.custom_trade_info[metadata['pair']]['atr'] = dataframe[['date', 'atr']].copy().set_index('date')
            self.custom_trade_info[metadata['pair']]['sroc'] = dataframe[['date', 'sroc']].copy().set_index('date')
            self.custom_trade_info[metadata['pair']]['ssl-dir'] = dataframe[['date', 'ssl-dir']].copy().set_index('date')
            self.custom_trade_info[metadata['pair']]['rmi-up-trend'] = dataframe[['date', 'rmi-up-trend']].copy().set_index('date')
            self.custom_trade_info[metadata['pair']]['candle-up-trend'] = dataframe[['date', 'candle-up-trend']].copy().set_index('date')
        dataframe = merge_informative_pair(dataframe, informative_1h, self.timeframe, self.informative_timeframe, ffill=True)
        # The indicators for the normal (5m) timeframe
        dataframe = self.normal_tf_indicators(dataframe, metadata)
        return dataframe
    ## cryptofrog signals

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ## close ALWAYS needs to be lower than the heiken low at 5m
        ## Hansen's HA EMA at informative timeframe
        ## potential uptick incoming so entry
        # this tries to find extra entrys in undersold regions
        # find smaller temporary dips in sideways
        ## if nothing else is making a entry signal
        ## just throw in any old SQZMI shit based fastd
        ## this needs work!
        ## volume sanity checks
        dataframe.loc[(dataframe['close'] < dataframe['Smooth_HA_L']) & (dataframe['emac_1h'] < dataframe['emao_1h']) & ((dataframe['bbw_expansion'] == 1) & (dataframe['sqzmi'] == False) & ((dataframe['mfi'] < 20) | (dataframe['dmi_minus'] > 30)) | (dataframe['close'] < dataframe['sar']) & ((dataframe['srsi_d'] >= dataframe['srsi_k']) & (dataframe['srsi_d'] < 30)) & ((dataframe['fastd'] > dataframe['fastk']) & (dataframe['fastd'] < 23)) & (dataframe['mfi'] < 30) | ((dataframe['dmi_minus'] > 30) & qtpylib.crossed_above(dataframe['dmi_minus'], dataframe['dmi_plus']) & (dataframe['close'] < dataframe['bb_lowerband']) | (dataframe['sqzmi'] == True) & ((dataframe['fastd'] > dataframe['fastk']) & (dataframe['fastd'] < 20))) & (dataframe['vfi'] < 0.0) & (dataframe['volume'] > 0)), 'entry'] = 1
        return dataframe
    ## more going on here

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(self.exit_condition_1_enable.value & (dataframe['rsi'] > self.exit_rsi_bb_1.value) & (dataframe['close'] > dataframe['bb_upperband']) & (dataframe['close'].shift(1) > dataframe['bb_upperband'].shift(1)) & (dataframe['close'].shift(2) > dataframe['bb_upperband'].shift(2)) & (dataframe['close'].shift(3) > dataframe['bb_upperband'].shift(3)) & (dataframe['close'].shift(4) > dataframe['bb_upperband'].shift(4)) & (dataframe['close'].shift(5) > dataframe['bb_upperband'].shift(5)) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_2_enable.value & (dataframe['rsi'] > self.exit_rsi_bb_2.value) & (dataframe['close'] > dataframe['bb_upperband']) & (dataframe['close'].shift(1) > dataframe['bb_upperband'].shift(1)) & (dataframe['close'].shift(2) > dataframe['bb_upperband'].shift(2)) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_3_enable.value & (dataframe['rsi'] > self.exit_rsi_main_3.value) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_4_enable.value & (dataframe['rsi'] > self.exit_dual_rsi_rsi_4.value) & (dataframe['rsi_1h'] > self.exit_dual_rsi_rsi_1h_4.value) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_6_enable.value & (dataframe['close'] < dataframe['ema_200']) & (dataframe['close'] > dataframe['ema_50']) & (dataframe['rsi'] > self.exit_rsi_under_6.value) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_7_enable.value & (dataframe['rsi_1h'] > self.exit_rsi_1h_7.value) & qtpylib.crossed_below(dataframe['ema_12'], dataframe['ema_26']) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_8_enable.value & (dataframe['close'] > dataframe['bb_upperband_1h'] * self.exit_bb_relative_8.value) & (dataframe['volume'] > 0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit'] = 1
        return dataframe
    '\n    Everything from here completely stolen from the godly work of @werkkrew\n    \n    Custom Stoploss \n    '

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        trade_dur = int((current_time.timestamp() - trade.open_date_utc.timestamp()) // 60)
        if self.config['runmode'].value in ('live', 'dry_run'):
            dataframe, last_updated = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
            sroc = dataframe['sroc'].iat[-1]
        else:
            # If in backtest or hyperopt, get the indicator values out of the trades dict (Thanks @JoeSchr!)
            sroc = self.custom_trade_info[trade.pair]['sroc'].loc[current_time]['sroc']
        if current_profit < self.cstp_threshold.value:
            if self.cstp_bail_how.value == 'roc' or self.cstp_bail_how.value == 'any':
                # Dynamic bailout based on rate of change
                if sroc / 100 <= self.cstp_bail_roc.value:
                    return 0.001
            if self.cstp_bail_how.value == 'time' or self.cstp_bail_how.value == 'any':
                # Dynamic bailout based on time
                if trade_dur > self.cstp_bail_time.value:
                    return 0.001
        return 1
    '\n    Freqtrade ROI Overload for dynamic ROI functionality\n    '

    def min_roi_reached_dynamic(self, trade: Trade, current_profit: float, current_time: datetime, trade_dur: int) -> Tuple[Optional[int], Optional[float]]:
        minimal_roi = self.minimal_roi
        _, table_roi = self.min_roi_reached_entry(trade_dur)
        # see if we have the data we need to do this, otherwise fall back to the standard table
        if self.custom_trade_info and trade and (trade.pair in self.custom_trade_info):
            if self.config['runmode'].value in ('live', 'dry_run'):
                dataframe, last_updated = self.dp.get_analyzed_dataframe(pair=trade.pair, timeframe=self.timeframe)
                rmi_trend = dataframe['rmi-up-trend'].iat[-1]
                candle_trend = dataframe['candle-up-trend'].iat[-1]
                ssl_dir = dataframe['ssl-dir'].iat[-1]
            else:
                # If in backtest or hyperopt, get the indicator values out of the trades dict (Thanks @JoeSchr!)
                rmi_trend = self.custom_trade_info[trade.pair]['rmi-up-trend'].loc[current_time]['rmi-up-trend']
                candle_trend = self.custom_trade_info[trade.pair]['candle-up-trend'].loc[current_time]['candle-up-trend']
                ssl_dir = self.custom_trade_info[trade.pair]['ssl-dir'].loc[current_time]['ssl-dir']
            min_roi = table_roi
            max_profit = trade.calc_profit_ratio(trade.max_rate)
            pullback_value = max_profit - self.droi_pullback_amount.value
            in_trend = False
            if self.droi_trend_type.value == 'rmi' or self.droi_trend_type.value == 'any':
                if rmi_trend == 1:
                    in_trend = True
            if self.droi_trend_type.value == 'ssl' or self.droi_trend_type.value == 'any':
                if ssl_dir == 'up':
                    in_trend = True
            if self.droi_trend_type.value == 'candle' or self.droi_trend_type.value == 'any':
                if candle_trend == 1:
                    in_trend = True
            # Force the ROI value high if in trend
            if in_trend == True:
                min_roi = 100
                # If pullback is enabled, allow to exit if a pullback from peak has happened regardless of trend
                if self.droi_pullback.value == True and current_profit < pullback_value:
                    if self.droi_pullback_respect_table.value == True:
                        min_roi = table_roi
                    else:
                        min_roi = current_profit / 2
        else:
            min_roi = table_roi
        return (trade_dur, min_roi)
    # Change here to allow loading of the dynamic_roi settings

    def min_roi_reached(self, trade: Trade, current_profit: float, current_time: datetime) -> bool:
        trade_dur = int((current_time.timestamp() - trade.open_date_utc.timestamp()) // 60)
        if self.use_dynamic_roi:
            _, roi = self.min_roi_reached_dynamic(trade, current_profit, current_time, trade_dur)
        else:
            _, roi = self.min_roi_reached_entry(trade_dur)
        if roi is None:
            return False
        else:
            return current_profit > roi
    # Get the current price from the exchange (or local cache)

    def get_current_price(self, pair: str, refresh: bool) -> float:
        if not refresh:
            rate = self.custom_current_price_cache.get(pair)
            # Check if cache has been invalidated
            if rate:
                return rate
        ask_strategy = self.config.get('ask_strategy', {})
        if ask_strategy.get('use_order_book', False):
            ob = self.dp.orderbook(pair, 1)
            rate = ob[f"{ask_strategy['price_side']}s"][0][0]
        else:
            ticker = self.dp.ticker(pair)
            rate = ticker['last']
        self.custom_current_price_cache[pair] = rate
        return rate
    '\n    Stripped down version from Schism, meant only to update the price data a bit\n    more frequently than the default instead of getting all sorts of trade information\n    '

    def populate_trades(self, pair: str) -> dict:
        # Initialize the trades dict if it doesn't exist, persist it otherwise
        if not pair in self.custom_trade_info:
            self.custom_trade_info[pair] = {}
        # init the temp dicts and set the trade stuff to false
        trade_data = {}
        trade_data['active_trade'] = False
        # active trade stuff only works in live and dry, not backtest
        if self.config['runmode'].value in ('live', 'dry_run'):
            # find out if we have an open trade for this pair
            active_trade = Trade.get_trades([Trade.pair == pair, Trade.is_open.is_(True)]).all()
            # if so, get some information
            if active_trade:
                # get current price and update the min/max rate
                current_rate = self.get_current_price(pair, True)
                active_trade[0].adjust_min_max_rates(current_rate)
        return trade_data
    # nested hyperopt class

    class HyperOpt:
        # defining as dummy, so that no error is thrown about missing
        # exit indicator space when hyperopting for all spaces

        @staticmethod
        def indicator_space() -> List[Dimension]:
            return []
## goddamnit

def RMI(dataframe, *, length=20, mom=5):
    """
    Source: https://github.com/freqtrade/technical/blob/master/technical/indicators/indicators.py#L912
    """
    df = dataframe.copy()
    df['maxup'] = (df['close'] - df['close'].shift(mom)).clip(lower=0)
    df['maxdown'] = (df['close'].shift(mom) - df['close']).clip(lower=0)
    df.fillna(0, inplace=True)
    df['emaInc'] = ta.EMA(df, price='maxup', timeperiod=length)
    df['emaDec'] = ta.EMA(df, price='maxdown', timeperiod=length)
    df['RMI'] = np.where(df['emaDec'] == 0, 0, 100 - 100 / (1 + df['emaInc'] / df['emaDec']))
    return df['RMI']

def SSLChannels_ATR(dataframe, length=7):
    """
    SSL Channels with ATR: https://www.tradingview.com/script/SKHqWzql-SSL-ATR-channel/
    Credit to @JimmyNixx for python
    """
    df = dataframe.copy()
    df['ATR'] = ta.ATR(df, timeperiod=14)
    df['smaHigh'] = df['high'].rolling(length).mean() + df['ATR']
    df['smaLow'] = df['low'].rolling(length).mean() - df['ATR']
    df['hlv'] = np.where(df['close'] > df['smaHigh'], 1, np.where(df['close'] < df['smaLow'], -1, np.NAN))
    df['hlv'] = df['hlv'].ffill()
    df['sslDown'] = np.where(df['hlv'] < 0, df['smaHigh'], df['smaLow'])
    df['sslUp'] = np.where(df['hlv'] < 0, df['smaLow'], df['smaHigh'])
    return (df['sslDown'], df['sslUp'])

def SROC(dataframe, roclen=21, emalen=13, smooth=21):
    df = dataframe.copy()
    roc = ta.ROC(df, timeperiod=roclen)
    ema = ta.EMA(df, timeperiod=emalen)
    sroc = ta.ROC(ema, timeperiod=smooth)
    return sroc
# Elliot Wave Oscillator

def EWO(dataframe, sma1_length=5, sma2_length=35):
    df = dataframe.copy()
    sma1 = ta.EMA(df, timeperiod=sma1_length)
    sma2 = ta.EMA(df, timeperiod=sma2_length)
    smadif = (sma1 - sma2) / df['close'] * 100
    return smadif