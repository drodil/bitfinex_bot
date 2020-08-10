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
    # Traded coin pairs
    coin_pairs = ['btcusd', 'ethusd', 'iotusd', 'xrpusd', 'ltcusd',
                'zecusd', 'dshusd', 'eosusd', 'neousd', 'etcusd',
                'xtzusd', 'ampusd' ]
    # Maximum spend in USD for single buy
    max_spend_in_usd = 175
    # Minimu spend in USD for single buy
    min_spend_in_usd = 10
    # Maximum number of different coins
    max_number_of_coins = 7
    # Candle intervals to fetch
    interval = ["1m", "15m", "30m", "5m"]
    # Trade fees in percentage
    trade_fee_percentage = 0.002
    # Desired profit percentage
    profit_multiplier = 1.006
    # Multiplier to break even with fees
    break_even_multiplier = 1 + (trade_fee_percentage * 2)

    public_v1 = bitfinex.PublicV1()
    public_v2 = bitfinex.PublicV2()
    buy_history = dict()
    buy_attempts = dict()
    latest_price = dict()
    latest_score = dict()
    aff_code = "RQr8dEzNJ"
    USD = 0
    balance = []
    available_currencies = []

    log_file = open("trades.txt", "a+")
    f = open("account_info.txt", 'r')
    message = f.read().split("\n")
    trading_v1 = bitfinex.TradingV1(message[0], message[1])
    trading_v2 = bitfinex.Trading_v2(message[0], message[1])

    ds = datastore.Client()

    def __init__(self):
        self._refresh_balance()

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
            self._save_history()

        with open('history.json', 'r') as fp:
            self.buy_history = json.load(fp)

        self.buy_history = {key:val for key, val in self.buy_history.items() if key in self.coin_pairs}

        logging.info("Bot initialized")

    def run(self):
        logging.info("Bot is running")
        decision_point = len(self.interval) - 1
        break_point = len(self.interval) - decision_point

        logging.debug("Currently available currencies: " + ", ".join(self.available_currencies))

        while True:
            for coin in self.coin_pairs:
                buy = 0
                force_buy = 0
                force_sell = 0
                sell = 0

                for i, minute in enumerate(self.interval):
                    try:
                        array = np.array(self.public_v2.candles(minute, "t" + coin.upper(), "hist"))[::-1]
                        df = pd.DataFrame(data=array[:,0:6],
                                          columns=["date", "open", "close", "high", "low", "volume"])

                        indicator = Indicator(df)
                        signal = indicator.rate(coin, minute)

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
                if coin in self.buy_history and coin in self.available_currencies:
                    if price > self.buy_history[coin] * self.profit_multiplier:
                        logging.debug(coin + " IS profitable with price " + str(price) + " > " + str(self.buy_history[coin] * self.profit_multiplier))
                    else:
                        logging.debug(coin + " is NOT profitable with price " + str(price) + " < " + str(self.buy_history[coin] * self.profit_multiplier))

                self.latest_score[coin] = sell
                if coin in self.latest_price:
                    if self.latest_price[coin] > price:
                        logging.debug(coin + " price is going down " + str(self.latest_price[coin]) + " -> " + str(price))
                        force_sell = force_sell + 1
                    if self.latest_price[coin] < price:
                        logging.debug(coin + " price is going up " + str(self.latest_price[coin]) + " -> " + str(price))
                        force_buy = force_buy + 1

                if sell == len(self.interval):
                    force_sell = force_sell + 1
                if buy == len(self.interval):
                    force_buy = force_buy + 1

                self.latest_price[coin] = price
                if buy == len(self.interval):
                    force_buy = force_buy + 1
                if sell == len(self.interval):
                    force_sell = force_sell + 1

                if coin in self.buy_attempts:
                    if self.buy_attempts[coin] > 8:
                        logging.debug(coin + " it's too late to catch the buy train")
                        buy = 0
                        force_buy = 0

                logging.debug(coin + " decision: B: " + str(buy) + " FB: " + str(force_buy) + " S: " + str(sell) + " FS: " + str(force_sell))
                if(buy >= decision_point or force_buy >= decision_point):
                    ask = self._get_ask(coin, price)
                    bought = self._buy_coin(coin, str(ask), force_buy >= decision_point)
                    if not bought:
                        if coin not in self.buy_attempts:
                            self.buy_attempts[coin] = 0
                        else:
                            self.buy_attempts[coin] = self.buy_attempts[coin] + 1
                    elif coin in self.buy_attempts:
                        del self.buy_attempts[coin]

                elif(sell >= decision_point or force_sell >= decision_point):
                    bid = self._get_bid(coin, price)
                    sold = self._sell_coin(coin, str(bid), force_sell >= decision_point)
                    if coin in self.buy_attempts:
                        del self.buy_attempts[coin]
                else:
                    if coin in self.buy_attempts:
                        del self.buy_attempts[coin]

    def _buy_coin(self, coin, price, force):
        if force is True and coin in self.available_currencies:
            if coin in self.buy_history and coin in self.available_currencies:
                if float(price) < self.buy_history[coin] * self.profit_multiplier:
                    logging.debug(coin + " not buying more as it is not profitable yet")
                    return False
            logging.debug(coin + " is on good run, trying to buy more")
        elif force is True:
            logging.debug(coin + " is on good run, trying to force buy")

        self._refresh_balance()
        if coin not in self.available_currencies or force is True:
            logging.info(coin + " buy attempt")
            if (len(self.available_currencies) >= self.max_number_of_coins):
                # If not enough USD, sell some other coin to buy more
                if self.USD < self.min_spend_in_usd:
                    sortedScores = {k: v for k, v in sorted(self.latest_score.items(), key=lambda x: x[1])}
                    sold = False
                    for key, value in sortedScores.items():
                        if key in self.available_currencies:
                            if key in self.latest_price and value > 1:
                                logging.debug(key + " is tried to swap to " + coin)
                                bid = self._get_bid(key, self.latest_price[key])
                                sold = self._sell_coin(key, bid, False)
                                if sold:
                                    time.sleep(10.0)
                                    self._refresh_balance()
                                    break

                    if sold is not True:
                        logging.info(coin + " buy failed as could not sell another coin")
                        return False

                amount = min(self.max_spend_in_usd, max(self.min_spend_in_usd, Decimal(self.USD))) / Decimal(price)
                if amount >= 0.0001:
                    logging.info(coin + " buy of " + str(amount) + " at " + str(price))
                    resp = self.trading_v1.new_order(coin, amount, price, "buy", "exchange market", aff_code=self.aff_code, exchange='bitfinex', use_all_available=False)

                    if resp is not None:
                        hist = float(price)
                        if coin in self.buy_history:
                            hist = max(hist, self.buy_history[coin])
                        self.buy_history[coin] = hist
                        self._save_history()
                        self._log_action("BUY", coin, price)
                        self._refresh_balance()
                        return True
                    else:
                        logging.error(coin + " buy failed!")
                else:
                    logging.info(coin + " buy failed: not enough USD (" + str(self.USD) + ")")
            elif len(self.available_currencies) < self.max_number_of_coins:
                amount = min(self.max_spend_in_usd, max(self.min_spend_in_usd, Decimal(self.USD))) / Decimal(price)
                if amount >= 0.0001:
                    logging.info(coin + " buy of " + str(amount) + " at " + str(price))
                    resp = self.trading_v1.new_order(coin, amount, Decimal(price), "buy", "exchange market", aff_code=self.aff_code, exchange='bitfinex', use_all_available=False)
                    if resp is not None:
                        hist = float(price)
                        if coin in self.buy_history:
                            hist = max(hist, self.buy_history[coin])
                        self.buy_history[coin] = hist
                        self._save_history()
                        self._log_action("BUY", coin, price)
                        self._refresh_balance()
                        return True
                    else:
                        logging.error(coin + " buy failed!")
                else:
                    logging.info(coin + " buy failed: not enough USD (" + str(self.USD) + ")")
        else:
            logging.info(coin + " not buying as we already have it and no indication to buy more")
        return False

    def _sell_coin(self, coin, price, force):
        self._refresh_balance()
        multiplier = self.profit_multiplier
        if force is True:
            logging.debug(coin + " is looking bad, trying to break even..")
            multiplier = self.break_even_multiplier

        if (coin in self.available_currencies):
            logging.info(coin + " selling attempt")
            amount = "0"
            sell = True
            for dict in self.balance:
                if dict["currency"] == coin:
                    amount = dict["amount"]

            if coin in self.buy_history:
                if float(price) < self.buy_history[coin] * multiplier:
                    logging.info(coin + " not selling CP: " + str(price) + " BP: " + str(self.buy_history[coin]) + " PP: " + str(self.buy_history[coin] * multiplier))
                    sell = False

            if sell == True:
                logging.info(coin + " sell of " + str(amount) + " at " + str(price))
                resp = self.trading_v1.new_order(coin, amount, price, "sell", "exchange market", aff_code=self.aff_code, exchange='bitfinex', use_all_available=True)
                if resp is not None:
                    if coin in self.buy_history:
                        buyPrice = self.buy_history[coin]
                        buyValue = float(buyPrice) * float(amount) * float(1 - self.trade_fee_percentage)
                        sellValue = float(amount) * float(price) * float(1 - self.trade_fee_percentage)
                        logging.info(coin + " sell made profit of " + str(sellValue - buyValue) + "USD")
                    self._log_action("SELL", coin, price)
                    self._refresh_balance()
                    if coin in self.buy_history:
                        del self.buy_history[coin]
                        self._save_history()
                    return True
                else:
                    logging.error(coin + " sell failed!")
        else:
            logging.warning(coin + " sell failed as we do not have it")
        return False

    def _refresh_balance(self):
        balance = self.trading_v1.balances()
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

    def _save_history(self):
        with open("history.json", "w") as fp:
            json.dump(self.buy_history, fp)

    def _log_action(self, action, coin, price):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        self.log_file.write(dt_string + "\t" + action + "\t" + coin + "\t" + str(price) + "\n")

    def _get_bid(self, coin, default):
        resp = self.public_v1.ticker(coin)
        if 'bid' in resp:
            return float(resp['bid'])
        return default

    def _get_ask(self, coin, default):
        resp = self.public_v1.ticker(coin)
        if 'ask' in resp:
            return float(resp['ask'])
        return default

bot = Bot()
bot.run()
