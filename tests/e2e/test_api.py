import pytest
from . import api_client
from tests.random_refs import random_batchref, random_sku, random_orderid


@pytest.mark.usefixtures("restart_api", "postgres_db")
def test_happy_path_returns_201_and_allocated_batch():
    sku, other_sku = random_sku(), random_sku("other")
    early_batch = random_batchref(1)
    later_batch = random_batchref(2)
    other_batch = random_batchref(3)
    api_client.post_to_add_batch(later_batch, sku, 100, "2010-01-03")
    api_client.post_to_add_batch(early_batch, sku, 100, "2010-01-01")
    api_client.post_to_add_batch(other_batch, other_sku, 100, None)

    r = api_client.post_to_allocate(
        order_id=random_orderid(), sku=sku, qty=10, expect_success=True
    )

    assert r.json()["batch_ref"] == early_batch


@pytest.mark.usefixtures("restart_api", "postgres_db")
def test_unhappy_path_returns_400_and_error_message():
    invalid_sku, order_id = random_sku(), random_orderid()
    r = api_client.post_to_allocate(
        order_id=order_id, sku=invalid_sku, qty=10, expect_success=False
    )
    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid sku {invalid_sku}"
