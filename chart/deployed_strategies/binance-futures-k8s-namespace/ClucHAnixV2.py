from typing import Optional
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair, DecimalParameter, stoploss_from_open
from pandas import DataFrame, Series
from datetime import datetime

def bollinger_bands(stock_price, window_size, num_of_std):
    rolling_mean = stock_price.rolling(window=window_size).mean()
    rolling_std = stock_price.rolling(window=window_size).std()
    lower_band = rolling_mean - rolling_std * num_of_std
    return (np.nan_to_num(rolling_mean), np.nan_to_num(lower_band))

def ha_typical_price(bars):
    res = (bars['ha_high'] + bars['ha_low'] + bars['ha_close']) / 3.0
    return Series(index=bars.index, data=res)

class ClucHAnixV2(IStrategy):
    INTERFACE_VERSION = 3
    '\n    PASTE OUTPUT FROM HYPEROPT HERE\n    Can be overridden for specific sub-strategies (stake currencies) at the bottom.\n    '
    entry_params = {'bbdelta-close': 0.01965, 'bbdelta-tail': 0.95089, 'close-bblower': 0.00799, 'closedelta-close': 0.00556, 'rocr-1h': 0.54904}
    # Sell hyperspace params:
    # custom stoploss params, come from BB_RPB_TSL
    exit_params = {'pHSL': -0.15, 'pPF_1': 0.02, 'pPF_2': 0.05, 'pSL_1': 0.02, 'pSL_2': 0.04, 'exit-fisher': 0.38414, 'exit-bbmiddle-close': 1.07634}
    # ROI table:
    minimal_roi = {'0': 100}
    # Stoploss:
    stoploss = -0.99  # use custom stoploss
    # Trailing stop:
    trailing_stop = False
    trailing_stop_positive = 0.001
    trailing_stop_positive_offset = 0.012
    trailing_only_offset_is_reached = False
    '\n    END HYPEROPT\n    '
    timeframe = '1m'
    # Make sure these match or are not overridden in config
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    # Custom stoploss
    use_custom_stoploss = True
    process_only_new_candles = True
    startup_candle_count = 168
    order_types = {'entry': 'limit', 'exit': 'limit', 'emergencyexit': 'limit', 'forceentry': 'limit', 'forceexit': 'limit', 'stoploss': 'limit', 'stoploss_on_exchange': False, 'stoploss_on_exchange_interval': 60, 'stoploss_on_exchange_limit_ratio': 0.99}
    # hard stoploss profit
    pHSL = DecimalParameter(-0.2, -0.04, default=-0.08, decimals=3, space='exit', load=True)
    # profit threshold 1, trigger point, SL_1 is used
    pPF_1 = DecimalParameter(0.008, 0.02, default=0.016, decimals=3, space='exit', load=True)
    pSL_1 = DecimalParameter(0.008, 0.02, default=0.011, decimals=3, space='exit', load=True)
    # profit threshold 2, SL_2 is used
    pPF_2 = DecimalParameter(0.04, 0.1, default=0.08, decimals=3, space='exit', load=True)
    pSL_2 = DecimalParameter(0.02, 0.07, default=0.04, decimals=3, space='exit', load=True)

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, '1h') for pair in pairs]
        informative_pairs += [(f'BTC/USDT', '1d')]
        return informative_pairs

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        # hard stoploss profit
        HSL = self.pHSL.value
        PF_1 = self.pPF_1.value
        SL_1 = self.pSL_1.value
        PF_2 = self.pPF_2.value
        SL_2 = self.pSL_2.value
        # For profits between PF_1 and PF_2 the stoploss (sl_profit) used is linearly interpolated
        # between the values of SL_1 and SL_2. For all profits above PL_2 the sl_profit value
        # rises linearly with current profit, for profits below PF_1 the hard stoploss profit is used.
        if current_profit > PF_2:
            sl_profit = SL_2 + (current_profit - PF_2)
        elif current_profit > PF_1:
            sl_profit = SL_1 + (current_profit - PF_1) * (SL_2 - SL_1) / (PF_2 - PF_1)
        else:
            sl_profit = HSL
        # Only for hyperopt invalid return
        if sl_profit >= current_profit:
            return -0.99
        return stoploss_from_open(sl_profit, current_profit)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # # Heikin Ashi Candles
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['ha_open'] = heikinashi['open']
        dataframe['ha_close'] = heikinashi['close']
        dataframe['ha_high'] = heikinashi['high']
        dataframe['ha_low'] = heikinashi['low']
        # Set Up Bollinger Bands
        mid, lower = bollinger_bands(ha_typical_price(dataframe), window_size=40, num_of_std=2)
        dataframe['lower'] = lower
        dataframe['mid'] = mid
        dataframe['bbdelta'] = (mid - dataframe['lower']).abs()
        dataframe['closedelta'] = (dataframe['ha_close'] - dataframe['ha_close'].shift()).abs()
        dataframe['tail'] = (dataframe['ha_close'] - dataframe['ha_low']).abs()
        dataframe['bb_lowerband'] = dataframe['lower']
        dataframe['bb_middleband'] = dataframe['mid']
        dataframe['ema_fast'] = ta.EMA(dataframe['ha_close'], timeperiod=3)
        dataframe['ema_slow'] = ta.EMA(dataframe['ha_close'], timeperiod=50)
        dataframe['volume_mean_slow'] = dataframe['volume'].rolling(window=30).mean()
        dataframe['rocr'] = ta.ROCR(dataframe['ha_close'], timeperiod=28)
        rsi = ta.RSI(dataframe)
        dataframe['rsi'] = rsi
        rsi = 0.1 * (rsi - 50)
        dataframe['fisher'] = (np.exp(2 * rsi) - 1) / (np.exp(2 * rsi) + 1)
        inf_tf = '1h'
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=inf_tf)
        inf_heikinashi = qtpylib.heikinashi(informative)
        informative['ha_close'] = inf_heikinashi['close']
        informative['rocr'] = ta.ROCR(informative['ha_close'], timeperiod=168)
        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, inf_tf, ffill=True)
        # get btc 1d informative
        inf_tf_1d = '1d'
        informative_btc_1d = self.dp.get_pair_dataframe(pair=f'BTC/USDT', timeframe=inf_tf_1d)
        informative_btc_1d['ema90'] = ta.EMA(informative_btc_1d, timeperiod=90)
        macd = ta.MACD(informative_btc_1d, fastperiod=12, slowperiod=26, signalperiod=9)
        informative_btc_1d['macd'] = macd['macd']
        informative_btc_1d['macdsignal'] = macd['macdsignal']
        informative_btc_1d['macdhist'] = macd['macdhist']
        dataframe = merge_informative_pair(dataframe, informative_btc_1d, self.timeframe, inf_tf_1d, ffill=True)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.entry_params
        dataframe.loc[:, 'enter_tag'] = 'clucha '
        dataframe.loc[((dataframe['macd_1d'] > dataframe['macdsignal_1d']) & (dataframe['macdhist_1d'] > dataframe['macdhist_1d'].shift()) | (dataframe['close_1d'] > dataframe['ema90_1d'])) & (dataframe['rocr_1h'].gt(params['rocr-1h']) & dataframe['lower'].shift().gt(0) & dataframe['bbdelta'].gt(dataframe['ha_close'] * params['bbdelta-close']) & dataframe['closedelta'].gt(dataframe['ha_close'] * params['closedelta-close']) & dataframe['tail'].lt(dataframe['bbdelta'] * params['bbdelta-tail']) & dataframe['ha_close'].lt(dataframe['lower'].shift()) & dataframe['ha_close'].le(dataframe['ha_close'].shift()) | (dataframe['ha_close'] < dataframe['ema_slow']) & (dataframe['ha_close'] < params['close-bblower'] * dataframe['bb_lowerband'])), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.exit_params
        dataframe.loc[(dataframe['fisher'] > params['exit-fisher']) & dataframe['ha_high'].le(dataframe['ha_high'].shift(1)) & dataframe['ha_high'].shift(1).le(dataframe['ha_high'].shift(2)) & dataframe['ha_close'].le(dataframe['ha_close'].shift(1)) & (dataframe['ema_fast'] > dataframe['ha_close']) & (dataframe['ha_close'] * params['exit-bbmiddle-close'] > dataframe['bb_middleband']) & (dataframe['volume'] > 0), 'exit_long'] = 1
        return dataframe

class ClucDCAV2(ClucHAnixV2):
    position_adjustment_enable = True
    max_reentry_orders = 2
    max_reentry_multiplier = 3
    # This is called when placing the initial order (opening trade)

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float, min_stake: float, max_stake: float, entry_tag: Optional[str], **kwargs) -> float:
        if self.config['position_adjustment_enable'] is True and self.config['stake_amount'] == 'unlimited':
            return proposed_stake / self.max_reentry_multiplier
        else:
            return proposed_stake

    def adjust_trade_position(self, trade: Trade, current_time: datetime, current_rate: float, current_profit: float, min_stake: float, max_stake: float, **kwargs):
        if self.config['position_adjustment_enable'] is False or current_profit > -0.06:
            return None
        filled_entrys = trade.select_filled_orders('entry')
        count_of_entrys = len(filled_entrys)
        # Maximum 2 reentrys, equal stake as the original
        if 0 < count_of_entrys <= self.max_reentry_orders:
            try:
                # This returns first order stake size
                stake_amount = filled_entrys[0].cost
                # This then calculates current safety order size
                stake_amount = stake_amount
                return stake_amount
            except Exception as exception:
                return None
        return None