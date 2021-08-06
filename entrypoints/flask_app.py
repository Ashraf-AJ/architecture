from datetime import datetime
from flask import Flask, request
from requests.api import get
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from adapters import orm, repository
from domain import model
from service_layer import services
import config

orm.start_mappers()
# get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
get_session = sessionmaker(bind=create_engine(config.get_dev_db_uri()))
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate():
    session = get_session()
    repo = repository.SqlAlchemyRepository(session)
    try:
        batch_ref = services.allocate(
            request.json["order_id"],
            request.json["sku"],
            request.json["qty"],
            repo,
            session,
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400
    return {"batch_ref": batch_ref}, 201


@app.route("/batches", methods=["POST"])
def add_batch():
    session = get_session()
    repo = repository.SqlAlchemyRepository(session)
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    services.add_batch(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta,
        repo,
        session,
    )
    return {"success": True}, 201
