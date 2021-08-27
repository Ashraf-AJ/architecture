from abc import ABC, abstractmethod
from allocation.domain import model


class AbstractRepository(ABC):
    @abstractmethod
    def add(self, product: model.Product) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, sku: str) -> model.Product:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        self.session = session

    def add(self, product: model.Product) -> None:
        self.session.add(product)

    def get(self, sku: str) -> model.Product:
        return self.session.query(model.Product).filter_by(sku=sku).first()
