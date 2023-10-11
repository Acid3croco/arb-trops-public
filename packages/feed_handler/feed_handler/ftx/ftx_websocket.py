from cryptofeed.exchanges import FTX
from cryptofeed.defines import LIQUIDATIONS, TRADES

from feed_handler.exchange_websocket import ExchangeWebsocket


class FtxWebsocket(ExchangeWebsocket):

    def __init__(self, *args):
        # LIQUIDATIONS are not supported by FTX, they send TRADES instead
        # containing a field is_liquidation = True
        self.custom_callbacks = {LIQUIDATIONS: None}

        super().__init__(FTX, *args)

        self.has_trades = TRADES in self.channels
        self.has_liquidations = LIQUIDATIONS in self.channels

    async def on_trades_cb(self, trade, timestamp: float):
        if self.has_liquidations and trade.raw['liquidation'] is True:
            await super().on_liquidations_cb(trade, timestamp)
        elif self.has_trades and trade.raw['liquidation'] is False:
            await super().on_trades_cb(trade, timestamp)

    def _get_rate(sefl, obj, instr):
        # FTX 'current' rate is previous rate payment
        # whereas predicted rate is next rate payment
        return super()._get_predicted_rate(obj, instr)
