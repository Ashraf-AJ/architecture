from datetime import date
import pytest
from unittest import mock
from collections import deque

from sqlalchemy.orm import clear_mappers
from allocation import views
from allocation import bootstrap
from allocation.domain import commands
from allocation.service_layer import unit_of_work
from tests.random_refs import random_batchref, random_orderid, random_sku

today = date.today()


@pytest.fixture
def message_bus(in_memory_session_factory):
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(in_memory_session_factory),
        message_queue_factory=deque,
        publish=lambda *args, **kwargs: None,
        notifications=mock.Mock(),
    )
    yield bus
    clear_mappers()


def test_allocations_view(message_bus):
    ready_batch, later_batch, other_later_batch = (
        random_batchref("ready"),
        random_batchref("later"),
        random_batchref("other-later"),
    )
    sku1, sku2 = random_sku(1), random_sku(2)
    order, other_order = random_orderid(), random_orderid()
    message_bus.handle(commands.CreateBatch(ready_batch, sku1, 50, None))
    message_bus.handle(commands.CreateBatch(later_batch, sku2, 50, today))
    message_bus.handle(commands.Allocate(order, sku1, 20))
    message_bus.handle(commands.Allocate(order, sku2, 20))
    # add a spurious batch and order to make sure we're getting the right ones
    message_bus.handle(
        commands.CreateBatch(other_later_batch, sku1, 50, today)
    )
    message_bus.handle(commands.Allocate(other_order, sku1, 30))
    message_bus.handle(commands.Allocate(other_order, sku2, 10))

    assert views.allocations(order, message_bus.uow) == [
        {"sku": sku1, "batch_ref": ready_batch},
        {"sku": sku2, "batch_ref": later_batch},
    ]


def test_deallocation(message_bus):
    batch1, batch2 = random_batchref(1), random_batchref(2)
    sku = random_sku()
    order = random_orderid()
    message_bus.handle(commands.CreateBatch(batch1, sku, 50, None))
    message_bus.handle(commands.CreateBatch(batch2, sku, 50, today))
    message_bus.handle(commands.Allocate(order, sku, 40))
    message_bus.handle(commands.ChangeBatchQuantity(batch1, sku, 10))

    assert views.allocations(order, message_bus.uow) == [
        {"sku": sku, "batch_ref": batch2},
    ]
