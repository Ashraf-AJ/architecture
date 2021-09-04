from abc import ABC, abstractmethod
from typing import Set
from allocation.domain import model


class AbstractRepository(ABC):
    def __init__(self):
        self.seen = set()  # type: Set[model.Product]

    def add(self, product: model.Product) -> None:
        self._add(product)
        self.seen.add(product)

    def get(self, sku: str) -> model.Product:
        product = self._get(sku)
        if product:
            self.seen.add(product)
        return product

    @abstractmethod
    def _add(self, product: model.Product) -> None:
        raise NotImplementedError

    @abstractmethod
    def _get(self, sku: str) -> model.Product:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, product: model.Product) -> None:
        self.session.add(product)

    def _get(self, sku: str) -> model.Product:
        return self.session.query(model.Product).filter_by(sku=sku).first()
