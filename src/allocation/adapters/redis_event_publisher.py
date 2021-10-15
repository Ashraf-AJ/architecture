import json
import logging
from dataclasses import asdict
import redis
from allocation import config
from allocation.domain import events

r = redis.Redis(**config.get_redis_host_and_port())
logger = logging.getLogger(__name__)


def publish_message(channel, event: events.Event):
    logger.debug(f"publishing: channel={channel}, event={event}")
    r.publish(channel, json.dumps(asdict(event)))
