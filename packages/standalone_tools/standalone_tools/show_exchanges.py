import sys

from tabulate import tabulate
from cryptofeed.defines import *

from arb_defines.defines import *
from arb_logger.logger import get_logger
from db_handler.wrapper import DBWrapper
from arb_defines.arb_dataclasses import Exchange

LOGGER = get_logger('show_instruments', log_in_file=False)


class ShowExchanges:

    def __init__(self) -> None:
        self.exchanges = self.get_exchanges_from_db()

    def get_exchanges_from_db(self) -> list[Exchange]:
        exchanges = DBWrapper(LOGGER).get_exchanges()

        if len(exchanges) == 0:
            LOGGER.error(f"ERROR cannot find exchanges in DB")
            exit(0)

        return exchanges

    def show(self):
        exchanges = [[
            'ID',
            'Name',
            'Feed name',
            'Status',
        ]]
        for exchange in self.exchanges:
            exchanges.append([
                exchange.id,
                exchange.exchange_name,
                exchange.feed_name,
                exchange.exchange_status,
            ])

        LOGGER.info('Feed name is unique, not Name')
        print()
        print(tabulate(exchanges, headers='firstrow'), end="\n\n")
        print(tabulate([["Total", len(exchanges) - 1]]))


def main():
    show_exchanges = ShowExchanges()
    show_exchanges.show()


if __name__ == '__main__':
    main()
