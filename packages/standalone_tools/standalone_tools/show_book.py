import time
import logging

from argparse import ArgumentParser

from curses import wrapper, curs_set
from datetime import datetime, timezone

from arb_defines.status import StatusEnum

from cryptofeed.defines import *
from arb_logger.logger import get_logger

from arb_defines.defines import *
from db_handler.wrapper import DBWrapper
from redis_manager.redis_manager import RedisManager
from redis_manager.redis_wrappers import InstrumentRedis
from redis_manager.redis_events import FundingRateEvent, InstrStatusEvent, OrderBookEvent, TradeEvent
from arb_defines.arb_dataclasses import AggrBook, AggrFundingRate, FundingRate, InstrStatus, Instrument, OrderBook

BOX_OFFSET = 8
MIN_COL_SIZE = 80
BOOK_DEPTH = 5

LOGGER = get_logger('show_book',
                    log_in_file=True,
                    short=True,
                    level=logging.WARNING)


class ShowBook:

    def __init__(self, args):
        self.refresh_rate = args.refresh
        self.last_time = 0
        self.fix_screen = False

        self.args = args
        self.base = args.base
        self.quotes = args.quotes
        self.currencies_names = args.currencies
        self.instr_types = args.types
        self.exchanges = args.exchanges
        self.instr_ids = args.instr_ids
        self.contract_types = args.contract_types
        self.convert = args.convert

        self._currencies = self.get_currencies()
        self._instruments = self.get_instruments()

        self.redis_manager: RedisManager = RedisManager(self._instruments +
                                                        self._currencies,
                                                        logger=LOGGER)

        self.aggrbook = AggrBook(currencies=self.currencies)
        self.aggrbook.set_orderbooks(
            list(self.instruments.values()) + list(self.currencies.values()))

        funding_rates = {i: i.funding_rate for i in self.instruments.values()}
        self.aggrfundingrate = AggrFundingRate(funding_rates=funding_rates)

    @property
    def instruments(self):
        return {
            id: i
            for id, i in self.redis_manager.instruments.items()
            if i in self._instruments
        }

    @property
    def currencies(self):
        return {
            id: i
            for id, i in self.redis_manager.instruments.items()
            if i in self._currencies
        }

    def get_instruments(self) -> list[Instrument]:
        if self.instr_ids:
            instruments = DBWrapper(LOGGER).get_instruments_with_ids(
                self.instr_ids)
        else:
            instruments = DBWrapper(LOGGER).get_instruments(
                base=self.base.upper(),
                quote=self.quotes,
                instr_type=self.instr_types,
                exchange_name=self.exchanges,
                contract_type=self.contract_types)

        if len(instruments) == 0:
            LOGGER.error(f"ERROR cannot find {self.base} in DB")
            LOGGER.error(self.args)
            exit(0)

        return instruments

    def get_currencies(self) -> list[Instrument]:
        if not self.currencies_names:
            return []
        currencies = DBWrapper(LOGGER).get_currencies(self.currencies_names,
                                                      quote='USDT',
                                                      exchange_name='BINANCE')

        if len(currencies) == 0:
            LOGGER.error(f"ERROR cannot find {self.currencies_names} in DB")
            LOGGER.error(self.args)
            exit(0)

        return currencies

    def run(self, stdout):
        curs_set(0)
        stdout.nodelay(True)
        self.stdout = stdout

        instrs = (list(self.instruments.values()) +
                  list(self.currencies.values()))

        self.redis_manager.subscribe_event(InstrStatusEvent(instrs),
                                           self.on_instr_status_event)
        self.redis_manager.subscribe_event(OrderBookEvent(instrs),
                                           self.on_order_book_event)
        self.redis_manager.subscribe_event(TradeEvent(self.instruments))
        self.redis_manager.subscribe_event(
            FundingRateEvent(self.instruments.values()),
            self.on_funding_rate_event)

        self.show_books()
        self.redis_manager.run()

    def on_instr_status_event(self, instr_status: InstrStatus):
        instr = self.redis_manager.instruments.get(instr_status.instr_id)
        self.aggrfundingrate.upadte_funding_rate(instr)
        self.show_books(force=True)

    def on_funding_rate_event(self, funding_rate: FundingRate):
        instr = self.redis_manager.instruments.get(funding_rate.instr_id)
        self.aggrfundingrate.upadte_funding_rate(instr, funding_rate)
        self.show_books()

    def on_order_book_event(self, orderbook: OrderBook):
        instr = self.redis_manager.instruments.get(orderbook.instr_id)
        self.aggrbook.update_aggrbook(instr, orderbook)
        self.show_books()

    def show_books(self, force=False):
        stdout = self.stdout
        c = self.stdout.getch()
        if c == ord('q'):
            exit(1)
        if c == ord('p'):
            self.fix_screen = not self.fix_screen
        if c == ord('c'):
            self.convert = not self.convert

        if self.convert:
            stdout.addstr(0, 60, 'CONVERTED')
        if self.fix_screen:
            stdout.addstr(0, 50, 'PAUSED')
        else:
            if time.time() > self.last_time + self.refresh_rate or force:
                self.last_time = time.time()
                self.stdout.clear()
                self.show_recap(stdout, self.instruments)

                stdout.addstr(BOX_OFFSET - 1, 0, "-" * (MIN_COL_SIZE - 1))
                row = 0
                for instr_redis in self.instruments.values():
                    # # if instr_redis.status not in [
                    # #         UNDEFINED, INSTRUMENT_STATUS_UNAVAILABLE
                    # # ]:
                    if instr_redis.status.l2_book == StatusEnum.UP:
                        row += self.show_book(stdout, instr_redis,
                                              row * BOX_SIZE + BOX_OFFSET)

        stdout.refresh()

    def show_recap(self, stdout, instr_data):
        stdout.addstr(0, 0, f"Recap - {datetime.now(tz=timezone.utc)}")

        fees = True
        spread = self.aggrbook.hit_hit_spread(fees=fees) or 0
        buy_price, _, buy_instr = self.aggrbook.taker_buy(fees=fees)
        sell_price, _, sell_instr = self.aggrbook.taker_sell(fees=fees)
        b_rate = (self.aggrbook.get_currency_rate(buy_instr)
                  if self.convert else 1)
        s_rate = (self.aggrbook.get_currency_rate(sell_instr)
                  if self.convert else 1)
        buy_price = buy_price or 0
        sell_price = sell_price or 0
        buy_price = round(buy_price * b_rate, 9)
        sell_price = round(sell_price * s_rate, 9)
        stdout.addstr(
            2, 0,
            f"HIT HIT: {str(round(spread * 100, 3)).rjust(7)}% - {str(buy_instr).rjust(35)} - {str(buy_price).rjust(11)} - {str(sell_price).ljust(11)} - {sell_instr}"
        )

        spread = self.aggrbook.liq_hit_spread(fees=fees) or 0
        buy_price, _, buy_instr = self.aggrbook.maker_buy(fees=fees)
        sell_price, _, sell_instr = self.aggrbook.taker_sell(fees=fees)
        b_rate = (self.aggrbook.get_currency_rate(buy_instr)
                  if self.convert else 1)
        s_rate = (self.aggrbook.get_currency_rate(sell_instr)
                  if self.convert else 1)
        buy_price = buy_price or 0
        sell_price = sell_price or 0
        buy_price = round(buy_price * b_rate, 9)
        sell_price = round(sell_price * s_rate, 9)
        stdout.addstr(
            3, 0,
            f"LIQ HIT: {str(round(spread * 100, 3)).rjust(7)}% - {str(buy_instr).rjust(35)} - {str(buy_price).rjust(11)} - {str(sell_price).ljust(11)} - {sell_instr}"
        )

        spread = self.aggrbook.hit_liq_spread(fees=fees) or 0
        buy_price, _, buy_instr = self.aggrbook.taker_buy(fees=fees)
        sell_price, _, sell_instr = self.aggrbook.maker_sell(fees=fees)
        b_rate = (self.aggrbook.get_currency_rate(buy_instr)
                  if self.convert else 1)
        s_rate = (self.aggrbook.get_currency_rate(sell_instr)
                  if self.convert else 1)
        buy_price = buy_price or 0
        sell_price = sell_price or 0
        buy_price = round(buy_price * b_rate, 9)
        sell_price = round(sell_price * s_rate, 9)
        stdout.addstr(
            4, 0,
            f"HIT LIQ: {str(round(spread * 100, 3)).rjust(7)}% - {str(buy_instr).rjust(35)} - {str(buy_price).rjust(11)} - {str(sell_price).ljust(11)} - {sell_instr}"
        )

        spread = self.aggrbook.liq_liq_spread(fees=fees) or 0
        buy_price, _, buy_instr = self.aggrbook.maker_buy(fees=fees)
        sell_price, _, sell_instr = self.aggrbook.maker_sell(fees=fees)
        b_rate = (self.aggrbook.get_currency_rate(buy_instr)
                  if self.convert else 1)
        s_rate = (self.aggrbook.get_currency_rate(sell_instr)
                  if self.convert else 1)
        buy_price = buy_price or 0
        sell_price = sell_price or 0
        buy_price = round(buy_price * b_rate, 9)
        sell_price = round(sell_price * s_rate, 9)
        stdout.addstr(
            5, 0,
            f"LIQ LIQ: {str(round(spread * 100, 3)).rjust(7)}% - {str(buy_instr).rjust(35)} - {str(buy_price).rjust(11)} - {str(sell_price).ljust(11)} - {sell_instr}"
        )

        spread, buy_instr, sell_instr = self.aggrfundingrate.spread()
        _, buy_rate = self.aggrfundingrate.buy_side()
        _, sell_rate = self.aggrfundingrate.sell_side()
        buy_rate = buy_rate.predicted_rate if buy_rate else 0
        sell_rate = sell_rate.predicted_rate if sell_rate else 0
        apr = spread * 3 * 365 * 100 if spread else 0
        try:
            apy = ((1 + spread)**(3 * 365) - 1) * 100 if spread else 0
        except OverflowError:
            apy = 0
        stdout.addstr(
            6, 0,
            f"F RTE %: {str(round(spread * 100, 3) if spread is not None else 'NA').rjust(7)}% - {str(buy_instr).rjust(35)} - {str(round(buy_rate * 100, 3) if buy_rate is not None else 'NA').rjust(11)} - {str(round(sell_rate * 100, 3) if sell_rate is not None else 'NA').ljust(11)} - {sell_instr} - APR: {apr:.3f}% - APY: {apy:.3f}%"
        )

    def show_book(self, stdout, instr_redis: InstrumentRedis, row):
        rows, cols = stdout.getmaxyx()
        if row + BOX_SIZE > rows:
            stdout.addstr(row, 0, f"Not enought rows in term")
            return 0
        if cols < MIN_COL_SIZE:
            stdout.addstr(row, 0, f"Not enought cols in term")
            return 0
        if instr_redis.orderbook is None:
            return 0

        if not instr_redis.orderbook.timestamp:
            return 0
        curr_time = datetime.fromtimestamp(
            instr_redis.orderbook.timestamp,
            tz=timezone.utc).strftime('%H:%M:%S.%f')
        stdout.addstr(
            row + 0, 0,
            f"{curr_time} - {str(instr_redis.id).rjust(6)} {str(instr_redis).ljust(40)} {instr_redis.status}"
        )

        stdout.addstr(row + 2, 0, "size".rjust(10))
        stdout.addstr(row + 2, 20, "bid".rjust(10))
        stdout.addstr(row + 2, 40, "ask".rjust(10))
        stdout.addstr(row + 2, 59, "size".rjust(10))

        curr_bid, _ = instr_redis.orderbook.bid()
        curr_ask, _ = instr_redis.orderbook.ask()
        rate = self.aggrbook.get_currency_rate(
            instr_redis) if self.convert else 1
        for limit in range(BOOK_DEPTH):
            bid, bid_size = instr_redis.orderbook.bid(limit)
            ask, ask_size = instr_redis.orderbook.ask(limit)
            stdout.move(row + 3 + limit, 0)
            stdout.clrtoeol()
            stdout.addstr(row + 3 + limit, 0,
                          f"{str(round(bid_size, 9)).rjust(10)}")
            stdout.addstr(row + 3 + limit, 20,
                          f"{str(round(bid * rate, 9)).rjust(10)}")
            stdout.addstr(row + 3 + limit, 40,
                          f"{str(round(ask * rate, 9)).rjust(10)}")
            stdout.addstr(row + 3 + limit, 59,
                          f"{str(round(ask_size, 9)).rjust(10)}")

        row += BOOK_DEPTH
        stdout.addstr(
            row + 4, 0,
            f"Spread: {(float(curr_ask) - float(curr_bid)) / float(curr_bid) * 100:.3f}%"
        )
        if instr_redis.funding_rate is not None:
            stdout.addstr(
                row + 5, 0,
                f"Funding rate: {instr_redis.funding_rate.rate * 100:.5f}%\t\tAPR: {instr_redis.funding_rate.apr * 100:.5f}%"
            )
            stdout.addstr(
                row + 6, 0,
                f"Predict rate: {instr_redis.funding_rate.predicted_rate * 100:.5f}%\t\tAPY: {instr_redis.funding_rate.apy * 100:.5f}%"
            )
        lt = instr_redis.last_trade
        if lt:
            trade_time = lt.time.astimezone(
                tz=timezone.utc).strftime('%H:%M:%S.%f')
            stdout.addstr(row + 7, 0,
                          f"Last trade: {lt.qty}@{lt.price} {trade_time}")
        else:
            stdout.addstr(row + 7, 0, f"Last trade: None")

        stdout.addstr(row + 8, 0, "-" * (MIN_COL_SIZE - 1))

        return 1


