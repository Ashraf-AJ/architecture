from typing import Iterable
from unittest import mock
import pytest
from allocation.adapters import repository
from allocation.domain import model
from allocation.service_layer import services, unit_of_work


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
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)

    assert "batch1" in [
        b.reference for b in uow.products.get("SIMPLE-LAMP").batches
    ]
    assert uow.committed is True


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)
    services.add_batch("batch2", "SIMPLE-LAMP", 100, None, uow)
    assert "batch2" in [
        b.reference for b in uow.products.get("SIMPLE-LAMP").batches
    ]


def test_returns_allocations():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)
    batch_ref = services.allocate("order1", "SIMPLE-LAMP", 10, uow)

    assert batch_ref == "batch1"


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)
    with pytest.raises(services.InvalidSku, match="NONEXISTINGSKU"):
        services.allocate("order1", "NONEXISTINGSKU", 10, uow)


def test_commits():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)
    services.allocate("order1", "SIMPLE-LAMP", 10, uow)
    assert uow.committed is True


def test_sends_email_on_out_of_stock_error():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 10, None, uow)
    with mock.patch("allocation.adapters.email.send_email") as mock_send_email:
        services.allocate("order1", "SIMPLE-LAMP", 20, uow)
        assert mock_send_email.call_args == mock.call(
            "test@example.com", "out of stock SIMPLE-LAMP"
        )
