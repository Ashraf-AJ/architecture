from datetime import date
from typing import Iterable, Optional
from domain import model
from adapters import repository
from service_layer.unit_of_work import AbstractUnitOfWork


class InvalidSku(Exception):
    pass


def is_valid(sku: str, batches: Iterable[model.Batch]) -> bool:
    return sku in {b.sku for b in batches}


def allocate(
    order_id: str, sku: str, qty: int, uow: AbstractUnitOfWork
) -> str:
    with uow:
        batches = uow.batches.list()
        if not is_valid(sku, batches):
            raise InvalidSku(f"Invalid sku {sku}")
        batch_ref = model.allocate(
            model.OrderLine(order_id, sku, qty), batches
        )
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
        uow.batches.add(model.Batch(reference, sku, qty, eta))
        uow.commit()
