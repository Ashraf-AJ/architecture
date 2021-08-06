from datetime import date
from typing import Iterable, Optional
from domain import model
from adapters import repository


class InvalidSku(Exception):
    pass


def is_valid(sku: str, batches: Iterable[model.Batch]) -> bool:
    return sku in {b.sku for b in batches}


def allocate(
    order_id: str, sku: str, qty: int, repo: repository.RepositoryBase, session
) -> str:
    batches = repo.list()
    if not is_valid(sku, batches):
        raise InvalidSku(f"Invalid sku {sku}")
    batch_ref = model.allocate(model.OrderLine(order_id, sku, qty), batches)
    session.commit()
    return batch_ref


def add_batch(
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    repo: repository.RepositoryBase,
    session,
) -> None:
    repo.add(model.Batch(reference, sku, qty, eta))
    session.commit()
