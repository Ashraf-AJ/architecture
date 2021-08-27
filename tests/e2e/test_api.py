import pytest
import requests
from allocation import config
from tests.random_refs import random_batchref, random_sku, random_orderid


def post_to_add_batch(reference, sku, qty, eta):
    url = config.get_api_url()
    r = requests.post(
        f"{url}/batches",
        json={"reference": reference, "sku": sku, "qty": qty, "eta": eta},
    )
    assert r.status_code == 201


@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_201_and_allocated_batch():
    sku, other_sku = random_sku(), random_sku("other")
    early_batch = random_batchref(1)
    later_batch = random_batchref(2)
    other_batch = random_batchref(3)
    post_to_add_batch(later_batch, sku, 100, "2010-01-03")
    post_to_add_batch(early_batch, sku, 100, "2010-01-01")
    post_to_add_batch(other_batch, other_sku, 100, None)
    order_line = {"order_id": random_orderid(1), "sku": sku, "qty": 10}

    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json=order_line)

    assert r.status_code == 201
    assert r.json()["batch_ref"] == early_batch


@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    invalid_sku, order_id = random_sku(), random_orderid()
    line = {"order_id": order_id, "sku": invalid_sku, "qty": 10}
    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json=line)
    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid sku {invalid_sku}"
