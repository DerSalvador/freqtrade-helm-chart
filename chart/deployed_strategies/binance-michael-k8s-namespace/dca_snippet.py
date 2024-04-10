# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame, Series
# --------------------------------
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from freqtrade.persistence import Trade
import time
logger = logging.getLogger(__name__)

class YourStrat(IStrategy):
    INTERFACE_VERSION = 3
    # replace this by your strategy
    print('YourStrat')

class TrailingBuyStrat(YourStrat):
    # Orignal idea by @MukavaValkku, code by @tirail and @stash86
    #
    # This class is designed to inherit from yours and starts trailing entry with your entry signals
    # Trailing entry starts at any entry signal
    # Trailing entry stops  with BUY if : price decreases and rises again more than trailing_entry_offset
    # Trailing entry stops with NO BUY : current price is > initial price * (1 +  trailing_entry_max) OR custom_exit tag
    # IT IS NOT COMPATIBLE WITH BACKTEST/HYPEROPT
    #
    # if process_only_new_candles = True, then you need to use 1m timeframe (and normal strategy timeframe as informative)
    # if process_only_new_candles = False, it will use ticker data and you won't need to change anything
    process_only_new_candles = False
    custom_info_trail_entry = dict()
    # Trailing entry parameters
    trailing_entry_order_enabled = True
    trailing_expire_seconds = 300
    # If the current candle goes above min_uptrend_trailing_profit % before trailing_expire_seconds_uptrend seconds, entry the coin
    trailing_entry_uptrend_enabled = False
    trailing_expire_seconds_uptrend = 90
    min_uptrend_trailing_profit = 0.02
    debug_mode = True
    trailing_entry_max_stop = 0.1  # stop trailing entry if current_price > starting_price * (1+trailing_entry_max_stop)
    trailing_entry_max_entry = 0.002  # entry if price between uplimit (=min of serie (current_price * (1 + trailing_entry_offset())) and (start_price * 1+trailing_entry_max_entry))
    init_trailing_dict = {'trailing_entry_order_started': False, 'trailing_entry_order_uplimit': 0, 'start_trailing_price': 0, 'enter_tag': None, 'start_trailing_time': None, 'offset': 0}

    def trailing_entry(self, pair, reinit=False):
        # returns trailing entry info for pair (init if necessary)
        if not pair in self.custom_info_trail_entry:
            self.custom_info_trail_entry[pair] = dict()
        if reinit or not 'trailing_entry' in self.custom_info_trail_entry[pair]:
            self.custom_info_trail_entry[pair]['trailing_entry'] = self.init_trailing_dict
        return self.custom_info_trail_entry[pair]['trailing_entry']

    def trailing_entry_info(self, pair: str, current_price: float):
        # current_time live, dry run
        current_time = datetime.now(timezone.utc)
        if not self.debug_mode:
            return
        trailing_entry = self.trailing_entry(pair)
        logger.info(f"pair: {pair} : start: {trailing_entry['start_trailing_price']:.4f}, duration: {current_time - trailing_entry['start_trailing_time']}, current: {current_price:.4f}, uplimit: {trailing_entry['trailing_entry_order_uplimit']:.4f}, profit: {self.current_trailing_profit_ratio(pair, current_price) * 100:.2f}%, offset: {trailing_entry['offset']}")

    def current_trailing_profit_ratio(self, pair: str, current_price: float) -> float:
        trailing_entry = self.trailing_entry(pair)
        if trailing_entry['trailing_entry_order_started']:
            return (trailing_entry['start_trailing_price'] - current_price) / trailing_entry['start_trailing_price']
        else:
            return 0

    def entry(self, dataframe, pair: str, current_price: float, enter_tag: str):
        dataframe.iloc[-1, dataframe.columns.get_loc('enter_long')] = 1
        ratio = '%.2f' % (self.current_trailing_profit_ratio(pair, current_price) * 100)
        if 'enter_tag' in dataframe.columns:
            dataframe.iloc[-1, dataframe.columns.get_loc('enter_tag')] = f'{enter_tag} ({ratio} %)'
        self.trailing_entry_info(pair, current_price)
        logger.info(f'price OK for {pair} ({ratio} %, {current_price}), order may not be triggered if all slots are full')

    def trailing_entry_offset(self, dataframe, pair: str, current_price: float):
        # return rebound limit before a entry in % of initial price, function of current price
        # return None to stop trailing entry (will start again at next entry signal)
        # return 'forceentry' to force immediate entry
        # (example with 0.5%. initial price : 100 (uplimit is 100.5), 2nd price : 99 (no entry, uplimit updated to 99.5), 3price 98 (no entry uplimit updated to 98.5), 4th price 99 -> BUY
        current_trailing_profit_ratio = self.current_trailing_profit_ratio(pair, current_price)
        default_offset = 0.005
        trailing_entry = self.trailing_entry(pair)
        if not trailing_entry['trailing_entry_order_started']:
            return default_offset
        # example with duration and indicators
        # dry run, live only
        last_candle = dataframe.iloc[-1]
        current_time = datetime.now(timezone.utc)
        trailing_duration = current_time - trailing_entry['start_trailing_time']
        if trailing_duration.total_seconds() > self.trailing_expire_seconds:
            if current_trailing_profit_ratio > 0 and last_candle['pre_entry'] == 1:
                # more than 1h, price under first signal, entry signal still active -> entry
                return 'forceentry'
            else:
                # wait for next signal
                return None
        elif self.trailing_entry_uptrend_enabled and trailing_duration.total_seconds() < self.trailing_expire_seconds_uptrend and (current_trailing_profit_ratio < -1 * self.min_uptrend_trailing_profit):
            # less than 90s and price is rising, entry
            return 'forceentry'
        if current_trailing_profit_ratio < 0:
            # current price is higher than initial price
            return default_offset
        trailing_entry_offset = {0.06: 0.02, 0.03: 0.01, 0: default_offset}
        for key in trailing_entry_offset:
            if current_trailing_profit_ratio > key:
                return trailing_entry_offset[key]
        return default_offset
    # end of trailing entry parameters
    # -----------------------------------------------------

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs):
        tag = super().custom_exit(pair, trade, current_time, current_rate, current_profit, **kwargs)
        if tag:
            self.trailing_entry_info(pair, current_rate)
            self.trailing_entry(pair, reinit=True)
            logger.info(f'STOP trailing entry for {pair} because of {tag}')
        return tag

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        self.trailing_entry(metadata['pair'])
        return dataframe

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float, rate: float, time_in_force: str, exit_reason: str, **kwargs) -> bool:
        val = super().confirm_trade_exit(pair, trade, order_type, amount, rate, time_in_force, exit_reason, **kwargs)
        self.trailing_entry(pair, reinit=True)
        return val

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, **kwargs) -> bool:
        val = super().confirm_trade_entry(pair, order_type, amount, rate, time_in_force, **kwargs)
        # stop trailing when entry signal ! prevent from entrying much higher price when slot is free
        self.trailing_entry_info(pair, rate)
        self.trailing_entry(pair, reinit=True)
        logger.info(f'STOP trailing entry for {pair} because I entry it')
        return val

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe = dataframe.rename(columns={'entry': 'pre_entry'})
        if self.trailing_entry_order_enabled and self.config['runmode'].value in ('live', 'dry_run'):  # trailing live dry ticker, 1m
            last_candle = dataframe.iloc[-1].squeeze()
            if not self.process_only_new_candles:
                current_price = self.get_current_price(metadata['pair'])
            else:
                current_price = last_candle['close']
            dataframe['enter_long'] = 0
            trailing_entry = self.trailing_entry(metadata['pair'])
            trailing_entry_offset = self.trailing_entry_offset(dataframe, metadata['pair'], current_price)
            if not trailing_entry['trailing_entry_order_started'] and last_candle['pre_entry'] == 1:
                open_trades = Trade.get_trades([Trade.pair == metadata['pair'], Trade.is_open.is_(True)]).all()
                if not open_trades:
                    # start trailing entry
                    self.custom_info_trail_entry[metadata['pair']]['trailing_entry'] = {'trailing_entry_order_started': True, 'trailing_entry_order_uplimit': last_candle['close'], 'start_trailing_price': last_candle['close'], 'enter_tag': last_candle['enter_tag'] if 'enter_tag' in last_candle else 'entry signal', 'start_trailing_time': datetime.now(timezone.utc), 'offset': 0}
                    self.trailing_entry_info(metadata['pair'], current_price)
                    logger.info(f"start trailing entry for {metadata['pair']} at {last_candle['close']}")
            elif trailing_entry['trailing_entry_order_started']:
                if trailing_entry_offset == 'forceentry':
                    # entry in custom conditions
                    self.entry(dataframe, metadata['pair'], current_price, trailing_entry['entry_tag'])
                elif trailing_entry_offset is None:
                    # stop trailing entry custom conditions
                    self.trailing_entry(metadata['pair'], reinit=True)
                    logger.info(f"""STOP trailing entry for {metadata['pair']} because "trailing entry offset" returned None""")
                elif current_price < trailing_entry['trailing_entry_order_uplimit']:
                    # update uplimit
                    old_uplimit = trailing_entry['trailing_entry_order_uplimit']
                    self.custom_info_trail_entry[metadata['pair']]['trailing_entry']['trailing_entry_order_uplimit'] = min(current_price * (1 + trailing_entry_offset), self.custom_info_trail_entry[metadata['pair']]['trailing_entry']['trailing_entry_order_uplimit'])
                    self.custom_info_trail_entry[metadata['pair']]['trailing_entry']['offset'] = trailing_entry_offset
                    self.trailing_entry_info(metadata['pair'], current_price)
                    logger.info(f"update trailing entry for {metadata['pair']} at {old_uplimit} -> {self.custom_info_trail_entry[metadata['pair']]['trailing_entry']['trailing_entry_order_uplimit']}")
                elif current_price < trailing_entry['start_trailing_price'] * (1 + self.trailing_entry_max_entry):
                    # entry ! current price > uplimit && lower thant starting price
                    self.entry(dataframe, metadata['pair'], current_price, trailing_entry['entry_tag'])
                elif current_price > trailing_entry['start_trailing_price'] * (1 + self.trailing_entry_max_stop):
                    # stop trailing entry because price is too high
                    self.trailing_entry(metadata['pair'], reinit=True)
                    self.trailing_entry_info(metadata['pair'], current_price)
                    logger.info(f"STOP trailing entry for {metadata['pair']} because of the price is higher than starting price * {1 + self.trailing_entry_max_stop}")
                else:
                    # uplimit > current_price > max_price, continue trailing and wait for the price to go down
                    self.trailing_entry_info(metadata['pair'], current_price)
                    logger.info(f"price too high for {metadata['pair']} !")
        else:  # No entry trailing
            dataframe.loc[dataframe['pre_entry'] == 1, 'enter_long'] = 1
        return dataframe

    def get_current_price(self, pair: str) -> float:
        ticker = self.dp.ticker(pair)
        current_price = ticker['last']
        return current_price

