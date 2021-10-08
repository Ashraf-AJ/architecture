from datetime import date
from typing import Iterable
from unittest import mock
import pytest
from allocation.adapters import repository
from allocation.domain import events, model, commands
from allocation.service_layer import handlers, message_bus, unit_of_work

today = date.today()


class FakeRepository(repository.AbstractRepository):
    def __init__(self, products: Iterable[model.Product]) -> None:
        super().__init__()
        self._products = set(products)

    def _add(self, product: model.Product) -> None:
        self._products.add(product)

    def _get(self, sku: str) -> model.Product:
        return next((b for b in self._products if b.sku == sku), None)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self) -> None:
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


def test_add_batch():
    uow = FakeUnitOfWork()
    message_bus.handle(
        commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None), uow
    )

    assert "batch1" in [
        b.reference for b in uow.products.get("SIMPLE-LAMP").batches
    ]
    assert uow.committed is True


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()
    message_bus.handle(
        commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None), uow
    )

    message_bus.handle(
        commands.CreateBatch("batch2", "SIMPLE-LAMP", 100, None), uow
    )

    assert "batch2" in [
        b.reference for b in uow.products.get("SIMPLE-LAMP").batches
    ]


def test_returns_allocations():
    uow = FakeUnitOfWork()
    message_bus.handle(
        commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None), uow
    )

    results = message_bus.handle(
        commands.Allocate("order1", "SIMPLE-LAMP", 10), uow
    )

    assert "batch1" == results.pop(0)


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    message_bus.handle(
        commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None), uow
    )

    with pytest.raises(handlers.InvalidSku, match="NONEXISTINGSKU"):
        message_bus.handle(
            commands.Allocate("order1", "NONEXISTINGSKU", 10), uow
        )


def test_commits():
    uow = FakeUnitOfWork()
    message_bus.handle(
        commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None), uow
    )

    message_bus.handle(commands.Allocate("order1", "SIMPLE-LAMP", 10), uow)

    assert uow.committed is True


def test_sends_email_on_out_of_stock_error():
    uow = FakeUnitOfWork()
    message_bus.handle(
        commands.CreateBatch("batch1", "SIMPLE-LAMP", 10, None), uow
    )

    with mock.patch("allocation.adapters.email.send_email") as mock_send_email:
        message_bus.handle(commands.Allocate("order1", "SIMPLE-LAMP", 20), uow)
        assert mock_send_email.call_args == mock.call(
            "test@example.com", "out of stock SIMPLE-LAMP"
        )


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        uow = FakeUnitOfWork()
        sku = "ROUND-TABLE"
        message_bus.handle(commands.CreateBatch("batch1", sku, 100, None), uow)

        [batch1] = uow.products.get(sku).batches

        assert batch1.available_quantity == 100

        message_bus.handle(
            commands.ChangeBatchQuantity("batch1", sku, 50), uow
        )

        assert batch1.available_quantity == 50

    def test_reallocates_if_necessary(self):
        uow = FakeUnitOfWork()
        sku = "FLAT-TABLE"
        message_history = [
            commands.CreateBatch("batch1", sku, 50, None),
            commands.CreateBatch("batch2", sku, 50, today),
            commands.Allocate("order1", sku, 20),
            commands.Allocate("order2", sku, 20),
        ]
        for message in message_history:
            message_bus.handle(message, uow)

        [batch1, batch2] = uow.products.get(sku).batches

        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        # the batch quantity changed 50 -> 25
        message_bus.handle(
            commands.ChangeBatchQuantity("batch1", sku, 25), uow
        )
        # one of the orders will be deallocated
        # batch(25) - order(20) = batch(5)
        assert batch1.available_quantity == 5
        # the deallocated order will be allocated to the other available batch
        # batch(50) - order(20) = batch(30)
        assert batch2.available_quantity == 30
