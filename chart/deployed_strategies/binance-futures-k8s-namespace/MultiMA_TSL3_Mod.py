import freqtrade.vendor.qtpylib.indicators as qtpylib
from typing import Dict, List
import numpy as np
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair, DecimalParameter, IntParameter, RealParameter, BooleanParameter, timeframe_to_minutes
from pandas import DataFrame, Series
from functools import reduce
from freqtrade.persistence import Trade
from datetime import datetime, timedelta
from freqtrade.exchange import timeframe_to_prev_date
from technical.indicators import zema, VIDYA
###########################################################################################################
##    MultiMA_TSL, modded by stash86, based on SMAOffsetProtectOptV1 (modded by Perkmeister)             ##
##    Based on @Lamborghini Store's SMAOffsetProtect strat, heavily based on @tirail's original SMAOffset##
##                                                                                                       ##
##    Strategy for Freqtrade https://github.com/freqtrade/freqtrade                                      ##
##                                                                                                       ##
##    Thanks to                                                                                          ##
##    - Perkmeister, for their snippets for the exit signals and decaying EMA exit                       ##
##    - ChangeToTower, for the PMax idea                                                                 ##
##    - JimmyNixx, for their snippet to limit close value from the peak (that I modify into 5m tf check) ##
##    - froggleston, for the Heikinashi check snippet from Cryptofrog                                    ##
##    - Uzirox, for their pump detection code                                                            ##
##                                                                                                       ##
##                                                                                                       ##
###########################################################################################################
# I hope you do enough testing before proceeding, either backtesting and/or dry run.
# Any profits and losses are all your responsibility

