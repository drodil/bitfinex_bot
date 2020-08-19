# encoding=utf8

import requests  # pip install requests
import json
import base64
import hashlib
import hmac
import time  # for nonce


def _nonce():
    return str(int(round(time.time() * 1e9)))


class PublicV1:
    base_url = "https://api.bitfinex.com/"

    def _get(self, path, **kwargs):
        return requests.get(self.base_url + path, kwargs)

    def funding_book(self, currency):
        res = self._get('/v1/lendbook/{}'.format(currency))
        return res.json()

    def lends(self, currency):
        res = self._get('/v1/lends/{}'.format(currency))
        return res.json()

    def order_book(self, symbol):
        res = self._get('/v1/book/{}'.format(symbol))
        return res.json()

    def stats(self, symbol):
        res = self._get('v1/stats/{}'.format(symbol))
        return res.json()

    def symbols(self):
        res = self._get('v1/symbols')
        return res.json()

    def symbol_details(self):
        res = self._get('v1/symbols_details')
        return res.json()

    def ticker(self, symbol='btcusd'):
        res = self._get('/v1/pubticker/{}'.format(symbol))
        return res.json()

    def trades(self, symbol):
        res = self._get('v1/trades/{}'.format(symbol))
        return res.json()


class PublicV2:
    base_url = "https://api.bitfinex.com/"

    def _get(self, path, **kwargs):
        return requests.get(self.base_url + path, kwargs)

    def ticker(self, symbol='tBTCUSD'):
        res = self._get('v2/ticker/{}'.format(symbol))
        return res.json()

    def tickers(self, symbols):
        res = self._get('v2/tickers?symbols=t{}'.format(',t'.join(symbols)))
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


class TradingV2:
    def __init__(self, key, secret):
        self.base_url = "https://api.bitfinex.com/"
        self.key = key
        self.secret = secret.encode()

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

    def req(self, path, params=None):
        if params is None:
            params = {}
        nonce = _nonce()
        body = params
        raw_body = json.dumps(body)
        headers = self._headers(path, nonce, raw_body)
        url = self.base_url + path
        resp = requests.post(url, headers=headers, data=raw_body, verify=True)
        return resp

    def active_orders(self):
        response = self.req("v2/auth/r/orders")
        if response.status_code == 200:
            return response.json()
        else:
            print(response.status_code)
            print(response)
            return ''


class TradingV1:
    def __init__(self, key, secret):
        self.base_url = "https://api.bitfinex.com"
        self.key = key
        self.secret = secret.encode()

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
        raw_body = json.dumps(body)
        headers = self._sign_payload(body)
        url = self.base_url + path
        resp = requests.post(url, headers=headers, data=raw_body, verify=True)

        if resp.status_code == 200:
            return resp.json()
        else:
            print('Status code: ', resp.status_code)
            print('Text: ', resp.text)
            print(resp.url)

    def account_info(self):
        payload = {
            'request': '/v1/account_infos',
            'nonce': _nonce()
        }
        return self._post('/v1/account_infos', payload)

    def account_fees(self):
        payload = {
            'request': '/v1/account_fees',
            'nonce': _nonce()
        }
        return self._post('/v1/account_fees', payload)

    def active_orders(self):
        payload = {
            'request': '/v1/orders',
            'nonce': _nonce()
        }
        return self._post('/v1/orders', payload)

    def active_positions(self):
        payload = {
            'request': '/v1/positions',
            'nonce': _nonce()
        }
        return self._post('/v1/positions', payload)

    def balances(self):
        payload = {
            'request': '/v1/balances',
            'nonce': _nonce()
        }
        return self._post('/v1/balances', payload)

    def balance_history(self, currency):
        payload = {
            'request': '/v1/history',
            'nonce': _nonce(),
            'currency': currency
        }
        return self._post('/v1/history', payload)

    def cancel_all_orders(self):
        payload = {
            'request': '/v1/order/cancel/all',
            'nonce': _nonce()
        }
        return self._post('/v1/order/cancel/all', payload)

    def cancel_order(self, order_id):
        payload = {
            'request': '/v1/order/cancel',
            'nonce': _nonce(),
            'order_id': order_id
        }
        return self._post('/v1/order/cancel', payload)

    def claim_position(self, position_id, amount):
        payload = {
            "request": "/v1/position/claim",
            "nonce": _nonce,
            "position_id": position_id,
            'amount': str(amount)
        }
        return self._post('/v1/position/claim', payload)

    def deposit(self, method, wallet_name, renew=0):
        payload = {
            'request': '/v1/deposit/new',
            'nonce': _nonce(),
            'method': method,
            'wallet_name': wallet_name,
            'renew': renew
        }
        return self._post('/v1/deposit/new', payload)

    def deposit_withdrawal_history(self, currency):
        payload = {
            'request': '/v1/history/movements',
            'nonce': _nonce(),
            'currency': currency
        }
        return self._post('/v1/history/movements', payload)

    def key_permissions(self):
        payload = {
            'request': '/v1/key_info',
            'nonce': _nonce()
        }
        return self._post('/v1/key_info', payload)

    def new_order(self, symbol, amount, price, side, type_, aff_code=None, exchange='bitfinex',
                  use_all_available=False):
        payload = {
            'request': '/v1/order/new',
            'nonce': _nonce(),
            'symbol': symbol,
            'amount': str(amount),
            'price': str(price),
            'side': side,
            'type': type_,
            'exchange': exchange,
            'aff_code': aff_code,
            'use_all_available': int(use_all_available),
            'ocoorder': False,
            'buy_price_oco': 0,
            'sell_price_oco': 0
        }
        return self._post('/v1/order/new', payload)

    def margin_info(self):
        payload = {
            'request': '/v1/margin_infos',
            'nonce': _nonce()
        }
        return self._post('/v1/margin_infos', payload)

    def order_status(self, order_id):
        payload = {
            'request': '/v1/order/status',
            'nonce': _nonce(),
            order_id: order_id
        }
        return self._post('/v1/order/status', payload)

    def summary(self):
        payload = {
            'request': '/v1/summary',
            'nonce': _nonce()
        }
        return self._post('/v1/summary', payload)
