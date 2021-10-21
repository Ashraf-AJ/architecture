from datetime import date
from allocation import views
from allocation.domain import commands
from allocation.service_layer import message_bus, unit_of_work
from tests.random_refs import random_batchref, random_orderid, random_sku

today = date.today()


def test_allocations_view(pg_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(pg_session_factory)
    ready_batch, later_batch, other_later_batch = (
        random_batchref("ready"),
        random_batchref("later"),
        random_batchref("other-later"),
    )
    sku1, sku2 = random_sku(1), random_sku(2)
    order, other_order = random_orderid(), random_orderid()
    message_bus.handle(commands.CreateBatch(ready_batch, sku1, 50, None), uow)
    message_bus.handle(commands.CreateBatch(later_batch, sku2, 50, today), uow)
    message_bus.handle(commands.Allocate(order, sku1, 20), uow)
    message_bus.handle(commands.Allocate(order, sku2, 20), uow)
    # add a spurious batch and order to make sure we're getting the right ones
    message_bus.handle(
        commands.CreateBatch(other_later_batch, sku1, 50, today), uow
    )
    message_bus.handle(commands.Allocate(other_order, sku1, 30), uow)
    message_bus.handle(commands.Allocate(other_order, sku2, 10), uow)

    assert views.allocations(order, uow) == [
        {"sku": sku1, "batch_ref": ready_batch},
        {"sku": sku2, "batch_ref": later_batch},
    ]


def test_deallocation(pg_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(pg_session_factory)
    batch1, batch2 = random_batchref(1), random_batchref(2)
    sku = random_sku()
    order = random_orderid()
    message_bus.handle(commands.CreateBatch(batch1, sku, 50, None), uow)
    message_bus.handle(commands.CreateBatch(batch2, sku, 50, today), uow)
    message_bus.handle(commands.Allocate(order, sku, 40), uow)
    message_bus.handle(commands.ChangeBatchQuantity(batch1, sku, 10), uow)

    assert views.allocations(order, uow) == [
        {"sku": sku, "batch_ref": batch2},
    ]
