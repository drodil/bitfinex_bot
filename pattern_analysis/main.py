import time

import numpy as np
import pandas as pd
import talib as tb
import talib.abstract as abstract
from bitfinex import bitfinex

interval = "6h"
coinPairs = ['btcusd', 'ethusd', 'iotusd', 'xrpusd', 'ltcusd',
                'zecusd', 'dshusd', 'eosusd', 'neousd', 'etcusd']

publicV1 = bitfinex.PublicV1()
publicV2 = bitfinex.PublicV2()
functions= tb.get_function_groups()['Pattern Recognition']

while True:
    for coin in coinPairs:
        try:
            array = np.array(publicV2.candles(interval, "t" + coin.upper(), "hist"))[::-1]
            df = pd.DataFrame(data=array[:,0:6], columns=["date", "open", "close", "high", "low", "volume"])
            max_total = 0
            for length in range(10, len(df)):
                total = 0
                for talib_function in functions:
                    res = abstract.Function(talib_function)(df)
                    total += res[length]
                if total >= 400:
                    max_total = total
                    print(coin, length, df["close"][length], total)


            print(coin, max_total)



        except Exception as ex:
            print(ex)
            time.sleep(75.0)
            pass

