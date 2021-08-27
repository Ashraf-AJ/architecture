from typing import Optional, List
from datetime import date
import time
import traceback
import pytest
from allocation.domain import model
from allocation.service_layer import unit_of_work
from tests.random_refs import random_batchref, random_sku, random_orderid


def insert_batch(session, reference, sku, qty, eta, product_version=1):
    session.execute(
        "INSERT INTO products (sku, version_number) VALUES (:sku, :version)",
        dict(sku=sku, version=product_version),
    )
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
        " VALUES (:reference, :sku, :qty, :eta)",
        dict(reference=reference, sku=sku, qty=qty, eta=eta),
    )


def insert_batch_and_raises_exception(
    exception: Exception,
    session,
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
) -> None:
    insert_batch(session, reference, sku, qty, eta, product_version=1)
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


def test_uow_can_retrieve_a_product_and_allocate_to_it(session_factory):
    session = session_factory()
    insert_batch(session, "batch1", "SIMPLE-CHAIR", 100, None)
    session.commit()

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        product = uow.products.get("SIMPLE-CHAIR")
        line = model.OrderLine("order1", "SIMPLE-CHAIR", 10)
        product.allocate(line)
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


def try_to_allocate(orderid, sku, exceptions):
    line = model.OrderLine(orderid, sku, 10)
    try:
        with unit_of_work.SqlAlchemyUnitOfWork() as uow:
            product = uow.products.get(sku=sku)
            product.allocate(line)
            time.sleep(1)
            uow.commit()
            assert product.version_number == 2
    except Exception as e:
        print(traceback.format_exc())
        exceptions.append(e)


from concurrent import futures


def test_concurrent_updates_to_version_are_not_allowed(pg_session_factory):
    sku, batch = random_sku(), random_batchref()
    session = pg_session_factory()
    insert_batch(session, batch, sku, 100, eta=None, product_version=1)
    session.commit()

    order1, order2 = random_orderid(1), random_orderid(2)
    exceptions = []  # type: List[Exception]
    tasks = [
        (order1, sku, exceptions),
        (order2, sku, exceptions),
    ]
    with futures.ThreadPoolExecutor(2) as executor:
        for i in range(len(tasks)):
            executor.submit(try_to_allocate, *tasks[i])

    [[version]] = session.execute(
        "SELECT version_number FROM products WHERE sku=:sku",
        dict(sku=sku),
    )
    assert version == 2
    [exception] = exceptions
    assert "could not serialize access due to concurrent update" in str(
        exception
    )

    orders = session.execute(
        "SELECT order_id FROM allocations"
        " JOIN batches ON allocations.batch_id = batches.id"
        " JOIN order_lines ON allocations.order_line_id = order_lines.id"
        " WHERE order_lines.sku=:sku",
        dict(sku=sku),
    )
    assert len(list(orders)) == 1
