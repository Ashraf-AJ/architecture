from typing import Iterable, List
import pytest
from adapters import repository
from domain import model
from service_layer import services


class FakeRepository(repository.RepositoryBase):
    def __init__(self, batches: Iterable[model.Batch]) -> None:
        self._batches = set(batches)

    def add(self, batch: model.Batch) -> None:
        self._batches.add(batch)

    def get(self, reference: str) -> model.Batch:
        return next(b for b in self._batches if b.reference == reference)

    def list(self) -> List[model.Batch]:
        return list(self._batches)


class FakeSession:
    committed: bool = False

    def commit(self) -> None:
        self.committed = True


def test_add_batch():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, repo, session)
    assert repo.get("batch1") is not None
    assert session.committed is True


def test_returns_allocations():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, repo, session)
    batch_ref = services.allocate("order1", "SIMPLE-LAMP", 10, repo, session)

    assert batch_ref == "batch1"


def test_error_for_invalid_sku():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, repo, session)
    with pytest.raises(services.InvalidSku, match="NONEXISTINGSKU"):
        services.allocate("order1", "NONEXISTINGSKU", 10, repo, session)


def test_commits():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("batch1", "SIMPLE-LAMP", 100, None, repo, session)
    services.allocate("order1", "SIMPLE-LAMP", 10, repo, session)
    assert session.committed is True
