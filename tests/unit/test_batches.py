from datetime import date
from typing import Tuple
import pytest
from allocation.domain.model import Batch, OrderLine


def make_batch_and_line(
    sku: str, batch_qty: int, line_qty: int
) -> Tuple[Batch, OrderLine]:
    return (
        Batch("batch-001", sku, qty=batch_qty, eta=date.today()),
        OrderLine("order-123", sku, qty=line_qty),
    )


def test_allocating_to_a_batch_reduces_the_available_quantity():
    batch, line = make_batch_and_line("SMALL-TABLE", batch_qty=20, line_qty=2)
    batch.allocate(line)
    assert batch.available_quantity == 18


def test_can_allocate_if_available_greater_than_required():
    large_batch, small_line = make_batch_and_line("SAMLL-TABLE", 20, 2)
    assert large_batch.can_allocate(small_line)


def test_cannot_allocate_if_available_smaller_than_required():
    small_batch, large_line = make_batch_and_line("SAMLL-TABLE", 10, 20)
    assert small_batch.can_allocate(large_line) is False


def test_can_allocate_if_available_equal_to_required():
    batch, line = make_batch_and_line("SAMLL-TABLE", 10, 10)
    assert batch.can_allocate(line)


def test_cannot_allocate_if_skus_do_not_match():
    batch = Batch("batch-001", "SMALL-TABLE", qty=20, eta=date.today())
    different_sku_line = OrderLine("order-123", "LARGE-TABLE", qty=2)
    assert batch.can_allocate(different_sku_line) is False


def test_allocation_is_idempotent():
    batch, line = make_batch_and_line("ROUND-TABLE", 20, 2)
    batch.allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 18
