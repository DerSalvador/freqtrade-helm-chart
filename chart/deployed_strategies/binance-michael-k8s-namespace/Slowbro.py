# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, merge_informative_pair
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
# --------------------------------
'\n                   ,-\'"-.\n             __...| .".  |\n        ,--+"     \' |   ,\'\n       | .\'   ..--,  `-\' `.\n       |/    |  ,\' |       :\n       |\\...-+-".._|       |\n     ,"            `--.     `.     _..-\'+"/__\n    /   .              |      :,-"\'     `" |_\'\n ..| .    _,....___,\'  |    ,\'            /..\'.__.-\'  /V     |   \'                ,\'""\n`. |  `:  \\.       |  .               ,\'         ,.-.\n  `:       |       |  \'             .^.        ,\' ,"`.\n    `.     |       | /               _.\\.---..\'  /   |     ,-,.\n      `._  A      / j              ."       /   /    |   .\',\' |\n         `. `...-\' ,\'             /        /._ /     | ,\' /   |\n           |"-----\'             ,\'        /   /-.__  |\'  /    |\n           | _.--\'"\'""`.       .         /   /     `"^-.,     |\n           |"       ____\\     j             j            `"--.|\n           |  _.-""\'     \\    |             |                j\n         _,+."_           \\   |             |                |\n        \'    . `.     _.-"\'.     ,          |                \'\n       |_    | `.`. ,\'      `.   |          |               .\n       | `-. |  ,\'.\\         .\\   \\         |              /\n       |\\   ;+-\'   "\\      ,\'  `.  \\        |             /\n       \'\\."         \\ _.-\'     ,`. \\       \'            /\n        \\\\           :       .\'   `.`._     \\          / `-..-.\n         ``.          |    _." _...,:.._`.    `._     ,\'   -. \'\n          `.`.        |`".\'__.\'           `,...__"--`/  |   / |\n            `.`.     _\'    \\|             ,\'       ,\'_  `..\'  |..__,.\n              `._`--".\'     \\`._      _,-\'       ,\' `-\'  /    | .  ,\'\n                 `""\'        `. `"\'""\'   ,-" _,-\'    _ .\'     \'  `\' `.\n                               `-.._____:  |"       _," ."  ,\'__,.."\'\n                                         `.|-...,.<\'    `,_""\'`./\n                                             `.\'   `"--\'" mh\nSLOWBRO v100\n\n'

class Slowbro(IStrategy):
    INTERFACE_VERSION = 3
    minimal_roi = {'0': 0.1, '1440': 0.2, '2880': 0.3, '10080': 1.0}
    # Stoploss:
    stoploss = -0.99
    timeframe = '1h'
    inf_timeframe = '1d'
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 30
    process_only_new_candles = False

    def informative_pairs(self):
        # add all whitelisted pairs on informative timeframe
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.inf_timeframe) for pair in pairs]
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.inf_timeframe)
        informative['30d-low'] = informative['close'].rolling(30).min()
        informative['30d-high'] = informative['close'].rolling(30).max()
        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, self.inf_timeframe, ffill=True)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[qtpylib.crossed_above(dataframe['close'], dataframe[f'30d-low_{self.inf_timeframe}']), 'entry'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[qtpylib.crossed_above(dataframe['close'], dataframe[f'30d-high_{self.inf_timeframe}']), 'exit'] = 1
        return dataframe