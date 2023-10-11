import logging

from argparse import ArgumentParser

from cryptofeed.defines import *
from curses import curs_set, wrapper

from arb_defines.defines import *
from arb_logger.logger import get_logger
from db_handler.wrapper import DBWrapper
from arb_defines.arb_dataclasses import Exchange
from redis_manager.redis_events import BalanceEvent
from redis_manager.redis_manager import RedisManager

LOGGER = get_logger('show_balances', log_in_file=False, level=logging.WARNING)


class ShowBalances:

    def __init__(self, args):
        self.args = args
        self.currencies = args.currencies
        self.exchanges = args.exchanges

        exchanges = self.get_exchanges_from_db()
        self.redis_manager: RedisManager = RedisManager(exchanges=exchanges,
                                                        logger=LOGGER)

    def get_exchanges_from_db(self) -> list[Exchange]:
        exchanges = DBWrapper(LOGGER).get_exchanges(
            exchange_names=self.exchanges)

        if len(exchanges) == 0:
            LOGGER.error(f"ERROR cannot find {self.exchanges} in DB")
            LOGGER.error(self.args)
            exit(0)

        return exchanges

    def show(self):
        if self.args.live:
            wrapper(self._show_live)
        else:
            self._show_snap()

    def _show_snap(self):
        for exchange in self.redis_manager.exchanges.values():
            if exchange and exchange.balances:
                print(f'{str(exchange.feed_name)}')
                for balance in exchange.balances.values():
                    if balance.qty != 0 and (balance.currency
                                             in self.currencies
                                             or not self.currencies):
                        print(
                            f'\t{str(balance.currency).ljust(10)} {balance.qty}'
                        )

    def _subscribe_to_exchanges(self):
        self.redis_manager.subscribe_event(
            BalanceEvent(self.redis_manager.exchanges.values()),
            self._on_balance_event)

    def _on_balance_event(self, balance):
        self._refresh_live()

    def _show_live(self, stdout):
        curs_set(0)
        stdout.nodelay(True)
        self.stdout = stdout

        self._subscribe_to_exchanges()
        self._refresh_live()
        self.redis_manager.run()

    def _refresh_live(self):
        self.stdout.clear()
        row = 0
        for exchange in self.redis_manager.exchanges.values():
            if exchange and exchange.balances:
                self.stdout.addstr(row, 0,
                                   f'{exchange.feed_name} {exchange.id}')
                row += 1
                for balance in exchange.balances.values():
                    if balance.qty != 0 and (balance.currency
                                             in self.currencies
                                             or not self.currencies):
                        self.stdout.addstr(
                            row, 4,
                            f'{str(balance.currency).ljust(10)} {round(balance.qty, 5)}'
                        )
                        row += 1
                row += 1
        self.stdout.refresh()


def main():
    parser = ArgumentParser(description='Show balances on exchanges')

    parser.add_argument('currencies', metavar='CURRENCY', type=str, nargs='*')
    parser.add_argument('-e', '--exchanges', metavar='EXCHANGE', nargs='*')
    parser.add_argument('-l', '--live', action='store_true')

    args = parser.parse_args()

    show_balances = ShowBalances(args)
    show_balances.show()


if __name__ == '__main__':
    main()
