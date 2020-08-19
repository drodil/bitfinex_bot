# Bitfinex trading bot

Original idea: https://github.com/DorukKorkmaz/bitfinex-bot

This trading bot is using Bitfinex APIs to do automatic day-trading. It's main
purpose is to buy low and sell high before the value is going back down.

**DISCLAIMER: I will not take any responsibility for any money you might lose
using this bot. Use it at your own risk!**

## Requirements

TALib is used to calculate technical analysis for the cryptocoins. All
dependencies are included in the setup.py so you can use pip to install the bot.
Additionally Python 3.8 > is required.

```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
sudo ./configure
sudo make
sudo make install
```

```bash
cd bitfinex_bot/
pip3 install .
```

If you have errors during ta-lib installation, please see
https://github.com/mrjbq7/ta-lib

Additionally I have the bot running in [Google Cloud](https://cloud.google.com/)
VM and it's using the google-cloud-logging to log all buy and sell events. If
you do not want this, please remove the google cloud handler from the code.

## Usage

You should insert your Bitfinex API key and secret into
file **bitfinex_bot/account_info** in the following format:

```
<API Key>
<API Secret>
```

Modify the necessary parameters in the bot.py for your liking:

```python
# Traded coin pairs
coin_pairs = ['btcusd', 'ethusd', 'iotusd', 'xrpusd', 'ltcusd',
             'zecusd', 'dshusd', 'eosusd', 'neousd', 'etcusd',
             'xtzusd', 'ampusd' ]
# Maximum spend in USD for single buy
max_spend_in_usd = 175
# Minimum spend in USD for single buy
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
```

If you installed the bot via pip, please install it again after updating the
parameters.

Run the bot.py or 'bitfinex-bot' to start the bot.

## TODO

* Add the parameters to configuration file and load it from there on-fly
* Add command line arguments
* Use Bitfinex WebSocket API for better performance and API limiting
* Publish history of trades of my experiences with the bot

## Donate

If you like this project, please feel free to toss me a coin for :beer:

* BTC: 1EoFkrRa5ahABTujm7fcCHc7ChZC9iVvJh
* ETH: 0xB1beBe881238b961cb6ee686188C461bC110bb81
* LTC: MCviHR1nKiRrKiKy4VZyucjTGna7JpBRh5
* Paypal:
  [Donate](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=8DU7QGNN4Z6SC&source=url)