class MultiMA_TSL3_Mod(IStrategy):
    INTERFACE_VERSION = 3
    DATESTAMP = 0
    SELLMA = 1
    SELL_TRIGGER = 2
    # Buy hyperspace params:
    # value loaded from strategy
    entry_params = {'entry_rsi_fast_max': 98, 'entry_rsi_fast_min': 36, 'entry_rsi_max': 79, 'entry_rsi_min': 24, 'ewo_high': 0.546, 'ewo_high2': 8.497, 'ewo_low': -14.239, 'ewo_low2': -15.614, 'fast_ewo': 12, 'pmax_pct_max': 83.754, 'pmax_pct_min': 20.09, 'slow_ewo': 150, 'volume_pct_max': 8.721, 'volume_pct_min': 0.247, 'entry_condition_ema_enable': True, 'close_pct_max': 0.06785, 'close_pct_min': 0.01121}
    # Sell hyperspace params:
    exit_params = {'base_nb_candles_ema_exit': 65, 'base_nb_candles_ema_exit2': 49, 'high_offset_exit_ema': 1.074}
    # Protection hyperspace params:
    protection_params = {'cooldown_lookback': 39, 'low_profit_lookback': 29, 'low_profit_min_req': -0.03, 'low_profit_stop_duration': 52}
    # ROI table:
    minimal_roi = {'0': 100}
    stoploss = -0.15
    use_custom_stoploss = True
    # Trailing stoploss (not used)
    trailing_stop = False
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.018
    # Buy hyperspace params:
    "optimize_entry_ema = False # Not used\n    base_nb_candles_entry_ema = IntParameter(5, 80, default=20, space='entry', optimize=optimize_entry_ema)\n    low_offset_ema = DecimalParameter(0.9, 1.1, default=0.958, space='entry', optimize=optimize_entry_ema)\n    base_nb_candles_entry_ema2 = IntParameter(5, 80, default=20, space='entry', optimize=optimize_entry_ema)\n    low_offset_ema2 = DecimalParameter(0.9, 1.1, default=0.958, space='entry', optimize=optimize_entry_ema)\n\n    optimize_entry_trima = False # Not used\n    base_nb_candles_entry_trima = IntParameter(5, 80, default=20, space='entry', optimize=optimize_entry_trima)\n    low_offset_trima = DecimalParameter(0.9, 0.99, default=0.958, space='entry', optimize=optimize_entry_trima)\n    base_nb_candles_entry_trima2 = IntParameter(5, 80, default=20, space='entry', optimize=optimize_entry_trima)\n    low_offset_trima2 = DecimalParameter(0.9, 0.99, default=0.958, space='entry', optimize=optimize_entry_trima)\n    \n    optimize_entry_zema = False # Not used\n    base_nb_candles_entry_zema = IntParameter(5, 80, default=20, space='entry', optimize=optimize_entry_zema)\n    low_offset_zema = DecimalParameter(0.9, 0.99, default=0.958, space='entry', optimize=optimize_entry_zema)\n    base_nb_candles_entry_zema2 = IntParameter(5, 80, default=20, space='entry', optimize=optimize_entry_zema)\n    low_offset_zema2 = DecimalParameter(0.9, 0.99, default=0.958, space='entry', optimize=optimize_entry_zema)\n\n    optimize_entry_hma = False # Not used\n    base_nb_candles_entry_hma = IntParameter(5, 80, default=20, space='entry', optimize=optimize_entry_hma)\n    low_offset_hma = DecimalParameter(0.9, 0.99, default=0.958, space='entry', optimize=optimize_entry_hma)\n    base_nb_candles_entry_hma2 = IntParameter(5, 80, default=20, space='entry', optimize=optimize_entry_hma)\n    low_offset_hma2 = DecimalParameter(0.9, 0.99, default=0.958, space='entry', optimize=optimize_entry_hma)"
    entry_condition_enable_optimize = False  # Not used
    entry_condition_ema_enable = BooleanParameter(default=True, space='entry', optimize=entry_condition_enable_optimize)
    "entry_condition_trima_enable = BooleanParameter(default=True, space='entry', optimize=entry_condition_enable_optimize)\n    entry_condition_zema_enable = BooleanParameter(default=True, space='entry', optimize=entry_condition_enable_optimize)\n    entry_condition_hma_enable = BooleanParameter(default=True, space='entry', optimize=entry_condition_enable_optimize)"
    ewo_check_optimize = True
    ewo_low = DecimalParameter(-20.0, -8.0, default=-20.0, space='entry', optimize=ewo_check_optimize)
    ewo_high = DecimalParameter(0.0, 12.0, default=6.0, space='entry', optimize=ewo_check_optimize)
    ewo_low2 = DecimalParameter(-20.0, -8.0, default=-20.0, space='entry', optimize=ewo_check_optimize)
    ewo_high2 = DecimalParameter(2.0, 12.0, default=6.0, space='entry', optimize=ewo_check_optimize)
    fast_ewo = IntParameter(10, 50, default=50, space='entry', optimize=True)
    slow_ewo = IntParameter(100, 200, default=200, space='entry', optimize=True)
    pct_optimize = True
    pmax_pct_min = DecimalParameter(1.0, 100.0, default=1, space='entry', optimize=pct_optimize)
    pmax_pct_max = DecimalParameter(1.0, 100.0, default=1, space='entry', optimize=pct_optimize)
    volume_pct_min = DecimalParameter(0.01, 20, default=0.01, space='entry', optimize=pct_optimize)
    volume_pct_max = DecimalParameter(0.01, 20, default=0.01, space='entry', optimize=pct_optimize)
    high_precision_pct_optimize = False  # Optimise this setting individually
    close_pct_min = RealParameter(0.0001, 0.1, default=0.01, space='entry', optimize=high_precision_pct_optimize)
    close_pct_max = RealParameter(0.0001, 0.1, default=0.01, space='entry', optimize=high_precision_pct_optimize)
    entry_rsi_optimize = True
    entry_rsi_min = IntParameter(0, 100, default=1, space='entry', optimize=entry_rsi_optimize)
    entry_rsi_max = IntParameter(0, 100, default=100, space='entry', optimize=entry_rsi_optimize)
    entry_rsi_fast_min = IntParameter(0, 100, default=1, space='entry', optimize=entry_rsi_optimize)
    entry_rsi_fast_max = IntParameter(0, 100, default=100, space='entry', optimize=entry_rsi_optimize)
    # Sell hyperspace params:
    optimize_exit_ema = True
    base_nb_candles_ema_exit = IntParameter(5, 80, default=20, space='exit', optimize=True)
    high_offset_exit_ema = DecimalParameter(0.99, 1.1, default=1.012, space='exit', optimize=True)
    base_nb_candles_ema_exit2 = IntParameter(5, 80, default=20, space='exit', optimize=True)
    # Protection hyperspace params:
    cooldown_lookback = IntParameter(2, 48, default=2, space='protection', optimize=True)
    low_profit_optimize = True
    low_profit_lookback = IntParameter(2, 60, default=20, space='protection', optimize=low_profit_optimize)
    low_profit_stop_duration = IntParameter(12, 200, default=20, space='protection', optimize=low_profit_optimize)
    low_profit_min_req = DecimalParameter(-0.05, 0.05, default=-0.05, space='protection', decimals=2, optimize=low_profit_optimize)

    @property
    def protections(self):
        prot = []
        prot.append({'method': 'CooldownPeriod', 'stop_duration_candles': self.cooldown_lookback.value})
        prot.append({'method': 'LowProfitPairs', 'lookback_period_candles': self.low_profit_lookback.value, 'trade_limit': 1, 'stop_duration': int(self.low_profit_stop_duration.value), 'required_profit': self.low_profit_min_req.value})
        return prot
    # Optimal timeframe for the strategy.
    timeframe = '5m'
    # storage dict for custom info
    custom_info = {}
    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True
    # These values can be overridden in the "ask_strategy" section in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 400

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return False
        last_candle = dataframe.iloc[-1]
        if self.custom_info[pair][self.DATESTAMP] != last_candle['date']:
            # new candle, update EMA and check exit
            # smoothing coefficients
            exit_ema = self.custom_info[pair][self.SELLMA]
            if exit_ema == 0:
                exit_ema = last_candle['ema_exit']
            emaLength = 32
            alpha = 2 / (1 + emaLength)
            # update exit_ema
            exit_ema = alpha * last_candle['close'] + (1 - alpha) * exit_ema
            self.custom_info[pair][self.SELLMA] = exit_ema
            self.custom_info[pair][self.DATESTAMP] = last_candle['date']
            if (last_candle['close'] > exit_ema * self.high_offset_exit_ema.value) & (last_candle['entry_copy'] == 0):
                if self.config['runmode'].value in ('live', 'dry_run'):
                    self.custom_info[pair][self.SELL_TRIGGER] = 1
                    return False
                entry_tag = 'empty'
                if hasattr(trade, 'entry_tag') and trade.entry_tag is not None:
                    entry_tag = trade.entry_tag
                else:
                    trade_open_date = timeframe_to_prev_date(self.timeframe, trade.open_date_utc)
                    entry_signal = dataframe.loc[dataframe['date'] < trade_open_date]
                    if not entry_signal.empty:
                        entry_signal_candle = entry_signal.iloc[-1]
                        entry_tag = entry_signal_candle['entry_tag'] if entry_signal_candle['entry_tag'] != '' else 'empty'
                return f'New Sell Signal ({entry_tag})'
        return False
    #credit to Perkmeister for this custom stoploss to help the strategy ride a green candle when the exit signal triggered

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        sl_new = 1
        if self.custom_info[pair][self.SELL_TRIGGER] == 1:
            if self.config['runmode'].value in ('live', 'dry_run'):
                sl_new = 0.001
        if current_profit > 0.2:
            sl_new = 0.05
        elif current_profit > 0.1:
            sl_new = 0.03
        elif current_profit > 0.06:
            sl_new = 0.02
        elif current_profit > 0.03:
            sl_new = 0.01
        return sl_new

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, **kwargs) -> bool:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return False
        last_candle = dataframe.iloc[-1].squeeze()
        if rate > last_candle['close']:
            return False
        self.custom_info[pair][self.DATESTAMP] = last_candle['date']
        self.custom_info[pair][self.SELLMA] = last_candle['ema_exit']
        return True

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float, rate: float, time_in_force: str, exit_reason: str, **kwargs) -> bool:
        self.custom_info[pair][self.SELL_TRIGGER] = 0
        return True

    def get_ticker_indicator(self):
        return int(self.timeframe[:-1])

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Parabolic SAR
        dataframe['sar'] = ta.SAR(dataframe)
        # EWO
        #dataframe['ema_delta'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema2.value)) - ta.EMA(dataframe, int(self.base_nb_candles_entry_ema.value)) *self.low_offset_ema.value # EWO delta? Not used anyway
        dataframe['ewo'] = EWO(dataframe, self.fast_ewo.value, self.slow_ewo.value)
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_84'] = ta.RSI(dataframe, timeperiod=84)
        dataframe['rsi_112'] = ta.RSI(dataframe, timeperiod=112)
        # Heiken Ashi
        heikinashi = qtpylib.heikinashi(dataframe)
        heikinashi['volume'] = dataframe['volume']
        dataframe['ha_up'] = (heikinashi['close'] > heikinashi['open']).astype('int')
        dataframe['ha_down'] = (heikinashi['open'] > heikinashi['close']).astype('int')
        # Profit Maximizer - PMAX
        dataframe['pm'], dataframe['pmx'] = pmax(heikinashi, MAtype=1, length=9, multiplier=27, period=10, src=3)
        dataframe['source'] = (dataframe['high'] + dataframe['low'] + dataframe['open'] + dataframe['close']) / 4
        dataframe['pmax_thresh'] = ta.EMA(dataframe['source'], timeperiod=9)
        dataframe = HA(dataframe, 4)
        if self.config['runmode'].value in ('live', 'dry_run'):
            # Exchange downtime protection
            dataframe['live_data_ok'] = dataframe['volume'].rolling(window=72, min_periods=72).min() > 0
        else:
            dataframe['live_data_ok'] = True
        # Check if the entry already exists
        if not metadata['pair'] in self.custom_info:
            # Create empty entry for this pair {datestamp, exitma, exit_trigger}
            self.custom_info[metadata['pair']] = ['', 0, 0]
        dataframe['24hr_high'] = dataframe['high'].rolling(window=288, min_periods=288).max()
        dataframe['smooth_high'] = ta.EMA(dataframe['24hr_high'], timeperiod=2)
        dataframe['high_rising'] = (dataframe['smooth_high'] > dataframe['smooth_high'].shift()).astype('int')
        dataframe['high_falling'] = (dataframe['smooth_high'] < dataframe['smooth_high'].shift()).astype('int')
        dataframe['24hr_low'] = dataframe['low'].rolling(window=288, min_periods=288).min()
        dataframe['smooth_low'] = ta.EMA(dataframe['24hr_low'], timeperiod=2)
        dataframe['low_rising'] = (dataframe['smooth_low'] > dataframe['smooth_low'].shift()).astype('int')
        dataframe['low_falling'] = (dataframe['smooth_low'] < dataframe['smooth_low'].shift()).astype('int')
        dataframe['24hr_delta'] = dataframe['24hr_high'] - dataframe['24hr_low']
        dataframe['smooth_delta'] = ta.EMA(dataframe['24hr_delta'], timeperiod=2)
        dataframe['delta_rising'] = (dataframe['smooth_delta'] > dataframe['smooth_delta'].shift()).astype('int')
        dataframe['pmax_high_delta'] = dataframe['24hr_high'] - dataframe['pmax_thresh']
        dataframe['smooth_pmax_high'] = ta.EMA(dataframe['pmax_high_delta'], timeperiod=2)
        dataframe['pmax_low_delta'] = dataframe['pmax_thresh'] - dataframe['24hr_low']
        dataframe['smooth_pmax_low'] = ta.EMA(dataframe['pmax_low_delta'], timeperiod=2)
        dataframe['pmax_pct'] = (dataframe['pmax_thresh'] - dataframe['24hr_low']) / (dataframe['24hr_high'] - dataframe['24hr_low']) * 100
        dataframe['pmax_pct_rising'] = (dataframe['pmax_pct'] > dataframe['pmax_pct'].shift()).astype('int')
        dataframe['smooth_volume'] = ta.EMA(dataframe['volume'], timeperiod=2)
        dataframe['smooth_volume_slow'] = ta.EMA(dataframe['volume'], timeperiod=12)
        dataframe['volume_pct'] = dataframe['volume'].pct_change()
        dataframe['smooth_volume_pct'] = ta.EMA(dataframe['volume_pct'], timeperiod=2)
        dataframe['volume_pct_rising'] = (dataframe['volume_pct'] > dataframe['volume_pct'].shift()).astype('int')
        dataframe['smooth_volume_pct_rising'] = ta.EMA(dataframe['volume_pct_rising'], timeperiod=2)
        dataframe['close_pct'] = dataframe['close'].pct_change()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        "dataframe['ema_offset_entry'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema.value)) *self.low_offset_ema.value\n        dataframe['ema_offset_entry2'] = ta.EMA(dataframe, int(self.base_nb_candles_entry_ema2.value)) *self.low_offset_ema2.value"
        dataframe['ema_exit'] = ta.EMA(dataframe, int(self.base_nb_candles_ema_exit.value))
        dataframe.loc[:, 'entry_tag'] = ''
        dataframe.loc[:, 'entry_copy'] = 0
        dataframe.loc[:, 'entry'] = 0
        if self.entry_condition_ema_enable.value:
            #(dataframe['pm'] <= dataframe['pmax_thresh'])
            #&
            #(dataframe['ha_up'].rolling(self.ha_rolling_up.value).sum() == self.ha_rolling_up.value)
            #&
            #(qtpylib.crossed_above(dataframe['HA_Close'].shift(self.ha_rolling_up.value -1 ), dataframe['HA_Open'].shift(self.ha_rolling_up.value + 1)))
            #&
            #(dataframe['ha_down'].shift(self.ha_rolling_up.value).rolling(self.ha_rolling_down.value).sum() == self.ha_rolling_down.value)
            #&
            #&
            #(dataframe['high_rising'] == 1)
            entry_offset_ema = qtpylib.crossed_below(dataframe['sar'], dataframe['pmax_thresh']) & (dataframe['pmax_thresh'] > dataframe['pm']) & (dataframe['pmax_thresh'] > dataframe['sar'])
            dataframe.loc[entry_offset_ema, 'entry_tag'] += 'ema '
            conditions.append(entry_offset_ema)
        "if (self.entry_condition_zema_enable.value):\n            dataframe['zema_offset_entry'] = zema(dataframe, int(self.base_nb_candles_entry_zema.value)) *self.low_offset_zema.value\n            dataframe['zema_offset_entry2'] = zema(dataframe, int(self.base_nb_candles_entry_zema2.value)) *self.low_offset_zema2.value\n            entry_offset_zema = (\n                (\n                    (dataframe['close'] < dataframe['zema_offset_entry'])\n                    &\n                    (dataframe['pm'] <= dataframe['pmax_thresh'])\n                )\n                |\n                (\n                    (dataframe['close'] < dataframe['zema_offset_entry2'])\n                    &\n                    (dataframe['pm'] > dataframe['pmax_thresh'])\n                )\n            )\n            dataframe.loc[entry_offset_zema, 'entry_tag'] += 'zema '\n            conditions.append(entry_offset_zema)\n\n        if (self.entry_condition_hma_enable.value):\n            dataframe['hma_offset_entry'] = qtpylib.hull_moving_average(dataframe['close'], window=int(self.base_nb_candles_entry_hma.value)) *self.low_offset_hma.value\n            dataframe['hma_offset_entry2'] = qtpylib.hull_moving_average(dataframe['close'], window=int(self.base_nb_candles_entry_hma2.value)) *self.low_offset_hma2.value\n            entry_offset_hma = (\n                (\n                    (\n                        (dataframe['close'] < dataframe['hma_offset_entry'])\n                        &\n                        (dataframe['pm'] <= dataframe['pmax_thresh'])\n                        &\n                        (dataframe['rsi'] < 35)\n    \n                    )\n                    |\n                    (\n                        (dataframe['close'] < dataframe['hma_offset_entry2'])\n                        &\n                        (dataframe['pm'] > dataframe['pmax_thresh'])\n                        &\n                        (dataframe['rsi'] < 30)\n                    )\n                )\n                &\n                (dataframe['rsi_fast'] < 30)\n                \n            )\n            dataframe.loc[entry_offset_hma, 'entry_tag'] += 'hma '\n            conditions.append(entry_offset_hma)"
        #(dataframe['open'] < dataframe['ema_offset_entry'])
        #&
        #(dataframe['entry_low_rolling'].shift().rolling(self.entry_smooth_ha_rolling.value).sum() == self.entry_low_rolling.value)
        #&
        #(dataframe['delta_rising'].rolling(5).sum() == self.entry_smooth_ha_rolling.value)
        #&
        #(dataframe['close'] > (dataframe['ema_exit'] * self.high_offset_exit_ema.value))
        #&
        #(dataframe['close'].rolling(288).max() < (dataframe['close'] * 1.10 ))
        #&
        #(dataframe['Smooth_HA_O'].shift(1) < dataframe['Smooth_HA_H'].shift(1))
        #&
        #(dataframe['rsi_fast'] > self.entry_rsi_fast.value)
        #&
        #(dataframe['rsi_84'] > 60)
        #&
        #(dataframe['rsi_112'] > 60)
        #&
        #(dataframe['ewo'] > self.ewo_high.value)
        #&
        #(
        #    (
        #        (dataframe['close'] > dataframe['pmax_thresh'])
        #        &
        #        (dataframe['pm'] > dataframe['pmax_thresh'])
        #        &
        #        (
        #            (dataframe['ewo'] < self.ewo_low.value)
        #            |
        #            (
        #                (dataframe['ewo'] > self.ewo_high.value)
        #                &
        #                (dataframe['rsi'] < self.rsi_entry.value)
        #            )
        #        )
        #    )
        #    |
        #    (
        #        (dataframe['close'] > dataframe['pmax_thresh'])
        #        &
        #        (dataframe['pm'] > dataframe['pmax_thresh'])
        #        &
        #        (
        #            (dataframe['ewo'] < self.ewo_low2.value)
        #            |
        #            (
        #                (dataframe['ewo'] > self.ewo_high2.value)
        #                &
        #                (dataframe['rsi'] < self.rsi_entry2.value)
        #            )
        #        )
        #    )
        #)
        #&
        add_check = dataframe['live_data_ok'] & (dataframe['pmax_pct'] > self.pmax_pct_min.value) & (dataframe['volume_pct'] > self.volume_pct_min.value) & (dataframe['close_pct'] > self.close_pct_min.value) & (dataframe['rsi'] > self.entry_rsi_min.value) & (dataframe['rsi_fast'] > self.entry_rsi_fast_min.value) & (dataframe['pmax_pct'] < self.pmax_pct_max.value) & (dataframe['volume_pct'] < self.volume_pct_max.value) & (dataframe['close_pct'] < self.close_pct_max.value) & (dataframe['rsi'] < self.entry_rsi_max.value) & (dataframe['rsi_fast'] < self.entry_rsi_fast_max.value) & (dataframe['ewo'] > self.ewo_high.value) & (dataframe['volume'] > 0)
        if conditions:
            dataframe.loc[add_check & reduce(lambda x, y: x | y, conditions), ['entry_copy', 'entry']] = (1, 1)
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit'] = 0
        return dataframe
# Elliot Wave Oscillator

def EWO(dataframe, sma1_length=5, sma2_length=35):
    df = dataframe.copy()
    sma1 = ta.EMA(df, timeperiod=sma1_length)
    sma2 = ta.EMA(df, timeperiod=sma2_length)
    smadif = (sma1 - sma2) / df['close'] * 100
    return smadif
# PMAX

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
# smoothed Heiken Ashi

def HA(dataframe, smoothing=None):
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

def pump_warning(dataframe, perc=15):
    df = dataframe.copy()
    df['change'] = df['high'] - df['low']
    df['test1'] = df['close'] > df['open']
    df['test2'] = df['change'] / df['low'] > perc / 100
    df['result'] = (df['test1'] & df['test2']).astype('int')
    return df['result']