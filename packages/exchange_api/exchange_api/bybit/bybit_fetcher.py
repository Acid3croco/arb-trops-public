import asyncio
from collections import defaultdict

from unsync import unsync

from exchange_api.base_fetcher import BaseFetcher
from arb_defines.arb_dataclasses import Order, Position


class BybitFetcher(BaseFetcher):

    @unsync
    async def fetch_positions(self) -> list[Position]:
        self.logger.warning(f'will get raw_positions')
        params = [{
            'subType': 'linear',
            'settleCoin': 'USDT'
        }, {
            'subType': 'linear',
            'settleCoin': 'USDC'
        }, {
            'subType': 'inverse',
            'settleCoin': 'BTC'
        }]
        raw_positions = await asyncio.gather(
            *[self.exchange_api.fetch_positions(params=p) for p in params])
        self.logger.warning(f'raw_positions: {raw_positions}')

        positions = []

        for p in sum(raw_positions, []):
            instr_id = self.code_mapping.get(p['symbol'])
            if not instr_id:
                continue

            qty = float(p.get('contracts', 0))
            qty = qty if p.get('side') == 'long' else -abs(qty)
            price = float(p.get('entryPrice', 0))
            position = Position(instr_id, qty, price)
            positions.append(position)

        return positions

    @unsync
    async def fetch_orders(self) -> list[Order]:
        raw_orders = []
        for instr in self.instr_id_mapping.values():
            try:
                _orders = await self.exchange_api.fetch_open_orders(
                    instr.exchange_code)
            except Exception as e:
                self.logger.error(e)
                _orders = []
            self.logger.info(
                f'{len(_orders)} orders fetched for {instr.exchange_code}')
            raw_orders.extend(_orders)

        return self.parse_orders(raw_orders)
