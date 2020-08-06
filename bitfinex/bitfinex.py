# encoding=utf8

import requests  # pip install requests
import logging
import json
import base64
import hashlib
import hmac
import os
import time  # for nonce


class PublicV1:
    """
    Class for unauthenticated interactions with the version 1 REST API
    """
    base_url = "https://api.bitfinex.com/"

    def __init__(self):
        logging.getLogger("requests").setLevel(logging.WARNING)

    def _get(self, path, *args, **kwargs):
        logging.getLogger("requests").setLevel(logging.WARNING)
        return requests.get(self.base_url + path, kwargs)

    def funding_book(self, currency):
        """
        Get the full margin funding book
        
        Parameters
        ----------
        currency: str   
                    Currency to look for

        Returns
        -------

        """
        res = self._get('/v1/lendbook/{}'.format(currency))
        return res.json()

    def lends(self, currency):

        """
        Get a list of the most recent funding data for the given 
        currency: total amount provided and Flash Return Rate (in % by 365 days) over time.
        
        Parameters
        ----------
        currency: str
                  Currency to look for.

        Returns
        -------

        """
        res = self._get('/v1/lends/{}'.format(currency))
        return res.json()

    def order_book(self, symbol):
        """
        Get the full order book.
        
        Parameters
        ----------
        symbol: str
                Symbol to look for

        Returns
        -------

        """
        res = self._get('/v1/book/{}'.format(symbol))
        return res.json()

    def stats(self, symbol):
        """
        Various statistics about the requested pair.
        
        Parameters
        ----------
        symbol: str
                The symbol you want information about. 
                You can find the list of valid symbols by calling the symbols methods.

        Returns
        -------

        """
        res = self._get('v1/stats/{}'.format(symbol))
        return res.json()

    def symbols(self):
        """
        A list of symbol names
        
        Returns
        -------

        """
        res = self._get('v1/symbols')
        return res.json()

    def symbol_details(self):
        """
        
        Returns
        -------

        """
        res = self._get('v1/symbols_details')
        return res.json()


    def ticker(self, symbol='btcusd'):
        """
        The ticker is a high level overview of the state of the market. 
        It shows you the current best bid and ask, as well as the last 
        trade price. It also includes information such as daily volume 
        and how much the price has moved over the last day.
        
        Parameters
        ----------
        symbol: str
                The symbol you want information about. 
                You can find the list of valid symbols by calling the symbols method.

        Returns
        -------
        response:
                Result of enquiry

        """

        res = self._get('/v1/pubticker/{}'.format(symbol))
        return res.json()

    def trades(self, symbol):
        """
        Get a list of the most recent trades for the given symbol.
        
        Parameters
        ----------
        symbol: str
                Symbol to look for.

        Returns
        -------

        """
        res = self._get('v1/trades/{}'.format(symbol))
        return res.json()




class PublicV2:
    base_url = "https://api.bitfinex.com/"

    def __init__(self):
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def _get(self, path, *args, **kwargs):
        return requests.get(self.base_url + path, kwargs)

    def ticker(self, symbol='tBTCUSD'):
        res = self._get('v2/ticker/{}'.format(symbol))
        return res.json()

    def trades(self, symbol='tBTCUSD'):
        res = self._get('v2/trades/{}/hist'.format(symbol))
        return res.json()

    def books(self, symbol, precision):
        res = self._get('v2/book/{0}/{1}'.format(symbol, precision))
        return res.json()

    def stats(self, key, size, symbol, side, section):
        res = self._get('v2/stats1/{0}:{1}:{2}:{3}/{4}'.format(key, size, symbol, side, section))
        return res.json()

    def candles(self, timeframe, symbol, section):
        res = self._get('v2/candles/trade:{0}:{1}/{2}'.format(timeframe, symbol, section))
        return res.json()


