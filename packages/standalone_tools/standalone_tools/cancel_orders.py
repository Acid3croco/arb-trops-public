import os
import pathlib

from cryptofeed.defines import FTX, SPOT, PERPETUAL, BINANCE_FUTURES

from arb_logger.logger import get_logger
from db_handler.wrapper import DBWrapper
from exchange_api.base_api import ExchangeAPI
from exchange_api.ftx.ftx_api import FtxApi
from exchange_api.binance_futures.binance_futures_api import BinanceFuturesApi

ExchangeApi = {
    BINANCE_FUTURES: BinanceFuturesApi,
    FTX: FtxApi,
}

logger = get_logger("cancel_orders")


def cancel_orders():
    base = ['BTC']
    quote = ['USD']
    instr_type = [SPOT, PERPETUAL]
    exchanges = ['FTX']

    logger.info(f"get instruments {base} {quote} {instr_type} {exchanges}")

    db = DBWrapper()
    for exchange in exchanges:
        instruments = db.get_instruments(base=base,
                                         quote=quote,
                                         instr_type=instr_type,
                                         exchange_name=[exchange])
        if not instruments:
            logger.error('No instruments found, stopping here')
            continue

        logger.info(
            f"Done loading {len(instruments)} instruments: {[i.instr_code for i in instruments]}"
        )
        ea = ExchangeApi.get(exchange)
        ex: ExchangeAPI = ea(instruments)
        ex.on_cancel_all_orders_event()


config_dirname = pathlib.Path(
    os.path.dirname(__file__)) / ".." / "config" / "keys"

if not config_dirname.exists():
    logger.error("cannot find keys")
    exit(1)

os.environ['ARB_TROPS_CONFIG'] = config_dirname.as_posix()

cancel_orders()