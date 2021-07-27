import model
import repository


def insert_order_line(session):
    session.execute(
        "INSERT INTO order_lines (order_id, sku, qty) VALUES"
        '("order1", "RED-RIBBON", 10)'
    )
    [[order_line_id]] = session.execute(
        "SELECT id FROM order_lines WHERE order_id=:order_id AND sku=:sku",
        dict(order_id="order1", sku="RED-RIBBON"),
    )

    return order_line_id


def insert_batch(session, reference):
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES"
        '(:reference, "RED-RIBBON", 100, null)',
        dict(reference=reference),
    )

    [[batch_id]] = session.execute(
        "SELECT id FROM batches WHERE reference=:reference",
        dict(reference=reference),
    )

    return batch_id


def insert_allocations(session, order_line_id, batch_id):
    session.execute(
        "INSERT INTO allocations (order_line_id, batch_id) VALUES"
        "(:order_line_id, :batch_id)",
        dict(order_line_id=order_line_id, batch_id=batch_id),
    )


def test_repsitory_can_save_a_batch(session):
    batch_data = "batch1", "sku1", 100, None
    batch = model.Batch(*batch_data)
    repo = repository.SqlAlchemyRepository(session)
    repo.add(batch)
    session.commit()

    rows = session.execute(
        "SELECT reference, sku, _purchased_quantity, eta FROM batches"
    )

    assert list(rows) == [batch_data]


def test_repository_can_retrieve_a_complex_object(session):
    order_line_id = insert_order_line(session)
    batch_id = insert_batch(session, "batch1")
    insert_batch(session, "batch2")
    insert_allocations(session, order_line_id, batch_id)

    repo = repository.SqlAlchemyRepository(session)
    retrieved = repo.get("batch1")

    expected = model.Batch("batch1", "RED-RIBBON", 100, None)

    assert retrieved == expected  # only compares batch.reference
    assert retrieved.sku == expected.sku
    assert retrieved._purchased_quantity == expected._purchased_quantity
    assert retrieved.eta == expected.eta
    assert retrieved._allocations == {
        model.OrderLine("order1", "RED-RIBBON", 10)
    }


def test_repository_can_list_batches(session):
    insert_batch(session, "batch1")
    insert_batch(session, "batch2")

    repo = repository.SqlAlchemyRepository(session)

    assert repo.list() == [
        model.Batch("batch1", "RED-RIBBON", 100, None),
        model.Batch("batch2", "RED-RIBBON", 100, None),
    ]