class Trading_v2():
    def __init__(self, key, secret):
        self.base_url = "https://api.bitfinex.com/"
        self.key = key
        self.secret = secret.encode()
        logging.getLogger("requests").setLevel(logging.WARNING)

    def _nonce(self):
        """
        Returns a nonce
        Used in authentication
        """
        return str(int(round(time.time() * 10000)))

    def _headers(self, path, nonce, body):
        signature = "/api/" + path + nonce + body
        h = hmac.new(self.secret, signature.encode(), hashlib.sha384)
        signature = h.hexdigest()
        return {
            "bfx-nonce": nonce,
            "bfx-apikey": self.key,
            "bfx-signature": signature,
            "content-type": "application/json"
        }

    def req(self, path, params={}):
        nonce = self._nonce()
        body = params
        rawBody = json.dumps(body)
        headers = self._headers(path, nonce, rawBody)
        url = self.base_url + path
        resp = requests.post(url, headers=headers, data=rawBody, verify=True)
        return resp

    def active_orders(self):
        """
        Fetch active orders
        """
        response = self.req("v2/auth/r/orders")
        if response.status_code == 200:
            return response.json()
        else:
            print(response.status_code)
            print(response)
            return ''


class TradingV1:

    """
    Class for interacting with the authenticated REST endpoints for version 1 of the API.
    """

    def __init__(self, key, secret):
        self.base_url = "https://api.bitfinex.com"
        self.key = key
        self.secret = secret.encode()
        logging.getLogger("requests").setLevel(logging.WARNING)

    def _nonce(self):
        """
        Returns a nonce
        Used in authentication
        """
        return str(int(round(time.time() * 1e9)))

    def _sign_payload(self, payload):
        payload_json = json.dumps(payload).encode()
        payload_base = base64.b64encode(payload_json)

        h = hmac.new(self.secret, payload_base, hashlib.sha384)
        signature = h.hexdigest()

        return {
            "X-BFX-APIKEY": self.key,
            "X-BFX-SIGNATURE": signature,
            "X-BFX-PAYLOAD": payload_base
        }

    def _post(self, path, params):
        body = params
        rawBody = json.dumps(body)
        headers = self._sign_payload(body)
        url = self.base_url + path
        resp = requests.post(url, headers=headers, data=rawBody, verify=True)

        if resp.status_code == 200:
            return resp.json()

        else:
            print('Status code: ', resp.status_code)
            print('Text: ', resp.text)
            print(resp.url)

    def account_info(self):
        payload = {
            'request': '/v1/account_infos',
            'nonce': self._nonce()
        }
        return self._post('/v1/account_infos', payload)

    def account_fees(self):
        """
        Return information about your account (trading fees)
        
        Returns
        -------

        """
        payload = {
            'request': '/v1/account_fees',
            'nonce': self._nonce()
        }
        return self._post('/v1/account_fees', payload)

    def active_orders(self):
        """
        View your active orders.

        Returns
        -------
        response:
                A list of the results of /order/status for all your live orders.
        """

        payload = {
            'request': '/v1/orders',
            'nonce': self._nonce()
        }
        return self._post('/v1/orders', payload)

    def active_positions(self):
        """
        View your active positions.
        
        Returns
        -------

        """
        payload = {
            'request': '/v1/positions',
            'nonce': self._nonce()
        }
        return self._post('/v1/positions', payload)

    def balances(self):
        """
        See your wallet balances

        Returns
        -------

        """
        payload = {
            'request': '/v1/balances',
            'nonce': self._nonce()
        }
        return self._post('/v1/balances', payload)

    def balance_history(self, currency):
        """
        View all of your balance ledger entries.
        
        Parameters
        ----------
        currency: str
                 The currency to look for.

        Returns
        -------
        response:
                Result of balance history enquiry.
        """
        payload = {
            'request': '/v1/history',
            'nonce': self._nonce(),
            'currency': currency
        }
        return self._post('/v1/history', payload)

    def cancel_all_orders(self):
        """
        Cancel all active orders at once.

        Returns
        -------
        response:
                Confirmation of cancellation of the orders.
        """
        payload = {
            'request': '/v1/order/cancel/all',
            'nonce': self._nonce()
        }
        return self._post('/v1/order/cancel/all', payload)

    def cancel_order(self, order_id):
        """
        Cancel an order

        Parameters
        ----------
        order_id: int
                Order number to be canceled.

        Returns
        -------
        response: response result of post request

        """

        payload = {
            'request': '/v1/order/cancel',
            'nonce': self._nonce(),
            'order_id': order_id
        }
        return self._post('/v1/order/cancel', payload)

    def claim_position(self, position_id, amount):
        """
        A position can be claimed if:

        It is a long position: The amount in the last unit of the position pair that you have
        in your trading wallet AND/OR the realized profit of the position is greater or equal
        to the purchase amount of the position (base price position amount) and the funds which 
        need to be returned. For example, for a long BTCUSD position, you can claim the position 
        if the amount of USD you have in the trading wallet is greater than the base price the 
        position amount and the funds used.
        
        It is a short position: The amount in the first unit of the position pair that you have 
        in your trading wallet is greater or equal to the amount of the position and the margin funding used.
        
        Parameters
        ----------
        position_id: int
                    Position ID
        amount: int
                The partial amount you wish to claim.

        Returns
        -------
        response:
                Result of position claim request
        

        """

        payload = {
            "request": "/v1/position/claim",
            "nonce": self._nonce,
            "position_id": position_id,
            'amount': str(amount)
        }
        return self._post('/v1/position/claim', payload)

    def deposit(self, method, wallet_name, renew=0):
        """
        Return your deposit address to make a new deposit.
        
        Parameters
        ----------
        method: str
                Method of deposit (methods accepted: “bitcoin”, “litecoin”, “ethereum”, 
                “mastercoin” (tethers), "ethereumc", "zcash", "monero", "iota").
        wallet_name: str
                    Wallet to deposit in (accepted: “trading”, “exchange”, “deposit”). 
                    Your wallet needs to already exist
        renew: int, default is 0
               If set to 1, will return a new unused deposit address

        Returns
        -------
        response:
                Response to post request

        """
        payload = {
            'request': '/v1/deposit/new',
            'nonce': self._nonce(),
            'method': method,
            'wallet_name': wallet_name,
            'renew': renew
        }
        return self._post('/v1/deposit/new', payload)

    def deposit_withdrawal_history(self, currency):
        """
        View your past deposits/withdrawals.
        
        Parameters
        ----------
        currency: str
                The currency to look for

        Returns
        -------
        response:
                Result of enquiry

        """

        payload = {
            'request': '/v1/history/movements',
            'nonce': self._nonce(),
            'currency': currency
        }
        return self._post('/v1/history/movements', payload)



    def key_permissions(self):
        """
        Check the permissions of the key being used to generate this request.
        
        Returns
        -------

        """
        payload = {
            'request': '/v1/key_info',
            'nonce': self._nonce()
        }
        return self._post('/v1/key_info', payload)

    def new_order(self, symbol, amount, price, side, type_, exchange='bitfinex', use_all_available=False):
        """
        Sets up new order.

        Parameters
        ----------
        symbol: str
                Valid trading pair symbol
        amount: float
                Amount of currency to be traded
        price: float
                Price to trade currency at.
        side: str:
                Valid values: 'buy' or 'sell'
        type_: str
                Transaction type. Either “market” / “limit” / “stop” / “trailing-stop” / “fill-or-kill” /
                “exchange market” / “exchange limit” / “exchange stop” / “exchange trailing-stop” /
                “exchange fill-or-kill”. (
                type starting by “exchange ” are exchange orders, others are margin trading orders)

        exchange: str, default is 'bitfinex'
                    Exchange to trade one. Typically 'bitfinex'
        use_all_available: bool, default is False.
                            True will post an order using all the available balance.

        Returns
        -------
        response: response object

        """
        payload = {
            'request': '/v1/order/new',
            'nonce': self._nonce(),
            'symbol': symbol,
            'amount': str(amount),
            'price': str(price),
            'side': side,
            'type': type_,
            'exchange': exchange,
            'use_all_available': int(use_all_available),
            'ocoorder': False,
            'buy_price_oco': 0,
            'sell_price_oco': 0
        }
        return self._post('/v1/order/new', payload)

    def margin_info(self):
        """
        See your trading wallet information for margin trading.

        Returns
        -------
        """
        payload = {
            'request': '/v1/margin_infos',
            'nonce': self._nonce()
        }
        return self._post('/v1/margin_infos', payload)

    def order_status(self, order_id):
        """
        Get the status of an order. Is it active? Was it cancelled? To what extent has it been executed? etc.

        Parameters
        ----------
        order_id: int
                Order id

        Returns
        -------
        response:
                Order details
        """

        payload = {
            'request': '/v1/order/status',
            'nonce': self._nonce(),
            order_id: order_id
        }
        return self._post('/v1/order/status', payload)

    def summary(self):
        payload = {
            'request': '/v1/summary',
            'nonce': self._nonce()
        }
        return self._post('/v1/summary', payload)







