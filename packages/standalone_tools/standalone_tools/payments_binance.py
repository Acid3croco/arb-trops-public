import ccxt

from datetime import datetime, timezone

config = {
    'apiKey':
    'IUzz5bhwUcEui7wfXFaOdT5jFhBZQPeRoOpS8HqCcNtqNrP1FCCvXXBfJto1jKTB',
    'secret':
    'V4WLieWiMMIah2BSSImznUe5ia0DyEqvSeWKYZUieoAstjSpIDx6SUiIiwao09hR',
    'options': {
        'defaultType': 'future',
    }
}
e = ccxt.binance(config)

results = []

curr_date = datetime(2022, 5, 29, tzinfo=timezone.utc)
end_date = datetime.now(timezone.utc)
symbol = 'WAVESUSDT'

while curr_date < end_date:
    res = e.fapiPrivate_get_income(
        params={
            'symbol': symbol,
            'startTime': curr_date.timestamp(),
            'endTime': end_date.timestamp(),
            'limit': 1000,
        })
    last_dt = datetime.fromtimestamp(int(res[-1]['time']) / 1000,
                                     tz=timezone.utc)
    if not res or last_dt == curr_date:
        break
    else:
        results += res
        curr_date = last_dt

tot = sum([float(r['income']) for r in results if r['symbol'] == symbol])
print(symbol, tot)