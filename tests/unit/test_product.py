from datetime import date, timedelta
import pytest
from allocation.domain.model import Batch, OrderLine, Product, OutOfStock

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_current_stock_batches_to_shipments():
    sku = "RETRO-CLOCK"
    in_stock_batch = Batch("in-stock-batch", sku, 100, eta=None)
    shipment_batch = Batch("shipment-batch", sku, 100, eta=tomorrow)
    product = Product(sku, [in_stock_batch, shipment_batch])
    line = OrderLine("oref", sku, 10)

    product.allocate(line)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches():
    sku = "MINIMALIST-SPOON"
    earliest = Batch("speedy-batch", sku, 100, eta=today)
    medium = Batch("normal-batch", sku, 100, eta=tomorrow)
    latest = Batch("slow-batch", sku, 100, eta=later)
    product = Product(sku, [medium, latest, earliest])
    line = OrderLine("oref", sku, 10)

    product.allocate(line)

    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref():
    sku = "HIGHBROWPOSTER"
    in_stock_batch = Batch("in-stock-batch-ref", sku, 100, eta=None)
    shipment_batch = Batch("shipment-batch-ref", sku, 100, eta=tomorrow)
    product = Product(sku, [shipment_batch, in_stock_batch])
    line = OrderLine("oref", sku, 10)
    allocation = product.allocate(line)
    assert allocation == in_stock_batch.reference


def test_raises_out_of_stock_exception_if_cannot_allocate():
    sku = "SMALL-TABLE"
    batch = Batch("batch1", sku, 10, eta=tomorrow)
    product = Product(sku, [batch])
    product.allocate(OrderLine("order1", sku, 10))
    with pytest.raises(OutOfStock, match=sku):
        product.allocate(OrderLine("order2", sku, 1))


def test_increments_version_number():
    sku = "SMALL-TABLE"
    batch = Batch("batch1", sku, 100, eta=tomorrow)
    product = Product(sku, [batch])
    line = OrderLine("order1", sku, 10)
    product.version_number = 2
    assert product.version_number == 2

    product.allocate(line)

    assert product.version_number == 3
