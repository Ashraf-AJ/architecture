from typing import Callable, Dict, List, Type
from collections import deque
from allocation.domain import events
from allocation.service_layer import handlers
from allocation.service_layer.unit_of_work import AbstractUnitOfWork


def handle(event: events.Event, uow: AbstractUnitOfWork) -> None:
    queue = deque([event])
    results = []
    while queue:
        event = queue.popleft()
        for handler in HANDLERS[type(event)]:
            results.append(handler(event, uow))
            queue.extend(uow.collect_new_events())
    return results


HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
    events.AllocationRequired: [handlers.allocate],
    events.BatchCreated: [handlers.add_batch],
    events.BatchQuantityChanged: [handlers.change_batch_quantity],
}  # type: Dict[Type[events.Event], List[Callable]]
