from datetime import datetime
from flask import Flask, request
from allocation.adapters import orm
from allocation.domain import events
from allocation.service_layer import handlers, message_bus, unit_of_work

orm.start_mappers()
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate():
    try:

        event = events.AllocationRequired(
            request.json["order_id"], request.json["sku"], request.json["qty"]
        )
        results = message_bus.handle(
            event, unit_of_work.SqlAlchemyUnitOfWork()
        )
        batch_ref = results.pop(0)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400
    return {"batch_ref": batch_ref}, 201


@app.route("/batches", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    event = events.BatchCreated(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta,
    )
    message_bus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())

    return {"success": True}, 201
