import os
import time

from uuid import uuid4

from arb_logger.logger import get_logger
from watchers.watcher_base import WatcherBase
from arb_defines.defines import UPDATE, SNAPSHOT
from arb_utils.resolver import resolve_instruments
from redis_manager.redis_events import SentinelEvent
from redis_manager.redis_manager import RedisManager
from arb_defines.arb_dataclasses import SentinelPayload
from arb_utils.args_parser import instruments_args_parser

LOGGER = get_logger('sentinel_base', short=True)


class SentinelBase(WatcherBase):
    """Base class for sentinels."""
    short_logger = True
    sentinel_name = None
    grp_instr = False
    sort_instr = False

    def __init__(self, instruments) -> None:
        if not self.sentinel_name:
            raise ValueError(
                f'{self.__class__.__name__} needs a sentinel_name')

        self.values = []
        super().__init__(instruments)

    @property
    def sentinel_id(self):
        if self.instruments:
            if not hasattr(self, '_ids'):
                self._ids = '_'.join(
                    [str(i.id) for i in self.instruments.values()])
            return f'{self.sentinel_name}:{self._ids}'
        return f'{self.sentinel_name}'

    @staticmethod
    def sentinel_server_id(sentinel_id, instruments=None):
        server_id = f'{sentinel_id}_server'
        if instruments:
            _ids = '_'.join([str(i.id) for i in sorted(instruments)])
            return f'{server_id}:{_ids}'
        return server_id

    @staticmethod
    def sentinel_client_id(sentinel_name, client_id, instruments=None):
        sentinel_id = f'{sentinel_name}_{client_id}'
        if instruments:
            _ids = '_'.join([str(i.id) for i in sorted(instruments.values())])
            return f'{sentinel_id}:{_ids}'
        return sentinel_id

    def subscribe_to_events(self):
        server_id = f'{self.sentinel_name}_server'
        self.redis_manager.subscribe_event(
            SentinelEvent(self.instruments,
                          server_id,
                          grp_instr=self.grp_instr),
            self.on_sentinel_server_event)
        super().subscribe_to_events()

    def on_sentinel_server_event(self, payload: SentinelPayload):
        if payload.action == UPDATE:
            self.send_update(payload=payload)
        if payload.action == SNAPSHOT:
            self.send_snapshot(payload=payload)

    def _send_event(self, action, data, payload: SentinelPayload = None):
        sentinel_id = self.sentinel_id
        if payload and payload.data and payload.data.get('client_id'):
            sentinel_id = self.sentinel_client_id(self.sentinel_name,
                                                  payload.data['client_id'],
                                                  self.instruments)
        payload = SentinelPayload(sentinel_id, action=action, data=data)
        self.redis_manager.publish_event(SentinelEvent, payload)

    def send_update(self, data=None, payload=None):
        data = data or {'values': [self.values[-1] if self.values else None]}
        self._send_event(UPDATE, data, payload)

    def send_snapshot(self, data=None, payload=None):
        data = data or {'values': self.values}
        self._send_event(SNAPSHOT, data, payload)


class SentinelClientBase:
    """
    Base class for sentinels clients.
    Connect to sentinel and asks for snapshot.
    Then listen to update and maintain a local cache.
    """
    sentinel_class: SentinelBase = None
    values_max_len = 10000

    def __init__(self,
                 redis_manager: RedisManager,
                 instruments=None,
                 update_callback=None,
                 snapshot_callback=None) -> None:
        if not self.sentinel_class:
            raise ValueError(
                f'{self.__class__.__name__} needs a sentinel_class')

        self.logger = redis_manager.logger
        self.client_id = uuid4()

        self.redis_manager = redis_manager
        self.instruments = instruments
        self.update_callback = update_callback
        self.snapshot_callback = snapshot_callback

        self.values = []

        self.subscribe_to_events()
        self.ask_snapshot()

    def ask_snapshot(self):
        sentinel_id = self.sentinel_class.sentinel_server_id(
            self.sentinel_class.sentinel_name, self.instruments)
        payload = SentinelPayload(sentinel_id,
                                  action=SNAPSHOT,
                                  data={'client_id': self.client_id})
        self.redis_manager.publish_event(SentinelEvent, payload)

    def subscribe_to_events(self):
        sentinel_name = f'{self.sentinel_class.sentinel_name}_{self.client_id}'
        self.redis_manager.subscribe_event(
            SentinelEvent(self.instruments,
                          sentinel_name,
                          grp_instr=self.sentinel_class.grp_instr),
            self.on_sentinel_event)
        self.redis_manager.subscribe_event(
            SentinelEvent(self.instruments,
                          self.sentinel_class.sentinel_name,
                          grp_instr=self.sentinel_class.grp_instr),
            self.on_sentinel_event)

    def on_sentinel_event(self, payload: SentinelPayload):
        if payload.action == SNAPSHOT:
            return self.on_snapshot_event(payload)
        if payload.action == UPDATE:
            return self.on_update_event(payload)

    def _format_values(self, values):
        return values

    def on_snapshot_event(self, payload: SentinelPayload):
        if payload.data:
            values = payload.data.get('values')
            values = self._format_values(values)
            if values:
                self.values = values
            if len(self.values) > self.values_max_len:
                self.values = self.values[-self.values_max_len:]
        if self.snapshot_callback:
            self.snapshot_callback(payload)

    def on_update_event(self, payload: SentinelPayload):
        if payload.data:
            values = payload.data.get('values')
            values = self._format_values(values)
            if values:
                self.values += values
            if len(self.values) > self.values_max_len:
                self.values = self.values[-self.values_max_len:]
        if self.update_callback:
            self.update_callback(payload)


def start_sentinel(args, sentinel_class, instruments, grp_instr):

    def _start(args, sentinel_class, instruments):
        if args.instr_ids:
            order = [int(i) for i in args.instr_ids]
            instruments = sorted(instruments, key=lambda x: order.index(x.id))
        instr_ids = ' '.join([str(i.id) for i in instruments])

        process_name = f'{sentinel_class.sentinel_name}_sentinel'
        kill_cmd = f'pkill -f "{process_name} --instr-ids {instr_ids} --daemon"'
        LOGGER.info(kill_cmd)
        os.system(kill_cmd)

        # only kill
        if args.kill:
            return

        cmd = f'{process_name} --instr-ids {instr_ids} --daemon'
        run_cmd = f'nohup {cmd} </dev/null >/dev/null 2>&1 &'
        LOGGER.info(run_cmd)
        os.system(run_cmd)

    if grp_instr:
        _start(args, sentinel_class, instruments)
    else:
        for instr in instruments:
            _start(args, sentinel_class, [instr])


def sentinel_main(sentinel_class: SentinelBase,
                  grp_instr,
                  parser=None,
                  logger=None):
    global LOGGER
    LOGGER = logger or LOGGER

    if not parser:
        parser = instruments_args_parser(sentinel_class.__class__.__name__)
        parser.add_argument('--daemon', action='store_true')
        parser.add_argument('--kill',
                            action='store_true',
                            help='Only kill sentinel')

    args = parser.parse_args()
    instruments = resolve_instruments(args)

    if sentinel_class.sort_instr == False and args.instr_ids is not None:
        instruments.sort(key=lambda x: args.instr_ids.index(x.id))

    if args.daemon:
        sentinel = sentinel_class(instruments)
        return sentinel.run()
    start_sentinel(args, sentinel_class, instruments, grp_instr)
