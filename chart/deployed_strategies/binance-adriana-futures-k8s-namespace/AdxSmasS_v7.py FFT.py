kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n binance-adriana-futures exec -it pod/freqtrade-binance-adriana-futures-669f5576b5-2wnwd -c freqtrade -- cat /freqtrade/user_data/strategies/AdxSmasS_v7.py FFT.py
# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
from pandas import DataFrame
from freqtrade.persistence import Trade
from datetime import datetime, timedelta
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from typing import Optional
# --------------------------------

class AdxSmasS_v7(IStrategy):
    INTERFACE_VERSION = 3
    '\n\n    author@: Gert Wohlgemuth\n\n    converted from:\n\n    https://github.com/sthewissen/Mynt/blob/master/src/Mynt.Core/Strategies/AdxSmas.cs\n\n    '
    INTERFACE_VERSION: int = 3
    # Can this strategy go short?
    can_short: bool = True
    # Minimal ROI designed for the strategy.
    # adjust based on market conditions. We would recommend to keep it low for quick turn arounds
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = { '0': 0.8}
    # Optimal stoploss designed for the strategy
    stoploss = -0.25
    # Optimal timeframe for the strategy
    timeframe = '1h'
    use_custom_stoploss = False

    # @property
    # def protections(self):
    #     return [{'method': 'CooldownPeriod', 'stop_duration_candles': 3}, {'method': 'MaxDrawdown', 'lookback_period_candles': 12, 'trade_limit': 20, 'stop_duration_candles': 3, 'max_allowed_drawdown': 0.075}, {'method': 'LowProfitPairs', 'lookback_period_candles': 6, 'trade_limit': 2, 'stop_duration_candles': 60, 'required_profit': 0.03}, {'method': 'LowProfitPairs', 'lookback_period_candles': 24, 'trade_limit': 4, 'stop_duration_candles': 2, 'required_profit': 0.01}]

    # def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
    #     # use the initial stoploss until the profit is above 3%
    #     if current_profit < 0.03:
    #         return -1  # return a value bigger than the initial stoploss to keep using the initial stoploss
    #     # After reaching the desired offset, allow the stoploss to trail by half the profit
    #     desired_stoploss = current_profit / 2
    #     # Use a minimum of 2% and a maximum of 7.5%
    #     return max(min(desired_stoploss, 0.075), 0.02)
    # #if current_profit < 0.001 and current_time - timedelta(minutes=140) > trade.open_date_utc:
    # #    return -0.005
    # #return 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['short'] = ta.SMA(dataframe, timeperiod=3)
        dataframe['long'] = ta.SMA(dataframe, timeperiod=6)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(), ['enter_long', 'enter_tag']] = (0, 'no_long_enter')
        dataframe.loc[(dataframe['adx'] < 25) & qtpylib.crossed_above(dataframe['long'], dataframe['short']), 'enter_short'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(), ['exit_long', 'exit_tag']] = (0, 'no_long_exit')
        dataframe.loc[(dataframe['adx'] > 25) & qtpylib.crossed_above(dataframe['short'], dataframe['long']), 'exit_short'] = 1
        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:

        return 3
cat: FFT.py: No such file or directory
