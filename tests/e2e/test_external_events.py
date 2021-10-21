import json
import pytest
from tenacity import Retrying, stop_after_delay
from . import api_client, redis_client
from ..random_refs import random_batchref, random_orderid, random_sku


@pytest.mark.usefixtures("restart_api", "postgres_db", "restart_redis_pubsub")
def test_change_batch_quantity_leads_to_reallocation():
    early_batch, late_batch = random_batchref("early"), random_batchref("late")
    sku, order_id = random_sku(), random_orderid()
    api_client.post_to_add_batch(early_batch, sku, 20, "2021-12-12")
    api_client.post_to_add_batch(late_batch, sku, 20, "2021-12-14")

    api_client.post_to_allocate(order_id, sku, 15)
    response = api_client.get_allocations(order_id)
    assert response.json() == [{"sku": sku, "batch_ref": early_batch}]

    subscription = redis_client.subscribe_to("line_allocated")

    redis_client.publish_message(
        "change_batch_quantity",
        {"reference": early_batch, "sku": sku, "qty": 10},
    )

    messages = []
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                messages.append(message)
                print(message)
            data = json.loads(messages[-1]["data"])
            assert data["order_id"] == order_id
            assert data["batch_ref"] == late_batch


@pytest.mark.usefixtures("restart_api", "postgres_db", "restart_redis_pubsub")
def test_allocate_leads_to_allocation():
    batch_ref = random_batchref()
    sku, order_id = random_sku(), random_orderid()
    api_client.post_to_add_batch(batch_ref, sku, 20, None)

    subscription = redis_client.subscribe_to("line_allocated")

    redis_client.publish_message(
        "allocate",
        {"order_id": order_id, "sku": sku, "qty": 10},
    )

    messages = []
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                messages.append(message)
                print(message)
            data = json.loads(messages[-1]["data"])
            assert data["order_id"] == order_id
            assert data["batch_ref"] == batch_ref
