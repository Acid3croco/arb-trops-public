import atexit
import logging
import platform

from cmd import Cmd

from arb_logger.logger import get_logger
from redis_manager.redis_events import OrderBookEvent
from watchers.executor_base import ExecutorBase
from arb_utils.resolver import resolve_instruments
from arb_utils.args_parser import instruments_args_parser


class SeekerBase(ExecutorBase):

    def subscribe_to_events(self):
        self.redis_manager.subscribe_event(OrderBookEvent(self.instruments))
        return super().subscribe_to_events()


class SeekerClientBase(Cmd):
    linked_class: SeekerBase = None

    def __init__(self, instruments):
        super().__init__()

        # make tab key completion working for macos
        if platform.system() == 'Darwin':
            self._set_macos()

        self.logger = get_logger(self.__class__.__name__,
                                 short=True,
                                 level=logging.INFO)

    def _set_macos(self):
        import readline
        readline.parse_and_bind("bind ^I rl_complete")

    def run(self):
        # th = Thread(target=self.listen_server, daemon=True)
        # th.start()
        self.cmdloop('Think before you type...')


def seeker_main(seeker_client_class: SeekerClientBase):
    name = seeker_client_class.linked_class.__name__
    parser = instruments_args_parser(name)
    parser.add_argument('--server',
                        action='store_true',
                        help='Run in server mode')
    args = parser.parse_args()

    instruments = resolve_instruments(args)
    if args.instr_ids:
        order = [int(i) for i in args.instr_ids]
        instruments = sorted(instruments, key=lambda x: order.index(x.id))

    if args.server:
        seeker = seeker_client_class.linked_class(instruments)
    else:
        seeker = seeker_client_class(instruments)

    def clean_exit():
        nonlocal seeker
        if hasattr(seeker, 'disconnect'):
            seeker.disconnect()
        del seeker

    atexit.register(clean_exit)

    seeker.run()
