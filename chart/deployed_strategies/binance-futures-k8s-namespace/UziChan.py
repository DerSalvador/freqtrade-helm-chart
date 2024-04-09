# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
# --------------------------------
import talib.abstract as ta
import logging
import pandas_ta as pta
from pandas import DataFrame, Series
from datetime import datetime, timezone
from freqtrade.persistence import Trade
logger = logging.getLogger(__name__)

class UziChan(IStrategy):
    INTERFACE_VERSION = 3
    minimal_roi = {'0': 0.1}
    stoploss = -0.1
    timeframe = '5m'
    # def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs):     
    #     dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)        
    #     if current_profit*100 > 1: 
    #         return 'exit_1.2pc'
    #     return None

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['perc'] = (dataframe['high'] - dataframe['low']) / dataframe['low'] * 100
        dataframe['avg3_perc'] = ta.EMA(dataframe['perc'], 3)
        dataframe['perc_norm'] = (dataframe['perc'] - dataframe['perc'].rolling(50).min()) / (dataframe['perc'].rolling(50).max() - dataframe['perc'].rolling(50).min())
        # Uzirox's channel prezzo
        periodo = 15
        dataframe['uc_mid'] = pta.ssf(dataframe['close'], 5)
        dataframe['uc_stdv'] = ta.STDDEV(dataframe['uc_mid'], periodo).round(5)
        dataframe['uc_low'] = ta.EMA(dataframe['uc_mid'] - dataframe['uc_stdv'], 3).round(5)
        dataframe['uc_up'] = ta.EMA(dataframe['uc_mid'] + dataframe['uc_stdv'], 3).round(5)
        dataframe['co'] = ta.ADOSC(dataframe, fastperiod=30, slowperiod=100).round(3)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[((dataframe['close'] < dataframe['uc_low']) | (dataframe['open'] < dataframe['uc_low'])) & (dataframe['co'] > dataframe['co'].shift()), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['high'] > dataframe['uc_up']) & (dataframe['co'] > dataframe['co'].shift()), 'exit'] = 1
        return dataframe

