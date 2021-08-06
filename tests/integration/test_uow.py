from typing import Optional
from datetime import date
import pytest
from domain import model
from service_layer import unit_of_work


def insert_batch(
    session, reference: str, sku: str, qty: int, eta: Optional[date]
) -> None:
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES"
        "(:reference, :sku, :_purchased_quantity, :eta)",
        dict(reference=reference, sku=sku, _purchased_quantity=qty, eta=eta),
    )


def insert_batch_and_raises_exception(
    exception: Exception,
    session,
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
) -> None:
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES"
        "(:reference, :sku, :_purchased_quantity, :eta)",
        dict(reference=reference, sku=sku, _purchased_quantity=qty, eta=eta),
    )
    raise exception()


def get_allocated_batch_ref(session, order_id: str, sku: str) -> str:
    [[order_line_id]] = session.execute(
        "SELECT id FROM order_lines WHERE order_id=:order_id AND sku=:sku",
        dict(order_id=order_id, sku=sku),
    )
    [[batch_ref]] = session.execute(
        "SELECT b.reference from allocations JOIN batches as b ON batch_id=b.id"
        " WHERE order_line_id=:order_line_id",
        dict(order_line_id=order_line_id),
    )
    return batch_ref


def test_uow_can_retrieve_a_batch_and_allocate_to_it(session_factory):
    session = session_factory()
    insert_batch(session, "batch1", "SIMPLE-CHAIR", 100, None)
    session.commit()
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        batch = uow.batches.get("batch1")
        line = model.OrderLine("order1", "SIMPLE-CHAIR", 10)
        batch.allocate(line)
        uow.commit()
    allocated_batch = get_allocated_batch_ref(
        session, "order1", "SIMPLE-CHAIR"
    )
    assert allocated_batch == "batch1"


def test_rolls_back_uncommitted_work_by_default(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        insert_batch(uow.session, "batch1", "SIMPLE-CHAIR", 100, None)
    session = session_factory()
    rows = list(session.execute("SELECT * FROM batches"))
    assert rows == []


def test_rolls_back_on_error(session_factory):
    class MyException(Exception):
        pass

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with pytest.raises(MyException):
        with uow:
            insert_batch_and_raises_exception(
                MyException, uow.session, "batch1", "SIMPLE-CHAIR", 100, None
            )

    session = session_factory()
    rows = list(session.execute('SELECT * FROM "batches"'))
    assert rows == []
