from datetime import datetime
from flask import request, jsonify
from allocation import views, bootstrap
from allocation.domain import commands
from allocation.entrypoints.flask_utils import create_app
from allocation.service_layer import handlers, unit_of_work


app = create_app()
# with app.app_context:
bus = bootstrap.bootstrap()


@app.route("/allocate", methods=["POST"])
def allocate():
    try:

        cmd = commands.Allocate(
            request.json["order_id"], request.json["sku"], request.json["qty"]
        )
        bus.handle(cmd)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400
    return {"success": True}, 201


@app.route("/allocations/<order_id>", methods=["GET"])
def allocations_view(order_id):
    result = views.allocations(order_id, bus.uow)
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
    bus.handle(cmd)

    return {"success": True}, 201