class TrailingBuyStrat2(YourStrat):
    # Original idea by @MukavaValkku, code by @tirail and @stash86
    #
    # This class is designed to inherit from yours and starts trailing entry with your entry signals
    # Trailing entry starts at any entry signal and will move to next candles if the trailing still active
    # Trailing entry stops  with BUY if : price decreases and rises again more than trailing_entry_offset
    # Trailing entry stops with NO BUY : current price is > initial price * (1 +  trailing_entry_max) OR custom_exit tag
    # IT IS NOT COMPATIBLE WITH BACKTEST/HYPEROPT
    #
    process_only_new_candles = True
    custom_info_trail_entry = dict()
    # Trailing entry parameters
    trailing_entry_order_enabled = True
    trailing_expire_seconds = 1800
    # If the current candle goes above min_uptrend_trailing_profit % before trailing_expire_seconds_uptrend seconds, entry the coin
    trailing_entry_uptrend_enabled = False
    trailing_expire_seconds_uptrend = 90
    min_uptrend_trailing_profit = 0.02
    debug_mode = True
    trailing_entry_max_stop = 0.02  # stop trailing entry if current_price > starting_price * (1+trailing_entry_max_stop)
    trailing_entry_max_entry = 0.0  # entry if price between uplimit (=min of serie (current_price * (1 + trailing_entry_offset())) and (start_price * 1+trailing_entry_max_entry))
    init_trailing_dict = {'trailing_entry_order_started': False, 'trailing_entry_order_uplimit': 0, 'start_trailing_price': 0, 'enter_tag': None, 'start_trailing_time': None, 'offset': 0, 'allow_trailing': False}

    def trailing_entry(self, pair, reinit=False):
        # returns trailing entry info for pair (init if necessary)
        if not pair in self.custom_info_trail_entry:
            self.custom_info_trail_entry[pair] = dict()
        if reinit or not 'trailing_entry' in self.custom_info_trail_entry[pair]:
            self.custom_info_trail_entry[pair]['trailing_entry'] = self.init_trailing_dict.copy()
        return self.custom_info_trail_entry[pair]['trailing_entry']

    def trailing_entry_info(self, pair: str, current_price: float):
        # current_time live, dry run
        current_time = datetime.now(timezone.utc)
        if not self.debug_mode:
            return
        trailing_entry = self.trailing_entry(pair)
        duration = 0
        try:
            duration = current_time - trailing_entry['start_trailing_time']
        except TypeError:
            duration = 0
        finally:
            logger.info(f"pair: {pair} : start: {trailing_entry['start_trailing_price']:.4f}, duration: {duration}, current: {current_price:.4f}, uplimit: {trailing_entry['trailing_entry_order_uplimit']:.4f}, profit: {self.current_trailing_profit_ratio(pair, current_price) * 100:.2f}%, offset: {trailing_entry['offset']}")

    def current_trailing_profit_ratio(self, pair: str, current_price: float) -> float:
        trailing_entry = self.trailing_entry(pair)
        if trailing_entry['trailing_entry_order_started']:
            return (trailing_entry['start_trailing_price'] - current_price) / trailing_entry['start_trailing_price']
        else:
            return 0

    def trailing_entry_offset(self, dataframe, pair: str, current_price: float):
        # return rebound limit before a entry in % of initial price, function of current price
        # return None to stop trailing entry (will start again at next entry signal)
        # return 'forceentry' to force immediate entry
        # (example with 0.5%. initial price : 100 (uplimit is 100.5), 2nd price : 99 (no entry, uplimit updated to 99.5), 3price 98 (no entry uplimit updated to 98.5), 4th price 99 -> BUY
        current_trailing_profit_ratio = self.current_trailing_profit_ratio(pair, current_price)
        default_offset = 0.005
        trailing_entry = self.trailing_entry(pair)
        if not trailing_entry['trailing_entry_order_started']:
            return default_offset
        # example with duration and indicators
        # dry run, live only
        last_candle = dataframe.iloc[-1]
        current_time = datetime.now(timezone.utc)
        trailing_duration = current_time - trailing_entry['start_trailing_time']
        if trailing_duration.total_seconds() > self.trailing_expire_seconds:
            if current_trailing_profit_ratio > 0 and last_candle['enter_long'] == 1:
                # more than 1h, price under first signal, entry signal still active -> entry
                return 'forceentry'
            else:
                # wait for next signal
                return None
        elif self.trailing_entry_uptrend_enabled and trailing_duration.total_seconds() < self.trailing_expire_seconds_uptrend and (current_trailing_profit_ratio < -1 * self.min_uptrend_trailing_profit):
            # less than 90s and price is rising, entry
            return 'forceentry'
        if current_trailing_profit_ratio < 0:
            # current price is higher than initial price
            return default_offset
        trailing_entry_offset = {0.06: 0.02, 0.03: 0.01, 0: default_offset}
        for key in trailing_entry_offset:
            if current_trailing_profit_ratio > key:
                return trailing_entry_offset[key]
        return default_offset
    # end of trailing entry parameters
    # -----------------------------------------------------

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        self.trailing_entry(metadata['pair'])
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, **kwargs) -> bool:
        val = super().confirm_trade_entry(pair, order_type, amount, rate, time_in_force, **kwargs)
        if val:
            if self.trailing_entry_order_enabled and self.config['runmode'].value in ('live', 'dry_run'):
                val = False
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if len(dataframe) >= 1:
                    last_candle = dataframe.iloc[-1].squeeze()
                    current_price = rate
                    trailing_entry = self.trailing_entry(pair)
                    trailing_entry_offset = self.trailing_entry_offset(dataframe, pair, current_price)
                    if trailing_entry['allow_trailing']:
                        if not trailing_entry['trailing_entry_order_started'] and last_candle['enter_long'] == 1:
                            # start trailing entry
                            # self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_started'] = True
                            # self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_uplimit'] = last_candle['close']
                            # self.custom_info_trail_entry[pair]['trailing_entry']['start_trailing_price'] = last_candle['close']
                            # self.custom_info_trail_entry[pair]['trailing_entry']['entry_tag'] = f"initial_entry_tag (strat trail price {last_candle['close']})"
                            # self.custom_info_trail_entry[pair]['trailing_entry']['start_trailing_time'] = datetime.now(timezone.utc)
                            # self.custom_info_trail_entry[pair]['trailing_entry']['offset'] = 0
                            trailing_entry['trailing_entry_order_started'] = True
                            trailing_entry['trailing_entry_order_uplimit'] = last_candle['close']
                            trailing_entry['start_trailing_price'] = last_candle['close']
                            trailing_entry['enter_tag'] = last_candle['enter_tag']
                            trailing_entry['start_trailing_time'] = datetime.now(timezone.utc)
                            trailing_entry['offset'] = 0
                            self.trailing_entry_info(pair, current_price)
                            logger.info(f"start trailing entry for {pair} at {last_candle['close']}")
                        elif trailing_entry['trailing_entry_order_started']:
                            if trailing_entry_offset == 'forceentry':
                                # entry in custom conditions
                                val = True
                                ratio = '%.2f' % (self.current_trailing_profit_ratio(pair, current_price) * 100)
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f'price OK for {pair} ({ratio} %, {current_price}), order may not be triggered if all slots are full')
                            elif trailing_entry_offset is None:
                                # stop trailing entry custom conditions
                                self.trailing_entry(pair, reinit=True)
                                logger.info(f'STOP trailing entry for {pair} because "trailing entry offset" returned None')
                            elif current_price < trailing_entry['trailing_entry_order_uplimit']:
                                # update uplimit
                                old_uplimit = trailing_entry['trailing_entry_order_uplimit']
                                self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_uplimit'] = min(current_price * (1 + trailing_entry_offset), self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_uplimit'])
                                self.custom_info_trail_entry[pair]['trailing_entry']['offset'] = trailing_entry_offset
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f"update trailing entry for {pair} at {old_uplimit} -> {self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_uplimit']}")
                            elif current_price < trailing_entry['start_trailing_price'] * (1 + self.trailing_entry_max_entry):
                                # entry ! current price > uplimit && lower thant starting price
                                val = True
                                ratio = '%.2f' % (self.current_trailing_profit_ratio(pair, current_price) * 100)
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f"current price ({current_price}) > uplimit ({trailing_entry['trailing_entry_order_uplimit']}) and lower than starting price price ({trailing_entry['start_trailing_price'] * (1 + self.trailing_entry_max_entry)}). OK for {pair} ({ratio} %), order may not be triggered if all slots are full")
                            elif current_price > trailing_entry['start_trailing_price'] * (1 + self.trailing_entry_max_stop):
                                # stop trailing entry because price is too high
                                self.trailing_entry(pair, reinit=True)
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f'STOP trailing entry for {pair} because of the price is higher than starting price * {1 + self.trailing_entry_max_stop}')
                            else:
                                # uplimit > current_price > max_price, continue trailing and wait for the price to go down
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f'price too high for {pair} !')
                    else:
                        logger.info(f'Wait for next entry signal for {pair}')
                if val == True:
                    self.trailing_entry_info(pair, rate)
                    self.trailing_entry(pair, reinit=True)
                    logger.info(f'STOP trailing entry for {pair} because I entry it')
        return val

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if self.trailing_entry_order_enabled and self.config['runmode'].value in ('live', 'dry_run'):
            last_candle = dataframe.iloc[-1].squeeze()
            trailing_entry = self.trailing_entry(metadata['pair'])
            if last_candle['enter_long'] == 1:
                if not trailing_entry['trailing_entry_order_started']:
                    open_trades = Trade.get_trades([Trade.pair == metadata['pair'], Trade.is_open.is_(True)]).all()
                    if not open_trades:
                        logger.info(f"Set 'allow_trailing' to True for {metadata['pair']} to start trailing!!!")
                        # self.custom_info_trail_entry[metadata['pair']]['trailing_entry']['allow_trailing'] = True
                        trailing_entry['allow_trailing'] = True
                        initial_entry_tag = last_candle['enter_tag'] if 'enter_tag' in last_candle else 'entry signal'
                        dataframe.loc[:, 'enter_tag'] = f"{initial_entry_tag} (start trail price {last_candle['close']})"
            elif trailing_entry['trailing_entry_order_started'] == True:
                logger.info(f"Continue trailing for {metadata['pair']}. Manually trigger entry signal!!")
                dataframe.loc[:, 'enter_long'] = 1
                dataframe.loc[:, 'enter_tag'] = trailing_entry['enter_tag']
        # dataframe['entry'] = 1
        return dataframe
