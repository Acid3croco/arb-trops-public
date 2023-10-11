import re
import logging
import platform

from cmd import Cmd
from threading import Thread
from types import NoneType

from tabulate import tabulate

from dataclasses import fields
from arb_logger.logger import get_logger
from arb_defines.status import StatusEnum
from watchers.executor_base import ExecutorBase
from redis_manager.redis_events import TriggerEvent
from redis_manager.redis_handler import RedisHandler
from arb_defines.arb_dataclasses import TriggerPayload


class TriggerBase(ExecutorBase):
    config_class = None

    def __init__(self, instruments) -> None:
        super().__init__(instruments)

        self._register_trigger()

    def _register_trigger(self):
        self.logger.info(f'Registering trigger {self.id}')
        is_registered = self.redis_manager.redis_instance.get(self.id)

        if is_registered and is_registered == StatusEnum.UP.name:
            self.logger.warning(
                f'Trigger {self.id} already registered, exiting here')
            # exit()

        self.redis_manager.redis_instance.set(self.id, StatusEnum.UP.name)

    def disconnect(self):
        self.logger.info(f'Stopping trigger {self.id}')
        self.redis_manager.redis_instance.set(self.id,
                                              StatusEnum.UNAVAILABLE.name)

    def cancel_all_pendings(self):
        self.cancel_all = False
        super().cancel_all_pendings()

    def subscribe_to_events(self):
        super().subscribe_to_events()
        self.redis_manager.subscribe_event(TriggerEvent(self.id),
                                           self.on_trigger_event)

    def on_trigger_event(self, payload: TriggerPayload):
        if hasattr(self, 'config_class') and payload.config is not None:
            self.config = self.config_class(**payload.config)
        self.logger.info(f'Trigger event received: {payload}')

        match payload.action:
            case 'cancel_all':
                self.cancel_all_pendings()
            case 'stop_server':
                self.cancel_all_pendings()
                self.disconnect()
                exit()
            case 'send_orders':
                self.send_orders_to_client()

    def send_orders_to_client(self):
        self.send_trigger_client(
            TriggerPayload(trigger_id=self.client_id,
                           action='send_orders',
                           data=dict(self.redis_manager.orders_manager.orders)))

    def send_trigger_client(self, payload: TriggerPayload):
        self.redis_manager.publish_event(TriggerEvent, payload)


class TriggerClient(Cmd):
    linked_class = None
    config = None

    def __init__(self, instruments):
        super().__init__()

        # make tab key completion working for macos
        if platform.system() == 'Darwin':
            self._set_macos()

        self.logger = get_logger(self.__class__.__name__,
                                 short=True,
                                 level=logging.INFO)
        if not self.linked_class:
            self.logger.error('No linked class defined')
            raise ValueError('No linked class defined')

        self.redis_handler = RedisHandler(logger=self.logger)

        self.instruments = {i.id: i for i in instruments}
        self.id = TriggerBase._build_name(self.__class__.__name__, instruments)
        self.server_id = TriggerBase._build_name(self.linked_class.__name__,
                                                 instruments)

        super().__init__()

    def _set_macos(self):
        import readline
        readline.parse_and_bind("bind ^I rl_complete")

    def preloop(self) -> None:
        self.logger.info(f'Starting {self.server_id}')
        self.show_config()

    def precmd(self, line) -> None:
        self.logger.debug(line)
        return line

    def run(self):
        th = Thread(target=self.listen_server, daemon=True)
        th.start()
        self.cmdloop('Think before you type...')

    def listen_server(self):
        """
        It listens to the trigger server events.
        """
        self.logger.info('Starting listener thread')
        self.redis_handler.subscribe_event(TriggerEvent(self.id),
                                           self.on_trigger_event)
        self.redis_handler.run()

    def on_trigger_event(self, payload: TriggerPayload):
        """
        The function is called when a trigger event is received

        Args:
          payload (TriggerPayload): TriggerPayload
        """
        self.logger.debug(f'Trigger event received: {payload}')

    def do_exit(self, args):
        self.logger.info(f'EXIT {self.id}')
        exit()

    def do_name(self, args):
        self.logger.info(f"\nName's '{self.id}'")
        self.logger.info(f"\nServer Name's '{self.server_id}'")

    def do_debug(self, args):
        if self.logger.level != logging.DEBUG:
            self.logger.setLevel(logging.DEBUG)
            self.logger.info('Setting logger to DEBUG')
        else:
            self.logger.setLevel(logging.INFO)
            self.logger.info('Setting logger to INFO')

    def do_config(self, args):
        self.show_config()

    def show_config(self):
        if not hasattr(self, 'config'):
            self.logger.error('No config available')
            return

        config = tabulate([(field.name, getattr(self.config, field.name))
                           for field in fields(self.config)],
                          headers=['KEY', 'VALUE'],
                          tablefmt='fancy_grid')
        self.logger.info(f'\n{config}')

    def do_instruments(self, args):
        self.show_instr()

    def do_set(self, args):
        """
        It takes a string of the form "key value" and sets the attribute of the
        config object with the name "key" to the value "value"

        :param args: The arguments passed to the command
        """
        try:
            key, value = re.split(' |=|:', args, 1)
        except ValueError:
            self.logger.error('Invalid syntax')
            return
        if hasattr(self.config, key):
            prev = getattr(self.config, key)
            letype = type(prev)
            if letype is not NoneType:
                value = letype(value)
            setattr(self.config, key, value)

    def complete_set(self, text, line, begidx, endidx):
        names = [
            f.name for f in fields(self.config)
            if (True if not text else f.name.startswith(text))
        ]
        spl = re.split(' ', line)
        name = spl[1] if len(spl) > 1 else ''
        if name in names:
            return [getattr(self.config, name)]
        return names

    def do_stop(self, args):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id, action='stop'))

    def do_start(self, args):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id, action='start', config=self.config))

    def do_stop_server(self, args):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id, action='stop_server'))

    def do_cancel_all(self, args):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id, action='cancel_all'))

    def do_show_orders(self, args):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id, action='send_orders'))

    def show_instr(self):
        table = tabulate(self.instruments.items(),
                         headers=['ID', 'Instrument'],
                         tablefmt='fancy_grid')
        self.logger.info(f'\n{table}')

    def do_push_config(self, _):
        self.send_trigger(
            TriggerPayload(trigger_id=self.server_id,
                           action='config',
                           config=self.config))

    def send_trigger(self, payload: TriggerPayload):
        self.redis_handler.publish_event(TriggerEvent, payload)
