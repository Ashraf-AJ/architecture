from typing import Iterable, List
import pytest
from adapters import repository
from domain import model
from service_layer import services, unit_of_work


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches: Iterable[model.Batch]) -> None:
        self._batches = set(batches)

    def add(self, batch: model.Batch) -> None:
        self._batches.add(batch)

    def get(self, reference: str) -> model.Batch:
        return next(b for b in self._batches if b.reference == reference)

    def list(self) -> List[model.Batch]:
        return list(self._batches)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self) -> None:
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


def test_add_batch():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)
    assert uow.batches.get("batch1") is not None
    assert uow.committed is True


def test_returns_allocations():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)
    batch_ref = services.allocate("order1", "SIMPLE-LAMP", 10, uow)

    assert batch_ref == "batch1"


def test_error_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)
    with pytest.raises(services.InvalidSku, match="NONEXISTINGSKU"):
        services.allocate("order1", "NONEXISTINGSKU", 10, uow)


def test_commits():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, uow)
    services.allocate("order1", "SIMPLE-LAMP", 10, uow)
    assert uow.committed is True
