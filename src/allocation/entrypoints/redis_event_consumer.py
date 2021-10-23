from collections import deque
import json
import logging
import redis
from typing import Dict, Callable
from allocation import config
from allocation import bootstrap
from allocation.domain import commands
from allocation.service_layer import message_bus

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())


def main():
    logger.info("Redis pubsub starting")
    bus = bootstrap.bootstrap(message_queue_factory=deque)
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(*CHANNELS)

    for msg in pubsub.listen():
        handle(msg, bus)


def handle(msg, bus: message_bus.MessageBus):
    channel = str(msg["channel"], "utf-8")
    handler = HANDLERS[channel]
    handler(msg, bus)


def handle_change_batch_quantity(msg, bus: message_bus.MessageBus):
    logging.debug(f"handling {msg}")
    data = json.loads(msg["data"])
    cmd = commands.ChangeBatchQuantity(
        data["reference"], data["sku"], data["qty"]
    )
    bus.handle(cmd)


def handle_allocate(msg, bus: message_bus.MessageBus):
    logging.debug(f"handling {msg}")
    data = json.loads(msg["data"])
    cmd = commands.Allocate(data["order_id"], data["sku"], data["qty"])
    bus.handle(cmd)


HANDLERS = {
    "change_batch_quantity": handle_change_batch_quantity,
    "allocate": handle_allocate,
}  # type: Dict[str, Callable]

CHANNELS = list(HANDLERS.keys())
if __name__ == "__main__":
    main()
