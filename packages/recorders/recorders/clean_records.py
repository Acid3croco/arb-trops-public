import os
import traceback

from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

from tqdm import tqdm
from pandas.errors import EmptyDataError, ParserError

from recorders.trades_reader import TradesReader
from recorders.l2_book_reader import L2BookReader
from recorders.funding_reader import FundingReader


class CleanRecords:

    def __init__(self):
        self.records_path = os.getenv('ARB_RECORDS_PATH')

        if self.records_path is None:
            raise ValueError('ARB_RECORDS_PATH is not set')

    def _get_all_record_files(self) -> list[Path]:
        """
        only get csv files in root path
        """
        prev_day = datetime.now().date() - timedelta(days=1)
        prev_day_str = prev_day.strftime('%Y%m%d')
        files = [
            p for p in Path(self.records_path).rglob(f'*{prev_day_str}*/*.csv')
            if 'candles' in p.stem
            or self._get_file_date(p).date() < datetime.now().date()
        ]
        return files

    def clean_records(self):
        for path in tqdm(self._get_all_record_files()):
            kind = path.stem.split('_')[0]

            # print(f'cleaning {path}')
            try:
                df = self._load_df(path, kind)
                df = self._clean_df(df, kind)
            except EmptyDataError:
                print(f'empty file {path}')
                continue
            except Exception as e:
                print(f'error loading/cleaning {path}: {e}')
                print(traceback.format_exc())
                continue

            self._save_df(df, path, kind)

    def _load_df(self, path: Path, kind):
        if kind == 'candles':
            df = pd.read_csv(path.absolute(), index_col=0)
        else:
            # Duplicated from L2BookReader ... may be refactored
            try:
                df = pd.read_csv(path.absolute(), index_col=0, header=None)
            except ParserError as e:
                col_len = int(e.args[0].split(' ')[-1])
                df = pd.read_csv(path.absolute(),
                                 index_col=0,
                                 header=None,
                                 names=list(range(col_len)))
                df.columns = self._get_columns(df, kind)
                L2BookReader._fix_uneven_cols(df)
        return df

    def _clean_df(self, df: pd.DataFrame, kind):
        df = df.mask(df.shift(1) == df)
        df.columns = self._get_columns(df, kind)
        df.index.name = 'timestamp'
        return df

    def _save_df(self, df: pd.DataFrame, path: Path, kind):
        path = path.with_suffix(".parquet")
        # print(f'saving {path}')
        df.to_parquet(path)

        # check if new file exists
        if path.exists():
            can_delete = kind == 'candles'
            if kind != 'candles':
                file_date = self._get_file_date(path)
                can_delete = file_date.date() < datetime.now().date()
                # print(f'removing {path.with_suffix(".csv")}')
            if can_delete:
                os.remove(path.with_suffix('.csv'))

    def _get_columns(self, df, kind):
        if kind == 'l2':
            return L2BookReader._get_columns(df)
        if kind == 'candles':
            return ['open', 'high', 'low', 'close', 'volume']
        if kind == 'trades':
            return TradesReader.class_small.columns
        if kind == 'funding':
            return FundingReader.class_small.columns
        else:
            raise ValueError(f'unknown kind {kind}')

    def _get_file_date(self, path: Path):
        date_str = path.stem.split('_')[-1]
        return datetime.strptime(date_str, '%Y%m%d')


def main():
    cleaner = CleanRecords()
    cleaner.clean_records()


if __name__ == '__main__':
    main()
