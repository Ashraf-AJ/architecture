from dataclasses import asdict
from typing import Callable, Type, Dict, List
from allocation.adapters.notifications import AbstractNotifications
from allocation.domain import commands, model, events
from allocation.service_layer.unit_of_work import (
    AbstractUnitOfWork,
    SqlAlchemyUnitOfWork,
)


class InvalidSku(Exception):
    pass


def allocate(command: commands.Allocate, uow: AbstractUnitOfWork) -> str:
    with uow:
        product = uow.products.get(command.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {command.sku}")
        product.allocate(
            model.OrderLine(command.order_id, command.sku, command.qty)
        )
        uow.commit()


def reallocate(event: events.Deallocated, uow: AbstractUnitOfWork):
    with uow:
        product = uow.products.get(event.sku)
        product.events.append(commands.Allocate(**asdict(event)))
        uow.commit()


def add_batch(
    command: commands.CreateBatch,
    uow: AbstractUnitOfWork,
) -> None:
    with uow:
        product = uow.products.get(command.sku)
        if product is None:
            product = model.Product(command.sku, batches=[])
            uow.products.add(product)

        product.batches.append(
            model.Batch(
                command.reference, command.sku, command.qty, command.eta
            )
        )
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock, notifications: AbstractNotifications
):
    notifications.send("test@example.com", f"out of stock {event.sku}")


def change_batch_quantity(
    command: commands.ChangeBatchQuantity, uow: AbstractUnitOfWork
):
    with uow:
        product = uow.products.get(command.sku)
        product.change_batch_quantity(
            command.reference, command.sku, command.qty
        )
        uow.commit()


def publish_allocated_event(event: events.Allocated, publish: Callable):
    publish("line_allocated", event)


def add_allocation_to_read_model(
    event: events.Allocated, uow: SqlAlchemyUnitOfWork
):
    with uow:
        uow.session.execute(
            """
            INSERT INTO allocations_view (order_id, sku, batch_ref)
            VALUES (:order_id, :sku, :batch_ref)
            """,
            dict(
                order_id=event.order_id,
                sku=event.sku,
                batch_ref=event.batch_ref,
            ),
        )
        uow.commit()


def remove_allocation_from_read_model(
    event: events.Deallocated, uow: SqlAlchemyUnitOfWork
):
    with uow:
        uow.session.execute(
            "DELETE FROM allocations_view WHERE sku= :sku AND order_id= :order_id",
            dict(sku=event.sku, order_id=event.order_id),
        )
        uow.commit()


EVENT_HANDLERS = {
    events.OutOfStock: [send_out_of_stock_notification],
    events.Allocated: [
        publish_allocated_event,
        add_allocation_to_read_model,
    ],
    events.Deallocated: [
        reallocate,
        remove_allocation_from_read_model,
    ],
}  # type: Dict[Type[events.Event], List[Callable]]

COMMAND_HANDLERS = {
    commands.Allocate: allocate,
    commands.CreateBatch: add_batch,
    commands.ChangeBatchQuantity: change_batch_quantity,
}  # type: Dict[Type[commands.Command], Callable]
