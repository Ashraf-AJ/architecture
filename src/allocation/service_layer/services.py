from datetime import date
from typing import Optional
from allocation.domain import model
from allocation.service_layer.unit_of_work import AbstractUnitOfWork


class InvalidSku(Exception):
    pass


def allocate(
    order_id: str, sku: str, qty: int, uow: AbstractUnitOfWork
) -> str:
    with uow:
        product = uow.products.get(sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {sku}")
        batch_ref = product.allocate(model.OrderLine(order_id, sku, qty))
        uow.commit()
    return batch_ref


def add_batch(
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: AbstractUnitOfWork,
) -> None:
    with uow:
        product = uow.products.get(sku)
        if product is None:
            product = model.Product(sku, [])
            uow.products.add(product)

        product.batches.append(model.Batch(reference, sku, qty, eta))
        uow.commit()
