import talib.abstract as tb
import logging

adxLimit = 25
cciUpperLimit = 100
cciLowerLimit = -100
rsiUpperLimit = 70
rsiLowerLimit = 30


class Indicator:
    maxRating = 1
    minRating = -1

    def __init__(self, dataframe):
        self.dataframe = dataframe

    def signal(self):
        ma14 = tb.SMA(self.dataframe, 14)
        ma30 = tb.SMA(self.dataframe, 30)

        ma14current = ma14[len(ma14) - 1]
        ma30current = ma30[len(ma30) - 1]

        if ma14current > ma30current:
            return 1
        elif ma14current < ma30current:
            return -1
        else:
            return 0

    def rate(self, coin, time):
        bbands = self.bbands()
        cci = self.cci()
        rsi = self.rsi()
        ma = self.ma()
        ultosc = self.ultosc()
        mom = self.mom()
        macd = self.macd()
        point = 0
        debug = coin + " " + time + ": "

        if bbands == "buy":
            point = point + 1
            debug = debug + "BBANDS: buy "
        elif bbands == "sell":
            point = point - 1
            debug = debug + "BBANDS: sell "

        if cci == "buy":
            point = point + 0.5
            debug = debug + "CCI: buy "
        elif cci == "sell":
            point = point - 0.5
            debug = debug + "CCI: sell "

        if mom == "buy":
            point = point + 0.5
            debug = debug + "MOM: buy "
        elif mom == "sell":
            point = point - 0.5
            debug = debug + "MOM: sell "

        if macd == "buy":
            point = point + 0.5
            debug = debug + "MACD: buy "
        elif macd == "sell":
            point = point - 0.5
            debug = debug + "MACD: sell "

        if rsi == "buy":
            point = point + 1
            debug = debug + "RSI: buy "
        elif rsi == "sell":
            point = point - 1
            debug = debug + "RSI: sell "

        if ma == "buy":
            point = point + 1
            debug = debug + "MA: buy "
        elif ma == "sell":
            point = point - 1
            debug = debug + "MA: sell "

        if ultosc == "buy":
            point = point + 1
            debug = debug + "ULTOSC: buy "
        elif ultosc == "sell":
            point = point - 1
            debug = debug + "ULTOSC: sell "

        logging.debug(debug + "-> " + str(point))
        return point

    def bbands(self):
        bbands = tb.BBANDS(self.dataframe, timeperiod=100, nbdevup=2.0, nbdevdn=2.0, matype=0)
        if (self.dataframe['open'][len(self.dataframe) - 1] < bbands['lowerband'][len(bbands) - 1] <
                self.dataframe['close'][len(self.dataframe) - 1]):
            return "buy"
        elif (self.dataframe['open'][len(self.dataframe) - 1] > bbands['upperband'][len(bbands) - 1] >
              self.dataframe['close'][len(self.dataframe) - 1]):
            return "sell"
        else:
            return "neutral"

    def ma(self):
        if self.ema() == "buy" and self.sma() == "buy":
            return "buy"
        elif self.ema() == "sell" and self.sma() == "sell":
            return "sell"
        else:
            return "neutral"

    def ema(self):
        buy = 0
        sell = 0
        for period in [5, 10, 20]:
            real = tb.EMA(self.dataframe, timeperiod=period)
            value = real[len(real) - 1]
            price = self.dataframe['close'][len(self.dataframe) - 1]
            if value > price:
                sell = sell + 1
            elif value < price:
                buy = buy + 1
        if sell == 3:
            return "sell"
        elif buy == 3:
            return "buy"
        else:
            return "neutral"

    def sma(self):
        buy = 0
        sell = 0
        for period in [5, 10, 20]:
            real = tb.SMA(self.dataframe, timeperiod=period)
            value = real[len(real) - 1]
            price = self.dataframe['close'][len(self.dataframe) - 1]
            if value > price:
                sell = sell + 1
            elif value < price:
                buy = buy + 1
        if sell == 3:
            return "sell"
        elif buy == 3:
            return "buy"
        else:
            return "neutral"

    def sar(self):
        sar = tb.SAR(self.dataframe, acceleration=0, maximum=0)
        if self.dataframe['open'][len(self.dataframe) - 1] > sar[len(sar) - 1]:
            return "buy"
        elif self.dataframe['open'][len(self.dataframe) - 1] < sar[len(sar) - 1]:
            return "sell"
        else:
            return "neutral"

    def wma(self):
        real = tb.WMA(self.close, timeperiod=30)
        return real

    def adx(self):
        adx = tb.ADX(self.dataframe, timeperiod=14)
        value = adx[len(adx) - 1]
        if value > adxLimit:
            return "strong"
        elif value < adxLimit:
            return "weak"
        else:
            return "neutral"

    def cci(self):
        cci = tb.CCI(self.dataframe, timeperiod=20)
        value = cci[len(cci) - 1]
        if value > cciUpperLimit:
            return "sell"
        elif value < cciLowerLimit:
            return "buy"
        else:
            return "neutral"

    def macd(self):
        macd = tb.MACD(self.dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        value = macd['macd'][len(macd) - 1]
        signal = macd['macdsignal'][len(macd) - 1]
        if value > signal:
            return "buy"
        elif value < signal:
            return "sell"
        else:
            return "neutral"

    def mom(self):
        mom = tb.MOM(self.dataframe, timeperiod=10)
        value = mom[len(mom) - 1]
        old_value = mom[len(mom) - 2]
        if value > old_value:
            return "buy"
        else:
            return "sell"

    def rsi(self):
        rsi = tb.RSI(self.dataframe, timeperiod=14)
        value = rsi[len(rsi) - 1]
        if value > rsiUpperLimit:
            return "sell"
        elif value < rsiLowerLimit:
            return "buy"
        else:
            return "neutral"

    def stoch(self):
        stoch = tb.STOCH(self.dataframe, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        slowk = stoch["slowk"][len(stoch) - 1]

        if slowk > 80:
            return "overbought"
        elif slowk > 60:
            return "buy"
        elif slowk < 20:
            return "oversold"
        elif slowk < 40:
            return "sell"
        else:
            return "neutral"

    def stochf(self):
        stochf = tb.STOCHF(self.dataframe, fastk_period=5, fastd_period=3, fastd_matype=0)
        fastk = stochf["fastk"][len(stochf) - 1]

        if fastk > 80:
            return "overbought"
        elif fastk > 60:
            return "buy"
        elif fastk < 20:
            return "oversold"
        elif fastk < 40:
            return "sell"
        else:
            return "neutral"

    def stochrsi(self):
        stochrsi = tb.STOCHRSI(self.dataframe, fastk_period=5, fastd_period=3, fastd_matype=0)
        fastk = stochrsi["fastk"][len(stochrsi) - 1]

        if fastk > 80:
            return "overbought"
        elif fastk > 60:
            return "buy"
        elif fastk < 20:
            return "oversold"
        elif fastk < 40:
            return "sell"
        else:
            return "neutral"

    def ultosc(self):
        real = tb.ULTOSC(self.dataframe, timeperiod1=7, timeperiod2=14, timeperiod3=28)
        value = real[len(real) - 1]
        if value > 70:
            return "buy"
        elif value < 40:
            return "sell"
        else:
            return "neutral"
