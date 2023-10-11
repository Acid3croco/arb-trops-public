import multiprocessing

from multiprocessing.context import Process

from arb_logger.logger import get_logger


class ProcessManager:

    def __init__(self, name=''):
        self.logger = get_logger(f'{self.__class__.__name__}{name}')
        self.processes: list(Process) = []

    def __del__(self):
        self.kill_all_processes()

    def _spawn_process(self, target, args=()):
        self.logger.info(f'spwaning process {target}')
        process: Process = multiprocessing.Process(target=target,
                                                   args=args,
                                                   name=target.__name__,
                                                   daemon=True)
        self.processes.append(process)
        process.start()
        if process.is_alive():
            self.logger.info(f"{target} launchs OK")
        else:
            self.logger.error(f"{target} launchs KO")

    def kill_all_processes(self):
        for process in reversed(self.processes):
            self.logger.info(f'terminate process {process}')
            process.terminate()

    def spawn_process(self, process):
        function, args = process
        self._spawn_process(function, args)

    def spawn_processes(self, processes):
        for process in processes:
            self.spawn_process(process)


# class ProcessManager:

#     def __init__(self, name=''):
#         self.logger = get_logger(f'{self.__class__.__name__}{name}')
#         self.processes: list(Process) = []

#     def _spawn_process(self, target, args=()):
#         self.logger.info(f'spwaning process {target}')
#         process: Process = multiprocessing.Process(target=target,
#                                                    args=args,
#                                                    name=target.__name__)
#         self.processes.append(process)
#         process.start()
#         if process.is_alive():
#             self.logger.info(f"{target} launchs OK")
#         else:
#             self.logger.error(f"{target} launchs KO")

#     def kill_all_processes(self):
#         for process in reversed(self.processes):
#             self.logger.info(f'terminate process {process}')
#             process.terminate()

#     def spawn_process(self, process):
#         function, args = process
#         self._spawn_process(function, args)

#     def spawn_processes(self, processes):
#         for process in processes:
#             self.spawn_process(process)