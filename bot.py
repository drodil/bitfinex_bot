from datetime import datetime
import time
import os
import json
import random
import logging

import numpy as np
import pandas as pd

import indicator as ind
import api as bitfinex


class Bot:
    # Traded coin pairs
    coin_pairs = ['btcusd', 'ethusd', 'iotusd', 'xrpusd', 'ltcusd',
                  'zecusd', 'dshusd', 'eosusd', 'neousd', 'etcusd',
                  'xtzusd', 'ampusd']
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
    # Quiet time after sell not to buy the same coin (in minutes)
    quiet_time = 30

    public_v1 = bitfinex.PublicV1()
    public_v2 = bitfinex.PublicV2()
    buy_history = dict()
    sell_history = dict()
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
    trading_v2 = bitfinex.TradingV2(message[0], message[1])

    def __init__(self):
        self._refresh_balance()

        gcloud_logging = True
        try:
            import google.cloud.logging
            from google.cloud.logging.handlers import CloudLoggingHandler
        except ImportError:
            gcloud_logging = False

        handlers = []

        if gcloud_logging:
            client = google.cloud.logging.Client()
            ghandler = CloudLoggingHandler(client)
            ghandler.setLevel(logging.INFO)
            handlers.append(ghandler)

        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        shandler = logging.StreamHandler()
        shandler.setFormatter(fmt)
        shandler.setLevel(logging.DEBUG)
        handlers.append(shandler)

        fhandler = logging.handlers.TimedRotatingFileHandler("bot.log", when="d", interval=1, backupCount=14)
        fhandler.setFormatter(fmt)
        fhandler.setLevel(logging.DEBUG)
        handlers.append(fhandler)

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s:%(message)s",
            handlers=handlers
        )

        if not os.path.isfile("history.json"):
            self._save_history()

        with open('history.json', 'r') as fp:
            self.buy_history = json.load(fp)

        self.buy_history = {key: val for key, val in self.buy_history.items() if key in self.coin_pairs}

        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        logging.info("Bot initialized")

    def run(self):
        logging.info("Bot is running")
        logging.debug("Currently available currencies: " + ", ".join(self.available_currencies))

        while True:
            try:
                for coin in self.coin_pairs:
                    self._handle_coin(coin)
            except Exception as ex:
                time.sleep(75.0)
                logging.error(ex)
                pass

    def _handle_coin(self, coin):
        decision_point = len(self.interval) - 1
        break_point = len(self.interval) - decision_point
        buy = 0
        force_buy = 0
        force_sell = 0
        sell = 0
        df = None

        for i, minute in enumerate(self.interval):
            array = np.array(self.public_v2.candles(minute, "t" + coin.upper(), "hist"))[::-1]
            df = pd.DataFrame(data=array[:, 0:6],
                              columns=["date", "open", "close", "high", "low", "volume"])

            indicator = ind.Indicator(df)
            signal = indicator.rate(coin, minute)

            time.sleep(2.0)
            if signal >= 1:
                if coin in self.available_currencies and i >= break_point and signal < 2:
                    break
                buy = buy + 1
                if signal >= 2:
                    force_buy = force_buy + 1
            elif signal <= -1:
                if coin not in self.available_currencies and i >= break_point and signal < 2:
                    break
                sell = sell + 1
                if signal <= -2:
                    force_sell = force_sell + 1

            if buy == 0 and sell == 0 and i >= break_point:
                time.sleep(2.0)
                break

        if df is None or 'close' not in df:
            logging.error(coin + " is missing price data")
            return

        price = float(df["close"][len(df) - 1])
        if coin in self.buy_history and coin in self.available_currencies:
            if price > self.buy_history[coin] * self.profit_multiplier:
                logging.debug(coin + " IS profitable with price " + str(price) + " > " + str(
                    self.buy_history[coin] * self.profit_multiplier))
                force_sell = force_sell + 1
            else:
                logging.debug(coin + " is NOT profitable with price " + str(price) + " < " + str(
                    self.buy_history[coin] * self.profit_multiplier))

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
            if self.buy_attempts[coin] > 6:
                logging.debug(coin + " it's too late to catch the buy train")
                buy = 0
                force_buy = 0

        logging.debug(
            coin + " decision: B: " + str(buy) + " FB: " + str(force_buy) + " S: " + str(sell) + " FS: " + str(
                force_sell))
        if buy >= decision_point or force_buy >= decision_point:
            ask = self._get_ask(coin, price)
            bought = self._buy_coin(coin, str(ask), force_buy >= decision_point)
            if not bought:
                if coin not in self.buy_attempts:
                    self.buy_attempts[coin] = 0
                elif self.buy_attempts[coin] < 10:
                    self.buy_attempts[coin] = self.buy_attempts[coin] + 1
            elif coin in self.buy_attempts:
                del self.buy_attempts[coin]

        elif sell >= decision_point or force_sell >= decision_point:
            bid = self._get_bid(coin, price)
            sold = self._sell_coin(coin, str(bid), force_sell >= decision_point)
            if sold and coin in self.buy_attempts:
                self.buy_attempts[coin] = self.buy_attempts[coin] - 1
        else:
            if coin in self.buy_attempts:
                self.buy_attempts[coin] = self.buy_attempts[coin] - 1

        if coin in self.buy_attempts and self.buy_attempts[coin] <= 0:
            del self.buy_attempts[coin]

    def _buy_coin(self, coin, price, force):
        if coin not in self.available_currencies and coin in self.sell_history:
            now = datetime.now()
            diff = now - self.sell_history[coin]
            minutes = diff.seconds / 60
            if minutes > self.quiet_time:
                logging.debug(coin + " not buying as it's on quiet period")
                return False
            del self.sell_history[coin]

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
            logging.debug(coin + " buy attempt")
            if (len(self.available_currencies) >= self.max_number_of_coins) and force is True:
                # If not enough USD, sell some other coin to buy more
                if self.USD < self.min_spend_in_usd:
                    sorted_scores = {k: v for k, v in sorted(self.latest_score.items(), key=lambda x: x[1])}
                    sold = False
                    for key, value in sorted_scores.items():
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
                        logging.debug(coin + " buy failed as could not sell another coin")
                        return False
                return self._handle_buy(coin, price)
            elif len(self.available_currencies) < self.max_number_of_coins:
                return self._handle_buy(coin, price)
        else:
            logging.debug(coin + " not buying as we already have it and no indication to buy more")
        return False

    def _handle_buy(self, coin, price):
        amount = min(self.max_spend_in_usd, max(self.min_spend_in_usd, int(self.USD))) / float(price)
        if amount >= 0.0001 and self.USD > self.min_spend_in_usd:
            logging.info(coin + " buy of " + str(amount) + " at " + str(price))
            resp = self.trading_v1.new_order(coin, amount, float(price), "buy", "exchange market",
                                             aff_code=self.aff_code, exchange='bitfinex',
                                             use_all_available=False)
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
            logging.debug(coin + " buy failed: not enough USD (" + str(self.USD) + ")")
        return False

    def _sell_coin(self, coin, price, force):
        self._refresh_balance()
        multiplier = self.profit_multiplier
        if force is True:
            logging.debug(coin + " is looking bad, trying to break even..")
            multiplier = self.break_even_multiplier

        if coin in self.available_currencies:
            logging.debug(coin + " selling attempt")
            amount = "0"
            for balances in self.balance:
                if balances["currency"] == coin:
                    amount = balances["amount"]

            if coin in self.buy_history:
                if float(price) < self.buy_history[coin] * multiplier:
                    logging.debug(
                        coin + " not selling CP: " + str(price) + " BP: " + str(self.buy_history[coin]) + " PP: " + str(
                            self.buy_history[coin] * multiplier))
                    return False

            return self._handle_buy(coin, amount, price)
        else:
            logging.warning(coin + " sell failed as we do not have it")
        return False

    def _handle_sell(self, coin, amount, price):
        logging.info(coin + " sell of " + str(amount) + " at " + str(price))
        resp = self.trading_v1.new_order(coin, amount, price, "sell", "exchange market", aff_code=self.aff_code,
                                         exchange='bitfinex', use_all_available=True)
        if resp is not None:
            if coin in self.buy_history:
                buy_price = self.buy_history[coin]
                buy_value = float(buy_price) * float(amount) * float(1 - self.trade_fee_percentage)
                sell_value = float(amount) * float(price) * float(1 - self.trade_fee_percentage)
                logging.info(coin + " sell made profit of " + str(sell_value - buy_value) + "USD")
            self._log_action("SELL", coin, price)
            self._refresh_balance()
            self.sell_history[coin] = datetime.now()
            if coin in self.buy_history:
                del self.buy_history[coin]
                self._save_history()
            return True
        else:
            logging.error(coin + " sell failed!")
        return False

    def _refresh_balance(self):
        balance = self.trading_v1.balances()
        if balance is not None:
            self.available_currencies = []
            self.balance = []
            for balances in balance:
                if balances["currency"] == "usd":
                    self.USD = float(balances["amount"])
                elif float(balances["amount"]) > 0.0001:
                    balances["currency"] = balances["currency"] + "usd"
                    self.available_currencies.append(balances["currency"])
                    self.balance.append(balances)
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


def main():
    bot = Bot()
    bot.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted by user!')
