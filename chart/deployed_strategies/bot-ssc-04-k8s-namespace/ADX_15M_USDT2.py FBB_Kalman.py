kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-ssc-04 exec -it pod/freqtrade-bot-ssc-04-8499ff6998-p5khc -c freqtrade -- cat /freqtrade/user_data/strategies/ADX_15M_USDT2.py FBB_Kalman.py
# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
# --------------------------------

class ADX_15M_USDT2(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '15m'
    # ROI table:
    minimal_roi = {'0': 0.10313, '102': 0.07627, '275': 0.04228, '588': 0}
    # Stoploss:
    stoploss = -0.31941

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=25)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=25)
        dataframe['sar'] = ta.SAR(dataframe)
        dataframe['mom'] = ta.MOM(dataframe, timeperiod=14)
        dataframe['exit-adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['exit-plus_di'] = ta.PLUS_DI(dataframe, timeperiod=25)
        dataframe['exit-minus_di'] = ta.MINUS_DI(dataframe, timeperiod=25)
        dataframe['exit-sar'] = ta.SAR(dataframe)
        dataframe['exit-mom'] = ta.MOM(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        #(dataframe['adx'] > 45) &
        #(dataframe['minus_di'] > 26) &
        # (dataframe['plus_di'] > 33) &
        dataframe.loc[qtpylib.crossed_above(dataframe['minus_di'], dataframe['plus_di']), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # (dataframe['minus_di'] > 22) &
        #(dataframe['plus_di'] > 24) &
        dataframe.loc[(dataframe['adx'] > 91) & (dataframe['exit-minus_di'] > 91) & qtpylib.crossed_above(dataframe['exit-plus_di'], dataframe['exit-minus_di']), 'exit'] = 1
        return dataframecat: FBB_Kalman.py: No such file or directory
