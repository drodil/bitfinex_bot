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

        ma5new = ma14[len(ma14) - 2]
        ma20new = ma30[len(ma30) - 2]

        ma5old = ma14[len(ma14) - 3]
        ma20old = ma30[len(ma30) - 3]

        if(ma14current > ma30current):
            return 1
        elif (ma14current < ma30current):
            return -1
        else:
            return 0

    def rate(self, coin, time):
        bbands = self.BBANDS()
        cci = self.CCI()
        rsi = self.RSI()
        ma = self.MA()
        ultosc = self.ULTOSC()
        adx = self.ADX()
        mom = self.MOM()
        macd = self.MACD()
        point = 0
        debug = coin + " " + time + ": "

        if (bbands == "buy"):
            point = point + 1
            debug = debug + "BBANDS: buy "
        elif (bbands == "sell"):
            point = point - 1
            debug = debug + "BBANDS: sell "

        if (cci == "buy"):
            point = point + 0.5
            debug = debug + "CCI: buy "
        elif (cci == "sell"):
            point = point - 0.5
            debug = debug + "CCI: sell "

        if (mom == "buy"):
            point = point + 0.5
            debug = debug + "MOM: buy "
        elif (mom == "sell"):
            point = point - 0.5
            debug = debug + "MOM: sell "

        if (macd == "buy"):
            point = point + 0.5
            debug = debug + "MACD: buy "
        elif (macd == "sell"):
            point = point - 0.5
            debug = debug + "MACD: sell "

        if (rsi == "buy"):
            point = point + 1
            debug = debug + "RSI: buy "
        elif (rsi == "sell"):
            point = point - 1
            debug = debug + "RSI: sell "

        if (ma == "buy"):
            point = point + 1
            debug = debug + "MA: buy "
        elif (ma == "sell"):
            point = point - 1
            debug = debug + "MA: sell "

        if (ultosc == "buy"):
            point = point + 1
            debug = debug + "ULTOSC: buy "
        elif (ultosc == "sell"):
            point = point - 1
            debug = debug + "ULTOSC: sell "

        logging.debug(debug + "-> " + str(point))
        return point

    def BBANDS(self):
        BBANDS = tb.BBANDS(self.dataframe, timeperiod=100, nbdevup=2.0, nbdevdn=2.0, matype=0)
        if(self.dataframe['open'][len(self.dataframe)-1] < BBANDS['lowerband'][len(BBANDS)-1] and BBANDS['lowerband'][len(BBANDS)-1] < self.dataframe['close'][len(self.dataframe)-1]):
            return "buy"
        elif(self.dataframe['open'][len(self.dataframe)-1] > BBANDS['upperband'][len(BBANDS)-1] and BBANDS['upperband'][len(BBANDS)-1] > self.dataframe['close'][len(self.dataframe)-1]):
            return "sell"
        else:
            return "neutral"

    def MA(self):
        if(self.EMA() == "buy" and self.SMA() == "buy"):
            return "buy"
        elif(self.EMA() == "sell" and self.SMA() == "sell"):
            return "sell"
        else:
            return "neutral"

    def EMA(self):
        buy = 0
        sell = 0
        for period in [5,10,20]:
            real = tb.EMA(self.dataframe, timeperiod=period)
            value = real[len(real)-1]
            price = self.dataframe['close'][len(self.dataframe) - 1]
            if (value > price):
                sell = sell +1
            elif (value < price):
                buy = buy + 1
        if (sell == 3):
            return "sell"
        elif (buy == 3):
            return "buy"
        else:
            return "neutral"

    def SMA(self):
        buy = 0
        sell = 0
        for period in [5,10,20]:
            real = tb.SMA(self.dataframe, timeperiod=period)
            value = real[len(real)-1]
            price = self.dataframe['close'][len(self.dataframe) - 1]
            if (value > price):
                sell = sell +1
            elif (value < price):
                buy = buy + 1
        if (sell == 3):
            return "sell"
        elif (buy == 3):
            return "buy"
        else:
            return "neutral"

    def SAR(self):
        SAR = tb.SAR(self.dataframe, acceleration=0, maximum=0)
        if (self.dataframe['open'][len(self.dataframe) - 1] > SAR[len(SAR) - 1]):
            return "buy"
        elif (self.dataframe['open'][len(self.dataframe) - 1] < SAR[len(SAR) - 1]):
            return "sell"
        else:
            return "neutral"

    def VMA(self):
        real = tb.WMA(self.close, timeperiod=30)

    def ADX(self):
        ADX = tb.ADX(self.dataframe, timeperiod=14)
        value = ADX[len(ADX) - 1]
        if(value > adxLimit):
            return "strong"
        elif (value < adxLimit):
            return "weak"
        else:
            return "neutral"

    def CCI(self):
        CCI = tb.CCI(self.dataframe, timeperiod=20)
        value = CCI[len(CCI) -1]
        preValue = CCI[len(CCI) -2]
        if (value > cciUpperLimit):
            return "sell"
        elif (value < cciLowerLimit):
            return "buy"
        else:
            return "neutral"

    def MACD(self):
        MACD = tb.MACD(self.dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        value = MACD['macd'][len(MACD)-1]
        signal = MACD['macdsignal'][len(MACD)-1]
        if (value > signal):
            return "buy"
        elif (value < signal):
            return "sell"
        else:
            return "neutral"

    def MOM(self):
        MOM = tb.MOM(self.dataframe, timeperiod=10)
        value = MOM[len(MOM) - 1]
        oldValue = MOM[len(MOM) - 2]
        if(value > oldValue):
            return "buy"
        else:
            return "sell"

    def RSI(self):
        RSI = tb.RSI(self.dataframe, timeperiod=14)
        value = RSI[len(RSI) - 1]
        if (value > rsiUpperLimit):
            return "sell"
        elif (value < rsiLowerLimit):
            return "buy"
        else:
            return "neutral"

    def STOCH(self):
        STOCH = tb.STOCH(self.dataframe, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        slowk = STOCH["slowk"][len(STOCH)-1]
        slowd = STOCH["slowd"][len(STOCH)-1]
        oldSlowk = STOCH["slowk"][len(STOCH)-2]
        oldSlowd = STOCH["slowd"][len(STOCH)-2]

        if (slowk > 80):
            return "overbought"
        elif (slowk > 60):
            return "buy"
        elif (slowk < 20):
            return "oversold"
        elif (slowk < 40):
            return "sell"
        else:
            return "neutral"

    def STOCHF(self):
        STOCHF= tb.STOCHF(self.dataframe, fastk_period=5, fastd_period=3, fastd_matype=0)
        fastk = STOCHF["fastk"][len(STOCHF) - 1]
        fastd = STOCHF["fastd"][len(STOCHF) - 1]
        oldFastk = STOCHF["fastk"][len(STOCHF) - 2]
        oldFastd = STOCHF["fastd"][len(STOCHF) - 2]

        if (fastk > 80):
            return "overbought"
        elif (fastk > 60):
            return "buy"
        elif (fastk < 20):
            return "oversold"
        elif (fastk < 40):
            return "sell"
        else:
            return "neutral"

    def STOCHRSI(self):
        STOCHRSI= tb.STOCHRSI(self.dataframe, fastk_period=5, fastd_period=3, fastd_matype=0)
        fastk = STOCHRSI["fastk"][len(STOCHRSI) - 1]
        fastd = STOCHRSI["fastd"][len(STOCHRSI) - 1]
        oldFastk = STOCHRSI["fastk"][len(STOCHRSI) - 2]
        oldFastd = STOCHRSI["fastd"][len(STOCHRSI) - 2]

        if (fastk > 80):
            return "overbought"
        elif (fastk > 60):
            return "buy"
        elif (fastk < 20):
            return "oversold"
        elif (fastk < 40):
            return "sell"
        else:
            return "neutral"

    def ULTOSC(self):
        REAL = tb.ULTOSC(self.dataframe, timeperiod1=7, timeperiod2=14, timeperiod3=28)
        value = REAL[len(REAL) - 1]
        if (value > 70):
            return "buy"
        elif (value < 40):
            return "sell"
        else:
            return "neutral"

