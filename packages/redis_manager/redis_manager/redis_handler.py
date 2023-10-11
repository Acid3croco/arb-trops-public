import time
import traceback

from abc import ABC
from typing import Callable
from dataclasses import dataclass

from redis.client import Redis

from arb_logger.logger import get_logger
from redis_manager.redis_events import CancelAllOrdersInstrEvent, OrderBookEvent, RedisEvent, OrderExchangeEvent, CancelOrderEvent, StrategyInfoDBEvent, OrderDBEvent, TradeEvent


@dataclass
class EventHandler:
    event: RedisEvent
    callbacks: list[Callable]
    deserialize: bool = True


class RedisHandler(ABC):

    def __init__(self, host='localhost', port=6379, logger=None):
        self.logger = logger or get_logger(self.__class__.__name__, short=True)

        self.redis_instance: Redis = Redis(host=host,
                                           port=port,
                                           decode_responses=True)
        self.pubsub = self.redis_instance.pubsub()

        self.events: dict[str, EventHandler] = {}

    def subscribe_event(self,
                        redis_event: RedisEvent,
                        callbacks=None,
                        deserialize=True):
        if not isinstance(callbacks, list):
            callbacks = [callbacks]
            callbacks = list(set(callbacks))

        channels = redis_event.get_channels()
        for c in channels:
            # Wrongly implemented? If channel is already subscribed we simply add the callbacks to the existing channel
            # but the redis_event could be different with different channels?
            # or since channels are built they should be the same/not exists hence bueno?
            if c not in self.events:
                self.pubsub.subscribe(c)
                self.events[c] = EventHandler(redis_event, callbacks,
                                              deserialize)
            else:
                for callback in callbacks:
                    if callback not in self.events[c].callbacks:
                        self.events[c].callbacks.append(callback)

    def psubscribe_event(self,
                         redis_event: RedisEvent,
                         callbacks=None,
                         deserialize=True):
        if not isinstance(callbacks, list):
            callbacks = [callbacks]
            callbacks = list(set(callbacks))

        channel = f'{redis_event.channel}*'
        if channel not in self.events:
            self.pubsub.psubscribe(channel)
            self.events[channel] = EventHandler(redis_event, callbacks,
                                                deserialize)
        else:
            for callback in callbacks:
                if callback not in self.events[channel].callbacks:
                    self.events[channel].callbacks.extend(callbacks)

    def run(self):
        self.logger.info(f'subscribed to channels {list(self.events.keys())}')

        if not self.events:
            self.logger.warning('no events subscribed, will run forever')
            while True:
                time.sleep(1)


        for message in self.pubsub.listen():
            if message and message['type'] in ['message', 'pmessage']:
                self.__handle_message(message)

    def __handle_message(self, message):
        channel = message['pattern'] or message['channel']
        event_handler: EventHandler = self.events.get(channel)

        if event_handler.event not in [OrderBookEvent, TradeEvent]:
            self.logger.debug(f'handling {event_handler} with message {message}')
        if not event_handler:
            self.logger.warning(f'unknown channel {channel}')
            return
        try:
            if event_handler.deserialize:
                payload = event_handler.event.deserialize(message['data'])
            else:
                payload = message['data']
            for callback in event_handler.callbacks:
                callback(payload)
        except Exception:
            self.logger.error(traceback.format_exc())

    def __publish_payload(self,
                          redis_event: RedisEvent,
                          payload,
                          channel=None):
        if channel is None:
            channel = redis_event.channel
            if hasattr(payload, 'instr_id'):
                channel += f':{payload.instr_id}'
            elif hasattr(payload, 'exchange_id'):
                channel += f':{payload.exchange_id}'
            elif hasattr(payload, 'trigger_id'):
                channel += f':{payload.trigger_id}'
            elif hasattr(payload, 'sentinel_id'):
                channel += f':{payload.sentinel_id}'

        payload = redis_event.serialize(payload)
        if redis_event.channel not in [OrderBookEvent.channel, TradeEvent.channel]:
            self.logger.debug(f'publishing on {channel} payload {payload}')
        self.redis_instance.publish(channel, payload)

    def publish_event(self, redis_event: RedisEvent, payload=None):
        # pass payload to XxxRedis and use his setter to remove math case

        if redis_event.channel not in [OrderBookEvent.channel, TradeEvent.channel]:
            self.logger.debug(f'publishing {redis_event} with payload {payload}')
        match redis_event():
            case OrderExchangeEvent() | CancelOrderEvent():
                channel = f'{redis_event.channel}:{payload.exchange_id}'
                self.__publish_payload(redis_event, payload, channel)
            case CancelAllOrdersInstrEvent():
                channel = f'{redis_event.channel}:{payload.exchange.id}'
                self.__publish_payload(redis_event, payload, channel)
            case OrderDBEvent() | StrategyInfoDBEvent():
                self.__publish_payload(redis_event, payload, redis_event.channel)
            case RedisEvent():
                self.__publish_payload(redis_event, payload)
            case _:
                self.logger.warning(f'unknown event {redis_event}')