def main():
    parser = ArgumentParser(description='Show books with rates and spreads')

    quotes = ['TUSD', 'USDT', 'USDS', 'BUSD', 'USDP', 'USDC', 'USD']

    parser.add_argument('base', metavar='BASE', type=str)
    parser.add_argument('-q',
                        '--quotes',
                        metavar='QUOTE',
                        nargs='*',
                        default=quotes)
    parser.add_argument('-t',
                        '--types',
                        metavar='TYPE',
                        nargs='*',
                        default=[SPOT, PERPETUAL, FUTURES])
    parser.add_argument('-c',
                        '--contract_types',
                        metavar='CONTRACT',
                        nargs='*',
                        default=[LINEAR])
    parser.add_argument('-C', '--currencies', metavar='CURRENCY', nargs='*')
    parser.add_argument('-e', '--exchanges', metavar='EXCHANGE', nargs='*')
    parser.add_argument('-i', '--instr-ids', metavar='INSTR_ID', nargs='*')
    parser.add_argument('-r', '--refresh', type=float, default=0.1)
    parser.add_argument('-d', '--depth', type=int, default=5)
    parser.add_argument('--convert', action='store_true')

    args = parser.parse_args()

    # dirty-ass hack
    global BOOK_DEPTH
    BOOK_DEPTH = args.depth
    global BOX_SIZE
    BOX_SIZE = 9 + BOOK_DEPTH

    show_book = ShowBook(args)
    wrapper(show_book.run)


if __name__ == "__main__":
    main()
