import logging
import numpy as np
import pandas as pd
from technical import qtpylib, pivots_points
from pandas import DataFrame
from datetime import datetime, timezone
from typing import Optional
from functools import reduce
import talib.abstract as ta
import pandas_ta as pta
from freqtrade.strategy import BooleanParameter, CategoricalParameter, DecimalParameter, IStrategy, IntParameter, RealParameter, merge_informative_pair
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.persistence import Trade
logger = logging.getLogger(__name__)

class thetank4TV(IStrategy):
    INTERFACE_VERSION = 3
    ### Strategy parameters ###
    exit_profit_only = True  ### No exiting at a loss
    use_custom_stoploss = True
    trailing_stop = True
    position_adjustment_enable = True
    ignore_roi_if_entry_signal = True
    use_exit_signal = True
    stoploss = -0.09
    startup_candle_count: int = 30
    timeframe = '15m'
    # DCA Parameters
    position_adjustment_enable = True
    max_entry_position_adjustment = 0
    max_dca_multiplier = 1
    minimal_roi = {'12000': 0.01, '2400': 0.1, '300': 0.15, '180': 0.3, '120': 0.4, '60': 0.45, '0': 0.5}
    ### Hyperoptable parameters ###
    # entry optizimation
    max_epa = CategoricalParameter([0, 1], default=0, space='entry', optimize=True)
    # protections
    cooldown_lookback = IntParameter(4, 48, default=16, space='protection', optimize=True)
    stop_duration = IntParameter(5, 96, default=5, space='protection', optimize=True)
    use_stop_protection = BooleanParameter(default=True, space='protection', optimize=True)
    # indicators
    wavelength = IntParameter(low=3, high=10, default=8, space='entry', optimize=True)
    crosslength = IntParameter(low=3, high=10, default=3, space='exit', optimize=True)
    filterlength = IntParameter(low=15, high=35, default=25, space='entry', optimize=True)
    # trading
    entry_rsi = IntParameter(low=20, high=35, default=25, space='entry', optimize=True, load=True)
    entry_rsi_bear = IntParameter(low=40, high=55, default=45, space='entry', optimize=True, load=True)
    entry_rsi_bull = IntParameter(low=40, high=75, default=65, space='entry', optimize=True, load=True)
    entry_wt_bear = IntParameter(low=20, high=55, default=45, space='entry', optimize=True, load=True)
    entry_wt_bull = IntParameter(low=30, high=75, default=65, space='entry', optimize=True, load=True)
    exit_rsi = IntParameter(low=50, high=80, default=55, space='exit', optimize=True, load=True)
    # dca level optimization
    dca1 = DecimalParameter(low=0.03, high=0.08, decimals=2, default=0.05, space='entry', optimize=True, load=True)
    # dca2 = DecimalParameter(low=0.08, high=0.15, decimals=2, default=0.10, space='entry', optimize=True, load=True)
    # dca3 = DecimalParameter(low=0.15, high=0.25, decimals=2, default=0.15, space='entry', optimize=True, load=True)
    #trailing stop loss optimiziation
    tsl_target5 = DecimalParameter(low=0.2, high=0.4, decimals=1, default=0.3, space='exit', optimize=True, load=True)
    ts5 = DecimalParameter(low=0.04, high=0.06, default=0.05, space='exit', optimize=True, load=True)
    tsl_target4 = DecimalParameter(low=0.18, high=0.3, default=0.2, space='exit', optimize=True, load=True)
    ts4 = DecimalParameter(low=0.03, high=0.05, default=0.045, space='exit', optimize=True, load=True)
    tsl_target3 = DecimalParameter(low=0.1, high=0.15, default=0.15, space='exit', optimize=True, load=True)
    ts3 = DecimalParameter(low=0.025, high=0.04, default=0.035, space='exit', optimize=True, load=True)
    tsl_target2 = DecimalParameter(low=0.07, high=0.12, default=0.1, space='exit', optimize=True, load=True)
    ts2 = DecimalParameter(low=0.015, high=0.03, default=0.02, space='exit', optimize=True, load=True)
    tsl_target1 = DecimalParameter(low=0.05, high=0.06, default=0.07, space='exit', optimize=True, load=True)
    ts1 = DecimalParameter(low=0.01, high=0.016, default=0.013, space='exit', optimize=True, load=True)
    tsl_target0 = DecimalParameter(low=0.02, high=0.05, default=0.03, space='exit', optimize=True, load=True)
    ts0 = DecimalParameter(low=0.008, high=0.015, default=0.013, space='exit', optimize=True, load=True)
    ### protections ###

    @property
    def protections(self):
        prot = []
        prot.append({'method': 'CooldownPeriod', 'stop_duration_candles': self.cooldown_lookback.value})
        if self.use_stop_protection.value:
            prot.append({'method': 'StoplossGuard', 'lookback_period_candles': 24 * 3, 'trade_limit': 1, 'stop_duration_candles': self.stop_duration.value, 'only_per_pair': False})
        return prot
    ### Dollar Cost Averaging ###
    # This is called when placing the initial order (opening trade)

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float, min_stake: Optional[float], max_stake: float, leverage: float, entry_tag: Optional[str], side: str, **kwargs) -> float:
        # if self.max_epa.value == 0:
        #     self.max_dca_multiplier = 1
        # elif self.max_epa.value == 1:
        #     self.max_dca_multiplier = 2
        # elif self.max_epa.value == 2:
        #     self.max_dca_multiplier = 3
        # else:
        #     self.max_dca_multiplier = 4
        # We need to leave most of the funds for possible further DCA orders
        # This also applies to fixed stakes
        return proposed_stake / self.max_dca_multiplier

    def adjust_trade_position(self, trade: Trade, current_time: datetime, current_rate: float, current_profit: float, min_stake: Optional[float], max_stake: float, current_entry_rate: float, current_exit_rate: float, current_entry_profit: float, current_exit_profit: float, **kwargs) -> Optional[float]:
        """
        Custom trade adjustment logic, returning the stake amount that a trade should be
        increased or decreased.
        This means extra entry or exit orders with additional fees.
        Only called when `position_adjustment_enable` is set to True.

        For full documentation please go to https://www.freqtrade.io/en/latest/strategy-advanced/

        When not implemented by a strategy, returns None

        :param trade: trade object.
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Current entry rate.
        :param current_profit: Current profit (as ratio), calculated based on current_rate.
        :param min_stake: Minimal stake size allowed by exchange (for both entries and exits)
        :param max_stake: Maximum stake allowed (either through balance, or by exchange limits).
        :param current_entry_rate: Current rate using entry pricing.
        :param current_exit_rate: Current rate using exit pricing.
        :param current_entry_profit: Current profit using entry pricing.
        :param current_exit_profit: Current profit using exit pricing.
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return float: Stake amount to adjust your trade,
                       Positive values to increase position, Negative values to decrease position.
                       Return None for no action.
        """
        if current_profit > 0.1 and trade.nr_of_successful_exits == 0:
            # Take half of the profit at +5%
            return -(trade.stake_amount / 2)
        if current_profit > -self.dca1.value and trade.nr_of_successful_entries == 1:
            return None
        # if current_profit > -(self.dca2.value) and trade.nr_of_successful_entries == 2:
        #     return None
        # if current_profit > -(self.dca3.value) and trade.nr_of_successful_entries == 3:
        #     return None
        # Obtain pair dataframe (just to show how to access it)
        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        filled_entries = trade.select_filled_orders(trade.entry_side)
        count_of_entries = trade.nr_of_successful_entries
        # Allow up to 3 additional increasingly larger entrys (4 in total)
        # Initial entry is 1x
        # If that falls to -2.5% profit, we entry more, 
        # If that falls down to -5% again, we entry 1.5x more
        # If that falls once again down to -5%, we entry  more
        # Total stake for this trade would be 1 + 1.5 + 2 + 2.5 = 7x of the initial allowed stake.
        # That is why max_dca_multiplier is 7
        # Hope you have a deep wallet!
        try:
            # This returns first order stake size
            stake_amount = filled_entries[0].cost
            # This then calculates current safety order size
            if count_of_entries == 1:
                stake_amount = stake_amount * 1
            elif count_of_entries == 2:
                stake_amount = stake_amount * 1
            elif count_of_entries == 3:
                stake_amount = stake_amount * 1
            else:
                stake_amount = stake_amount
            return stake_amount
        except Exception as exception:
            return None
        return None
    ### Trailing Stop ###

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        for stop5 in self.tsl_target5.range:
            if current_profit > stop5:
                for stop5a in self.ts5.range:
                    return stop5a
        for stop4 in self.tsl_target4.range:
            if current_profit > stop4:
                for stop4a in self.ts4.range:
                    return stop4a
        for stop3 in self.tsl_target3.range:
            if current_profit > stop3:
                for stop3a in self.ts3.range:
                    return stop3a
        for stop2 in self.tsl_target2.range:
            if current_profit > stop2:
                for stop2a in self.ts2.range:
                    return stop2a
        for stop1 in self.tsl_target1.range:
            if current_profit > stop1:
                for stop1a in self.ts1.range:
                    return stop1a
        for stop0 in self.tsl_target0.range:
            if current_profit > stop0:
                for stop0a in self.ts0.range:
                    return stop0a
        return self.stoploss
    ### NORMAL INDICATORS ###

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
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
        # Filter ZEMA
        for length in self.filterlength.range:
            dataframe[f'ema_1{length}'] = ta.EMA(dataframe['close'], timeperiod=length)
            dataframe[f'ema_2{length}'] = ta.EMA(dataframe[f'ema_1{length}'], timeperiod=length)
            dataframe[f'ema_dif{length}'] = dataframe[f'ema_1{length}'] - dataframe[f'ema_2{length}']
            dataframe[f'zema_{length}'] = dataframe[f'ema_1{length}'] + dataframe[f'ema_dif{length}']
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['rsi_ma'] = ta.SMA(dataframe['rsi'], timeperiod=7)
        # WaveTrend using OHLC4 or HA close - 3/21
        ap = 0.25 * (dataframe['high'] + dataframe['low'] + dataframe['close'] + dataframe['open'])
        for wave in self.wavelength.range:
            dataframe[f'esa{wave}'] = ta.EMA(ap, timeperiod=wave)
            dataframe[f'd{wave}'] = ta.EMA(abs(ap - dataframe[f'esa{wave}']), timeperiod=wave)
            dataframe[f'wave_ci{wave}'] = (ap - dataframe[f'esa{wave}']) / (0.015 * dataframe[f'd{wave}'])
            dataframe[f'wave_t1{wave}'] = ta.EMA(dataframe[f'wave_ci{wave}'], timeperiod=21)
            for cross in self.crosslength.range:
                dataframe[f'wave_t2{cross}_{wave}'] = ta.SMA(dataframe[f'wave_t1{wave}'], timeperiod=cross)
        # SMA
        dataframe['200_SMA'] = ta.SMA(dataframe['close'], timeperiod=200)
        dataframe['30_SMA'] = ta.SMA(dataframe['close'], timeperiod=30)
        dataframe['8_SMA'] = ta.SMA(dataframe['close'], timeperiod=8)
        # TTM Squeeze
        ttm_Squeeze = pta.squeeze(high=dataframe['high'], low=dataframe['low'], close=dataframe['close'], lazybear=True)
        dataframe['ttm_Squeeze'] = ttm_Squeeze['SQZ_20_2.0_20_1.5_LB']
        dataframe['ttm_ema'] = ta.EMA(dataframe['ttm_Squeeze'], timeperiod=4)
        dataframe['squeeze_ON'] = ttm_Squeeze['SQZ_ON']
        dataframe['squeeze_OFF'] = ttm_Squeeze['SQZ_OFF']
        dataframe['NO_squeeze'] = ttm_Squeeze['SQZ_NO']
        # Calculate the percentage change between the high and open prices for each 5-minute candle
        dataframe['perc_change'] = (dataframe['high'] / dataframe['open'] - 1) * 100
        # Create a custom indicator that checks if any of the past 100 5-minute candles' high price is 3% or more above the open price
        dataframe['candle_3perc_100'] = dataframe['perc_change'].rolling(200).apply(lambda x: np.where(x >= 3, 1, 0).sum()).shift()
        # Create a custom indicator that checks if the price has gone up 10% or more over the last hundred candles
        dataframe['candle_10perc_100'] = dataframe['close'].pct_change(periods=50).shift()
        # Calculate the percentage of the current candle's range where the close price is
        dataframe['close_percentage'] = (dataframe['close'] - dataframe['low']) / (dataframe['high'] - dataframe['low'])
        dataframe['body_size'] = abs(dataframe['open'] - dataframe['close'])
        dataframe['range_size'] = dataframe['high'] - dataframe['low']
        dataframe['body_range_ratio'] = dataframe['body_size'] / dataframe['range_size']
        dataframe['upper_wick_size'] = dataframe['high'] - dataframe[['open', 'close']].max(axis=1)
        dataframe['upper_wick_range_ratio'] = dataframe['upper_wick_size'] / dataframe['range_size']
        lookback_period = 10
        dataframe['max_high'] = dataframe['high'].rolling(lookback_period).max()
        dataframe['min_low'] = dataframe['low'].rolling(lookback_period).min()
        dataframe['close_position'] = (dataframe['close'] - dataframe['min_low']) / (dataframe['max_high'] - dataframe['min_low'])
        dataframe['current_candle_perc_change'] = (dataframe['high'] / dataframe['open'] - 1) * 100
        # if self.dp.runmode.value in ('live', 'dry_run'):
        #     ticker = self.dp.ticker(metadata['pair'])
        #     dataframe['last_price'] = ticker['last']
        #     dataframe['volume24h'] = ticker['quoteVolume']
        #     dataframe['vwap'] = ticker['vwap']
        # # Trading pair: {'symbol': 'KAVA/USDT', 'timestamp': 1675451904532, 'datetime': '2023-02-03T19:18:24.532Z', 
        # 'high': 1.0652, 'low': 1.0031, 'bid': 1.0382, 'bidVolume': None, 'ask': 1.0395, 'askVolume': None, 
        # 'vwap': 1.035200204815235, 'open': 1.0558, 'close': 1.0403, 'last': 1.0403, 'previousClose': None, 'change': -0.0155, 
        # 'percentage': -1.46, 'average': 1.04130553, 'baseVolume': 457210.7641, 'quoteVolume': 473304.67664005, 
        # 'info':
        # {'time': 1675451904532, 'symbol': 'KAVA-USDT', 'entry': '1.0382', 'exit': '1.0395', 'changeRate': '-0.0146', 'changePrice': '-0.0155', 'high': '1.0652', 'low': '1.0031', 'vol': '457210.7641', 'volValue': '473304.67664005', 'last': '1.0403', 'averagePrice': '1.04130553', 'takerFeeRate': '0.001', 'makerFeeRate': '0.001', 'takerCoefficient': '1', 'makerCoefficient': '1'}}, self.max_epa.value: 1, self.max_dca_multiplier: 2
        # if (dataframe['30_SMA'].iloc[-1] > dataframe['200_SMA'].iloc[-1] 
        #     and dataframe['30_SMA'].iloc[-1] > dataframe['30_SMA'].iloc[-2]
        #     and dataframe['200_SMA'].iloc[-1] > dataframe['200_SMA'].iloc[-2]).all():
        #     self.max_epa.value = 1
        # elif (dataframe['30_SMA'].iloc[-1] > dataframe['200_SMA'].iloc[-1] 
        #     and dataframe['30_SMA'].iloc[-1] > dataframe['30_SMA'].iloc[-2].all()):
        #     self.max_epa.value = 1
        # elif (dataframe['30_SMA'].iloc[-1] < dataframe['200_SMA'].iloc[-1] 
        #     and dataframe['30_SMA'].iloc[-1] > dataframe['30_SMA'].iloc[-2].all()):
        #     self.max_epa.value = 2
        # else:
        #     self.max_epa.value = 2
        # # print(f"Trading Pair: {dataframe.name}")
        # print(f"self.max_epa.value: {self.max_epa.value}")
        # print(f"self.max_dca_multiplier: {self.max_dca_multiplier}")
        # print(f"Trading pair: {ticker['symbol']}, max_epa: {self.max_epa.value}, dca_multiplier: {self.max_dca_multiplier}")
        return dataframe
    ### ENTRY CONDITIONS ###

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # df.loc[
        #     (
        #         # Signal: RSI crosses above 30
        #         (df['close'] > df[f'zema_{self.filterlength.value}'])&
        #         (df['close'] < df['r2']) &
        #         (df['squeeze_ON'] == 1)&
        #         (df['rsi_ma'] > df['rsi_ma'].shift(1)) &
        #         (df['200_SMA'] < df['200_SMA'].shift(1)) &
        #         (df['rsi'] < self.entry_rsi_bear.value) &
        #         (df[f'wave_t1{self.wavelength.value}'] < self.entry_wt_bear.value)&
        #         (df[f'wave_t1{self.wavelength.value}'] > df[f'wave_t1{self.wavelength.value}'].shift(1)) &  # Guard: Wave 1 is raising
        #         (qtpylib.crossed_above(df[f'wave_t1{self.wavelength.value}'], df[f'wave_t2{self.crosslength.value}_{self.wavelength.value}'])) &
        #         (df['volume'] > 0)   # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'ttm_Squeeze/WT - bear')
        # df.loc[
        #     (
        #         (df['close'] > df[f'zema_{self.filterlength.value}'])&
        #         (df['close'] < df['r2']) &
        #         (df['squeeze_ON'] == 1)&
        #         (df['rsi_ma'] > df['rsi_ma'].shift(1)) &
        #         (df['rsi'] < self.entry_rsi_bear.value) &
        #         (df['200_SMA'] < df['200_SMA'].shift(1)) &
        #         (df[f'wave_t1{self.wavelength.value}'] < self.entry_wt_bear.value)&
        #         (df[f'wave_t1{self.wavelength.value}'] > df[f'wave_t1{self.wavelength.value}'].shift(1)) &  # Guard: Wave 1 is raising
        #         (df[f'wave_t1{self.wavelength.value}'].shift(2) > df[f'wave_t1{self.wavelength.value}'].shift(1)) &
        #         (df['volume'] > 0)   # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'ttm_Squeeze/WTT - bear')
        # df.loc[
        #     (
        #         (df['close'] > df[f'zema_{self.filterlength.value}'])&
        #         (df['close'] < df['r2']) &
        #         (df['rsi_ma'] > df['rsi_ma'].shift(1)) &
        #         (df['rsi'] < self.entry_rsi_bear.value) &
        #         (df['200_SMA'] < df['200_SMA'].shift(1)) &
        #         (df[f'wave_t1{self.wavelength.value}'] < self.entry_wt_bear.value)&
        #         (df[f'wave_t1{self.wavelength.value}'] > df[f'wave_t1{self.wavelength.value}'].shift(1)) &  # Guard: Wave 1 is raising
        #         (df[f'wave_t1{self.wavelength.value}'].shift(2) > df[f'wave_t1{self.wavelength.value}'].shift(1)) &
        #         (df['volume'] > 0)   # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'WT transition - bear')
        # df.loc[
        #     (
        #         (df['close'] > df[f'zema_{self.filterlength.value}'])&
        #         (df['close'] < df['r2']) &
        #         (df['200_SMA'] < df['200_SMA'].shift(1)) &
        #         (df[f'wave_t1{self.wavelength.value}'] > df[f'wave_t1{self.wavelength.value}'].shift(1)) &  # Guard: Wave 1 is raising
        #         (df[f'wave_t1{self.wavelength.value}'] < self.entry_wt_bear.value) & 
        #         (df[f'wave_t1{self.wavelength.value}'].shift(2) > df[f'wave_t1{self.wavelength.value}'].shift(1)) &
        #         (df['volume'] > 0)   # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'WT - bear')
        # df.loc[
        #     (
        #         (df['close'] > df[f'zema_{self.filterlength.value}'])&
        #         (df['close'] < df['r2']) &
        #         (df['squeeze_ON'] == 1)&
        #         (df['rsi_ma'] > df['rsi_ma'].shift(1)) &
        #         (df['rsi'] < self.entry_rsi_bull.value) &
        #         (df['200_SMA'] > df['200_SMA'].shift(1)) &
        #         (df[f'wave_t1{self.wavelength.value}'] > df[f'wave_t1{self.wavelength.value}'].shift(1)) &  # Guard: Wave 1 is raising
        #         (qtpylib.crossed_above(df[f'wave_t1{self.wavelength.value}'], df[f'wave_t2{self.crosslength.value}_{self.wavelength.value}'])) &
        #         (df['volume'] > 0)   # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'ttm_Squeeze/WT - bull')
        # df.loc[
        #     (
        #         (df['close'] > df[f'zema_{self.filterlength.value}'])&
        #         (df['close'] < df['s1']) &
        #         (df['squeeze_ON'] == 1)&
        #         (df['rsi_ma'] > df['rsi_ma'].shift(1)) &
        #         (df['rsi'] < self.entry_rsi_bull.value) &
        #         (df['200_SMA'] > df['200_SMA'].shift(1)) &
        #         (df[f'wave_t1{self.wavelength.value}'] > df[f'wave_t1{self.wavelength.value}'].shift(1)) & 
        #         (df[f'wave_t1{self.wavelength.value}'] < self.entry_wt_bull.value) & 
        #         (df[f'wave_t1{self.wavelength.value}'].shift(2) > df[f'wave_t1{self.wavelength.value}'].shift(1)) &
        #         # Check if no candle high price rose more than 5% in the past 50 candles
        #         (df['candle_3perc_100'] == 0) &
        #         # Check if the price has not gone up 10% or more over the last hundred candles
        #         (df['candle_10perc_100'] < 0.5)  &
        #         # Check if the high price of the current candle is not 3% or more above the open price
        #         (df['current_candle_perc_change'] < 0.75) &
        #         (df['volume'] > 0)   # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'ttm_Squeeze/WTT - bull')
        # df.loc[
        #     (
        #         (df['close'] > df[f'zema_{self.filterlength.value}'])&
        #         (df['close'] < df['s1']) &
        #         (df['rsi_ma'] > df['rsi_ma'].shift(1)) &
        #         (df['rsi'] < self.entry_rsi_bull.value) &
        #         (df['200_SMA'] > df['200_SMA'].shift(1)) &
        #         (df[f'wave_t1{self.wavelength.value}'] > df[f'wave_t1{self.wavelength.value}'].shift(1)) &  # Guard: Wave 1 is raising
        #         (df[f'wave_t1{self.wavelength.value}'] < self.entry_wt_bull.value) & 
        #         (df[f'wave_t1{self.wavelength.value}'].shift(2) > df[f'wave_t1{self.wavelength.value}'].shift(1)) &
        #         # Check if no candle high price rose more than 5% in the past 50 candles
        #         (df['candle_3perc_100'] == 0) &
        #         # Check if the price has not gone up 10% or more over the last hundred candles
        #         (df['candle_10perc_100'] < 0.5)  &
        #         # Check if the high price of the current candle is not 3% or more above the open price
        #         (df['current_candle_perc_change'] < 0.75) &
        #         (df['volume'] > 0)   # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'WT transition - bull')
        # Guard: Wave 1 is raising
        # Check if no candle high price rose more than 5% in the past 50 candles
        # Check if the price has not gone up 10% or more over the last hundred candles
        # Check if the high price of the current candle is not 3% or more above the open price
        # Make sure Volume is not 0
        df.loc[(df['close'] > df[f'zema_{self.filterlength.value}']) & (df['close'] < df['s1']) & (df['200_SMA'] > df['200_SMA'].shift(1)) & (df[f'wave_t1{self.wavelength.value}'] > df[f'wave_t1{self.wavelength.value}'].shift(1)) & (df[f'wave_t1{self.wavelength.value}'] < self.entry_wt_bull.value) & (df[f'wave_t1{self.wavelength.value}'].shift(2) > df[f'wave_t1{self.wavelength.value}'].shift(1)) & (df['candle_3perc_100'] == 0) & (df['candle_10perc_100'] < 0.5) & (df['current_candle_perc_change'] < 0.75) & (df['volume'] > 0), ['enter_long', 'enter_tag']] = (1, 'WT - bull')
        # df.loc[
        #     (
        #         (df['close'] > df[f'zema_{self.filterlength.value}'])&
        #         (df['rsi'] >  self.entry_rsi.value) &
        #         (df['rsi'] < self.entry_rsi_bear.value) &
        #         (df['200_SMA'] < df['200_SMA'].shift(1)) &
        #         (qtpylib.crossed_above(df['rsi'], df['rsi_ma'])) &
        #         # Check if no candle high price rose more than 5% in the past 50 candles
        #         (df['candle_3perc_100'] == 0) &
        #         # Check if the price has not gone up 10% or more over the last hundred candles
        #         (df['candle_10perc_100'] < 0.5)  &
        #         # Check if the high price of the current candle is not 3% or more above the open price
        #         (df['current_candle_perc_change'] < 0.75) &
        #         (df['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'RSI-XO bear')
        # df.loc[
        #     (
        #         (df['rsi'] >  self.entry_rsi.value) &
        #         (df['rsi'] < self.entry_rsi_bull.value) &
        #         (df['30_SMA'] > df['200_SMA']) &
        #         (df['200_SMA'] > df['200_SMA'].shift(1)) &
        #         (qtpylib.crossed_above(df['rsi'], df['rsi_ma'])) &
        #         # Check if no candle high price rose more than 5% in the past 50 candles
        #         (df['candle_3perc_100'] == 0) &
        #         # Check if the price has not gone up 10% or more over the last hundred candles
        #         (df['candle_10perc_100'] < 0.5)  &
        #         # Check if the high price of the current candle is not 3% or more above the open price
        #         (df['current_candle_perc_change'] < 0.75) &
        #         (df['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     ['enter_long', 'enter_tag']] = (1, 'RSI-XO bull')
        return df
    ### EXIT CONDITIONS ###

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:  # Make sure Volume is not 0
        df.loc[qtpylib.crossed_below(df[f'zema_{self.filterlength.value}'], df['r3']) & (df['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'R3 - XO')  # Make sure Volume is not 0
        df.loc[qtpylib.crossed_below(df[f'zema_{self.filterlength.value}'], df['r2.75']) & (df['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'R2.75 - XO')  # Make sure Volume is not 0
        df.loc[qtpylib.crossed_below(df[f'zema_{self.filterlength.value}'], df['r2.50']) & (df['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'R2.5 - XO')  # Make sure Volume is not 0
        df.loc[qtpylib.crossed_below(df[f'zema_{self.filterlength.value}'], df['r2.25']) & (df['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'R2.25 - XO')  # Make sure Volume is not 0
        df.loc[qtpylib.crossed_below(df[f'zema_{self.filterlength.value}'], df['r2']) & (df['volume'] > 0), ['exit_long', 'exit_tag']] = (1, 'R2 - XO')
        return df