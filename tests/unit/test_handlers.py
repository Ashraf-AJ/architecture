from datetime import date
from typing import Iterable, Dict, List
from unittest import mock
from collections import defaultdict, deque
import pytest
from allocation import bootstrap
from allocation.adapters import repository
from allocation.adapters.notifications import AbstractNotifications
from allocation.domain import model, commands
from allocation.service_layer import handlers, unit_of_work

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


class FakeNotifications(AbstractNotifications):
    def __init__(self):
        self.sent = defaultdict(list)  # type: Dict[str, List[str]]

    def send(self, destination, message):
        self.sent[destination].append(message)


def bootstrap_test_app():
    return bootstrap.bootstrap(
        start_orm=False,
        uow=FakeUnitOfWork(),
        notifications=FakeNotifications(),
        message_queue_factory=deque,
        publish=lambda *args, **kwargs: None,
    )


class TestAddBatch:
    def test_add_batch(self):
        message_bus = bootstrap_test_app()
        message_bus.handle(
            commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None),
        )

        assert "batch1" in [
            b.reference
            for b in message_bus.uow.products.get("SIMPLE-LAMP").batches
        ]
        assert message_bus.uow.committed is True

    def test_add_batch_for_existing_product(self):
        message_bus = bootstrap_test_app()
        message_bus.handle(
            commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None),
        )

        message_bus.handle(
            commands.CreateBatch("batch2", "SIMPLE-LAMP", 100, None),
        )

        assert "batch2" in [
            b.reference
            for b in message_bus.uow.products.get("SIMPLE-LAMP").batches
        ]


class TestAllocate:
    def test_allocates(self):
        message_bus = bootstrap_test_app()
        message_bus.handle(
            commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None)
        )

        message_bus.handle(commands.Allocate("order1", "SIMPLE-LAMP", 10))

        [batch] = message_bus.uow.products.get("SIMPLE-LAMP").batches

        assert batch.available_quantity == 90

    def test_allocate_errors_for_invalid_sku(self):
        message_bus = bootstrap_test_app()
        message_bus.handle(
            commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None)
        )

        with pytest.raises(handlers.InvalidSku, match="NONEXISTINGSKU"):
            message_bus.handle(
                commands.Allocate("order1", "NONEXISTINGSKU", 10)
            )

    def test_commits(self):
        message_bus = bootstrap_test_app()
        message_bus.handle(
            commands.CreateBatch("batch1", "SIMPLE-LAMP", 100, None)
        )

        message_bus.handle(commands.Allocate("order1", "SIMPLE-LAMP", 10))

        assert message_bus.uow.committed is True

    def test_sends_email_on_out_of_stock_error(self):
        fake_notifs = FakeNotifications()
        message_bus = bootstrap.bootstrap(
            message_queue_factory=deque, notifications=fake_notifs
        )
        message_bus.handle(
            commands.CreateBatch("batch1", "SIMPLE-LAMP", 10, None)
        )
        message_bus.handle(commands.Allocate("order1", "SIMPLE-LAMP", 20))
        assert fake_notifs.sent["test@example.com"] == [
            "out of stock SIMPLE-LAMP"
        ]


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        message_bus = bootstrap_test_app()
        sku = "ROUND-TABLE"
        message_bus.handle(commands.CreateBatch("batch1", sku, 100, None))

        [batch1] = message_bus.uow.products.get(sku).batches

        assert batch1.available_quantity == 100

        message_bus.handle(commands.ChangeBatchQuantity("batch1", sku, 50))

        assert batch1.available_quantity == 50

    def test_reallocates_if_necessary(self):
        message_bus = bootstrap_test_app()
        sku = "FLAT-TABLE"
        message_history = [
            commands.CreateBatch("batch1", sku, 50, None),
            commands.CreateBatch("batch2", sku, 50, today),
            commands.Allocate("order1", sku, 20),
            commands.Allocate("order2", sku, 20),
        ]
        for message in message_history:
            message_bus.handle(message)

        [batch1, batch2] = message_bus.uow.products.get(sku).batches

        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        # the batch quantity changed 50 -> 25
        message_bus.handle(commands.ChangeBatchQuantity("batch1", sku, 25))
        # one of the orders will be deallocated
        # batch(25) - order(20) = batch(5)
        assert batch1.available_quantity == 5
        # the deallocated order will be allocated to the other available batch
        # batch(50) - order(20) = batch(30)
        assert batch2.available_quantity == 30
