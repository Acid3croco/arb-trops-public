import pandas as pd
from argparse import ArgumentParser


def read_trades():
    df = pd.read_csv('~/Downloads/trades.csv')
    df.columns = ['ID', 'Time', 'Product', 'Side', 'Order Type', 'Size', 'Price', 'Total', 'Fee', 'Fee Currency']

    return df


def read_funding_payment() -> object:
    df = pd.read_csv('~/Downloads/funding_payments.csv')
    df.columns = ['Date', 'Product', 'Payment', 'Rate']

    return df


def get_pnl(instruments):
    df = read_trades()
    df_fundings: pd.DataFrame = read_funding_payment()

    df_fundings.query('Product in @instruments', inplace=True)
    pnl_funding = df_fundings['Payment'].sum()
    pnl_funding *= -1

    df.query('Product in @instruments', inplace=True)
    df_buy = df.query('Side == "buy"')
    df_sell = df.query('Side == "sell"')
    pnl_trades = (df_sell['Size'] * df_sell['Price']).sum() - (df_buy['Size'] * df_buy['Price']).sum()
    cost = df['Fee'].sum()
    notional = (df_sell['Size'] * df_sell['Price']).sum() + (df_buy['Size'] * df_buy['Price']).sum()
    assert notional

    perf_pnl_funding = pnl_funding / (notional/2)
    all_pnl = pnl_trades + pnl_funding - cost
    print(f'Notional traded: {notional} $')
    print(f'pnl_trades={round(pnl_trades, 5)} $')
    print(f'cost={round(cost, 5)} $')
    print(f'pnl_funding={round(pnl_funding, 5)} $')
    print(f'all={round(all_pnl, 5)} $')
    print(f'perf_pnl_funding={round(perf_pnl_funding * 1e4, 5)} bps')
    print(f'Funding PNL for {instruments}: {round(all_pnl, 5)} $')


def main():
    parser = ArgumentParser(description='Get PNL fundings')

    parser.add_argument('-b', '--bases', metavar='BASE', nargs='*')
    args = parser.parse_args()
    get_pnl(args.bases)


if __name__ == "__main__":
    main()
