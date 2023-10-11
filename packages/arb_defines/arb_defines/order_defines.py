import cryptofeed.defines as defines

import arb_defines.defines as cust_defines


class OrderType:
    LIMIT = defines.LIMIT
    MARKET = defines.MARKET
    STOP_LIMIT = defines.STOP_LIMIT
    STOP_MARKET = defines.STOP_MARKET
    MAKER_OR_CANCEL = defines.MAKER_OR_CANCEL
    FILL_OR_KILL = defines.FILL_OR_KILL
    IMMEDIATE_OR_CANCEL = defines.IMMEDIATE_OR_CANCEL
    GOOD_TIL_CANCELED = defines.GOOD_TIL_CANCELED
