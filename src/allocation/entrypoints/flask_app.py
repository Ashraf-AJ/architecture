from datetime import datetime
from flask import Flask, request
from allocation.adapters import orm
from allocation.domain import model
from allocation.service_layer import services, unit_of_work

orm.start_mappers()
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate():
    try:
        batch_ref = services.allocate(
            request.json["order_id"],
            request.json["sku"],
            request.json["qty"],
            unit_of_work.SqlAlchemyUnitOfWork(),
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400
    return {"batch_ref": batch_ref}, 201


@app.route("/batches", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    services.add_batch(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta,
        unit_of_work.SqlAlchemyUnitOfWork(),
    )
    return {"success": True}, 201
