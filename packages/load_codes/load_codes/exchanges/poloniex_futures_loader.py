import ccxt

from polofutures import RestClient
from cryptofeed.defines import MAKER, POLONIEX_FUTURES

from load_codes.base_loader import BaseLoader


class poloniexfutures(ccxt.poloniex):

    def __init__(self, config={}):
        super().__init__(config)

        self.rest_client = RestClient()
        self.market_api = self.rest_client.market_api()

    def fetch_markets(self, params={}):
        markets = self.market_api.get_contracts_list()

        result = []
        for i in range(0, len(markets)):
            market = self.safe_value(markets, i)
            id = self.safe_string(market, 'symbol')
            baseId = self.safe_string(market, 'baseCurrency')
            quoteId = self.safe_string(market, 'quoteCurrency')
            base = self.safe_currency_code(baseId)
            quote = self.safe_currency_code(quoteId)
            status = self.safe_string(market, 'status')
            active = status == 'Open'
            # these are known defaults
            result.append({
                'id': id,
                'symbol': base + '/' + quote,
                'base': base,
                'quote': quote,
                'settle': None,
                'baseId': baseId,
                'quoteId': quoteId,
                'settleId': None,
                'type': 'future',
                'spot': False,
                'margin': False,
                'swap': False,
                'future': True,
                'option': False,
                'active': active,
                'contract': False,
                'linear': True,
                'inverse': None,
                'contractSize': None,
                'expiry': None,
                'expiryDatetime': None,
                'strike': None,
                'optionType': None,
                'precision': {
                    'amount': self.safe_number(market, 'multiplier'),
                    'price': self.safe_number(market, 'tickSize'),
                },
                'limits': {
                    'amount': {
                        'min': self.safe_number(market, 'multiplier'),
                        'max': self.safe_number(market, 'maxOrderQty'),
                    },
                    'price': {
                        'min': None,
                        'max': None,
                    },
                    'cost': {
                        'min': self.safe_number(market, 'initialMargin'),
                        'max': None,
                    },
                },
                'info': market,
            })
        return result


class PoloniexFuturesLoader(BaseLoader):
    feed_code = POLONIEX_FUTURES

    def __init__(self, db_wrapper, bases, quotes, instr_types):

        super().__init__(
            db_wrapper,
            bases,
            quotes,
            instr_types,
            poloniexfutures(),
            self.feed_code,
        )

    # def load_markets(self):
    #     markets = self.market_api.get_contracts_list()
    #     markets = self._parse_markets(markets)
    #     self.set_markets(self.markets)

    def get_fee_id(self, instrument, fee_type, percent_value, fixed_value=0):
        if fee_type == MAKER:
            percent_value = 0.0001
        else:
            percent_value = 0.00075
        return super().get_fee_id(instrument, fee_type, percent_value,
                                  fixed_value)


# market['EGLDUSDTPERP'] = {
#     'symbol': 'EGLDUSDTPERP',
#     'takerFixFee': 0.0,
#     'nextFundingRateTime': 27177007,
#     'openInterest': '15586',
#     'highPriceOf24h': 55.66999816894531,
#     'fundingFeeRate': 0.0,
#     'volumeOf24h': 7254.9,
#     'riskStep': 500000,
#     'makerFixFee': 0.0,
#     'isQuanto': True,
#     'maxRiskLimit': 20000,
#     'type': 'FFWCSX',
#     'predictedFundingFeeRate': 0.0,
#     'turnoverOf24h': 399163.13687515,
#     'rootSymbol': 'USDT',
#     'baseCurrency': 'EGLD',
#     'firstOpenDate': 1652963400000,
#     'tickSize': 0.01,
#     'initialMargin': 0.05,
#     'isDeleverage': True,
#     'markMethod': 'FairPrice',
#     'indexSymbol': '.PEGLDUSDT',
#     'markPrice': 55.27,
#     'minRiskLimit': 1000000,
#     'fundingBaseSymbol': '.EGLDINT8H',
#     'lowPriceOf24h': 54.56999969482422,
#     'lastTradePrice': 55.27,
#     'indexPriceTickSize': 0.01,
#     'fairMethod': 'FundingRate',
#     'takerFeeRate': 0.00075,
#     'fundingRateSymbol': '.EGLDUSDTPERPFPI8H',
#     'indexPrice': 55.27,
#     'makerFeeRate': 0.0001,
#     'isInverse': False,
#     'lotSize': 1,
#     'multiplier': 0.1,
#     'settleCurrency': 'USDT',
#     'maxLeverage': 20,
#     'fundingQuoteSymbol': '.USDTINT8H',
#     'quoteCurrency': 'USDT',
#     'maxOrderQty': 1000000,
#     'maxPrice': 1000000.0,
#     'maintainMargin': 0.025,
#     'status': 'Open'
# }
