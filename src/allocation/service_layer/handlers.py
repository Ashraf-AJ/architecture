from allocation.adapters import email, redis_event_publisher
from allocation.domain import commands, model, events
from allocation.service_layer.unit_of_work import AbstractUnitOfWork


class InvalidSku(Exception):
    pass


def allocate(command: commands.Allocate, uow: AbstractUnitOfWork) -> str:
    with uow:
        product = uow.products.get(command.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {command.sku}")
        batch_ref = product.allocate(
            model.OrderLine(command.order_id, command.sku, command.qty)
        )
        uow.commit()
    return batch_ref


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
    event: events.OutOfStock, uow: AbstractUnitOfWork
):
    email.send_email("test@example.com", f"out of stock {event.sku}")


def change_batch_quantity(
    command: commands.ChangeBatchQuantity, uow: AbstractUnitOfWork
):
    with uow:
        product = uow.products.get(command.sku)
        product.change_batch_quantity(
            command.reference, command.sku, command.qty
        )
        uow.commit()


def publish_allocated_event(event: events.Allocated, uow: AbstractUnitOfWork):
    redis_event_publisher.publish_message("line_allocated", event)
