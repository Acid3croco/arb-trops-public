from cryptofeed.defines import FTX, LIMIT
from ccxt.async_support.ftx import ftx as ftx_ccxt

from exchange_api.base_api import ExchangeAPI
from arb_defines.arb_dataclasses import Instrument, Order


class ftx(ftx_ccxt):
    rate_config = {
        'DELETE:orders': 0,
    }

    def calculate_rate_limiter_cost(self,
                                    api,
                                    method,
                                    path,
                                    params,
                                    config={},
                                    context={}):
        # print(
        #     f'calculate_rate_limiter_cost: {api} {method} {path} {params} {context}'
        # )
        cost = self.rate_config.get(
            f'{method}:{path}',
            super().calculate_rate_limiter_cost(api, method, path, params,
                                                config, context))
        # print(f'final cost: {cost}')
        return cost


class FtxApi(ExchangeAPI):
    feed_name = FTX

    def __init__(self, instruments: list[Instrument]):
        super().__init__(instruments, ftx)

    def _get_exchange_yaml(self, full_yaml):
        return full_yaml[self.exchange.feed_name.lower()]['Arb']

    def _overload_exchange_config(self, exchange_config):
        super()._overload_exchange_config(exchange_config)
        exchange_config['headers'] = {'FTX-SUBACCOUNT': 'Arb'}
        exchange_config['rateLimit'] = 105

    def _add_params_to_order(self, order: Order, params):
        params['rejectOnPriceBand'] = True
        if order.order_type == LIMIT:
            params['postOnly'] = True

    def modify_order(self, order):
        params = {
            'client_order_id': order.id,
            'size': order.qty,
            'price': order.price
        }
        res = self.exchange_api.private_post_orders_by_client_id_client_order_id_modify(
            params)
        _order = self.exchange_api.parse_order(res)
        order = self.fetcher.parse_order(_order)
        return order

    @staticmethod
    def _get_exchange_order_id(order: Order):
        return int(order.exchange_order_id)
