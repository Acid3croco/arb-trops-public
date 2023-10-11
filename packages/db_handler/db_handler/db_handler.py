import atexit

from db_handler.handler import DBHandler


def db_handler_invoke():
    db_handler = DBHandler()
    db_handler.run()

    def clean_exit(sig=None, frame=None):
        # idk if it works actually
        nonlocal db_handler
        db_handler.kill()
        del db_handler

    atexit.register(clean_exit)


def main():
    db_handler_invoke()
