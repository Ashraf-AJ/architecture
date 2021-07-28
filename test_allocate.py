from datetime import date, timedelta
import pytest
from model import Batch, OrderLine, allocate, OutOfStock

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_current_stock_batches_to_shipments():
    sku = "RETRO-CLOCK"
    in_stock_batch = Batch("in-stock-batch", sku, 100, eta=None)
    shipment_batch = Batch("shipment-batch", sku, 100, eta=tomorrow)
    line = OrderLine("oref", sku, 10)
    allocate(line, [shipment_batch, in_stock_batch])
    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches():
    sku = "MINIMALIST-SPOON"
    earliest = Batch("speedy-batch", sku, 100, eta=today)
    medium = Batch("normal-batch", sku, 100, eta=tomorrow)
    latest = Batch("slow-batch", sku, 100, eta=later)
    line = OrderLine("oref", sku, 10)
    allocate(line, [medium, earliest, latest])
    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref():
    sku = "HIGHBROWPOSTER"
    in_stock_batch = Batch("in-stock-batch-ref", sku, 100, eta=None)
    shipment_batch = Batch("shipment-batch-ref", sku, 100, eta=tomorrow)
    line = OrderLine("oref", sku, 10)
    allocation = allocate(line, [in_stock_batch, shipment_batch])
    assert allocation == in_stock_batch.reference


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = Batch("batch1", "SMALL-TABLE", 10, eta=tomorrow)
    allocate(OrderLine("order1", "SMALL-TABLE", 10), [batch])
    with pytest.raises(OutOfStock, match="SMALL-TABLE"):
        allocate(OrderLine("order2", "SMALL-TABLE", 1), [batch])
