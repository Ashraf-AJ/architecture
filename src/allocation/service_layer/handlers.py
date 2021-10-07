from allocation.adapters import email
from allocation.domain import model, events
from allocation.service_layer.unit_of_work import AbstractUnitOfWork


class InvalidSku(Exception):
    pass


def allocate(event: events.AllocationRequired, uow: AbstractUnitOfWork) -> str:
    with uow:
        product = uow.products.get(event.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {event.sku}")
        batch_ref = product.allocate(
            model.OrderLine(event.order_id, event.sku, event.qty)
        )
        uow.commit()
    return batch_ref


def add_batch(
    event: events.BatchCreated,
    uow: AbstractUnitOfWork,
) -> None:
    with uow:
        product = uow.products.get(event.sku)
        if product is None:
            product = model.Product(event.sku, [])
            uow.products.add(product)

        product.batches.append(
            model.Batch(event.reference, event.sku, event.qty, event.eta)
        )
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock, uow: AbstractUnitOfWork
):
    email.send_email("test@example.com", f"out of stock {event.sku}")


def change_batch_quantity(
    event: events.BatchQuantityChanged, uow: AbstractUnitOfWork
):
    with uow:
        product = uow.products.get(event.sku)
        product.change_batch_quantity(event.reference, event.sku, event.qty)
        uow.commit()
