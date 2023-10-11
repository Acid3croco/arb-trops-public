import ccxt

from datetime import datetime, timezone

config = {
    'apiKey': 'oPgPiZz9L8f3Cd2Bu8jRif_NbDmxSWrKhCgAVhLF',
    'secret': '1_66RcNL5M6csX76PlOhgyBAaA8gw_9hduPraYlX',
    'headers': {
        'FTX-SUBACCOUNT': 'Arb'
    }
}
e = ccxt.ftx(config)
[m for m in dir(e) if 'payment' in m]
results = []

curr_date = datetime(2022, 7, 29, tzinfo=timezone.utc)
end_date = datetime.now(timezone.utc)
symbol = 'CREAM-PERP'

while curr_date < end_date:
    res = e.private_get_funding_payments(
        params={
            'symbol': symbol,
            'start_time': curr_date.timestamp(),
            'end_time': end_date.timestamp(),
        })
    res = res['result']
    if not res or datetime.fromisoformat(res[0]['time']) == curr_date:
        break
    else:
        results += res
        curr_date = datetime.fromisoformat(res[0]['time'])

tot = sum([float(r['payment']) for r in results if r['future'] == symbol])
print(symbol, -tot)