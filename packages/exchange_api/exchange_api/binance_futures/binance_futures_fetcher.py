from arb_defines.arb_dataclasses import Balance, Order
from exchange_api.base_fetcher import BaseFetcher
from unsync import unsync


class BinanceFuturesFetcher(BaseFetcher):

    @unsync
    async def fetch_balance(self) -> list[Balance]:
        raw_balance = await self.exchange_api.fetch_balance()

        qty = float(raw_balance['info']['availableBalance'] or 0)
        total_qty = float(raw_balance['info']['totalWalletBalance'] or 0)
        balance = Balance(self.exchange.id, 'USDT', qty, total_qty)

        return [balance]

    @unsync
    async def fetch_orders(self) -> list[Order]:
        if len(self.code_mapping) >= 40:
            raw_orders = self.exchange_api.fetch_open_orders()
        else:
            raw_orders = []
            for symbol in self.code_mapping:
                raw_orders += await self.exchange_api.fetch_open_orders(symbol)

        return self.parse_orders(raw_orders)