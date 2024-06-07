kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-mssm-03 exec -it pod/freqtrade-bot-mssm-03-7bcbf65bf7-hjf5x -c freqtrade -- cat /freqtrade/user_data/strategies/AdxSmasS_v7_Long.py FFT_Lev.py
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.informative_decorator import informative
# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
from pandas import DataFrame
from freqtrade.persistence import Trade
from datetime import datetime, timedelta
from typing import Optional

class AdxSmasS_v7_Long(IStrategy):
    INTERFACE_VERSION = 3
    minimal_roi = {"0": 0.10}  # Targeting a 10% ROI
    # stoploss = -0.10  # Adjust stoploss for long futures trades
    timeframe = '5m'
    
    informative_timeframe = '15m'  # New informative timeframe

    def informative_pairs(self):
        # return [("BTC/USDT", self.informative_timeframe)]
        pairs = [
            ("BTC/USDT", self.informative_timeframe),   # Bitcoin - Mainstream and highly liquid
            ("ETH/USDT", self.informative_timeframe),   # Ethereum - Popular for both trading and smart contracts
            ("XRP/USDT", self.informative_timeframe),   # Ripple - Known for its fast transactions
            ("LTC/USDT", self.informative_timeframe),   # Litecoin - Often considered the silver to Bitcoin's gold
            ("BCH/USDT", self.informative_timeframe),   # Bitcoin Cash - A Bitcoin fork with different technical decisions
            # ("ADA/USDT", self.informative_timeframe),   # Cardano - Popular for its proof-of-stake mechanism
            ("DOT/USDT", self.informative_timeframe),   # Polkadot - Known for enabling cross-blockchain transfers
            ("LINK/USDT", self.informative_timeframe),  # Chainlink - Widely used for integrating real-world data into blockchains
            # ("BNB/USDT", self.informative_timeframe),   # Binance Coin - Utility token of the Binance exchange
            ("SOL/USDT", self.informative_timeframe)    # Solana - Known for its high throughput and fast transactions
        ]
        return pairs        

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Main Pair Indicators
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['short'] = ta.SMA(dataframe, timeperiod=3)
        dataframe['long'] = ta.SMA(dataframe, timeperiod=6)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        macd, macdsignal, macdhist = ta.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd
        dataframe['macdsignal'] = macdsignal
        dataframe['macdhist'] = macdhist
        upperband, middleband, lowerband = ta.BBANDS(dataframe['close'], timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
        dataframe['upperband'] = upperband
        dataframe['middleband'] = middleband
        dataframe['lowerband'] = lowerband

        # Informative Indicators for Multiple Pairs
        informative_pairs = self.informative_pairs()  # Retrieve list of informative pairs
        for pair, timeframe in informative_pairs:
            informative = self.dp.get_pair_dataframe(pair=pair, timeframe=timeframe)
            # Calculate SMA for each informative pair
            informative[f'{pair}_inf_sma'] = ta.SMA(informative, timeperiod=6)
            # Ensure correct alignment of timestamps when merging
            informative.set_index('date', inplace=True)

            # Merge each informative indicator back to the main dataframe
            dataframe = dataframe.join(informative[[f'{pair}_inf_sma']], how='left', rsuffix='_inf')

        return dataframe
    # def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    #     # Main Pair Indicators
    #     dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
    #     dataframe['short'] = ta.SMA(dataframe, timeperiod=3)
    #     dataframe['long'] = ta.SMA(dataframe, timeperiod=6)

    #     # Informative Pair Indicators
    #     informative = self.dp.get_pair_dataframe(pair="BTC/USDT", timeframe=self.informative_timeframe)
    #     informative['inf_long'] = ta.SMA(informative, timeperiod=6)
        
    #     # Merge informative indicators back to main dataframe
    #     dataframe = dataframe.join(informative[['inf_long']], on='date', rsuffix='_inf')

    #     return dataframe

    # def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    #     # Existing indicators
    #     dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
    #     dataframe['short'] = ta.SMA(dataframe, timeperiod=3)
    #     dataframe['long'] = ta.SMA(dataframe, timeperiod=6)

    #     # Additional Indicators
    #     dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
    #     macd, macdsignal, macdhist = ta.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    #     dataframe['macd'] = macd
    #     dataframe['macdsignal'] = macdsignal
    #     dataframe['macdhist'] = macdhist
    #     upperband, middleband, lowerband = ta.BBANDS(dataframe['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
    #     dataframe['upperband'] = upperband
    #     dataframe['middleband'] = middleband
    #     dataframe['lowerband'] = lowerband

    #     # Informative Pair Indicators
    #     informative = self.dp.get_pair_dataframe(pair="BTC/USDT", timeframe=self.informative_timeframe)
    #     informative['inf_long'] = ta.SMA(informative, timeperiod=6)
        
    #     # Merge informative indicators back to main dataframe
    #     dataframe = dataframe.join(informative[['inf_long']], on='date', rsuffix='_inf')

    #     return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Long Entry Conditions with cross-market analysis
        # Entry when the primary pair shows stronger momentum compared to informative pairs
        for pair, timeframe in self.informative_pairs():
            pair_sma_key = f'{pair}_inf_sma'
            # Fetch the data for the pair
            informative = self.dp.get_pair_dataframe(pair=pair, timeframe=timeframe)
            
            # Calculate indicators, e.g., SMAs
            informative['long_sma'] = ta.SMA(informative, timeperiod=50)
            informative['short_sma'] = ta.SMA(informative, timeperiod=20)
            
            # Join informative indicators back to the main dataframe
            # Note: Ensure your join keys ('date') are aligned and data is available at the same timestamps
            dataframe = dataframe.join(informative[['long_sma', 'short_sma']], on='date', rsuffix=f'_{pair}')

            # Check if the SMA of the primary pair is greater than the SMA of each informative pair
            dataframe.loc[
                (dataframe['adx'] > 40) &
                # (dataframe['rsi'] > 50) &  # RSI should indicate strength but not overbought
                (dataframe['macd'] > dataframe['macdsignal']) &  # Bullish MACD crossover
                (dataframe['long'] > dataframe['short']) &
                (dataframe['long'] > dataframe[pair_sma_key]), 'enter_long'] = 1

        dataframe['enter_short'] = 0  # Assuming no short entry handling as per strategy focus

        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:

        return 4

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Define your informative pairs and timeframes
        # informative_pairs = [
        #     ("BTC/USDT", "5m"),
        #     ("ETH/USDT", "5m"),
        #     # Add more pairs as needed
        # ]

        # Process each informative pair
        for pair, timeframe in self.informative_pairs():
            # Fetch the data for the pair
            informative = self.dp.get_pair_dataframe(pair=pair, timeframe=timeframe)
            
            # Calculate indicators, e.g., SMAs
            informative['long_sma'] = ta.SMA(informative, timeperiod=50)
            informative['short_sma'] = ta.SMA(informative, timeperiod=20)
            
            # Join informative indicators back to the main dataframe
            # Note: Ensure your join keys ('date') are aligned and data is available at the same timestamps
            dataframe = dataframe.join(informative[['long_sma', 'short_sma']], on='date', rsuffix=f'_{pair}')

        # Entry condition: Check SMA conditions across all informative pairs
        entry_condition = (dataframe['long'] > dataframe['short'])  # Base condition for the primary pair
        for pair, _ in informative_pairs:
            entry_condition &= (dataframe[f'long_sma_{pair}'] > dataframe[f'short_sma_{pair}'])

        # Apply the entry condition to the dataframe
        dataframe.loc[entry_condition, 'enter_long'] = 1
        dataframe['enter_short'] = 0  # Assuming no short entry handling

        return dataframe



    # def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    #     # Enhanced Long Entry Conditions
    #     dataframe.loc[
    #         (dataframe['adx'] > 25) &
    #         (dataframe['rsi'] > 50) &  # RSI should indicate not oversold
    #         (dataframe['macd'] > dataframe['macdsignal']) &  # Bullish MACD crossover
    #         (dataframe['close'] > dataframe['middleband']) &  # Price above middle Bollinger Band
    #         (dataframe['long'] > dataframe['short']) &
    #         (dataframe['long'] > dataframe['inf_long']), 'enter_long'] = 1

    #     dataframe['enter_short'] = 0  # Assuming no short entry handling

    #     return dataframe
    # def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    #     # Long Entry Condition: Simple cross above condition with informative pair
    #     dataframe.loc[(dataframe['adx'] > 25) & (dataframe['long'] > dataframe['short']) & (dataframe['long'] > dataframe['inf_long']), 'enter_long'] = 1
    #     dataframe.loc[(dataframe['adx'] > 25) & (dataframe['long'] > dataframe['short']) & (dataframe['long'] > dataframe['inf_long']), 'enter_short'] = 0
        
    #     return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Long Exit Conditions
        # Exit when RSI indicates overbought conditions, suggesting a potential reversal
        dataframe.loc[
            (dataframe['rsi'] > 70), 'exit_long'] = 1

        # Exit when the MACD line crosses below the signal line, indicating decreasing momentum
        dataframe.loc[
            (dataframe['macd'] < dataframe['macdsignal']), 'exit_long'] = 1

        # Exit when the price crosses below the lower Bollinger Band, indicating a potential sharp decline
        dataframe.loc[
            (dataframe['close'] < dataframe['lowerband']), 'exit_long'] = 1

        # Additional exit condition based on ADX and moving averages, as previously used
        # Exit if ADX falls below a certain threshold (e.g., 25), indicating a loss of trend strength
        dataframe.loc[
            (dataframe['adx'] < 25) | (dataframe['long'] < dataframe['short']), 'exit_long'] = 1

        # Remove any exit short logic if the strategy is only for long positions
        dataframe['exit_short'] = 0  # This ensures no shorts are exited as this strategy is designed for longs only

        return dataframe


    # def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    #     # Long Exit Condition: Opposite of entry or specific profit target/stoploss hit
    #     dataframe.loc[(dataframe['adx'] < 25) | (dataframe['long'] < dataframe['short']), 'exit_long'] = 1
    #     dataframe.loc[(dataframe['adx'] < 25) | (dataframe['long'] < dataframe['short']), 'exit_short'] = 0
    #     dataframe.loc[(), ['exit_short', 'exit_tag']] = (0, 'no_short_exit')
        
    #     return dataframe
cat: FFT_Lev.py: No such file or directory
