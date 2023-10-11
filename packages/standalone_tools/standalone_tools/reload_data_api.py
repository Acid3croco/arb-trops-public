from argparse import ArgumentParser
from db_handler.wrapper import DBWrapper

from redis_manager.redis_handler import RedisHandler
from redis_manager.redis_events import ExchangeApiEvent
from arb_defines.arb_dataclasses import ExchangeApiPayload


def main():
    parser = ArgumentParser(
        'Reload balances, potisions & orders from exchanges')

    parser.add_argument('exchanges', nargs='*', help='Exchanges to reload')

    args = parser.parse_args()

    exchanges = DBWrapper().get_exchanges(args.exchanges)

    redis_handler = RedisHandler()
    for exchange in exchanges:
        print(f'Reloading {exchange}')
        payload = ExchangeApiPayload(exchange_id=exchange.id,
                                     action='reload_data')
        redis_handler.publish_event(ExchangeApiEvent, payload)
