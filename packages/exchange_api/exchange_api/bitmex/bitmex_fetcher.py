from arb_defines.arb_dataclasses import Balance
from exchange_api.base_fetcher import BaseFetcher


class BitmexFetcher(BaseFetcher):

    def fetch_balance(self) -> list[Balance]:
        raw_balance = self.exchange_api.fetch_balance()
        total_balance = raw_balance['total']

        balance = []
        for currency, total_qty in total_balance.items():
            if total_qty != 0:
                qty = raw_balance['free'][currency]
                bal = Balance(self.exchange.id, currency, qty, total_qty)
                if bal.currency != 'BTC':
                    bal.total_qty /= 1000000
                    bal.qty /= 1000000
                balance.append(bal)

        return balance