#dynamic offset

class TrailingBuyStrat2a(YourStrat):
    # Original idea by @MukavaValkku, code by @tirail and @stash86
    #
    # This class is designed to inherit from yours and starts trailing entry with your entry signals
    # Trailing entry starts at any entry signal and will move to next candles if the trailing still active
    # Trailing entry stops  with BUY if : price decreases and rises again more than trailing_entry_offset
    # Trailing entry stops with NO BUY : current price is > initial price * (1 +  trailing_entry_max) OR custom_exit tag
    # IT IS NOT COMPATIBLE WITH BACKTEST/HYPEROPT
    #
    process_only_new_candles = True
    custom_info_trail_entry = dict()
    # Trailing entry parameters
    trailing_entry_order_enabled = True
    trailing_expire_seconds = 1800
    # If the current candle goes above min_uptrend_trailing_profit % before trailing_expire_seconds_uptrend seconds, entry the coin
    trailing_entry_uptrend_enabled = False
    trailing_expire_seconds_uptrend = 90
    min_uptrend_trailing_profit = 0.02
    debug_mode = True
    trailing_entry_max_stop = 0.02  # stop trailing entry if current_price > starting_price * (1+trailing_entry_max_stop)
    trailing_entry_max_entry = 0.0  # entry if price between uplimit (=min of serie (current_price * (1 + trailing_entry_offset())) and (start_price * 1+trailing_entry_max_entry))
    abort_trailing_when_exit_signal_triggered = False
    init_trailing_dict = {'trailing_entry_order_started': False, 'trailing_entry_order_uplimit': 0, 'start_trailing_price': 0, 'enter_tag': None, 'start_trailing_time': None, 'offset': 0, 'allow_trailing': False}

    def trailing_entry(self, pair, reinit=False):
        # returns trailing entry info for pair (init if necessary)
        if not pair in self.custom_info_trail_entry:
            self.custom_info_trail_entry[pair] = dict()
        if reinit or not 'trailing_entry' in self.custom_info_trail_entry[pair]:
            self.custom_info_trail_entry[pair]['trailing_entry'] = self.init_trailing_dict.copy()
        return self.custom_info_trail_entry[pair]['trailing_entry']

    def trailing_entry_info(self, pair: str, current_price: float):
        # current_time live, dry run
        current_time = datetime.now(timezone.utc)
        if not self.debug_mode:
            return
        trailing_entry = self.trailing_entry(pair)
        duration = 0
        try:
            duration = current_time - trailing_entry['start_trailing_time']
        except TypeError:
            duration = 0
        finally:
            logger.info(f"pair: {pair} : start: {trailing_entry['start_trailing_price']:.4f}, duration: {duration}, current: {current_price:.4f}, uplimit: {trailing_entry['trailing_entry_order_uplimit']:.4f}, profit: {self.current_trailing_profit_ratio(pair, current_price) * 100:.2f}%, offset: {trailing_entry['offset']}")

    def current_trailing_profit_ratio(self, pair: str, current_price: float) -> float:
        trailing_entry = self.trailing_entry(pair)
        if trailing_entry['trailing_entry_order_started']:
            return (trailing_entry['start_trailing_price'] - current_price) / trailing_entry['start_trailing_price']
        else:
            return 0

    def trailing_entry_offset(self, dataframe, pair: str, current_price: float):
        # return rebound limit before a entry in % of initial price, function of current price
        # return None to stop trailing entry (will start again at next entry signal)
        # return 'forceentry' to force immediate entry
        # (example with 0.5%. initial price : 100 (uplimit is 100.5), 2nd price : 99 (no entry, uplimit updated to 99.5), 3price 98 (no entry uplimit updated to 98.5), 4th price 99 -> BUY
        current_trailing_profit_ratio = self.current_trailing_profit_ratio(pair, current_price)
        last_candle = dataframe.iloc[-1]
        adapt = abs(last_candle['perc_norm'])  #NOTE: Uzirox variable offset
        default_offset = adapt * 0.01
        trailing_entry = self.trailing_entry(pair)
        if not trailing_entry['trailing_entry_order_started']:
            return default_offset
        # example with duration and indicators
        # dry run, live only
        last_candle = dataframe.iloc[-1]
        current_time = datetime.now(timezone.utc)
        trailing_duration = current_time - trailing_entry['start_trailing_time']
        if trailing_duration.total_seconds() > self.trailing_expire_seconds:
            if current_trailing_profit_ratio > 0 and last_candle['enter_long'] == 1:
                # more than 1h, price under first signal, entry signal still active -> entry
                return 'forceentry'
            else:
                # wait for next signal
                return None
        elif self.trailing_entry_uptrend_enabled and trailing_duration.total_seconds() < self.trailing_expire_seconds_uptrend and (current_trailing_profit_ratio < -1 * self.min_uptrend_trailing_profit):
            # less than 90s and price is rising, entry
            return 'forceentry'
        if current_trailing_profit_ratio < 0:
            # current price is higher than initial price
            return default_offset
        trailing_entry_offset = {0.06: 0.02, 0.03: 0.01, 0: default_offset}
        for key in trailing_entry_offset:
            if current_trailing_profit_ratio > key:
                return trailing_entry_offset[key]
        return default_offset
    # end of trailing entry parameters
    # -----------------------------------------------------

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        self.trailing_entry(metadata['pair'])
        # variable trailing entry offset
        dataframe['perc'] = (dataframe['high'].rolling(5).max() - dataframe['low'].rolling(5).min()) / dataframe['low'].rolling(5).min() * 100
        dataframe['perc_norm'] = 2 * ((dataframe['perc'] - dataframe['perc'].rolling(50).min()) / (dataframe['perc'].rolling(50).max() - dataframe['perc'].rolling(50).min())) - 1
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, **kwargs) -> bool:
        val = super().confirm_trade_entry(pair, order_type, amount, rate, time_in_force, **kwargs)
        if val:
            if self.trailing_entry_order_enabled and self.config['runmode'].value in ('live', 'dry_run'):
                val = False
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if len(dataframe) >= 1:
                    last_candle = dataframe.iloc[-1].squeeze()
                    current_price = rate
                    trailing_entry = self.trailing_entry(pair)
                    trailing_entry_offset = self.trailing_entry_offset(dataframe, pair, current_price)
                    if trailing_entry['allow_trailing']:
                        if not trailing_entry['trailing_entry_order_started'] and last_candle['enter_long'] == 1:
                            # start trailing entry
                            # self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_started'] = True
                            # self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_uplimit'] = last_candle['close']
                            # self.custom_info_trail_entry[pair]['trailing_entry']['start_trailing_price'] = last_candle['close']
                            # self.custom_info_trail_entry[pair]['trailing_entry']['entry_tag'] = f"initial_entry_tag (strat trail price {last_candle['close']})"
                            # self.custom_info_trail_entry[pair]['trailing_entry']['start_trailing_time'] = datetime.now(timezone.utc)
                            # self.custom_info_trail_entry[pair]['trailing_entry']['offset'] = 0
                            trailing_entry['trailing_entry_order_started'] = True
                            trailing_entry['trailing_entry_order_uplimit'] = last_candle['close']
                            trailing_entry['start_trailing_price'] = last_candle['close']
                            trailing_entry['enter_tag'] = last_candle['enter_tag']
                            trailing_entry['start_trailing_time'] = datetime.now(timezone.utc)
                            trailing_entry['offset'] = 0
                            self.trailing_entry_info(pair, current_price)
                            logger.info(f"start trailing entry for {pair} at {last_candle['close']}")
                        elif trailing_entry['trailing_entry_order_started']:
                            if trailing_entry_offset == 'forceentry':
                                # entry in custom conditions
                                val = True
                                ratio = '%.2f' % (self.current_trailing_profit_ratio(pair, current_price) * 100)
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f'price OK for {pair} ({ratio} %, {current_price}), order may not be triggered if all slots are full')
                            elif trailing_entry_offset is None:
                                # stop trailing entry custom conditions
                                self.trailing_entry(pair, reinit=True)
                                logger.info(f'STOP trailing entry for {pair} because "trailing entry offset" returned None')
                            elif current_price < trailing_entry['trailing_entry_order_uplimit']:
                                # update uplimit
                                old_uplimit = trailing_entry['trailing_entry_order_uplimit']
                                self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_uplimit'] = min(current_price * (1 + trailing_entry_offset), self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_uplimit'])
                                self.custom_info_trail_entry[pair]['trailing_entry']['offset'] = trailing_entry_offset
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f"update trailing entry for {pair} at {old_uplimit} -> {self.custom_info_trail_entry[pair]['trailing_entry']['trailing_entry_order_uplimit']}")
                            elif current_price < trailing_entry['start_trailing_price'] * (1 + self.trailing_entry_max_entry):
                                # entry ! current price > uplimit && lower thant starting price
                                val = True
                                ratio = '%.2f' % (self.current_trailing_profit_ratio(pair, current_price) * 100)
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f"current price ({current_price}) > uplimit ({trailing_entry['trailing_entry_order_uplimit']}) and lower than starting price price ({trailing_entry['start_trailing_price'] * (1 + self.trailing_entry_max_entry)}). OK for {pair} ({ratio} %), order may not be triggered if all slots are full")
                            elif current_price > trailing_entry['start_trailing_price'] * (1 + self.trailing_entry_max_stop):
                                # stop trailing entry because price is too high
                                self.trailing_entry(pair, reinit=True)
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f'STOP trailing entry for {pair} because of the price is higher than starting price * {1 + self.trailing_entry_max_stop}')
                            else:
                                # uplimit > current_price > max_price, continue trailing and wait for the price to go down
                                self.trailing_entry_info(pair, current_price)
                                logger.info(f'price too high for {pair} !')
                    else:
                        logger.info(f'Wait for next entry signal for {pair}')
                if val == True:
                    self.trailing_entry_info(pair, rate)
                    self.trailing_entry(pair, reinit=True)
                    logger.info(f'STOP trailing entry for {pair} because I entry it')
        return val

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if self.trailing_entry_order_enabled and self.config['runmode'].value in ('live', 'dry_run'):
            last_candle = dataframe.iloc[-1].squeeze()
            trailing_entry = self.trailing_entry(metadata['pair'])
            if last_candle['enter_long'] == 1:
                if not trailing_entry['trailing_entry_order_started']:
                    open_trades = Trade.get_trades([Trade.pair == metadata['pair'], Trade.is_open.is_(True)]).all()
                    if not open_trades:
                        logger.info(f"Set 'allow_trailing' to True for {metadata['pair']} to start trailing!!!")
                        # self.custom_info_trail_entry[metadata['pair']]['trailing_entry']['allow_trailing'] = True
                        trailing_entry['allow_trailing'] = True
                        initial_entry_tag = last_candle['enter_tag'] if 'enter_tag' in last_candle else 'entry signal'
                        dataframe.loc[:, 'enter_tag'] = f"{initial_entry_tag} (start trail price {last_candle['close']})"
            elif trailing_entry['trailing_entry_order_started'] == True:
                logger.info(f"Continue trailing for {metadata['pair']}. Manually trigger entry signal!!")
                dataframe.loc[:, 'enter_long'] = 1
                dataframe.loc[:, 'enter_tag'] = trailing_entry['enter_tag']
        # dataframe['entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_exit_trend(dataframe, metadata)
        if self.trailing_entry_order_enabled and self.abort_trailing_when_exit_signal_triggered and (self.config['runmode'].value in ('live', 'dry_run')):
            last_candle = dataframe.iloc[-1].squeeze()
            if last_candle['exit_long'] == 1:
                trailing_entry = self.trailing_entry(metadata['pair'])
                if trailing_entry['trailing_entry_order_started']:
                    logger.info(f"Sell signal for {metadata['pair']} is triggered!!! Abort trailing")
                    self.trailing_entry(metadata['pair'], reinit=True)
        return dataframe