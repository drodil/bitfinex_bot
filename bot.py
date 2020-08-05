from datetime import datetime
import time
import os
import json
import random
from decimal import Decimal

import bitfinex.bitfinex as bitfinex
import numpy as np
import pandas as pd
from bitfinex_bot.Indicator import Indicator


class Bot:
    coinPairs = ['btcusd', 'ethusd', 'iotusd', 'xrpusd', 'ltcusd',
                'zecusd', 'dshusd', 'eosusd', 'neousd', 'etcusd', 
                'xlmusd', 'xtzusd' ]

    publicV1 = bitfinex.PublicV1()
    publicV2 = bitfinex.PublicV2()

    buyHistory = {"ltcusd": 57.810, "eosusd": 3.0584, "neousd": 12.6, "algusd": 0.3178}
    latestPrice = {"dummy": 1.0}


    log_file = open("trades.txt", "a+")
    f = open("account_info.txt", 'r')
    message = f.read().split("\n")

    tradingV1 = bitfinex.TradingV1(message[0], message[1])
    tradingV2 = bitfinex.Trading_v2(message[0], message[1])

    # parameters

    maxSpendInUSD = 80
    maxNumberOfCurrencies = 5
    interval = ["1m", "30m", "15m", "5m"]
    sell_indications = []
    profitMultiplier = 1.006

    def __init__(self):

        self.USD = 0  # available USD dollars
        self.balance = []  # shows currencies with amounts(0.0 currencies are also included)
        self.available_currencies = []  # shows only available currencies
        self.refreshBalance()

        if os.path.isfile("history.json") != True:
            self.save_history()
        
        with open('history.json', 'r') as fp:
            self.buyHistory = json.load(fp)

        print("Bot initialized")

    def run(self):
        print("Bot is running")
        while True:
            btc_signals = {}
            for coin in self.coinPairs:
                buy = 0
                force_buy = 0
                sell = 0

                for minute in self.interval:
                    try:
                        array = np.array(self.publicV2.candles(minute, "t" + coin.upper(), "hist"))[::-1]
                        df = pd.DataFrame(data=array[:,0:6],
                                          columns=["date", "open", "close", "high", "low", "volume"])

                        indicator = Indicator(df)
                        signal = indicator.rate(coin, minute)
                        if coin == 'btcusd':
                            btc_signals[minute] = signal
                        elif minute in btc_signals:
                            to_add = btc_signals[minute] / 2
                            #print("Following BTC with " + str(to_add))
                            #signal = signal + to_add

                        time.sleep(15.0)
                        if (signal >= 1):
                            buy = buy + 1
                            if signal >= 2:
                                force_buy = force_buy + 1
                            elif coin in self.available_currencies:
                                break
                        elif (signal <= -1):
                            sell = sell + 1
                            if coin not in self.available_currencies:
                                break

                    except Exception as ex:
                        time.sleep(75.0)
                        print(ex)
                        pass

                    if sell == 0 and buy == 0:
                        break

                price = float(df["close"][len(df) - 1]) 
                if coin in self.buyHistory and coin in self.available_currencies:
                    if price > self.buyHistory[coin] * self.profitMultiplier:
                        print(coin + " is now profitable with price " + str(price))
                        sell = sell + 1
                    else:
                        print(coin + " is not profitable with price " + str(price))
                        sell = sell - 1

                self.latestPrice[coin] = price 
                decision_point = len(self.interval) - 1
                if(buy >= decision_point):
                    self.buyCoin(coin, str(price), force_buy == decision_point)
                elif(sell >= decision_point):
                    if coin in self.sell_indications:
                        self.sellCoin(coin, str(price))
                        self.sell_indications.remove(coin)
                    else:
                        self.sell_indications.append(coin)


    def buyCoin(self, coin, price, force):
        self.refreshBalance()
        if (coin not in self.available_currencies and force != True):
            print("Buying coin attempt: " + coin)
            print("Available currencies: " + str(self.available_currencies))
            if (len(self.available_currencies) >= self.maxNumberOfCurrencies) and force == True:
                print("More than", self.maxNumberOfCurrencies ,"currencies")
                coinToSell = str(random.choice(self.available_currencies))
                sold = False
                if coinToSell in self.latestPrice:
                    sold = self.sellCoin(coinToSell, self.latestPrice[coinToSell])
                    time.sleep(60.0)
                    self.refreshBalance()
                else:
                    print("No latest price available for " + coinToSell)

                amount = (min(self.maxSpendInUSD, Decimal(self.USD)) - 2) / Decimal(price)
                if sold and amount > 0:
                    print("Buying", amount, coin, "at", price)
                    resp = self.tradingV1.new_order(coin, amount, price, "buy", "exchange market", exchange='bitfinex', use_all_available=False)
                    
                    if resp is not None:
                        self.buyHistory[coin] = float(price)
                        self.save_history()
                        self.log_action("BUY", coin, price)
                        self.refreshBalance()
            elif len(self.available_currencies) < self.maxNumberOfCurrencies:
                amount = (min(self.maxSpendInUSD, Decimal(self.USD)) - 2) / Decimal(price)
                if amount > 0:
                    print("Buying", amount, coin, "at", price)
                    resp = self.tradingV1.new_order(coin, amount, Decimal(price), "buy", "exchange market", exchange='bitfinex', use_all_available=False)
                    if resp is not None:
                        self.buyHistory[coin] = float(price)
                        self.save_history()
                        self.log_action("BUY", coin, price)
                        self.refreshBalance()
                else:
                    print("Not enough USD (" + str(self.USD) + ") to buy " + coin)
            else:
                print("Keeping all as not enough indication to buy " + coin)

    def sellCoin(self, coin, price):
        self.refreshBalance()
        if (coin in self.available_currencies):
            print("Selling coin attempt: " + coin)
            print("Available currencies: " + str(self.available_currencies))
            amount = "0"
            sell = True
            for dict in self.balance:
                if dict["currency"] == coin:
                    amount = dict["amount"]

            if coin in self.buyHistory:
                if float(price) < self.buyHistory[coin] * self.profitMultiplier:
                    print("Not selling because it would be bad for business", price, self.buyHistory[coin] * self.profitMultiplier)
                    sell = False

            if sell == True:
                print("Selling", amount, coin, "at", price)
                resp = self.tradingV1.new_order(coin, amount, price, "sell", "exchange market", exchange='bitfinex', use_all_available=True)
                if resp is not None:
                    self.log_action("SELL", coin, price)
                    self.refreshBalance()
                    return True
        return False

    def refreshBalance(self):
        balance = self.tradingV1.balances()
        if(balance != None):
            self.available_currencies = []
            self.balance = []
            for dict in balance:
                if dict["currency"] == "usd":
                    self.USD = dict["amount"]
                elif (float(dict["amount"]) > 0.0001):
                    dict["currency"]= dict["currency"] + "usd"
                    self.available_currencies.append(dict["currency"])
                    self.balance.append(dict)
            self.available_currencies = self.sort(self.available_currencies)

    def sort(self, currency_list):
        index_currency_dict = {}
        res = []
        for currency in currency_list:
            index_currency_dict[self.coinPairs.index(currency)] = currency

        for key in sorted(index_currency_dict):
            res.append(index_currency_dict[key])

        return res

    def save_history(self):
        with open("history.json", "w") as fp:
            json.dump(self.buyHistory, fp)
    
    def log_action(self, action, coin, price):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        self.log_file.write(dt_string + "\t" + action + "\t" + coin + "\t" + str(price) + "\n")

bot = Bot()
bot.run()
