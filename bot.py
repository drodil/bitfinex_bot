from datetime import datetime
import time
import os
import sys
import json
import random
import logging
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler
from google.cloud import datastore
from decimal import Decimal

import bitfinex.bitfinex as bitfinex
import numpy as np
import pandas as pd
from bitfinex_bot.Indicator import Indicator


class Bot:
    coinPairs = ['btcusd', 'ethusd', 'iotusd', 'xrpusd', 'ltcusd',
                'zecusd', 'dshusd', 'eosusd', 'neousd', 'etcusd', 
                'xtzusd', 'ampusd' ]

    publicV1 = bitfinex.PublicV1()
    publicV2 = bitfinex.PublicV2()

    buyHistory = dict()
    buyAttempts = dict()
    latestPrice = dict()
    latestScore = dict()
    affCode = "RQr8dEzNJ"

    log_file = open("trades.txt", "a+")
    f = open("account_info.txt", 'r')
    message = f.read().split("\n")

    tradingV1 = bitfinex.TradingV1(message[0], message[1])
    tradingV2 = bitfinex.Trading_v2(message[0], message[1])

    # parameters

    maxSpendInUSD = 175
    minSpendInUSD = 10
    maxNumberOfCurrencies = 7
    interval = ["1m", "15m", "30m", "5m"]
    commission = 0.002
    profitMultiplier = 1.006
    breakEvenMultiplier = 1 + (commission * 2)

    ds = datastore.Client()

    def __init__(self):

        self.USD = 0  # available USD dollars
        self.balance = []  # shows currencies with amounts(0.0 currencies are also included)
        self.available_currencies = []  # shows only available currencies
        self.refreshBalance()

        client = google.cloud.logging.Client()
        ghandler = CloudLoggingHandler(client)
        ghandler.setLevel(logging.INFO)

        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        shandler = logging.StreamHandler()
        shandler.setFormatter(fmt)
        shandler.setLevel(logging.DEBUG)

        fhandler = logging.handlers.TimedRotatingFileHandler("bot.log", when="d", interval=1, backupCount=14)
        fhandler.setFormatter(fmt)
        fhandler.setLevel(logging.DEBUG)

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s:%(message)s",
            handlers=[
                shandler,
                fhandler,
                ghandler
            ]
        ) 

        if os.path.isfile("history.json") != True:
            self.save_history()
        
        with open('history.json', 'r') as fp:
            self.buyHistory = json.load(fp)

        self.buyHistory = {key:val for key, val in self.buyHistory.items() if key in self.coinPairs} 

        logging.info("Bot initialized")

    def learn(self):
        for coin in self.coinPairs:
            array = np.array(self.publicV2.candles("1M", "t" + coin.upper(), "hist"))[::-1]
            df = pd.DataFrame(data=array[:,1:6],
                              columns=["open", "close", "high", "low", "volume"])
            # https://blog.quantinsti.com/trading-using-machine-learning-python/
            time.sleep(5.0)

    def persist_candles(self, coin, period, candles):
        key = datastore.Key('candle', 1234)
        entity = datastore.Entity(key)
        entity['coin'] = coin
        entity['period'] = period
        entity['created'] = datetime.now()
        entity['candles'] = candles
        self.ds.put(entity)
 
    def run(self):
        logging.info("Bot is running")
        decision_point = len(self.interval) - 1
        break_point = len(self.interval) - decision_point

        logging.debug("Currently available currencies: " + ", ".join(self.available_currencies))

        #self.learn();

#        history = None

        while True:
#            history = self.publicV2.tickers(self.available_currencies)
#            print(history)

            btc_signals = {}
            for coin in self.coinPairs:
                buy = 0
                force_buy = 0
                force_sell = 0
                sell = 0

                for i, minute in enumerate(self.interval):
                    try:
                        array = np.array(self.publicV2.candles(minute, "t" + coin.upper(), "hist"))[::-1]
                        df = pd.DataFrame(data=array[:,0:6],
                                          columns=["date", "open", "close", "high", "low", "volume"])

