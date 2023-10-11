import pandas as pd

from datetime import datetime

from pandas.errors import ParserError

from arb_logger.logger import get_logger
from arb_defines.arb_dataclasses import OrderBook
from recorders.base_reader import BaseReader, main as base_main

process_name = 'l2_book_reader'
LOGGER = get_logger(process_name, short=True)


class L2BookReader(BaseReader):
    recorder_type = 'l2_book'
    class_small = OrderBook

    def read(self):
        uneven_cols = False
        if self.date.date() < datetime.now().date():
            df = pd.read_parquet(self.path)
        else:
            try:
                df = pd.read_csv(self.path, index_col=0, header=None)
            except ParserError as e:
                uneven_cols = True
                col_len = int(e.args[0].split(' ')[-1])
                df = pd.read_csv(self.path,
                                 index_col=0,
                                 header=None,
                                 names=list(range(col_len)))
        df.columns = self._get_columns(df)
        df.index = pd.to_datetime(df.index, unit='s')
        df.index.name = 'time'
        if uneven_cols:
            LOGGER.warning('Uneven columns, fixing')
            self._fix_uneven_cols(df)
        df.ffill(inplace=True)
        return df

    @staticmethod
    def _get_columns(df):
        columns = ['instr_id', 'bid_len', 'ask_len']

        col_len = int((len(list(df.columns)) - 3) / 2 / 2)
        for a in range(col_len):
            columns.append(f'bid_{a}')
            columns.append(f'bid_size_{a}')
        for a in range(col_len):
            columns.append(f'ask_{a}')
            columns.append(f'ask_size_{a}')

        return columns

    @staticmethod
    def _fix_uneven_cols(df):
        """
        number of bid and asks is not always the same
        for each row, account for the number of bid and ask, add nan to the missing and rebuild the row to match the columns
        """
        norm_number_of_cols = int((len(list(df.columns)) - 3) / 2 / 2)

        def _fix_row(row):
            bid_len = row['bid_len']
            ask_len = row['ask_len']
            bid_cols = row.iloc[3:int(3 + bid_len * 2)].values
            ask_cols = row.iloc[int(3 + bid_len * 2):int(3 + bid_len * 2 +
                                                         ask_len * 2)].values
            """
            add missing bid and ask values to match the number of bid and ask needed
            """
            bid_missing = int((norm_number_of_cols - bid_len) * 2)
            bid_cols = list(bid_cols) + [float('nan')] * bid_missing
            ask_missing = int((norm_number_of_cols - ask_len) * 2)
            ask_cols = list(ask_cols) + [float('nan')] * ask_missing
            return [row['instr_id'], norm_number_of_cols, norm_number_of_cols
                    ] + bid_cols + ask_cols

        df.apply(_fix_row, axis=1)


def main():
    base_main(L2BookReader, LOGGER)


if __name__ == '__main__':
    main()
