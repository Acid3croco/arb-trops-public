from enum import Enum


class StatusEnum(Enum):
    IGNORE = 'ignore'
    UNKNOWN = 'unknown'
    UNDEFINED = 'undefined'
    UNAVAILABLE = 'unavailable'
    UNREACHABLE = 'unreachable'
    UP = 'up'
    DOWN = 'down'
    STOP = 'stop'
    START = 'start'
    READY = 'ready'
    STARTING = 'starting'
    STOPPING = 'stopping'
    STOPPED = 'stopped'
    STARTED = 'started'
