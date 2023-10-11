from logging import Logger
from datetime import datetime, timedelta, timezone

import pandas as pd

from arb_logger.logger import get_logger
from recorders.base_recorder import BaseRecorder
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser

LOGGER = get_logger('base_reader', short=True, level='INFO')


class BaseReader:
    short_logger = True
    recorder_type = None
    class_small = None

    def __init__(self, instr_id, date=None, **kwargs):
        if not self.recorder_type or not self.class_small:
            raise NotImplementedError(
                'recorder_type/class_small must be defined')

        self.kwargs = kwargs
        self.instr_id = instr_id
        self.date = self.parse_date(date)
        LOGGER.debug(f'Date: {self.date.strftime("%Y-%m-%d")}')
        self.path = BaseRecorder.get_record_path(self.recorder_type, instr_id,
                                                 self.date)
        LOGGER.debug(f'Path: {self.path}')

    def parse_date(self, date):
        if isinstance(date, str) and '-' in date:
            return datetime.now(tz=timezone.utc) - timedelta(
                days=abs(int(date)))
        if isinstance(date, str):
            return datetime.strptime(date, '%Y%m%d')
        if not date:
            date = datetime.now(tz=timezone.utc)
        return date

    def get_reader(self):
        return open(self.path, 'r')

    def get_columns(self, df=None):
        if hasattr(self, '_get_columns'):
            return self._get_columns(df)
        if hasattr(self.class_small, 'columns'):
            return self.class_small.columns

    def read(self):
        is_prev_day = self.date.date() < datetime.now().date()
        if is_prev_day:
            df = pd.read_parquet(self.path)
        else:
            df = pd.read_csv(self.path, index_col=0, header=None)

        df.columns = self.get_columns(df)
        df.index = pd.to_datetime(df.index, unit='s')
        df.index.name = 'time'

        # if self.__class__.__name__ == 'L2BookReader' and is_prev_day:
        if is_prev_day:
            # ffill for l2_book because data are cleaned daily
            df.ffill(inplace=True)

        return df

    def _read(self):
        df = self.read()
        if self.kwargs.get('all'):
            pd.set_option('display.max_row', None)
        print(df)
        LOGGER.info(f'Read {len(df)} lines')


def main(reader_class: BaseReader, logger: Logger):
    global LOGGER
    LOGGER = logger

    parser = instruments_args_parser(
        description=f'Reader {reader_class.recorder_type}')
    parser.add_argument('-d',
                        '--date',
                        help='Date to read',
                        default=datetime.now(tz=timezone.utc))
    parser.add_argument('-a',
                        '--all',
                        help='Show full data',
                        action='store_true')

    args = parser.parse_args()
    instruments = resolve_instruments(args)

    reader = reader_class(instruments[0].id,
                          date=args.date,
                          **{'all': args.all})
    reader._read()
