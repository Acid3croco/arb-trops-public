# %%
import ccxt

import pprint

from cryptofeed.defines import BYBIT, FTX, PERPETUAL

from db_handler.wrapper import DBWrapper
from arb_defines.arb_dataclasses import Instrument

# %%
e = ccxt.ftx()
db = DBWrapper()

# %%
instruments: list[Instrument] = db.get_instruments(base=None,
                                                   quote=None,
                                                   instr_type=PERPETUAL,
                                                   exchange_name=FTX)

print(len(instruments), 'instruments found')

# %%
all_min_bp = []
for instr in instruments:
    print('fetch', instr)
    last = e.fetch_ohlcv(instr.exchange_code, '1m', limit=1)
    if not last:
        print('no data for', instr)
        continue
    ltp = last[-1][4]
    min_bp = instr.tick_size / ltp * 10000
    print('min_bp', min_bp)
    all_min_bp.append([instr, min_bp])

# %%
all_min_bp.sort(key=lambda x: x[1], reverse=True)
oklol = [[str(x[0]), x[1]] for x in all_min_bp]
pprint.pprint(oklol[:10])

# %%
