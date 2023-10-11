from cmd import Cmd

from arb_logger.logger import get_logger


class ArbCmd(Cmd):
    prompt = ''

    def __init__(self, process_manager):
        self.process_manager = process_manager
        self.logger = get_logger(self.__class__.__name__)
        super().__init__()

    def do_exit(self, args):
        self.logger.info('EXIT ARB, kill all processes')
        self.process_manager.kill_all_processes()
        raise SystemExit()


if __name__ == '__main__':
    app = ArbCmd()
    app.cmdloop('')