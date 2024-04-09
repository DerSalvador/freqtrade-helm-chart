import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair
from pandas import DataFrame, Series
from functools import reduce
from datetime import datetime
from freqtrade.persistence import Trade
from technical.indicators import RMI

class Hacklemore3(IStrategy):
    INTERFACE_VERSION = 3
    '\n    PASTE OUTPUT FROM HYPEROPT HERE\n    '
    # ROI table:
    minimal_roi = {'0': 0.15, '5': 0.015}
    # Stoploss:
    stoploss = -0.99
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    '\n    END HYPEROPT\n    '
    timeframe = '5m'
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.01
    ignore_roi_if_entry_signal = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['volume_mean_slow'] = dataframe['volume'].rolling(window=24).mean()
        dataframe['rmi'] = RMI(dataframe)
        dataframe['sar'] = ta.SAR(dataframe)
        dataframe['max'] = dataframe['high'].rolling(12).max()
        dataframe['min'] = dataframe['low'].rolling(12).min()
        dataframe['upper'] = np.where(dataframe['max'] > dataframe['max'].shift(), 1, 0)
        dataframe['lower'] = np.where(dataframe['min'] < dataframe['min'].shift(), 1, 0)
        dataframe['up_trend'] = np.where(dataframe['upper'].rolling(3, min_periods=1).sum() != 0, 1, 0)
        dataframe['dn_trend'] = np.where(dataframe['lower'].rolling(3, min_periods=1).sum() != 0, 1, 0)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        active_trade = False
        if self.config['runmode'].value in ('live', 'dry_run'):
            active_trade = Trade.get_trades([Trade.pair == metadata['pair'], Trade.is_open.is_(True)]).all()
        # Normal entry triggers that apply to new trades we want to enter
        if not active_trade:
            conditions.append((dataframe['up_trend'] == 1) & (dataframe['rmi'] > 55) & (dataframe['rmi'] >= dataframe['rmi'].rolling(3).mean()) & (dataframe['close'] > dataframe['close'].shift()) & (dataframe['close'].shift() > dataframe['close'].shift(2)) & (dataframe['sar'] < dataframe['close']) & (dataframe['sar'].shift() < dataframe['close'].shift()) & (dataframe['volume'] < dataframe['volume_mean_slow'].shift(1) * 30))
        else:
            # Persist a entry signal for existing trades to make use of ignore_roi_if_entry_signal = True
            # when this entry signal is not present a exit will happen according to ROI table
            conditions.append(dataframe['rmi'] >= 75)
        conditions.append(dataframe['volume'].gt(0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        active_trade = False
        if self.config['runmode'].value in ('live', 'dry_run'):
            active_trade = Trade.get_trades([Trade.pair == metadata['pair'], Trade.is_open.is_(True)]).all()
        # if we are in an active trade for this pair consider various things in our exit signal
        if active_trade:
            ob = self.dp.orderbook(metadata['pair'], 1)
            current_price = ob['asks'][0][0]
            current_profit = active_trade[0].calc_profit_ratio(rate=current_price)
            max_price = active_trade[0].max_rate
            # if we are at a loss, consider what the trend looks like in the exit
            if current_profit < 0:
                # custom exit-reason: dynamic-stop-loss
                conditions.append((dataframe['dn_trend'] == 1) & (dataframe['rmi'] < 50) & dataframe['volume'].gt(0))
            else:
                # if we are in a profit, produce a sort of dynamic trailing stoploss
                # custom exit-reason: dynamic-trailing-stop
                conditions.append((current_price > max_price * 0.8) & (dataframe['close'] < dataframe['close'].shift()) & (dataframe['high'] < dataframe['high'].shift()))
        else:
            # impossible condition needed for some reason?
            conditions.append(dataframe['volume'].lt(0))
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit'] = 1
        return dataframe

    def check_entry_timeout(self, pair: str, trade: Trade, order: dict, **kwargs) -> bool:
        ob = self.dp.orderbook(pair, 1)
        current_price = ob['bids'][0][0]
        # Cancel entry order if price is more than 1% above the order.
        if current_price > order['price'] * 1.01:
            return True
        return False

    def check_exit_timeout(self, pair: str, trade: Trade, order: dict, **kwargs) -> bool:
        ob = self.dp.orderbook(pair, 1)
        current_price = ob['asks'][0][0]
        # Cancel exit order if price is more than 1% below the order.
        if current_price < order['price'] * 0.99:
            return True
        return False

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, **kwargs) -> bool:
        ob = self.dp.orderbook(pair, 1)
        current_price = ob['asks'][0][0]
        # Cancel entry order if price is more than 1% above the order.
        if current_price > rate * 1.01:
            return False
        return True
    '\n    def min_roi_reached(self, trade: Trade, current_profit: float, current_time: datetime) -> bool:\n        _, roi = self.min_roi_reached_entry(0)\n\n        if roi is None:\n           if Trade.max_rate >= Trade.rate * 0.8 and Trade.rate > Trade.open_rate: \n                return False\n            if Trade.max_rate < Trade.rate * 0.8 and Trade.rate < Trade.open_rate: \n                return False\n            if Trade.max_rate < Trade.rate * 0.8 and Trade.rate > Trade.open_rate: \n                return current_profit > roi\n        return False\n    '