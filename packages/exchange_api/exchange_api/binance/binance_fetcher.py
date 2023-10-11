from unsync import unsync

from arb_defines.arb_dataclasses import Position
from exchange_api.base_fetcher import BaseFetcher


class BinanceFetcher(BaseFetcher):

    @unsync
    async def fetch_positions(self) -> list[Position]:
        # since its all spot, there is no positions
        return []
