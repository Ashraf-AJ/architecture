import json
import logging
import redis

from allocation import config
from allocation.domain import commands
from allocation.adapters import orm
from allocation.service_layer import message_bus, unit_of_work

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())

CHANNELS = ["change_batch_quantity", "allocate"]


def main():
    orm.start_mappers()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(*CHANNELS)

    for msg in pubsub.listen():
        handle(msg)


def handle(msg):
    channel = str(msg["channel"], "utf-8")
    handler = HANDLERS[channel]
    handler(msg)


def handle_change_batch_quantity(msg):
    logging.debug(f"handling {msg}")
    data = json.loads(msg["data"])
    cmd = commands.ChangeBatchQuantity(
        data["reference"], data["sku"], data["qty"]
    )
    message_bus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())


def handle_allocate(msg):
    logging.debug(f"handling {msg}")
    data = json.loads(msg["data"])
    cmd = commands.Allocate(data["order_id"], data["sku"], data["qty"])
    message_bus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())


HANDLERS = {
    "change_batch_quantity": handle_change_batch_quantity,
    "allocate": handle_allocate,
}

if __name__ == "__main__":
    main()
