import time

import ccxt.pro as ccxtpro
from cryptofeed.defines import *

from arb_defines.arb_dataclasses import OrderBook
from feed_handler.exchange_websocket_pro import ExchangeWebsocketPro


class BitgetWebsocket(ExchangeWebsocketPro):

    def __init__(self, *args):
        super().__init__(
            ccxtpro.bitget({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap'
                }
            }), *args)

    async def on_l2_book_cb(self, instr):
        while True:
            orderbook = await self.feed.watch_order_book(instr.feed_code,
                                                         limit=self.depth_limit
                                                         or self.max_depth)

            instr = self.get_instr_from_code(orderbook['symbol'])
            self._handle_status(instr, L2_BOOK)

            ob_ts = orderbook.get('timestamp')
            letimestamp = float(ob_ts) / 1000 if ob_ts else time.time()
            # need to remove third level
            bids = [l[:2] for l in orderbook['bids'][:self.max_depth]]
            asks = [l[:2] for l in orderbook['asks'][:self.max_depth]]
            ob = OrderBook(instr_id=instr.id,
                           bids=bids,
                           asks=asks,
                           timestamp=letimestamp)

            instr.set_orderbook(ob)
