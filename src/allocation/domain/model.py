from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from allocation.domain import events


class OutOfStock(Exception):
    pass


@dataclass(unsafe_hash=True)
class OrderLine:
    order_id: str
    sku: str
    qty: int


class Batch:
    def __init__(
        self,
        ref: str,
        sku: str,
        qty: int,
        eta: Optional[date],
    ) -> None:
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations = set()  # type: set[OrderLine]

    def __eq__(self, other):
        if not isinstance(other, Batch):
            return False
        return self.reference == other.reference

    def __hash__(self):
        return hash(self.reference)

    def __gt__(self, other):
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def allocate(self, line: OrderLine) -> None:
        if self.can_allocate(line):
            self._allocations.add(line)

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty

    def deallocate_one(self) -> OrderLine:
        return self._allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity


class Product:
    def __init__(
        self, sku: str, batches: List[Batch], version_number: int = 0
    ) -> None:
        self.sku = sku
        self.batches = batches
        self.version_number = version_number
        self.events = []  # type: List[events.Event]

    def allocate(self, line: OrderLine) -> str:
        try:
            batch: Batch = next(
                b for b in sorted(self.batches) if b.can_allocate(line)
            )
            batch.allocate(line)
            self.version_number += 1
            return batch.reference
        except StopIteration:
            self.events.append(events.OutOfStock(line.sku))
            # raise OutOfStock(f"Out of stock for sku {line.sku}")
            return None

    def change_batch_quantity(self, reference: str, sku: str, qty: int):
        batch: Batch = next(
            b for b in self.batches if b.reference == reference
        )
        batch._purchased_quantity = qty
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.events.append(
                events.AllocationRequired(line.order_id, line.sku, line.qty)
            )
