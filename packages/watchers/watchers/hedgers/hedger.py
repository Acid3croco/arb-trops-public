import time
import simplejson as json

from cryptofeed.defines import *

from arb_defines.defines import *
from watchers.watcher_base import WatcherBase


class Hedger(WatcherBase):

    def __init__(self, product):
        super().__init__(product)
        self.nbbo = None

    def run(self):
        channel = f'{EXEC}:{self.product}'

        self.subscribe_redis(channel, True)

    def _handle_message(self, obj):
        message = json.loads(obj)

        if message[SIDE] == BUY:
            hedge = self._find_highest_bid()
        else:
            hedge = self._find_lowest_ask()

        hedge[QTY] = -message[QTY]

        self._execute_hedge(hedge)

    def _find_highest_bid(self):
        # TODO: get all books in one pipe
        #! ADD MARKET MARKET
        highest_bid = {}

        for product in self.products:
            book = self.redis_instance.hgetall(product)

            if (float(book['timestamp']) < time.time() - 60 * 10):
                continue

            taker_fee = self.fees[product.split(':')[1]][PERPETUAL][TAKER]

            book[BID] = json.loads(book[BID])
            first_bid = next(iter(book[BID]))
            if (float(first_bid) * (1 + taker_fee) > highest_bid[PRICE]):
                highest_bid[PRODUCT] = product
                highest_bid[PRICE] = float(first_bid)

        return highest_bid

    def _find_lowest_ask(self):
        # TODO: get all books in one pipe
        #! ADD MARKET MARKET
        lowest_ask = {}

        for product in self.products:
            book = self.redis_instance.hgetall(product)

            if (float(book['timestamp']) < time.time() - 60 * 10):
                continue

            taker_fee = self.fees[product.split(':')[1]][PERPETUAL][TAKER]

            book[ASK] = json.loads(book[ASK])
            first_ask = next(iter(book[ASK]))
            if (float(first_ask) * (1 - taker_fee) < lowest_ask[PRICE]):
                lowest_ask[PRODUCT] = product
                lowest_ask[PRICE] = float(first_ask)

        return lowest_ask

    def _execute_hedge(self, hedge):
        _, exchange, product = hedge[PRODUCT].split(':')

        self.publish_redis(
            f'{exchange}:{ORDERS}', {
                ORDER_TYPE: MARKET,
                PRODUCT: product,
                PRICE: hedge[PRICE],
                QTY: hedge[QTY],
                'type': 'hedge',
            })


def simple_hedger_run(product):
    hedger = Hedger(product)
    hedger.run()