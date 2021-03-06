from datetime import date

import pytest
from allocation.domain import model

pytestmark = pytest.mark.usefixtures("mappers")


def test_orderline_mapper_can_load_lines(in_memory_session):
    in_memory_session.execute(
        "INSERT INTO order_lines (order_id, sku, qty) VALUES"
        '("order1", "SMALL-TABLE", 10),'
        '("order1", "MEDIUM-TABLE", 11),'
        '("order2", "LARGE-TABLE", 12)'
    )

    expected = [
        model.OrderLine("order1", "SMALL-TABLE", 10),
        model.OrderLine("order1", "MEDIUM-TABLE", 11),
        model.OrderLine("order2", "LARGE-TABLE", 12),
    ]

    assert in_memory_session.query(model.OrderLine).all() == expected


def test_orderline_mapper_can_save_lines(in_memory_session):
    line_data = "order1", "RED-RIBBON", 2
    new_line = model.OrderLine(*line_data)
    in_memory_session.add(new_line)
    in_memory_session.commit()

    rows = in_memory_session.execute(
        "SELECT order_id, sku, qty FROM order_lines"
    )
    assert list(rows) == [line_data]


def test_batches_mapper_can_load_batches(in_memory_session):
    in_memory_session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
        ' VALUES ("batch1", "sku1", 100, null)'
    )
    in_memory_session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
        ' VALUES ("batch2", "sku2", 200, "2011-04-11")'
    )
    expected = [
        model.Batch("batch1", "sku1", 100, None),
        model.Batch("batch2", "sku2", 200, date(2011, 4, 11)),
    ]

    assert in_memory_session.query(model.Batch).all() == expected


def test_batches_mapper_can_save_batches(in_memory_session):
    batch_data = "batch1", "sku1", 100, None
    batch = model.Batch("batch1", "sku1", 100, eta=None)
    in_memory_session.add(batch)
    in_memory_session.commit()

    rows = in_memory_session.execute(
        "SELECT reference, sku, _purchased_quantity, eta FROM batches"
    )

    assert list(rows) == [batch_data]


def test_allocations_mapper_can_load_allocations(in_memory_session):
    in_memory_session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
        ' VALUES ("batch1", "sku1", 100, null)'
    )
    [[batch_id]] = in_memory_session.execute(
        "SELECT id FROM batches WHERE reference=:ref AND sku=:sku",
        dict(ref="batch1", sku="sku1"),
    )

    in_memory_session.execute(
        "INSERT INTO order_lines (order_id, sku, qty) VALUES"
        '("order1", "sku1", 10)'
    )
    [[order_line_id]] = in_memory_session.execute(
        "SELECT id FROM order_lines WHERE order_id=:oid AND sku=:sku",
        dict(oid="order1", sku="sku1"),
    )
    in_memory_session.execute(
        "INSERT INTO allocations (order_line_id, batch_id) VALUES"
        "(:oid, :bid)",
        dict(oid=order_line_id, bid=batch_id),
    )
    batch = in_memory_session.query(model.Batch).filter_by(id=batch_id).first()
    assert batch._allocations == {model.OrderLine("order1", "sku1", 10)}


def test_allocations_mapper_can_save_allocations(in_memory_session):
    line = model.OrderLine("order1", "sku1", 10)
    batch = model.Batch("batch1", "sku1", 100, eta=None)
    batch.allocate(line)
    in_memory_session.add(batch)
    in_memory_session.commit()
    rows = in_memory_session.execute(
        "SELECT order_line_id, batch_id FROM allocations"
    )
    assert list(rows) == [(line.id, batch.id)]
