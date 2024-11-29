import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair, DecimalParameter, IntParameter, CategoricalParameter
from pandas import DataFrame, Series
from functools import reduce
from freqtrade.persistence import Trade
from datetime import datetime, timedelta
###########################################################################################################
##                NostalgiaForInfinityV4 by iterativ                                                     ##
##                                                                                                       ##
##    Strategy for Freqtrade https://github.com/freqtrade/freqtrade                                      ##
##                                                                                                       ##
###########################################################################################################
##               GENERAL RECOMMENDATIONS                                                                 ##
##                                                                                                       ##
##   For optimal performance, suggested to use between 4 and 6 open trades, with unlimited stake.        ##
##   A pairlist with 40 to 80 pairs. Volume pairlist works well.                                         ##
##   Prefer stable coin (USDT, BUSDT etc) pairs, instead of BTC or ETH pairs.                            ##
##   Highly recommended to blacklist leveraged tokens (*BULL, *BEAR, *UP, *DOWN etc).                    ##
##   Ensure that you don't override any variables in you config.json. Especially                         ##
##   the timeframe (must be 5m).                                                                         ##
##     use_exit_signal must set to true (or not set at all).                                             ##
##     exit_profit_only must set to false (or not set at all).                                           ##
##     ignore_roi_if_entry_signal must set to true (or not set at all).                                    ##
##                                                                                                       ##
###########################################################################################################
##               DONATIONS                                                                               ##
##                                                                                                       ##
##   Absolutely not required. However, will be accepted as a token of appreciation.                      ##
##                                                                                                       ##
##   BTC: bc1qvflsvddkmxh7eqhc4jyu5z5k6xcw3ay8jl49sk                                                     ##
##   ETH (ERC20): 0x83D3cFb8001BDC5d2211cBeBB8cB3461E5f7Ec91                                             ##
##   BEP20/BSC (ETH, BNB, ...): 0x86A0B21a20b39d16424B7c8003E4A7e12d78ABEe                               ##
##                                                                                                       ##
###########################################################################################################

