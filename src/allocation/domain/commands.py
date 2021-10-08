from dataclasses import dataclass
from typing import Optional
from datetime import date


class Command:
    pass


@dataclass
class CreateBatch(Command):
    reference: str
    sku: str
    qty: int
    eta: Optional[date] = None


@dataclass
class Allocate(Command):
    order_id: str
    sku: str
    qty: int


@dataclass
class ChangeBatchQuantity(Command):
    reference: str
    sku: str
    qty: int