class UziChanTB(UziChan):
    process_only_new_candles = True
    custom_info_trail_entry = dict()
    custom_info_trail_exit = dict()
    # Trailing entry parameters
    trailing_entry_order_enabled = True
    trailing_exit_order_enabled = True
    #trailing_expire_seconds = 1800      #NOTE 5m timeframe
    trailing_expire_seconds = 1800 / 5  #NOTE 1m timeframe
    #trailing_expire_seconds = 1800*3    #NOTE 15m timeframe
    # If the current candle goes above min_uptrend_trailing_profit % before trailing_expire_seconds_uptrend seconds, entry the coin
    trailing_entry_uptrend_enabled = True
    trailing_exit_uptrend_enabled = True
    trailing_expire_seconds_uptrend = 90
    min_uptrend_trailing_profit = 0.02
    debug_mode = True
    trailing_entry_max_stop = 0.02  # stop trailing entry if current_price > starting_price * (1+trailing_entry_max_stop)
    trailing_entry_max_entry = 0.0  # entry if price between uplimit (=min of serie (current_price * (1 + trailing_entry_offset())) and (start_price * 1+trailing_entry_max_entry))
    trailing_exit_max_stop = 0.02  # stop trailing exit if current_price < starting_price * (1+trailing_entry_max_stop)
    trailing_exit_max_exit = 0.0  # exit if price between downlimit (=max of serie (current_price * (1 + trailing_exit_offset())) and (start_price * 1+trailing_exit_max_exit))
    abort_trailing_when_exit_signal_triggered = True
    init_trailing_entry_dict = {'trailing_entry_order_started': False, 'trailing_entry_order_uplimit': 0, 'start_trailing_price': 0, 'entry_tag': None, 'start_trailing_time': None, 'offset': 0, 'allow_trailing': False}
    init_trailing_exit_dict = {'trailing_exit_order_started': False, 'trailing_exit_order_downlimit': 0, 'start_trailing_exit_price': 0, 'exit_tag': None, 'start_trailing_time': None, 'offset': 0, 'allow_exit_trailing': False}

    def trailing_entry(self, pair, reinit=False):
        # returns trailing entry info for pair (init if necessary)
        if not pair in self.custom_info_trail_entry:
            self.custom_info_trail_entry[pair] = dict()
        if reinit or not 'trailing_entry' in self.custom_info_trail_entry[pair]:
            self.custom_info_trail_entry[pair]['trailing_entry'] = self.init_trailing_entry_dict.copy()
        return self.custom_info_trail_entry[pair]['trailing_entry']

    def trailing_exit(self, pair, reinit=False):
        # returns trailing exit info for pair (init if necessary)
        if not pair in self.custom_info_trail_exit:
            self.custom_info_trail_exit[pair] = dict()
        if reinit or not 'trailing_exit' in self.custom_info_trail_exit[pair]:
            self.custom_info_trail_exit[pair]['trailing_exit'] = self.init_trailing_exit_dict.copy()
        return self.custom_info_trail_exit[pair]['trailing_exit']

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
            logger.info(f"pair: {pair} : start: {trailing_entry['start_trailing_price']:.4f}, duration: {duration}, current: {current_price:.4f}, uplimit: {trailing_entry['trailing_entry_order_uplimit']:.4f}, profit: {self.current_trailing_entry_profit_ratio(pair, current_price) * 100:.2f}%, offset: {trailing_entry['offset']}")

    def trailing_exit_info(self, pair: str, current_price: float):
        # current_time live, dry run
        current_time = datetime.now(timezone.utc)
        if not self.debug_mode:
            return
        trailing_exit = self.trailing_exit(pair)
        duration = 0
        try:
            duration = current_time - trailing_exit['start_trailing_time']
        except TypeError:
            duration = 0
        finally:
            logger.info(f"'\x1b[36m'SELL: pair: {pair} : start: {trailing_exit['start_trailing_exit_price']:.4f}, duration: {duration}, current: {current_price:.4f}, downlimit: {trailing_exit['trailing_exit_order_downlimit']:.4f}, profit: {self.current_trailing_exit_profit_ratio(pair, current_price) * 100:.2f}%, offset: {trailing_exit['offset']}")

    def current_trailing_entry_profit_ratio(self, pair: str, current_price: float) -> float:
        trailing_entry = self.trailing_entry(pair)
        if trailing_entry['trailing_entry_order_started']:
            return (trailing_entry['start_trailing_price'] - current_price) / trailing_entry['start_trailing_price']
        else:
            return 0

    def current_trailing_exit_profit_ratio(self, pair: str, current_price: float) -> float:
        trailing_exit = self.trailing_exit(pair)
        if trailing_exit['trailing_exit_order_started']:
            return (current_price - trailing_exit['start_trailing_exit_price']) / trailing_exit['start_trailing_exit_price']
        else:
            #return 0-((trailing_exit['start_trailing_exit_price'] - current_price) / trailing_exit['start_trailing_exit_price'])
            return 0

    def trailing_entry_offset(self, dataframe, pair: str, current_price: float):
        # return rebound limit before a entry in % of initial price, function of current price
        # return None to stop trailing entry (will start again at next entry signal)
        # return 'forceentry' to force immediate entry
        # (example with 0.5%. initial price : 100 (uplimit is 100.5), 2nd price : 99 (no entry, uplimit updated to 99.5), 3price 98 (no entry uplimit updated to 98.5), 4th price 99 -> BUY
        current_trailing_profit_ratio = self.current_trailing_entry_profit_ratio(pair, current_price)
        last_candle = dataframe.iloc[-1]
        adapt = last_candle['perc_norm'].round(5)
        default_offset = 0.0045 * (1 + adapt)  #NOTE: default_offset 0.0045 <--> 0.009
        trailing_entry = self.trailing_entry(pair)
        if not trailing_entry['trailing_entry_order_started']:
            return default_offset
        # example with duration and indicators
        # dry run, live only
        last_candle = dataframe.iloc[-1]
        current_time = datetime.now(timezone.utc)
        trailing_duration = current_time - trailing_entry['start_trailing_time']
        if trailing_duration.total_seconds() > self.trailing_expire_seconds:
            if current_trailing_profit_ratio > 0 and last_candle['entry'] == 1:
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

    def trailing_exit_offset(self, dataframe, pair: str, current_price: float):
        # return rebound limit before a entry in % of initial price, function of current price
        # return None to stop trailing entry (will start again at next entry signal)
        # return 'forceentry' to force immediate entry
        # (example with 0.5%. initial price : 100 (uplimit is 100.5), 2nd price : 99 (no entry, uplimit updated to 99.5), 3price 98 (no entry uplimit updated to 98.5), 4th price 99 -> BUY
        current_trailing_exit_profit_ratio = self.current_trailing_exit_profit_ratio(pair, current_price)
        last_candle = dataframe.iloc[-1]
        adapt = last_candle['perc_norm'].round(5)
        default_offset = 0.003 * (1 + adapt)  #NOTE: default_offset 0.003 <--> 0.006
        trailing_exit = self.trailing_exit(pair)
        if not trailing_exit['trailing_exit_order_started']:
            return default_offset
        # example with duration and indicators
        # dry run, live only
        last_candle = dataframe.iloc[-1]
        current_time = datetime.now(timezone.utc)
        trailing_duration = current_time - trailing_exit['start_trailing_time']
        if trailing_duration.total_seconds() > self.trailing_expire_seconds:
            if current_trailing_exit_profit_ratio > 0 and last_candle['exit'] == 1:
                # more than 1h, price over first signal, exit signal still active -> exit
                return 'forceexit'
            else:
                # wait for next signal
                return None
        elif self.trailing_exit_uptrend_enabled and trailing_duration.total_seconds() < self.trailing_expire_seconds_uptrend and (current_trailing_exit_profit_ratio < -1 * self.min_uptrend_trailing_profit):
            # less than 90s and price is falling, exit 
            return 'forceexit'
        if current_trailing_exit_profit_ratio > 0:
            # current price is lower than initial price
            return default_offset
        # 0.06: 0.02,
        # 0.03: 0.01,
        trailing_exit_offset = {0.1: default_offset}
        for key in trailing_exit_offset:
            if current_trailing_exit_profit_ratio < key:
                return trailing_exit_offset[key]
        return default_offset
    # end of trailing exit parameters
    # -----------------------------------------------------

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        self.trailing_entry(metadata['pair'])
        self.trailing_exit(metadata['pair'])
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
                        if not trailing_entry['trailing_entry_order_started'] and last_candle['entry'] == 1:
                            # start trailing entry
                            trailing_entry['trailing_entry_order_started'] = True
                            trailing_entry['trailing_entry_order_uplimit'] = last_candle['close']
                            trailing_entry['start_trailing_price'] = last_candle['close']
                            trailing_entry['entry_tag'] = last_candle['entry_tag']
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

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float, rate: float, time_in_force: str, exit_reason: str, **kwargs) -> bool:
        val = super().confirm_trade_exit(pair, trade, order_type, amount, rate, time_in_force, exit_reason, **kwargs)
        if val:
            if self.trailing_exit_order_enabled and self.config['runmode'].value in ('live', 'dry_run'):
                val = False
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if len(dataframe) >= 1:
                    last_candle = dataframe.iloc[-1].squeeze()
                    current_price = rate
                    trailing_exit = self.trailing_exit(pair)
                    trailing_exit_offset = self.trailing_exit_offset(dataframe, pair, current_price)
                    if trailing_exit['allow_exit_trailing']:
                        if not trailing_exit['trailing_exit_order_started'] and last_candle['exit'] == 1:
                            trailing_exit['trailing_exit_order_started'] = True
                            trailing_exit['trailing_exit_order_downlimit'] = last_candle['close']
                            trailing_exit['start_trailing_exit_price'] = trade.open_rate
                            trailing_exit['exit_tag'] = last_candle['exit_tag']
                            trailing_exit['start_trailing_time'] = datetime.now(timezone.utc)
                            trailing_exit['offset'] = 0
                            self.trailing_exit_info(pair, current_price)
                            logger.info(f'start trailing exit for {pair} at {trade.open_rate}')
                        elif trailing_exit['trailing_exit_order_started']:
                            if trailing_exit_offset == 'forceexit':
                                # exit in custom conditions
                                val = True
                                ratio = '%.2f' % (self.current_trailing_exit_profit_ratio(pair, current_price) * 100)
                                self.trailing_exit_info(pair, current_price)
                                logger.info(f'price OK for {pair} ({ratio} %, {current_price})')
                            elif trailing_exit_offset is None:
                                # stop trailing exit custom conditions
                                self.trailing_exit(pair, reinit=True)
                                logger.info(f'STOP trailing exit for {pair} because "trailing exit offset" returned None')
                            elif current_price > trailing_exit['trailing_exit_order_downlimit']:
                                # update downlimit
                                old_downlimit = trailing_exit['trailing_exit_order_downlimit']
                                self.custom_info_trail_exit[pair]['trailing_exit']['trailing_exit_order_downlimit'] = max(current_price * (1 - trailing_exit_offset), self.custom_info_trail_exit[pair]['trailing_exit']['trailing_exit_order_downlimit'])
                                self.custom_info_trail_exit[pair]['trailing_exit']['offset'] = trailing_exit_offset
                                self.trailing_exit_info(pair, current_price)
                                logger.info(f"update trailing exit for {pair} at {old_downlimit} -> {self.custom_info_trail_exit[pair]['trailing_exit']['trailing_exit_order_downlimit']}")
                            elif current_price > trailing_exit['start_trailing_exit_price'] * (1 - self.trailing_exit_max_exit):
                                # exit! current price < downlimit && higher than starting price
                                val = True
                                ratio = '%.2f' % (self.current_trailing_exit_profit_ratio(pair, current_price) * 100)
                                self.trailing_exit_info(pair, current_price)
                                logger.info(f"current price ({current_price}) < downlimit ({trailing_exit['trailing_exit_order_downlimit']}) but higher than starting price ({trailing_exit['start_trailing_exit_price'] * (1 + self.trailing_exit_max_exit)}). OK for {pair} ({ratio} %)")
                            elif current_price < trailing_exit['start_trailing_exit_price'] * (1 - self.trailing_exit_max_stop):
                                # stop trailing, exit fast, price too low
                                val = True
                                self.trailing_exit_info(pair, current_price)
                                logger.info(f'STOP trailing exit for {pair} because of the price is much lower than starting price * {1 + self.trailing_exit_max_stop}')
                            else:
                                # uplimit > current_price > max_price, continue trailing and wait for the price to go down
                                self.trailing_exit_info(pair, current_price)
                                logger.info(f'price too low for {pair} !')
                    else:
                        logger.info(f'Wait for next exit signal for {pair}')
                if val == True:
                    self.trailing_exit_info(pair, rate)
                    self.trailing_exit(pair, reinit=True)
                    logger.info(f'STOP trailing exit for {pair} because I SOLD it')
        if exit_reason != 'exit_signal':
            val = True
        return val

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if self.trailing_entry_order_enabled and self.config['runmode'].value in ('live', 'dry_run'):
            last_candle = dataframe.iloc[-1].squeeze()
            trailing_entry = self.trailing_entry(metadata['pair'])
            if last_candle['entry'] == 1:
                if not trailing_entry['trailing_entry_order_started']:
                    open_trades = Trade.get_trades([Trade.pair == metadata['pair'], Trade.is_open.is_(True)]).all()
                    if not open_trades:
                        logger.info(f"Set 'allow_trailing' to True for {metadata['pair']} to start trailing!!!")
                        # self.custom_info_trail_entry[metadata['pair']]['trailing_entry']['allow_trailing'] = True
                        trailing_entry['allow_trailing'] = True
                        initial_entry_tag = last_candle['entry_tag'] if 'entry_tag' in last_candle else 'entry signal'
                        dataframe.loc[:, 'entry_tag'] = f"{initial_entry_tag} (start trail price {last_candle['close']})"
            elif trailing_entry['trailing_entry_order_started'] == True:
                logger.info(f"Continue trailing for {metadata['pair']}. Manually trigger entry signal!!")
                dataframe.loc[:, 'entry'] = 1
                dataframe.loc[:, 'entry_tag'] = trailing_entry['entry_tag']
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_exit_trend(dataframe, metadata)
        if self.trailing_entry_order_enabled and self.abort_trailing_when_exit_signal_triggered and (self.config['runmode'].value in ('live', 'dry_run')):
            last_candle = dataframe.iloc[-1].squeeze()
            if last_candle['exit'] == 1:
                trailing_entry = self.trailing_entry(metadata['pair'])
                if trailing_entry['trailing_entry_order_started']:
                    logger.info(f"Sell signal for {metadata['pair']} is triggered!!! Abort trailing")
                    self.trailing_entry(metadata['pair'], reinit=True)
        if self.trailing_exit_order_enabled and self.config['runmode'].value in ('live', 'dry_run'):
            last_candle = dataframe.iloc[-1].squeeze()
            trailing_exit = self.trailing_exit(metadata['pair'])
            if last_candle['exit'] != 0:
                if not trailing_exit['trailing_exit_order_started']:
                    open_trades = Trade.get_trades([Trade.pair == metadata['pair'], Trade.is_open.is_(True)]).all()
                    #if not open_trades: 
                    if open_trades:
                        logger.info(f"Set 'allow_SELL_trailing' to True for {metadata['pair']} to start *SELL* trailing")
                        # self.custom_info_trail_entry[metadata['pair']]['trailing_entry']['allow_trailing'] = True
                        trailing_exit['allow_exit_trailing'] = True
                        initial_exit_tag = last_candle['exit_tag'] if 'exit_tag' in last_candle else 'exit signal'
                        dataframe.loc[:, 'exit_tag'] = f"{initial_exit_tag} (start trail price {last_candle['close']})"
            elif trailing_exit['trailing_exit_order_started'] == True:
                logger.info(f"Continue trailing for {metadata['pair']}. Manually trigger exit signal!")
                dataframe.loc[:, 'exit'] = 1
                dataframe.loc[:, 'exit_tag'] = trailing_exit['exit_tag']
        return dataframe
    plot_config = {'main_plot': {'uc_up': {'color': 'gray'}, 'uc_mid': {'color': 'green'}, 'uc_low': {'color': 'gray'}}, 'subplots': {}}