class NFI46Z(IStrategy):
    INTERFACE_VERSION = 3
    # ROI table:
    # I feel lucky!
    # We're going up?
    minimal_roi = {'0': 0.028, '10': 0.018, '40': 0.005, '180': 0.018}
    stoploss = -0.99
    # Trailing stoploss (not used)
    trailing_stop = False
    trailing_only_offset_is_reached = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.025
    # Custom Stoploss
    use_custom_stoploss = True
    # Optimal timeframe for the strategy.
    timeframe = '5m'
    inf_1h = '1h'
    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True
    # These values can be overridden in the "ask_strategy" section in the config.
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.001  # it doesn't meant anything, just to guarantee there is a minimal profit.
    ignore_roi_if_entry_signal = False
    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 400
    # Optional order type mapping.
    order_types = {'entry': 'market', 'exit': 'market', 'trailing_stop_loss': 'market', 'stoploss': 'market', 'stoploss_on_exchange': False}
    #############################################################
    entry_params = {'entry_bb20_close_bblowerband_4': 0.987, 'entry_bb20_close_bblowerband_safe_1': 1.014, 'entry_bb20_close_bblowerband_safe_2': 0.811, 'entry_bb20_volume_4': 34, 'entry_bb40_bbdelta_close_3': 0.052, 'entry_bb40_closedelta_close_3': 0.02, 'entry_bb40_tail_bbdelta_3': 0.397, 'entry_bb_offset_10': 0.982, 'entry_bb_offset_14': 0.981, 'entry_bb_offset_2': 0.983, 'entry_bb_offset_5': 0.987, 'entry_bb_offset_6': 0.986, 'entry_bb_offset_9': 0.981, 'entry_condition_10_enable': True, 'entry_condition_11_enable': False, 'entry_condition_12_enable': False, 'entry_condition_13_enable': False, 'entry_condition_14_enable': True, 'entry_condition_15_enable': False, 'entry_condition_16_enable': False, 'entry_condition_17_enable': True, 'entry_condition_18_enable': False, 'entry_condition_19_enable': False, 'entry_condition_1_enable': False, 'entry_condition_20_enable': False, 'entry_condition_21_enable': False, 'entry_condition_22_enable': False, 'entry_condition_23_enable': False, 'entry_condition_24_enable': True, 'entry_condition_25_enable': False, 'entry_condition_26_enable': False, 'entry_condition_27_enable': False, 'entry_condition_28_enable': False, 'entry_condition_29_enable': True, 'entry_condition_2_enable': True, 'entry_condition_3_enable': True, 'entry_condition_4_enable': False, 'entry_condition_5_enable': True, 'entry_condition_6_enable': False, 'entry_condition_7_enable': False, 'entry_condition_8_enable': False, 'entry_condition_9_enable': False, 'entry_dip_threshold_1': 0.014, 'entry_dip_threshold_10': 0.135, 'entry_dip_threshold_11': 0.156, 'entry_dip_threshold_12': 0.47, 'entry_dip_threshold_2': 0.127, 'entry_dip_threshold_3': 0.2, 'entry_dip_threshold_4': 0.243, 'entry_dip_threshold_5': 0.009, 'entry_dip_threshold_6': 0.072, 'entry_dip_threshold_7': 0.169, 'entry_dip_threshold_8': 0.487, 'entry_dip_threshold_9': 0.008, 'entry_ema_open_mult_14': 0.025, 'entry_ema_open_mult_15': 0.035, 'entry_ema_open_mult_5': 0.02, 'entry_ema_open_mult_6': 0.04, 'entry_ema_open_mult_7': 0.038, 'entry_ema_rel_15': 0.978, 'entry_ema_rel_3': 0.992, 'entry_ema_rel_5': 0.974, 'entry_ema_rel_8': 0.995, 'entry_ewo_12': 5.2, 'entry_ewo_13': -8.1, 'entry_ewo_16': 7.6, 'entry_ewo_17': -11.8, 'entry_ma_offset_10': 0.935, 'entry_ma_offset_11': 0.988, 'entry_ma_offset_12': 0.941, 'entry_ma_offset_13': 0.943, 'entry_ma_offset_14': 0.975, 'entry_ma_offset_15': 0.983, 'entry_ma_offset_16': 0.947, 'entry_ma_offset_17': 0.931, 'entry_ma_offset_9': 0.962, 'entry_macd_1': 0.05, 'entry_macd_2': 0.01, 'entry_mfi_1': 31.6, 'entry_mfi_11': 49.9, 'entry_mfi_2': 56.4, 'entry_mfi_9': 50.3, 'entry_min_inc_1': 0.048, 'entry_min_inc_11': 0.027, 'entry_pump_pull_threshold_1': 1.91, 'entry_pump_pull_threshold_2': 1.53, 'entry_pump_pull_threshold_3': 2.04, 'entry_pump_pull_threshold_4': 2.08, 'entry_pump_pull_threshold_5': 2.57, 'entry_pump_pull_threshold_6': 2.46, 'entry_pump_pull_threshold_7': 2.54, 'entry_pump_pull_threshold_8': 1.5, 'entry_pump_pull_threshold_9': 1.66, 'entry_pump_threshold_1': 0.549, 'entry_pump_threshold_2': 0.492, 'entry_pump_threshold_3': 0.453, 'entry_pump_threshold_4': 0.732, 'entry_pump_threshold_5': 0.815, 'entry_pump_threshold_6': 0.933, 'entry_pump_threshold_7': 0.535, 'entry_pump_threshold_8': 0.75, 'entry_pump_threshold_9': 0.65, 'entry_rsi_1': 30.1, 'entry_rsi_11': 34.4, 'entry_rsi_12': 35.2, 'entry_rsi_15': 32.4, 'entry_rsi_16': 47.5, 'entry_rsi_1h_1': 16.0, 'entry_rsi_1h_10': 30.0, 'entry_rsi_1h_2': 24.9, 'entry_rsi_1h_3': 24.7, 'entry_rsi_1h_4': 17.6, 'entry_rsi_1h_5': 30.6, 'entry_rsi_1h_diff_2': 42.7, 'entry_rsi_1h_max_1': 84.7, 'entry_rsi_1h_max_11': 86.7, 'entry_rsi_1h_max_2': 79.7, 'entry_rsi_1h_max_9': 79.5, 'entry_rsi_1h_min_1': 33.0, 'entry_rsi_1h_min_11': 43.4, 'entry_rsi_1h_min_2': 39.9, 'entry_rsi_1h_min_9': 38.9, 'entry_rsi_2': 39.7, 'entry_rsi_3': 10.0, 'entry_rsi_7': 33.2, 'entry_rsi_8': 41.8, 'entry_volume_10': 7.6, 'entry_volume_12': 8.9, 'entry_volume_14': 1.0, 'entry_volume_16': 6.3, 'entry_volume_2': 5.6, 'entry_volume_5': 2.8, 'entry_volume_6': 8.6, 'entry_volume_7': 4.9, 'entry_volume_9': 3.45, 'entry_volume_drop_1': 6.1, 'entry_volume_drop_2': 6.6, 'entry_volume_drop_3': 9.1, 'entry_volume_pump_1': 0.4}
    exit_params = {'exit_bb_relative_8': 1.073, 'exit_condition_1_enable': True, 'exit_condition_2_enable': False, 'exit_condition_3_enable': False, 'exit_condition_4_enable': False, 'exit_condition_5_enable': False, 'exit_condition_6_enable': False, 'exit_condition_7_enable': False, 'exit_condition_8_enable': False, 'exit_custom_dec_profit_max_1': 0.108, 'exit_custom_dec_profit_max_2': 0.165, 'exit_custom_dec_profit_min_1': 0.085, 'exit_custom_dec_profit_min_2': 0.084, 'exit_custom_profit_0': 0.048, 'exit_custom_profit_1': 0.02, 'exit_custom_profit_10': 0.111, 'exit_custom_profit_11': 0.313, 'exit_custom_profit_2': 0.086, 'exit_custom_profit_3': 0.01, 'exit_custom_profit_4': 0.052, 'exit_custom_profit_5': 0.077, 'exit_custom_profit_6': 0.051, 'exit_custom_profit_7': 0.085, 'exit_custom_profit_8': 0.08, 'exit_custom_profit_9': 0.083, 'exit_custom_profit_under_rel_1': 0.01, 'exit_custom_profit_under_rsi_diff_1': 2.12, 'exit_custom_pump_dec_profit_max_1': 0.03, 'exit_custom_pump_dec_profit_max_2': 0.074, 'exit_custom_pump_dec_profit_max_3': 0.112, 'exit_custom_pump_dec_profit_max_4': 0.051, 'exit_custom_pump_dec_profit_min_1': 0.03, 'exit_custom_pump_dec_profit_min_2': 0.053, 'exit_custom_pump_dec_profit_min_3': 0.057, 'exit_custom_pump_dec_profit_min_4': 0.044, 'exit_custom_pump_profit_1_1': 0.013, 'exit_custom_pump_profit_1_2': 0.39, 'exit_custom_pump_profit_1_3': 0.067, 'exit_custom_pump_profit_1_4': 0.109, 'exit_custom_pump_profit_1_5': 0.177, 'exit_custom_pump_profit_2_1': 0.028, 'exit_custom_pump_profit_2_2': 0.275, 'exit_custom_pump_profit_2_3': 0.028, 'exit_custom_pump_profit_2_4': 0.11, 'exit_custom_pump_profit_2_5': 0.24, 'exit_custom_pump_profit_3_1': 0.026, 'exit_custom_pump_profit_3_2': 0.46, 'exit_custom_pump_profit_3_3': 0.094, 'exit_custom_pump_profit_3_4': 0.098, 'exit_custom_pump_profit_3_5': 0.231, 'exit_custom_pump_rsi_1_1': 26.8, 'exit_custom_pump_rsi_1_2': 42.9, 'exit_custom_pump_rsi_1_3': 40.3, 'exit_custom_pump_rsi_1_4': 39.7, 'exit_custom_pump_rsi_1_5': 27.9, 'exit_custom_pump_rsi_2_1': 32.5, 'exit_custom_pump_rsi_2_2': 48.1, 'exit_custom_pump_rsi_2_3': 40.8, 'exit_custom_pump_rsi_2_4': 45.2, 'exit_custom_pump_rsi_2_5': 38.6, 'exit_custom_pump_rsi_3_1': 31.0, 'exit_custom_pump_rsi_3_2': 44.8, 'exit_custom_pump_rsi_3_3': 44.7, 'exit_custom_pump_rsi_3_4': 45.7, 'exit_custom_pump_rsi_3_5': 36.7, 'exit_custom_pump_trail_down_1': 0.034, 'exit_custom_pump_trail_profit_max_1': 0.09, 'exit_custom_pump_trail_profit_min_1': 0.016, 'exit_custom_pump_trail_rsi_max_1': 33.7, 'exit_custom_pump_trail_rsi_min_1': 25.0, 'exit_custom_pump_under_profit_max_1': 0.066, 'exit_custom_pump_under_profit_min_1': 0.057, 'exit_custom_rsi_0': 31.129, 'exit_custom_rsi_1': 48.18, 'exit_custom_rsi_10': 47.63, 'exit_custom_rsi_11': 38.45, 'exit_custom_rsi_2': 42.64, 'exit_custom_rsi_3': 46.33, 'exit_custom_rsi_4': 44.62, 'exit_custom_rsi_5': 41.47, 'exit_custom_rsi_6': 49.31, 'exit_custom_rsi_7': 51.68, 'exit_custom_rsi_8': 42.78, 'exit_custom_rsi_9': 55.93, 'exit_custom_stoploss_pump_loss_2': -0.052, 'exit_custom_stoploss_pump_loss_3': -0.127, 'exit_custom_stoploss_pump_ma_offset_1': 0.99, 'exit_custom_stoploss_pump_ma_offset_2': 0.91, 'exit_custom_stoploss_pump_ma_offset_3': 0.76, 'exit_custom_stoploss_pump_max_1': -0.034, 'exit_custom_stoploss_pump_max_profit_1': 0.022, 'exit_custom_stoploss_pump_max_profit_2': 0.029, 'exit_custom_stoploss_pump_max_profit_3': 0.024, 'exit_custom_stoploss_pump_min_1': -0.063, 'exit_custom_stoploss_under_rel_1': 0.018, 'exit_custom_stoploss_under_rsi_diff_1': 3.666, 'exit_custom_under_profit_0': 0.065, 'exit_custom_under_profit_1': 0.09, 'exit_custom_under_profit_10': 0.101, 'exit_custom_under_profit_11': 0.177, 'exit_custom_under_profit_2': 0.083, 'exit_custom_under_profit_3': 0.061, 'exit_custom_under_profit_4': 0.086, 'exit_custom_under_profit_5': 0.025, 'exit_custom_under_profit_6': 0.061, 'exit_custom_under_profit_7': 0.08, 'exit_custom_under_profit_8': 0.114, 'exit_custom_under_profit_9': 0.094, 'exit_custom_under_rsi_0': 30.1, 'exit_custom_under_rsi_1': 48.1, 'exit_custom_under_rsi_10': 43.1, 'exit_custom_under_rsi_11': 25.5, 'exit_custom_under_rsi_2': 64.6, 'exit_custom_under_rsi_3': 56.7, 'exit_custom_under_rsi_4': 64.3, 'exit_custom_under_rsi_5': 60.8, 'exit_custom_under_rsi_6': 47.1, 'exit_custom_under_rsi_7': 58.0, 'exit_custom_under_rsi_8': 51.2, 'exit_custom_under_rsi_9': 32.7, 'exit_dual_rsi_rsi_1h_4': 86.0, 'exit_dual_rsi_rsi_4': 76.0, 'exit_ema_relative_5': 0.006, 'exit_pump_threshold_1': 1.04, 'exit_pump_threshold_2': 0.46, 'exit_pump_threshold_3': 0.66, 'exit_pump_threshold_4': 0.5, 'exit_pump_threshold_5': 3.23, 'exit_pump_threshold_6': 0.94, 'exit_pump_threshold_7': 0.51, 'exit_pump_threshold_8': 0.55, 'exit_pump_threshold_9': 0.38, 'exit_rsi_1h_7': 92.0, 'exit_rsi_bb_1': 73.3, 'exit_rsi_bb_2': 73.0, 'exit_rsi_diff_5': 3.551, 'exit_rsi_main_3': 84.2, 'exit_rsi_under_6': 85.8, 'exit_trail_down_1': 0.069, 'exit_trail_down_2': 0.05, 'exit_trail_down_3': 0.023, 'exit_trail_profit_max_1': 0.61, 'exit_trail_profit_max_2': 0.4, 'exit_trail_profit_max_3': 0.15, 'exit_trail_profit_min_1': 0.17, 'exit_trail_profit_min_2': 0.131, 'exit_trail_profit_min_3': 0.062, 'exit_trail_rsi_max_1': 43.8, 'exit_trail_rsi_max_2': 30.6, 'exit_trail_rsi_min_1': 16.5, 'exit_trail_rsi_min_2': 31.9}
    #############################################################
    entry_condition_1_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_2_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_3_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_4_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_5_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_6_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_7_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_8_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_9_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_10_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_11_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_12_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_13_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_14_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_15_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_16_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_17_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_18_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_19_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_20_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_21_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_22_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_23_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_24_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_25_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_26_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_27_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_28_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_condition_29_enable = CategoricalParameter([True, False], default=True, space='entry', optimize=True, load=True)
    entry_bb20_close_bblowerband_safe_1 = DecimalParameter(0.7, 1.1, default=0.989, space='entry', optimize=True, load=True)
    entry_bb20_close_bblowerband_safe_2 = DecimalParameter(0.7, 1.1, default=0.982, space='entry', optimize=True, load=True)
    entry_volume_pump_1 = DecimalParameter(0.1, 0.9, default=0.4, space='entry', decimals=1, optimize=True, load=True)
    entry_volume_drop_1 = DecimalParameter(1, 10, default=3.8, space='entry', decimals=1, optimize=True, load=True)
    entry_volume_drop_2 = DecimalParameter(1, 10, default=3, space='entry', decimals=1, optimize=True, load=True)
    entry_volume_drop_3 = DecimalParameter(1, 10, default=2.7, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_1 = DecimalParameter(10.0, 40.0, default=16.5, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_2 = DecimalParameter(10.0, 40.0, default=15.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_3 = DecimalParameter(10.0, 40.0, default=20.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_4 = DecimalParameter(10.0, 40.0, default=35.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_5 = DecimalParameter(10.0, 60.0, default=39.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1 = DecimalParameter(10.0, 40.0, default=28.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_2 = DecimalParameter(7.0, 40.0, default=10.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_3 = DecimalParameter(7.0, 40.0, default=14.2, space='entry', decimals=1, optimize=True, load=True)
    entry_macd_1 = DecimalParameter(0.01, 0.09, default=0.02, space='entry', decimals=2, optimize=True, load=True)
    entry_macd_2 = DecimalParameter(0.01, 0.09, default=0.03, space='entry', decimals=2, optimize=True, load=True)
    # Normal dips
    entry_dip_threshold_1 = DecimalParameter(0.001, 0.05, default=0.02, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_2 = DecimalParameter(0.01, 0.2, default=0.14, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_3 = DecimalParameter(0.05, 0.4, default=0.32, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_4 = DecimalParameter(0.2, 0.5, default=0.5, space='entry', decimals=3, optimize=True, load=True)
    # Strict dips
    entry_dip_threshold_5 = DecimalParameter(0.001, 0.05, default=0.015, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_6 = DecimalParameter(0.01, 0.2, default=0.06, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_7 = DecimalParameter(0.05, 0.4, default=0.24, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_8 = DecimalParameter(0.2, 0.5, default=0.4, space='entry', decimals=3, optimize=True, load=True)
    # Loose dips
    entry_dip_threshold_9 = DecimalParameter(0.001, 0.05, default=0.026, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_10 = DecimalParameter(0.01, 0.2, default=0.24, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_11 = DecimalParameter(0.05, 0.4, default=0.42, space='entry', decimals=3, optimize=True, load=True)
    entry_dip_threshold_12 = DecimalParameter(0.2, 0.5, default=0.8, space='entry', decimals=3, optimize=True, load=True)
    # 12 hours
    entry_pump_pull_threshold_1 = DecimalParameter(1.5, 3.0, default=1.75, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_1 = DecimalParameter(0.4, 1.0, default=0.46, space='entry', decimals=3, optimize=True, load=True)
    # 36 hours
    entry_pump_pull_threshold_2 = DecimalParameter(1.5, 3.0, default=1.75, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_2 = DecimalParameter(0.4, 1.0, default=0.56, space='entry', decimals=3, optimize=True, load=True)
    # 48 hours
    entry_pump_pull_threshold_3 = DecimalParameter(1.5, 3.0, default=1.75, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_3 = DecimalParameter(0.4, 1.0, default=0.85, space='entry', decimals=3, optimize=True, load=True)
    # 12 hours strict
    entry_pump_pull_threshold_4 = DecimalParameter(1.5, 3.0, default=2.2, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_4 = DecimalParameter(0.4, 1.0, default=0.4, space='entry', decimals=3, optimize=True, load=True)
    # 36 hours strict
    entry_pump_pull_threshold_5 = DecimalParameter(1.5, 3.0, default=2.0, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_5 = DecimalParameter(0.4, 1.0, default=0.56, space='entry', decimals=3, optimize=True, load=True)
    # 48 hours strict
    entry_pump_pull_threshold_6 = DecimalParameter(1.5, 3.0, default=2.0, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_6 = DecimalParameter(0.4, 1.0, default=0.68, space='entry', decimals=3, optimize=True, load=True)
    # 24 hours loose
    entry_pump_pull_threshold_7 = DecimalParameter(1.5, 3.0, default=1.7, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_7 = DecimalParameter(0.4, 1.0, default=0.66, space='entry', decimals=3, optimize=True, load=True)
    # 36 hours loose
    entry_pump_pull_threshold_8 = DecimalParameter(1.5, 3.0, default=1.7, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_8 = DecimalParameter(0.4, 1.0, default=0.7, space='entry', decimals=3, optimize=True, load=True)
    # 48 hours loose
    entry_pump_pull_threshold_9 = DecimalParameter(1.3, 2.0, default=1.4, space='entry', decimals=2, optimize=True, load=True)
    entry_pump_threshold_9 = DecimalParameter(0.4, 1.8, default=1.6, space='entry', decimals=3, optimize=True, load=True)
    entry_min_inc_1 = DecimalParameter(0.01, 0.05, default=0.022, space='entry', decimals=3, optimize=True, load=True)
    entry_rsi_1h_min_1 = DecimalParameter(25.0, 40.0, default=30.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_max_1 = DecimalParameter(70.0, 90.0, default=80.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1 = DecimalParameter(20.0, 40.0, default=36.0, space='entry', decimals=1, optimize=True, load=True)
    entry_mfi_1 = DecimalParameter(20.0, 56.0, default=26.0, space='entry', decimals=1, optimize=True, load=True)
    entry_volume_2 = DecimalParameter(1.0, 10.0, default=2.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_min_2 = DecimalParameter(30.0, 40.0, default=36.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_max_2 = DecimalParameter(70.0, 95.0, default=90.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_diff_2 = DecimalParameter(30.0, 50.0, default=34.0, space='entry', decimals=1, optimize=True, load=True)
    entry_mfi_2 = DecimalParameter(30.0, 65.0, default=56.0, space='entry', decimals=1, optimize=True, load=True)
    entry_bb_offset_2 = DecimalParameter(0.97, 0.99, default=0.983, space='entry', decimals=3, optimize=True, load=True)
    entry_bb40_bbdelta_close_3 = DecimalParameter(0.005, 0.06, default=0.057, space='entry', optimize=True, load=True)
    entry_bb40_closedelta_close_3 = DecimalParameter(0.01, 0.03, default=0.023, space='entry', optimize=True, load=True)
    entry_bb40_tail_bbdelta_3 = DecimalParameter(0.15, 0.45, default=0.418, space='entry', optimize=True, load=True)
    entry_ema_rel_3 = DecimalParameter(0.97, 0.999, default=0.988, space='entry', decimals=3, optimize=True, load=True)
    entry_bb20_close_bblowerband_4 = DecimalParameter(0.9, 0.99, default=0.979, space='entry', optimize=True, load=True)
    entry_bb20_volume_4 = IntParameter(16, 35, default=18, space='entry', optimize=True, load=True)
    entry_volume_5 = DecimalParameter(1.0, 10.0, default=6.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ema_open_mult_5 = DecimalParameter(0.016, 0.03, default=0.019, space='entry', decimals=3, optimize=True, load=True)
    entry_bb_offset_5 = DecimalParameter(0.98, 1.0, default=0.999, space='entry', decimals=3, optimize=True, load=True)
    entry_ema_rel_5 = DecimalParameter(0.97, 0.999, default=0.988, space='entry', decimals=3, optimize=True, load=True)
    entry_volume_6 = DecimalParameter(1.0, 10.0, default=1.5, space='entry', decimals=1, optimize=True, load=True)
    entry_ema_open_mult_6 = DecimalParameter(0.03, 0.04, default=0.025, space='entry', decimals=3, optimize=True, load=True)
    entry_bb_offset_6 = DecimalParameter(0.98, 0.999, default=0.995, space='entry', decimals=3, optimize=True, load=True)
    entry_volume_7 = DecimalParameter(1.0, 10.0, default=2.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ema_open_mult_7 = DecimalParameter(0.02, 0.04, default=0.03, space='entry', decimals=3, optimize=True, load=True)
    entry_rsi_7 = DecimalParameter(24.0, 50.0, default=36.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_8 = DecimalParameter(30.0, 50.0, default=46.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ema_rel_8 = DecimalParameter(0.97, 0.999, default=0.988, space='entry', decimals=3, optimize=True, load=True)
    entry_volume_9 = DecimalParameter(1.0, 4.0, default=2.0, space='entry', decimals=2, optimize=True, load=True)
    entry_ma_offset_9 = DecimalParameter(0.94, 0.99, default=0.958, space='entry', decimals=3, optimize=True, load=True)
    entry_bb_offset_9 = DecimalParameter(0.97, 0.99, default=0.984, space='entry', decimals=3, optimize=True, load=True)
    entry_rsi_1h_min_9 = DecimalParameter(26.0, 40.0, default=30.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_max_9 = DecimalParameter(70.0, 90.0, default=80.0, space='entry', decimals=1, optimize=True, load=True)
    entry_mfi_9 = DecimalParameter(36.0, 65.0, default=56.0, space='entry', decimals=1, optimize=True, load=True)
    entry_volume_10 = DecimalParameter(1.0, 26.0, default=23.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ma_offset_10 = DecimalParameter(0.93, 0.97, default=0.94, space='entry', decimals=3, optimize=True, load=True)
    entry_bb_offset_10 = DecimalParameter(0.97, 0.99, default=0.994, space='entry', decimals=3, optimize=True, load=True)
    entry_rsi_1h_10 = DecimalParameter(20.0, 40.0, default=39.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ma_offset_11 = DecimalParameter(0.93, 0.99, default=0.938, space='entry', decimals=3, optimize=True, load=True)
    entry_min_inc_11 = DecimalParameter(0.005, 0.05, default=0.01, space='entry', decimals=3, optimize=True, load=True)
    entry_rsi_1h_min_11 = DecimalParameter(40.0, 60.0, default=55.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_1h_max_11 = DecimalParameter(70.0, 90.0, default=82.0, space='entry', decimals=1, optimize=True, load=True)
    entry_rsi_11 = DecimalParameter(30.0, 48.0, default=46.0, space='entry', decimals=1, optimize=True, load=True)
    entry_mfi_11 = DecimalParameter(36.0, 56.0, default=38.0, space='entry', decimals=1, optimize=True, load=True)
    entry_volume_12 = DecimalParameter(1.0, 10.0, default=2.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ma_offset_12 = DecimalParameter(0.93, 0.97, default=0.936, space='entry', decimals=3, optimize=True, load=True)
    entry_rsi_12 = DecimalParameter(26.0, 40.0, default=30.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ewo_12 = DecimalParameter(2.0, 6.0, default=2.8, space='entry', decimals=1, optimize=True, load=True)
    entry_ma_offset_13 = DecimalParameter(0.93, 0.98, default=0.952, space='entry', decimals=3, optimize=True, load=True)
    entry_ewo_13 = DecimalParameter(-14.0, -7.0, default=-7.9, space='entry', decimals=1, optimize=True, load=True)
    entry_volume_14 = DecimalParameter(1.0, 10.0, default=2.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ema_open_mult_14 = DecimalParameter(0.01, 0.03, default=0.014, space='entry', decimals=3, optimize=True, load=True)
    entry_bb_offset_14 = DecimalParameter(0.98, 1.0, default=0.992, space='entry', decimals=3, optimize=True, load=True)
    entry_ma_offset_14 = DecimalParameter(0.93, 0.99, default=0.998, space='entry', decimals=3, optimize=True, load=True)
    entry_ema_open_mult_15 = DecimalParameter(0.02, 0.04, default=0.026, space='entry', decimals=3, optimize=True, load=True)
    entry_ma_offset_15 = DecimalParameter(0.93, 0.99, default=0.985, space='entry', decimals=3, optimize=True, load=True)
    entry_rsi_15 = DecimalParameter(30.0, 50.0, default=32.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ema_rel_15 = DecimalParameter(0.97, 0.999, default=0.988, space='entry', decimals=3, optimize=True, load=True)
    entry_volume_16 = DecimalParameter(1.0, 10.0, default=2.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ma_offset_16 = DecimalParameter(0.93, 0.97, default=0.95, space='entry', decimals=3, optimize=True, load=True)
    entry_rsi_16 = DecimalParameter(26.0, 50.0, default=38.0, space='entry', decimals=1, optimize=True, load=True)
    entry_ewo_16 = DecimalParameter(4.0, 8.0, default=3.6, space='entry', decimals=1, optimize=True, load=True)
    entry_ma_offset_17 = DecimalParameter(0.93, 0.98, default=0.958, space='entry', decimals=3, optimize=True, load=True)
    entry_ewo_17 = DecimalParameter(-18.0, -10.0, default=-12.0, space='entry', decimals=1, optimize=True, load=True)
    # Sell
    exit_condition_1_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=True, load=True)
    exit_condition_2_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=True, load=True)
    exit_condition_3_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=True, load=True)
    exit_condition_4_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=True, load=True)
    exit_condition_5_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=True, load=True)
    exit_condition_6_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=True, load=True)
    exit_condition_7_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=True, load=True)
    exit_condition_8_enable = CategoricalParameter([True, False], default=True, space='exit', optimize=True, load=True)
    exit_rsi_bb_1 = DecimalParameter(60.0, 80.0, default=79.5, space='exit', decimals=1, optimize=True, load=True)
    exit_rsi_bb_2 = DecimalParameter(72.0, 90.0, default=81, space='exit', decimals=1, optimize=True, load=True)
    exit_rsi_main_3 = DecimalParameter(77.0, 90.0, default=82, space='exit', decimals=1, optimize=True, load=True)
    exit_dual_rsi_rsi_4 = DecimalParameter(72.0, 84.0, default=73.4, space='exit', decimals=1, optimize=True, load=True)
    exit_dual_rsi_rsi_1h_4 = DecimalParameter(78.0, 92.0, default=79.6, space='exit', decimals=1, optimize=True, load=True)
    exit_ema_relative_5 = DecimalParameter(0.005, 0.05, default=0.024, space='exit', optimize=True, load=True)
    exit_rsi_diff_5 = DecimalParameter(0.0, 20.0, default=4.4, space='exit', optimize=True, load=True)
    exit_rsi_under_6 = DecimalParameter(72.0, 90.0, default=79.0, space='exit', decimals=1, optimize=True, load=True)
    exit_rsi_1h_7 = DecimalParameter(80.0, 95.0, default=81.7, space='exit', decimals=1, optimize=True, load=True)
    exit_bb_relative_8 = DecimalParameter(1.05, 1.3, default=1.1, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_profit_0 = DecimalParameter(0.01, 0.1, default=0.01, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_0 = DecimalParameter(30.0, 40.0, default=33.0, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_profit_1 = DecimalParameter(0.01, 0.1, default=0.02, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_1 = DecimalParameter(30.0, 50.0, default=34.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_2 = DecimalParameter(0.01, 0.1, default=0.03, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_2 = DecimalParameter(30.0, 50.0, default=38.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_3 = DecimalParameter(0.01, 0.1, default=0.04, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_3 = DecimalParameter(30.0, 50.0, default=42.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_4 = DecimalParameter(0.01, 0.1, default=0.05, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_4 = DecimalParameter(35.0, 50.0, default=43.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_5 = DecimalParameter(0.01, 0.1, default=0.06, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_5 = DecimalParameter(35.0, 50.0, default=44.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_6 = DecimalParameter(0.01, 0.1, default=0.07, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_6 = DecimalParameter(38.0, 55.0, default=49.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_7 = DecimalParameter(0.01, 0.1, default=0.08, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_7 = DecimalParameter(40.0, 58.0, default=54.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_8 = DecimalParameter(0.06, 0.1, default=0.09, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_8 = DecimalParameter(40.0, 50.0, default=54.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_9 = DecimalParameter(0.05, 0.14, default=0.1, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_9 = DecimalParameter(40.0, 60.0, default=50.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_10 = DecimalParameter(0.1, 0.14, default=0.12, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_10 = DecimalParameter(38.0, 50.0, default=42.0, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_profit_11 = DecimalParameter(0.16, 0.45, default=0.2, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_rsi_11 = DecimalParameter(28.0, 40.0, default=34.0, space='exit', decimals=2, optimize=True, load=True)
    # Profit under EMA200
    exit_custom_under_profit_0 = DecimalParameter(0.01, 0.4, default=0.01, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_0 = DecimalParameter(28.0, 40.0, default=33.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_1 = DecimalParameter(0.01, 0.1, default=0.02, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_1 = DecimalParameter(36.0, 60.0, default=56.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_2 = DecimalParameter(0.01, 0.1, default=0.03, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_2 = DecimalParameter(46.0, 66.0, default=57.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_3 = DecimalParameter(0.01, 0.1, default=0.04, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_3 = DecimalParameter(50.0, 68.0, default=58.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_4 = DecimalParameter(0.02, 0.1, default=0.05, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_4 = DecimalParameter(50.0, 68.0, default=59.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_5 = DecimalParameter(0.02, 0.1, default=0.06, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_5 = DecimalParameter(46.0, 62.0, default=58.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_6 = DecimalParameter(0.03, 0.1, default=0.07, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_6 = DecimalParameter(44.0, 60.0, default=56.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_7 = DecimalParameter(0.04, 0.1, default=0.08, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_7 = DecimalParameter(46.0, 60.0, default=54.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_8 = DecimalParameter(0.06, 0.12, default=0.09, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_8 = DecimalParameter(40.0, 58.0, default=50.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_9 = DecimalParameter(0.08, 0.14, default=0.1, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_9 = DecimalParameter(32.0, 48.0, default=44.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_10 = DecimalParameter(0.1, 0.16, default=0.12, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_10 = DecimalParameter(30.0, 50.0, default=42.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_under_profit_11 = DecimalParameter(0.16, 0.3, default=0.2, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_under_rsi_11 = DecimalParameter(24.0, 40.0, default=34.0, space='exit', decimals=1, optimize=True, load=True)
    # Profit targets for pumped pairs 48h 1
    exit_custom_pump_profit_1_1 = DecimalParameter(0.01, 0.03, default=0.01, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_1_1 = DecimalParameter(26.0, 40.0, default=34.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_1_2 = DecimalParameter(0.01, 0.6, default=0.02, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_1_2 = DecimalParameter(36.0, 50.0, default=40.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_1_3 = DecimalParameter(0.02, 0.1, default=0.04, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_1_3 = DecimalParameter(38.0, 50.0, default=42.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_1_4 = DecimalParameter(0.06, 0.12, default=0.1, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_1_4 = DecimalParameter(36.0, 48.0, default=42.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_1_5 = DecimalParameter(0.14, 0.24, default=0.2, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_1_5 = DecimalParameter(20.0, 40.0, default=34.0, space='exit', decimals=1, optimize=True, load=True)
    # Profit targets for pumped pairs 36h 1
    exit_custom_pump_profit_2_1 = DecimalParameter(0.01, 0.03, default=0.01, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_2_1 = DecimalParameter(26.0, 40.0, default=34.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_2_2 = DecimalParameter(0.01, 0.6, default=0.02, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_2_2 = DecimalParameter(36.0, 50.0, default=40.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_2_3 = DecimalParameter(0.02, 0.1, default=0.04, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_2_3 = DecimalParameter(38.0, 50.0, default=40.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_2_4 = DecimalParameter(0.06, 0.12, default=0.1, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_2_4 = DecimalParameter(36.0, 48.0, default=42.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_2_5 = DecimalParameter(0.14, 0.24, default=0.2, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_2_5 = DecimalParameter(20.0, 40.0, default=34.0, space='exit', decimals=1, optimize=True, load=True)
    # Profit targets for pumped pairs 24h 1
    exit_custom_pump_profit_3_1 = DecimalParameter(0.01, 0.03, default=0.01, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_3_1 = DecimalParameter(26.0, 40.0, default=34.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_3_2 = DecimalParameter(0.01, 0.6, default=0.02, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_3_2 = DecimalParameter(34.0, 50.0, default=40.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_3_3 = DecimalParameter(0.02, 0.1, default=0.04, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_3_3 = DecimalParameter(38.0, 50.0, default=40.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_3_4 = DecimalParameter(0.06, 0.12, default=0.1, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_3_4 = DecimalParameter(36.0, 48.0, default=42.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_profit_3_5 = DecimalParameter(0.14, 0.24, default=0.2, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_rsi_3_5 = DecimalParameter(20.0, 40.0, default=34.0, space='exit', decimals=1, optimize=True, load=True)
    # SMA descending
    exit_custom_dec_profit_min_1 = DecimalParameter(0.01, 0.1, default=0.05, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_dec_profit_max_1 = DecimalParameter(0.06, 0.16, default=0.12, space='exit', decimals=3, optimize=True, load=True)
    # Under EMA100
    exit_custom_dec_profit_min_2 = DecimalParameter(0.05, 0.12, default=0.07, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_dec_profit_max_2 = DecimalParameter(0.06, 0.2, default=0.16, space='exit', decimals=3, optimize=True, load=True)
    # Trail 1
    exit_trail_profit_min_1 = DecimalParameter(0.1, 0.2, default=0.16, space='exit', decimals=2, optimize=True, load=True)
    exit_trail_profit_max_1 = DecimalParameter(0.4, 0.7, default=0.6, space='exit', decimals=2, optimize=True, load=True)
    exit_trail_down_1 = DecimalParameter(0.01, 0.08, default=0.03, space='exit', decimals=3, optimize=True, load=True)
    exit_trail_rsi_min_1 = DecimalParameter(16.0, 36.0, default=20.0, space='exit', decimals=1, optimize=True, load=True)
    exit_trail_rsi_max_1 = DecimalParameter(30.0, 50.0, default=50.0, space='exit', decimals=1, optimize=True, load=True)
    # Trail 2
    exit_trail_profit_min_2 = DecimalParameter(0.08, 0.16, default=0.1, space='exit', decimals=3, optimize=True, load=True)
    exit_trail_profit_max_2 = DecimalParameter(0.3, 0.5, default=0.4, space='exit', decimals=2, optimize=True, load=True)
    exit_trail_down_2 = DecimalParameter(0.02, 0.08, default=0.03, space='exit', decimals=3, optimize=True, load=True)
    exit_trail_rsi_min_2 = DecimalParameter(16.0, 36.0, default=20.0, space='exit', decimals=1, optimize=True, load=True)
    exit_trail_rsi_max_2 = DecimalParameter(30.0, 50.0, default=50.0, space='exit', decimals=1, optimize=True, load=True)
    # Trail 3
    exit_trail_profit_min_3 = DecimalParameter(0.01, 0.12, default=0.06, space='exit', decimals=3, optimize=True, load=True)
    exit_trail_profit_max_3 = DecimalParameter(0.1, 0.3, default=0.2, space='exit', decimals=2, optimize=True, load=True)
    exit_trail_down_3 = DecimalParameter(0.01, 0.06, default=0.05, space='exit', decimals=3, optimize=True, load=True)
    # Under & near EMA200, accept profit
    exit_custom_profit_under_rel_1 = DecimalParameter(0.01, 0.04, default=0.024, space='exit', optimize=True, load=True)
    exit_custom_profit_under_rsi_diff_1 = DecimalParameter(0.0, 20.0, default=4.4, space='exit', optimize=True, load=True)
    # Under & near EMA200, take the loss
    exit_custom_stoploss_under_rel_1 = DecimalParameter(0.001, 0.02, default=0.004, space='exit', optimize=True, load=True)
    exit_custom_stoploss_under_rsi_diff_1 = DecimalParameter(0.0, 20.0, default=8.0, space='exit', optimize=True, load=True)
    # 48h for pump exit checks
    exit_pump_threshold_1 = DecimalParameter(0.5, 1.2, default=0.9, space='exit', decimals=2, optimize=True, load=True)
    exit_pump_threshold_2 = DecimalParameter(0.4, 0.9, default=0.7, space='exit', decimals=2, optimize=True, load=True)
    exit_pump_threshold_3 = DecimalParameter(0.3, 0.7, default=0.5, space='exit', decimals=2, optimize=True, load=True)
    # 36h for pump exit checks
    exit_pump_threshold_4 = DecimalParameter(0.5, 0.9, default=0.72, space='exit', decimals=2, optimize=True, load=True)
    exit_pump_threshold_5 = DecimalParameter(3.0, 6.0, default=4.0, space='exit', decimals=2, optimize=True, load=True)
    exit_pump_threshold_6 = DecimalParameter(0.8, 1.6, default=1.0, space='exit', decimals=2, optimize=True, load=True)
    # 24h for pump exit checks
    exit_pump_threshold_7 = DecimalParameter(0.5, 0.9, default=0.68, space='exit', decimals=2, optimize=True, load=True)
    exit_pump_threshold_8 = DecimalParameter(0.3, 0.6, default=0.62, space='exit', decimals=2, optimize=True, load=True)
    exit_pump_threshold_9 = DecimalParameter(0.2, 0.5, default=0.3, space='exit', decimals=2, optimize=True, load=True)
    # Pumped, descending SMA
    exit_custom_pump_dec_profit_min_1 = DecimalParameter(0.001, 0.04, default=0.005, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_dec_profit_max_1 = DecimalParameter(0.03, 0.08, default=0.05, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_dec_profit_min_2 = DecimalParameter(0.01, 0.08, default=0.04, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_dec_profit_max_2 = DecimalParameter(0.04, 0.1, default=0.06, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_dec_profit_min_3 = DecimalParameter(0.02, 0.1, default=0.06, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_dec_profit_max_3 = DecimalParameter(0.06, 0.12, default=0.09, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_dec_profit_min_4 = DecimalParameter(0.01, 0.05, default=0.02, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_dec_profit_max_4 = DecimalParameter(0.02, 0.1, default=0.04, space='exit', decimals=3, optimize=True, load=True)
    # Pumped 48h 1, under EMA200
    exit_custom_pump_under_profit_min_1 = DecimalParameter(0.02, 0.06, default=0.04, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_under_profit_max_1 = DecimalParameter(0.04, 0.1, default=0.09, space='exit', decimals=3, optimize=True, load=True)
    # Pumped trail 1
    exit_custom_pump_trail_profit_min_1 = DecimalParameter(0.01, 0.12, default=0.05, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_trail_profit_max_1 = DecimalParameter(0.06, 0.16, default=0.07, space='exit', decimals=2, optimize=True, load=True)
    exit_custom_pump_trail_down_1 = DecimalParameter(0.01, 0.06, default=0.05, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_pump_trail_rsi_min_1 = DecimalParameter(16.0, 36.0, default=20.0, space='exit', decimals=1, optimize=True, load=True)
    exit_custom_pump_trail_rsi_max_1 = DecimalParameter(30.0, 50.0, default=70.0, space='exit', decimals=1, optimize=True, load=True)
    # Stoploss, pumped, 48h 1
    exit_custom_stoploss_pump_max_profit_1 = DecimalParameter(0.01, 0.04, default=0.025, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_stoploss_pump_min_1 = DecimalParameter(-0.1, -0.01, default=-0.02, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_stoploss_pump_max_1 = DecimalParameter(-0.1, -0.01, default=-0.01, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_stoploss_pump_ma_offset_1 = DecimalParameter(0.7, 0.99, default=0.94, space='exit', decimals=2, optimize=True, load=True)
    # Stoploss, pumped, 48h 1
    exit_custom_stoploss_pump_max_profit_2 = DecimalParameter(0.01, 0.04, default=0.025, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_stoploss_pump_loss_2 = DecimalParameter(-0.1, -0.01, default=-0.05, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_stoploss_pump_ma_offset_2 = DecimalParameter(0.7, 0.99, default=0.92, space='exit', decimals=2, optimize=True, load=True)
    # Stoploss, pumped, 36h 3
    exit_custom_stoploss_pump_max_profit_3 = DecimalParameter(0.01, 0.04, default=0.008, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_stoploss_pump_loss_3 = DecimalParameter(-0.16, -0.06, default=-0.12, space='exit', decimals=3, optimize=True, load=True)
    exit_custom_stoploss_pump_ma_offset_3 = DecimalParameter(0.7, 0.99, default=0.88, space='exit', decimals=2, optimize=True, load=True)
    #############################################################

    def get_ticker_indicator(self):
        return int(self.timeframe[:-1])

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        max_profit = (trade.max_rate - trade.open_rate) / trade.open_rate
        if last_candle is not None:
            if (current_profit > self.exit_custom_profit_11.value) & (last_candle['rsi'] < self.exit_custom_rsi_11.value):
                return 'signal_profit_11'
            if (self.exit_custom_profit_11.value > current_profit > self.exit_custom_profit_10.value) & (last_candle['rsi'] < self.exit_custom_rsi_10.value):
                return 'signal_profit_10'
            if (self.exit_custom_profit_10.value > current_profit > self.exit_custom_profit_9.value) & (last_candle['rsi'] < self.exit_custom_rsi_9.value):
                return 'signal_profit_9'
            if (self.exit_custom_profit_9.value > current_profit > self.exit_custom_profit_8.value) & (last_candle['rsi'] < self.exit_custom_rsi_8.value):
                return 'signal_profit_8'
            if (self.exit_custom_profit_8.value > current_profit > self.exit_custom_profit_7.value) & (last_candle['rsi'] < self.exit_custom_rsi_7.value):
                return 'signal_profit_7'
            if (self.exit_custom_profit_7.value > current_profit > self.exit_custom_profit_6.value) & (last_candle['rsi'] < self.exit_custom_rsi_6.value):
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
            elif (current_profit > self.exit_custom_under_profit_11.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_11.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_11'
            elif (self.exit_custom_under_profit_11.value > current_profit > self.exit_custom_under_profit_10.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_10.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_10'
            elif (self.exit_custom_under_profit_10.value > current_profit > self.exit_custom_under_profit_9.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_9.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_9'
            elif (self.exit_custom_under_profit_9.value > current_profit > self.exit_custom_under_profit_8.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_8.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_8'
            elif (self.exit_custom_under_profit_8.value > current_profit > self.exit_custom_under_profit_7.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_7.value) & (last_candle['close'] < last_candle['ema_200']):
                return 'signal_profit_u_7'
            elif (self.exit_custom_under_profit_7.value > current_profit > self.exit_custom_under_profit_6.value) & (last_candle['rsi'] < self.exit_custom_under_rsi_6.value) & (last_candle['close'] < last_candle['ema_200']):
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
            elif (self.exit_custom_pump_dec_profit_max_4.value > current_profit > self.exit_custom_pump_dec_profit_min_4.value) & last_candle['sma_200_dec'] & last_candle['exit_pump_24_2_1h']:
                return 'signal_profit_p_d_4'
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

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        # Manage losing trades and open room for better ones.
        if current_profit > 0:
            return 0.99
        else:
            trade_time_50 = current_time - timedelta(minutes=50)
            # Trade open more then 60 minutes. For this strategy it's means -> loss
            # Let's try to minimize the loss
            if trade_time_50 > trade.open_date_utc:
                try:
                    number_of_candle_shift = int((trade_time_50 - trade.open_date_utc).total_seconds() / 300)
                    dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                    candle = dataframe.iloc[-number_of_candle_shift].squeeze()
                    # We are at bottom. Wait...
                    if candle['rsi_1h'] < 35:
                        return 0.99
                    # Are we still sinking? 
                    if candle['close'] > candle['ema_200']:
                        if current_rate * 1.025 < candle['open']:
                            return 0.01
                    if current_rate * 1.015 < candle['open']:
                        return 0.01
                except IndexError as error:
                    # Whoops, set stoploss at 10%
                    return 0.5
        return 0.99

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

    def informative_pairs(self):
        # get access to all pairs available in whitelist.
        pairs = self.dp.current_whitelist()
        # Assign tf to each pair so they can be downloaded and cached for strategy.
        informative_pairs = [(pair, '1h') for pair in pairs]
        return informative_pairs

    def informative_1h_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        assert self.dp, 'DataProvider is required for multiple timeframes.'
        # Get the informative pair
        informative_1h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_1h)
        # EMA
        informative_1h['ema_12'] = ta.EMA(informative_1h, timeperiod=12)
        informative_1h['ema_15'] = ta.EMA(informative_1h, timeperiod=15)
        informative_1h['ema_20'] = ta.EMA(informative_1h, timeperiod=20)
        informative_1h['ema_26'] = ta.EMA(informative_1h, timeperiod=26)
        informative_1h['ema_35'] = ta.EMA(informative_1h, timeperiod=35)
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
        # Chaikin Money Flow
        informative_1h['cmf'] = chaikin_money_flow(informative_1h, 20)
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
        informative_1h['safe_pump_24'] = ((informative_1h['open'].rolling(24).max() - informative_1h['close'].rolling(24).min()) / informative_1h['close'].rolling(24).min() < self.entry_pump_threshold_1.value) | ((informative_1h['open'].rolling(24).max() - informative_1h['close'].rolling(24).min()) / self.entry_pump_pull_threshold_1.value > informative_1h['close'] - informative_1h['close'].rolling(24).min())
        informative_1h['safe_pump_36'] = ((informative_1h['open'].rolling(36).max() - informative_1h['close'].rolling(36).min()) / informative_1h['close'].rolling(36).min() < self.entry_pump_threshold_2.value) | ((informative_1h['open'].rolling(36).max() - informative_1h['close'].rolling(36).min()) / self.entry_pump_pull_threshold_2.value > informative_1h['close'] - informative_1h['close'].rolling(36).min())
        informative_1h['safe_pump_48'] = ((informative_1h['open'].rolling(48).max() - informative_1h['close'].rolling(48).min()) / informative_1h['close'].rolling(48).min() < self.entry_pump_threshold_3.value) | ((informative_1h['open'].rolling(48).max() - informative_1h['close'].rolling(48).min()) / self.entry_pump_pull_threshold_3.value > informative_1h['close'] - informative_1h['close'].rolling(48).min())
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
        dataframe['volume_mean_slow'] = dataframe['volume'].rolling(window=48).mean()
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
        # Alligator
        dataframe['lips'] = ta.SMA(dataframe, timeperiod=5)
        dataframe['smma_lips'] = dataframe['lips'].rolling(3).mean()
        dataframe['teeth'] = ta.SMA(dataframe, timeperiod=8)
        dataframe['smma_teeth'] = dataframe['teeth'].rolling(5).mean()
        dataframe['jaw'] = ta.SMA(dataframe, timeperiod=13)
        dataframe['smma_jaw'] = dataframe['jaw'].rolling(8).mean()
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        # MACD 
        dataframe['macd'], dataframe['signal'], dataframe['hist'] = ta.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        # SMA
        dataframe['sma_5'] = ta.EMA(dataframe, timeperiod=5)
        # Chopiness
        dataframe['chop'] = qtpylib.chopiness(dataframe, 14)
        # Dip protection
        dataframe['safe_dips'] = ((dataframe['open'] - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_1.value) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_2.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_3.value) & ((dataframe['open'].rolling(144).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_4.value)
        dataframe['safe_dips_normal'] = ((dataframe['open'] - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_1.value) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_2.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_3.value) & ((dataframe['open'].rolling(144).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_4.value)
        dataframe['safe_dips_strict'] = ((dataframe['open'] - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_5.value) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_6.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_7.value) & ((dataframe['open'].rolling(144).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_8.value)
        dataframe['safe_dips_loose'] = ((dataframe['open'] - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_9.value) & ((dataframe['open'].rolling(2).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_10.value) & ((dataframe['open'].rolling(12).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_11.value) & ((dataframe['open'].rolling(144).max() - dataframe['close']) / dataframe['close'] < self.entry_dip_threshold_12.value)
        # Volume
        dataframe['volume_mean_4'] = dataframe['volume'].rolling(4).mean().shift(1)
        dataframe['volume_mean_30'] = dataframe['volume'].rolling(30).mean()
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # The indicators for the 1h informative timeframe
        informative_1h = self.informative_1h_indicators(dataframe, metadata)
        dataframe = merge_informative_pair(dataframe, informative_1h, self.timeframe, self.inf_1h, ffill=True)
        # The indicators for the normal (5m) timeframe
        dataframe = self.normal_tf_indicators(dataframe, metadata)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(self.entry_condition_1_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & (dataframe['sma_200'] > dataframe['sma_200'].shift(20)) & dataframe['safe_dips'] & dataframe['safe_pump_48_1h'] & ((dataframe['close'] - dataframe['open'].rolling(36).min()) / dataframe['open'].rolling(36).min() > self.entry_min_inc_1.value) & (dataframe['rsi_1h'] > self.entry_rsi_1h_min_1.value) & (dataframe['rsi_1h'] < self.entry_rsi_1h_max_1.value) & (dataframe['rsi'] < self.entry_rsi_1.value) & (dataframe['mfi'] < self.entry_mfi_1.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_2_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & dataframe['safe_pump_24_strict_1h'] & (dataframe['volume_mean_4'] * self.entry_volume_2.value > dataframe['volume']) & (dataframe['rsi_1h'] > self.entry_rsi_1h_min_2.value) & (dataframe['rsi_1h'] < self.entry_rsi_1h_max_2.value) & (dataframe['rsi'] < dataframe['rsi_1h'] - self.entry_rsi_1h_diff_2.value) & (dataframe['mfi'] < self.entry_mfi_2.value) & (dataframe['close'] < dataframe['bb_lowerband'] * self.entry_bb_offset_2.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_3_enable.value & (dataframe['close'] > dataframe['ema_200_1h'] * self.entry_ema_rel_3.value) & (dataframe['ema_100'] > dataframe['ema_200']) & (dataframe['ema_50_1h'] > dataframe['ema_100_1h']) & (dataframe['ema_100_1h'] > dataframe['ema_200_1h']) & dataframe['safe_pump_36_1h'] & dataframe['lower'].shift().gt(0) & dataframe['bbdelta'].gt(dataframe['close'] * self.entry_bb40_bbdelta_close_3.value) & dataframe['closedelta'].gt(dataframe['close'] * self.entry_bb40_closedelta_close_3.value) & dataframe['tail'].lt(dataframe['bbdelta'] * self.entry_bb40_tail_bbdelta_3.value) & dataframe['close'].lt(dataframe['lower'].shift()) & dataframe['close'].le(dataframe['close'].shift()) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_4_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & dataframe['safe_dips_strict'] & dataframe['safe_pump_24_1h'] & (dataframe['close'] < dataframe['ema_50']) & (dataframe['close'] < self.entry_bb20_close_bblowerband_4.value * dataframe['bb_lowerband']) & (dataframe['volume'] < dataframe['volume_mean_30'].shift(1) * self.entry_bb20_volume_4.value))
        conditions.append(self.entry_condition_5_enable.value & (dataframe['ema_100'] > dataframe['ema_200']) & (dataframe['close'] > dataframe['ema_200_1h'] * self.entry_ema_rel_5.value) & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & dataframe['safe_dips'] & dataframe['safe_pump_36_strict_1h'] & (dataframe['volume_mean_4'] * self.entry_volume_5.value > dataframe['volume']) & (dataframe['ema_26'] > dataframe['ema_12']) & (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.entry_ema_open_mult_5.value) & (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) & (dataframe['close'] < dataframe['bb_lowerband'] * self.entry_bb_offset_5.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_6_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & dataframe['safe_dips_strict'] & (dataframe['volume'].rolling(4).mean() * self.entry_volume_6.value > dataframe['volume']) & (dataframe['ema_26'] > dataframe['ema_12']) & (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.entry_ema_open_mult_6.value) & (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) & (dataframe['close'] < dataframe['bb_lowerband'] * self.entry_bb_offset_6.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_7_enable.value & (dataframe['ema_100'] > dataframe['ema_200']) & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & dataframe['safe_dips'] & (dataframe['volume'].rolling(4).mean() * self.entry_volume_6.value > dataframe['volume']) & (dataframe['ema_26'] > dataframe['ema_12']) & (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.entry_ema_open_mult_7.value) & (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) & (dataframe['rsi'] < self.entry_rsi_7.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_8_enable.value & (dataframe['close'] > dataframe['ema_200_1h'] * self.entry_ema_rel_8.value) & (dataframe['ema_50_1h'] > dataframe['ema_100_1h']) & (dataframe['sma_200_1h'] > dataframe['sma_200_1h'].shift(24)) & (dataframe['close'] > dataframe['open']) & (dataframe['close'] > dataframe['smma_lips']) & (dataframe['smma_lips'] > dataframe['smma_teeth']) & (dataframe['smma_teeth'] > dataframe['smma_jaw']) & (dataframe['smma_lips'].shift(1) > dataframe['smma_teeth'].shift(1)) & (dataframe['smma_teeth'].shift(1) > dataframe['smma_jaw'].shift(1)) & (dataframe['smma_lips'] > dataframe['smma_lips'].shift(1)) & (dataframe['smma_teeth'] > dataframe['smma_teeth'].shift(1)) & (dataframe['smma_jaw'] > dataframe['smma_jaw'].shift(1)) & (dataframe['rsi'] < self.entry_rsi_8.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_9_enable.value & (dataframe['ema_50'] > dataframe['ema_200']) & (dataframe['ema_50_1h'] > dataframe['ema_100_1h']) & dataframe['safe_dips_strict'] & (dataframe['volume_mean_4'] * self.entry_volume_9.value > dataframe['volume']) & (dataframe['close'] < dataframe['sma_30'] * self.entry_ma_offset_9.value) & (dataframe['close'] < dataframe['bb_lowerband'] * self.entry_bb_offset_9.value) & (dataframe['rsi_1h'] > self.entry_rsi_1h_min_9.value) & (dataframe['rsi_1h'] < self.entry_rsi_1h_max_9.value) & (dataframe['mfi'] < self.entry_mfi_9.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_10_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_100_1h']) & (dataframe['sma_200_1h'] > dataframe['sma_200_1h'].shift(24)) & dataframe['safe_dips'] & dataframe['safe_pump_24_1h'] & (dataframe['volume_mean_4'] * self.entry_volume_10.value > dataframe['volume']) & (dataframe['close'] < dataframe['sma_30'] * self.entry_ma_offset_10.value) & (dataframe['close'] < dataframe['bb_lowerband'] * self.entry_bb_offset_10.value) & (dataframe['rsi_1h'] < self.entry_rsi_1h_10.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_11_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_100_1h']) & dataframe['safe_pump_24_1h'] & ((dataframe['close'] - dataframe['open'].rolling(36).min()) / dataframe['open'].rolling(36).min() > self.entry_min_inc_11.value) & (dataframe['close'] < dataframe['sma_30'] * self.entry_ma_offset_11.value) & (dataframe['rsi_1h'] > self.entry_rsi_1h_min_11.value) & (dataframe['rsi_1h'] < self.entry_rsi_1h_max_11.value) & (dataframe['rsi'] < self.entry_rsi_11.value) & (dataframe['mfi'] < self.entry_mfi_11.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_12_enable.value & (dataframe['sma_200_1h'] > dataframe['sma_200_1h'].shift(24)) & dataframe['safe_dips_strict'] & dataframe['safe_pump_24_strict_1h'] & (dataframe['volume_mean_4'] * self.entry_volume_12.value > dataframe['volume']) & (dataframe['close'] < dataframe['sma_30'] * self.entry_ma_offset_12.value) & (dataframe['ewo'] > self.entry_ewo_12.value) & (dataframe['rsi'] < self.entry_rsi_12.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_13_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_100_1h']) & (dataframe['sma_200_1h'] > dataframe['sma_200_1h'].shift(24)) & dataframe['safe_dips_strict'] & dataframe['safe_pump_24_strict_1h'] & (dataframe['close'] < dataframe['sma_30'] * self.entry_ma_offset_13.value) & (dataframe['ewo'] < self.entry_ewo_13.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_14_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & (dataframe['sma_200'] > dataframe['sma_200'].shift(20)) & dataframe['safe_dips_strict'] & dataframe['safe_pump_48_1h'] & (dataframe['volume_mean_4'] * self.entry_volume_14.value > dataframe['volume']) & (dataframe['ema_26'] > dataframe['ema_12']) & (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.entry_ema_open_mult_14.value) & (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) & (dataframe['close'] < dataframe['bb_lowerband'] * self.entry_bb_offset_14.value) & (dataframe['close'] < dataframe['sma_30'] * self.entry_ma_offset_14.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_15_enable.value & (dataframe['close'] > dataframe['ema_200_1h'] * self.entry_ema_rel_15.value) & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & dataframe['safe_dips_strict'] & (dataframe['ema_26'] > dataframe['ema_12']) & (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.entry_ema_open_mult_15.value) & (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) & (dataframe['rsi'] < self.entry_rsi_15.value) & (dataframe['close'] < dataframe['sma_30'] * self.entry_ma_offset_15.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_16_enable.value & (dataframe['ema_50_1h'] > dataframe['ema_200_1h']) & dataframe['safe_dips_strict'] & dataframe['safe_pump_24_strict_1h'] & (dataframe['volume_mean_4'] * self.entry_volume_16.value > dataframe['volume']) & (dataframe['close'] < dataframe['ema_20'] * self.entry_ma_offset_16.value) & (dataframe['ewo'] > self.entry_ewo_16.value) & (dataframe['rsi'] < self.entry_rsi_16.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_17_enable.value & dataframe['safe_dips_strict'] & (dataframe['close'] < dataframe['ema_20'] * self.entry_ma_offset_17.value) & (dataframe['ewo'] < self.entry_ewo_17.value) & (dataframe['volume'] > 0))
        ##From BigZ03
        conditions.append(self.entry_condition_18_enable.value & (dataframe['close'] > dataframe['ema_200']) & (dataframe['close'] > dataframe['ema_200_1h']) & (dataframe['close'] < dataframe['bb_lowerband'] * 0.993) & (dataframe['low'] < dataframe['bb_lowerband'] * 0.985) & (dataframe['close'].shift() > dataframe['bb_lowerband']) & (dataframe['rsi_1h'] < 72.8) & (dataframe['open'] > dataframe['close']) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['open'] - dataframe['close'] < dataframe['bb_upperband'].shift(2) - dataframe['bb_lowerband'].shift(2)) & (dataframe['volume'] > 0))  # Make sure Volume is not 0
        conditions.append(self.entry_condition_19_enable.value & (dataframe['high'] - dataframe['low'] < dataframe['open'] / 100) & (dataframe['open'] < dataframe['close']) & (dataframe['high'].shift() - dataframe['low'].shift() < dataframe['open'].shift() / 100) & (dataframe['high'].shift(2) - dataframe['low'].shift(2) < dataframe['open'].shift(2) / 100) & (dataframe['high'].shift(3) - dataframe['low'].shift(3) < dataframe['open'].shift(3) / 100) & (dataframe['high'].shift(4) - dataframe['low'].shift(4) < dataframe['open'].shift(4) / 100) & (dataframe['high'].shift(5) - dataframe['low'].shift(5) < dataframe['open'].shift(5) / 100) & (dataframe['high'].shift(6) - dataframe['low'].shift(6) < dataframe['open'].shift(6) / 100) & (dataframe['high'].shift(7) - dataframe['low'].shift(7) < dataframe['open'].shift(7) / 100) & (dataframe['high'].shift(8) - dataframe['low'].shift(8) < dataframe['open'].shift(8) / 100) & (dataframe['high'].shift(9) - dataframe['low'].shift(9) < dataframe['open'].shift(9) / 100) & (dataframe['bb_middleband'] > dataframe['bb_middleband'].shift(9) * 1.005) & (dataframe['rsi'] < 68) & (dataframe['volume'] > 0))  # Make sure Volume is not 0
        conditions.append(self.entry_condition_20_enable.value & (dataframe['close'] > dataframe['ema_200']) & (dataframe['rsi'] < 30) & (dataframe['close'] * 1.024 < dataframe['open'].shift(3)) & (dataframe['rsi_1h'] < 71) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_21_enable.value & (dataframe['close'] > dataframe['ema_200']) & (dataframe['close'] > dataframe['ema_200_1h']) & (dataframe['close'] < dataframe['bb_lowerband'] * self.entry_bb20_close_bblowerband_safe_1.value) & (dataframe['rsi_1h'] < 69) & (dataframe['open'] > dataframe['close']) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['open'] - dataframe['close'] < dataframe['bb_upperband'].shift(2) - dataframe['bb_lowerband'].shift(2)) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_22_enable.value & (dataframe['close'] > dataframe['ema_200']) & (dataframe['close'] < dataframe['bb_lowerband'] * self.entry_bb20_close_bblowerband_safe_2.value) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['open'] - dataframe['close'] < dataframe['bb_upperband'].shift(2) - dataframe['bb_lowerband'].shift(2)) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_23_enable.value & (dataframe['close'] > dataframe['ema_200_1h']) & (dataframe['close'] < dataframe['bb_lowerband']) & (dataframe['rsi'] < self.entry_rsi_3.value) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_3.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_24_enable.value & (dataframe['rsi_1h'] < self.entry_rsi_1h_1.value) & (dataframe['close'] < dataframe['bb_lowerband']) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['volume'] > 0))  # Make sure Volume is not 0
        conditions.append(self.entry_condition_25_enable.value & (dataframe['close'] > dataframe['ema_200']) & (dataframe['close'] > dataframe['ema_200_1h']) & (dataframe['ema_26'] > dataframe['ema_12']) & (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.entry_macd_1.value) & (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) & (dataframe['close'] < dataframe['bb_lowerband']) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_26_enable.value & (dataframe['rsi_1h'] < self.entry_rsi_1h_5.value) & (dataframe['ema_26'] > dataframe['ema_12']) & (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.entry_macd_2.value) & (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) & (dataframe['close'] < dataframe['bb_lowerband']) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_27_enable.value & (dataframe['rsi_1h'] < self.entry_rsi_1h_2.value) & (dataframe['ema_26'] > dataframe['ema_12']) & (dataframe['ema_26'] - dataframe['ema_12'] > dataframe['open'] * self.entry_macd_1.value) & (dataframe['ema_26'].shift() - dataframe['ema_12'].shift() > dataframe['open'] / 100) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_28_enable.value & (dataframe['rsi_1h'] < self.entry_rsi_1h_3.value) & (dataframe['rsi'] < self.entry_rsi_1.value) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] > 0))
        conditions.append(self.entry_condition_29_enable.value & (dataframe['rsi_1h'] < self.entry_rsi_1h_4.value) & (dataframe['rsi'] < self.entry_rsi_2.value) & (dataframe['volume'] < dataframe['volume'].shift() * self.entry_volume_drop_1.value) & (dataframe['volume_mean_slow'] > dataframe['volume_mean_slow'].shift(48) * self.entry_volume_pump_1.value) & (dataframe['volume_mean_slow'] * self.entry_volume_pump_1.value < dataframe['volume_mean_slow'].shift(48)) & (dataframe['volume'] > 0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(self.exit_condition_1_enable.value & (dataframe['rsi'] > self.exit_rsi_bb_1.value) & (dataframe['close'] > dataframe['bb_upperband']) & (dataframe['close'].shift(1) > dataframe['bb_upperband'].shift(1)) & (dataframe['close'].shift(2) > dataframe['bb_upperband'].shift(2)) & (dataframe['close'].shift(3) > dataframe['bb_upperband'].shift(3)) & (dataframe['close'].shift(4) > dataframe['bb_upperband'].shift(4)) & (dataframe['close'].shift(5) > dataframe['bb_upperband'].shift(5)) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_2_enable.value & (dataframe['rsi'] > self.exit_rsi_bb_2.value) & (dataframe['close'] > dataframe['bb_upperband']) & (dataframe['close'].shift(1) > dataframe['bb_upperband'].shift(1)) & (dataframe['close'].shift(2) > dataframe['bb_upperband'].shift(2)) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_3_enable.value & (dataframe['rsi'] > self.exit_rsi_main_3.value) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_4_enable.value & (dataframe['rsi'] > self.exit_dual_rsi_rsi_4.value) & (dataframe['rsi_1h'] > self.exit_dual_rsi_rsi_1h_4.value) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_6_enable.value & (dataframe['close'] < dataframe['ema_200']) & (dataframe['close'] > dataframe['ema_50']) & (dataframe['rsi'] > self.exit_rsi_under_6.value) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_7_enable.value & (dataframe['rsi_1h'] > self.exit_rsi_1h_7.value) & qtpylib.crossed_below(dataframe['ema_12'], dataframe['ema_26']) & (dataframe['volume'] > 0))
        conditions.append(self.exit_condition_8_enable.value & (dataframe['close'] > dataframe['bb_upperband_1h'] * self.exit_bb_relative_8.value) & (dataframe['volume'] > 0))  # Don't be gready, exit fast
        # Make sure Volume is not 0
        conditions.append((dataframe['close'] > dataframe['bb_middleband'] * 1.01) & (dataframe['volume'] > 0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit'] = 1
        return dataframe
# Elliot Wave Oscillator

def EWO(dataframe, sma1_length=5, sma2_length=35):
    df = dataframe.copy()
    sma1 = ta.EMA(df, timeperiod=sma1_length)
    sma2 = ta.EMA(df, timeperiod=sma2_length)
    smadif = (sma1 - sma2) / df['close'] * 100
    return smadif
# Chaikin Money Flow

def chaikin_money_flow(dataframe, n=20, fillna=False):
    """Chaikin Money Flow (CMF)
    It measures the amount of Money Flow Volume over a specific period.
    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:chaikin_money_flow_cmf
    Args:
        dataframe(pandas.Dataframe): dataframe containing ohlcv
        n(int): n period.
        fillna(bool): if True, fill nan values.
    Returns:
        pandas.Series: New feature generated.
    """
    df = dataframe.copy()
    mfv = (df['close'] - df['low'] - (df['high'] - df['close'])) / (df['high'] - df['low'])
    mfv = mfv.fillna(0.0)  # float division by zero
    mfv *= df['volume']
    cmf = mfv.rolling(n, min_periods=0).sum() / df['volume'].rolling(n, min_periods=0).sum()
    if fillna:
        cmf = cmf.replace([np.inf, -np.inf], np.nan).fillna(0)
    return Series(cmf, name='cmf')