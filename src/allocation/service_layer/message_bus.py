from typing import Callable, Dict, List, Type, Union
from collections import deque
import logging
from allocation.domain import events, commands
from allocation.service_layer import handlers
from allocation.service_layer.unit_of_work import AbstractUnitOfWork

Message = Union[events.Event, commands.Command]
logger = logging.getLogger(__name__)


def handle(message: Message, uow: AbstractUnitOfWork):
    queue = deque([message])
    while queue:
        message = queue.popleft()
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            handle_command(message, queue, uow)
        else:
            raise Exception(f"{message} is not an Event or a Command")


def handle_event(
    event: events.Event, queue: List[Message], uow: AbstractUnitOfWork
) -> None:
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            logger.debug(f"handling event {event} with handler {handler}")
            handler(event, uow)
            queue.extend(uow.collect_new_events())
        except Exception:
            logging.exception(f"Exception handling event {event}")
            continue


def handle_command(
    command: commands.Command, queue: List[Message], uow: AbstractUnitOfWork
):
    logging.debug(f"handling command {command}")
    try:
        handler = COMMAND_HANDLERS[type(command)]
        handler(command, uow)
        queue.extend(uow.collect_new_events())
    except Exception:
        logging.exception(f"Exception handling command {command}")
        raise


EVENT_HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
    events.Allocated: [
        handlers.publish_allocated_event,
        handlers.add_allocation_to_read_model,
    ],
    events.Deallocated: [
        handlers.reallocate,
        handlers.remove_allocation_from_read_model,
    ],
}  # type: Dict[Type[events.Event], List[Callable]]

COMMAND_HANDLERS = {
    commands.Allocate: handlers.allocate,
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}  # type: dict[Type[commands.Command], Callable]
