import os
import csv
import time
import atexit

from pathlib import Path
from logging import Logger
from threading import Thread
from collections import defaultdict
from datetime import datetime, timezone

from argparse import ArgumentParser
from arb_logger.logger import get_logger
from watchers.watcher_base import WatcherBase

LOGGER = get_logger('base_recorder', short=True)


class BaseRecorder(WatcherBase):
    short_logger = True
    recorder_type = None
    class_small = None
    notify_new_values = True
    log_level = 'INFO'

    def __init__(self):
        super().__init__()
        if not self.recorder_type or not self.class_small:
            raise NotImplementedError(
                'recorder_type/class_small must be defined')

        self.current_day = defaultdict(
            lambda: datetime.now(tz=timezone.utc).day)

        self.fds = {}
        self.prev_event = {}

        self.flush_thread = Thread(target=self.flush_fds, daemon=True)
        self.flush_thread.start()

    def __del__(self):
        self.close_fds()
        LOGGER.info('Closed fds')

    @staticmethod
    def get_record_path(recorder_type, instr_id, date: datetime = None):
        base = os.getenv('ARB_RECORDS_PATH')
        today = date.strftime('%Y%m%d') if date else datetime.now(
            tz=timezone.utc).strftime('%Y%m%d')

        extension = 'csv'
        # since records are converted to parquet at the end of the day,
        # we need to change the extension for L2BookReader if reading past
        if date and date.date() < datetime.now().date():
            extension = 'parquet'

        return Path(
            f'{base}/{recorder_type}/{today}/{recorder_type}_recorder_{instr_id}_{today}.{extension}'
        )

    def flush_fds(self):
        last_minute = -1
        while True:
            if last_minute != datetime.now(tz=timezone.utc).minute:
                last_minute = datetime.now(tz=timezone.utc).minute
                LOGGER.info('Flushing fds')
                for fd, _ in self.fds.values():
                    fd.flush()
            time.sleep(1)

    def get_fd(self, instr_id):
        fd, writer = self.fds.get(instr_id, (None, None))
        if not fd:
            fd, writer = self.open_fd(instr_id)
            self.fds[instr_id] = fd, writer
        return fd, writer

    def close_fds(self):
        self.logger.info('Closing fds')
        for fd, _ in self.fds.values():
            fd.close()
        self.fds = {}

    def open_fd(self, instr_id):
        self.logger.info(f'Opening fd, writer for {instr_id}')
        path = self.get_record_path(self.recorder_type, instr_id)

        if path.parent.exists() is False:
            path.parent.mkdir(parents=True)

        fd = open(path, 'a')
        writer = csv.writer(fd)
        return fd, writer

    def _check_day_change(self, instr_id, timestamp):
        if self.current_day[instr_id] != datetime.fromtimestamp(timestamp).day:
            self.current_day[instr_id] = datetime.fromtimestamp(timestamp).day
            self.logger.info(
                f'Day changed for {instr_id}, closing fd, re-opening')
            self.fds[instr_id][0].close()
            self.fds[instr_id] = self.open_fd(instr_id)

    def _check_new_values(self, event):
        prev_event = self.prev_event.get(event.instr_id, None)
        if not prev_event or prev_event != event:
            self.prev_event[event.instr_id] = event

            if self.notify_new_values:
                self.logger.debug(f'New values for {event.instr_id}')
            return True
        self.logger.warning(f'No new values for {event.instr_id}')
        return False

    def subscribe_to_events(self):
        raise NotImplementedError('subscribe_to_events must be implemented')

    def _format_data(self, event):
        return event.to_list()

    def on_any_event(self, event):
        event.__class__ = self.class_small
        if self._check_new_values(event) is True:
            data = self._format_data(event)
            if data is None:
                return
            self._check_day_change(event.instr_id, data[0])
            _, writer = self.get_fd(event.instr_id)
            writer.writerow(data)


def start_recorder(recorder_type, args):
    process_name = f'{recorder_type}_recorder'
    kill_cmd = f'pkill -f "{process_name} --daemon"'
    LOGGER.info(kill_cmd)
    os.system(kill_cmd)

    if args.kill:
        return
    cmd = f'{process_name} --daemon'
    run_cmd = f'nohup {cmd} </dev/null >/dev/null 2>&1 &'
    LOGGER.info(run_cmd)
    os.system(run_cmd)


def main(recorder_class: BaseRecorder, logger: Logger):
    global LOGGER
    LOGGER = logger

    parser = ArgumentParser(
        description=f'Records {recorder_class.recorder_type}')
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--kill', action='store_true', help='Kill recorder')

    args = parser.parse_args()

    if args.daemon:
        recorder = recorder_class()

        def clean_stop():
            nonlocal recorder
            del recorder

        atexit.register(clean_stop, recorder_class.recorder_type, args)

        return recorder.run()
    start_recorder(recorder_class.recorder_type, args)
