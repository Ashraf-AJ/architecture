from datetime import datetime
from flask import Flask, request, jsonify
from allocation import views
from allocation.adapters import orm
from allocation.domain import commands
from allocation.service_layer import handlers, message_bus, unit_of_work

orm.start_mappers()
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate():
    try:

        cmd = commands.Allocate(
            request.json["order_id"], request.json["sku"], request.json["qty"]
        )
        message_bus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400
    return {"success": True}, 201


@app.route("/allocations/<order_id>", methods=["GET"])
def allocations_view(order_id):
    result = views.allocations(order_id, unit_of_work.SqlAlchemyUnitOfWork())
    if not result:
        return "Not Found", 404
    return jsonify(result), 201


@app.route("/batches/", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    cmd = commands.CreateBatch(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta,
    )
    message_bus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())

    return {"success": True}, 201
