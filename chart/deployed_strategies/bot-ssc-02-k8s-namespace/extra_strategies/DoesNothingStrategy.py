kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-ssc-02 exec -it pod/freqtrade-bot-ssc-02-7cd5d5798b-z48tl -c freqtrade -- cat /extra_strategies/DoesNothingStrategy.py
# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
# --------------------------------

class DoesNothingStrategy(IStrategy):
    INTERFACE_VERSION = 3
    '\n\n    author@: Gert Wohlgemuth\n\n    just a skeleton\n\n    '
    # Minimal ROI designed for the strategy.
    # adjust based on market conditions. We would recommend to keep it low for quick turn arounds
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {'0': 0.01}
    # Optimal stoploss designed for the strategy
    stoploss = -0.25
    # Optimal timeframe for the strategy
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(), 'exit_long'] = 1
        return dataframe