#                        self.persist_candles(coin, minute, array)
                        indicator = Indicator(df)
                        signal = indicator.rate(coin, minute)
                        if coin == 'btcusd':
                            btc_signals[minute] = signal
                        elif minute in btc_signals:
                            to_add = btc_signals[minute] / 2
                            #print("Following BTC with " + str(to_add))
                            #signal = signal + to_add

                        time.sleep(2.0)
                        if (signal >= 1):
                            if coin in self.available_currencies and i >= break_point and signal < 2:
                                break
                            buy = buy + 1
                            if signal >= 2:
                                force_buy = force_buy + 1
                        elif (signal <= -1):
                            if coin not in self.available_currencies and i >= break_point and signal < 2:
                                break
                            sell = sell + 1
                            if signal <= -2:
                                force_sell = force_sell + 1

                    except Exception as ex:
                        time.sleep(75.0)
                        logging.error(ex)
                        pass

                    if buy == 0 and sell == 0 and i >= break_point:
                        time.sleep(2.0)
                        break

                if "close" not in df:
                    logging.error(coin + " is missing price data")
                    continue

                price = float(df["close"][len(df) - 1]) 
                if coin in self.buyHistory and coin in self.available_currencies:
                    if price > self.buyHistory[coin] * self.profitMultiplier:
                        logging.debug(coin + " IS profitable with price " + str(price) + " > " + str(self.buyHistory[coin] * self.profitMultiplier))
                    else:
                        logging.debug(coin + " is NOT profitable with price " + str(price) + " < " + str(self.buyHistory[coin] * self.profitMultiplier))

                self.latestScore[coin] = sell
                if coin in self.latestPrice:
                    if self.latestPrice[coin] > price:
                        logging.debug(coin + " price is going down " + str(self.latestPrice[coin]) + " -> " + str(price))
                        force_sell = force_sell + 1
                    if self.latestPrice[coin] < price:
                        logging.debug(coin + " price is going up " + str(self.latestPrice[coin]) + " -> " + str(price))
                        force_buy = force_buy + 1

                if sell == len(self.interval):
                    force_sell = force_sell + 1
                if buy == len(self.interval):
                    force_buy = force_buy + 1

                self.latestPrice[coin] = price 
                if buy == len(self.interval):
                    force_buy = force_buy + 1
                if sell == len(self.interval):
                    force_sell = force_sell + 1

                if coin in self.buyAttempts:
                    if self.buyAttempts[coin] > 8:
                        logging.debug(coin + " it's too late to catch the buy train")
                        buy = 0
                        force_buy = 0

                logging.debug(coin + " decision: B: " + str(buy) + " FB: " + str(force_buy) + " S: " + str(sell) + " FS: " + str(force_sell)) 
                if(buy >= decision_point or force_buy >= decision_point):
                    ask = self.get_ask(coin, price)
                    bought = self.buyCoin(coin, str(ask), force_buy >= decision_point)
                    if not bought:
                        if coin not in self.buyAttempts:
                            self.buyAttempts[coin] = 0
                        else:
                            self.buyAttempts[coin] = self.buyAttempts[coin] + 1
                    elif coin in self.buyAttempts:
                        del self.buyAttempts[coin]
                        
                elif(sell >= decision_point or force_sell >= decision_point):
                    bid = self.get_bid(coin, price)
                    sold = self.sellCoin(coin, str(bid), force_sell >= decision_point)
                    if coin in self.buyAttempts:
                        del self.buyAttempts[coin]
                else:
                    if coin in self.buyAttempts:
                        del self.buyAttempts[coin]

    def buyCoin(self, coin, price, force):
        if force is True and coin in self.available_currencies:
            if coin in self.buyHistory and coin in self.available_currencies:
                if float(price) < self.buyHistory[coin] * self.profitMultiplier:
                    logging.debug(coin + " not buying more as it is not profitable yet")
                    return False
            logging.debug(coin + " is on good run, trying to buy more")
        elif force is True:
            logging.debug(coin + " is on good run, trying to force buy")

        self.refreshBalance()
        if coin not in self.available_currencies or force is True:
            logging.info(coin + " buy attempt")
            if (len(self.available_currencies) >= self.maxNumberOfCurrencies):
                # If not enough USD, sell some other coin to buy more
                if self.USD < self.minSpendInUSD:
                    sortedScores = {k: v for k, v in sorted(self.latestScore.items(), key=lambda x: x[1])} 
                    sold = False
                    for key, value in sortedScores.items():
                        if key in self.available_currencies:
                            if key in self.latestPrice and value > 1:
                                logging.debug(key + " is tried to swap to " + coin)
                                bid = self.get_bid(key, self.latestPrice[key])
                                sold = self.sellCoin(key, bid, False)
                                if sold:
                                    time.sleep(10.0)
                                    self.refreshBalance()
                                    break

                    if sold is not True:
                        logging.info(coin + " buy failed as could not sell another coin")
                        return False

                amount = min(self.maxSpendInUSD, max(self.minSpendInUSD, Decimal(self.USD))) / Decimal(price)
                if amount >= 0.0001:
                    logging.info(coin + " buy of " + str(amount) + " at " + str(price))
                    resp = self.tradingV1.new_order(coin, amount, price, "buy", "exchange market", aff_code=self.affCode, exchange='bitfinex', use_all_available=False)
                    
                    if resp is not None:
                        hist = float(price)
                        if coin in self.buyHistory:
                            hist = max(hist, self.buyHistory[coin])
                        self.buyHistory[coin] = hist
                        self.save_history()
                        self.log_action("BUY", coin, price)
                        self.refreshBalance()
                        return True
                    else:
                        logging.error(coin + " buy failed!")
                else:
                    logging.info(coin + " buy failed: not enough USD (" + str(self.USD) + ")")
            elif len(self.available_currencies) < self.maxNumberOfCurrencies:
                amount = min(self.maxSpendInUSD, max(self.minSpendInUSD, Decimal(self.USD))) / Decimal(price)
                if amount >= 0.0001:
                    logging.info(coin + " buy of " + str(amount) + " at " + str(price))
                    resp = self.tradingV1.new_order(coin, amount, Decimal(price), "buy", "exchange market", aff_code=self.affCode, exchange='bitfinex', use_all_available=False)
                    if resp is not None:
                        hist = float(price)
                        if coin in self.buyHistory:
                            hist = max(hist, self.buyHistory[coin])
                        self.buyHistory[coin] = hist
                        self.save_history()
                        self.log_action("BUY", coin, price)
                        self.refreshBalance()
                        return True
                    else:
                        logging.error(coin + " buy failed!")
                else:
                    logging.info(coin + " buy failed: not enough USD (" + str(self.USD) + ")")
        else:
            logging.info(coin + " not buying as we already have it and no indication to buy more")
        return False

    def sellCoin(self, coin, price, force):
        self.refreshBalance()
        multiplier = self.profitMultiplier
        if force is True:
            logging.debug(coin + " is looking bad, trying to break even..")
            multiplier = self.breakEvenMultiplier

        if (coin in self.available_currencies):
            logging.info(coin + " selling attempt")
            amount = "0"
            sell = True
            for dict in self.balance:
                if dict["currency"] == coin:
                    amount = dict["amount"]

            if coin in self.buyHistory:
                if float(price) < self.buyHistory[coin] * multiplier: 
                    logging.info(coin + " not selling CP: " + str(price) + " BP: " + str(self.buyHistory[coin]) + " PP: " + str(self.buyHistory[coin] * multiplier))
                    sell = False

            if sell == True:
                logging.info(coin + " sell of " + str(amount) + " at " + str(price))
                resp = self.tradingV1.new_order(coin, amount, price, "sell", "exchange market", aff_code=self.affCode, exchange='bitfinex', use_all_available=True)
                if resp is not None:
                    if coin in self.buyHistory:
                        buyPrice = self.buyHistory[coin]
                        buyValue = float(buyPrice) * float(amount) * float(1 - self.commission)
                        sellValue = float(amount) * float(price) * float(1 - self.commission)
                        logging.info(coin + " sell made profit of " + str(sellValue - buyValue) + "USD")
                    self.log_action("SELL", coin, price)
                    self.refreshBalance()
                    if coin in self.buyHistory:
                        del self.buyHistory[coin]
                        self.save_history()
                    return True
                else:
                    logging.error(coin + " sell failed!")
        else:
            logging.warning(coin + " sell failed as we do not have it")
        return False

    def refreshBalance(self):
        balance = self.tradingV1.balances()
        if(balance != None):
            self.available_currencies = []
            self.balance = []
            for dict in balance:
                if dict["currency"] == "usd":
                    self.USD = float(dict["amount"])
                elif (float(dict["amount"]) > 0.0001):
                    dict["currency"]= dict["currency"] + "usd"
                    self.available_currencies.append(dict["currency"])
                    self.balance.append(dict)
            random.shuffle(self.available_currencies)

    def save_history(self):
        with open("history.json", "w") as fp:
            json.dump(self.buyHistory, fp)
    
    def log_action(self, action, coin, price):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        self.log_file.write(dt_string + "\t" + action + "\t" + coin + "\t" + str(price) + "\n")

    def get_bid(self, coin, default):
        resp = self.publicV1.ticker(coin)
        if 'bid' in resp:
            return float(resp['bid'])
        return default

    def get_ask(self, coin, default):
        resp = self.publicV1.ticker(coin)
        if 'ask' in resp:
            return float(resp['ask'])
        return default

bot = Bot()
bot.run()
