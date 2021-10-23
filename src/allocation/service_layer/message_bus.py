from typing import Callable, Dict, Iterable, List, Type, Union
import logging
from allocation.domain import events, commands
from allocation.service_layer.unit_of_work import AbstractUnitOfWork

Message = Union[events.Event, commands.Command]
logger = logging.getLogger(__name__)


class MessageBus:
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        message_queue_factory: Callable,
        event_handlers: Dict[Type[events.Event], List[Callable]],
        command_handlers: Dict[Type[commands.Command], Callable],
    ):
        self.uow = uow
        self.queue_factory = message_queue_factory
        # defer creating the message_queue until calling the "handle" method
        # which will happen inside a view function which provide the app context
        # needed to access "flask.g" object
        self.queue = None
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    def handle(self, message: Message):
        self.queue = self.queue_factory()
        self.queue.append(message)
        while self.queue:
            message = self.queue.popleft()
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, commands.Command):
                self.handle_command(message)
            else:
                raise Exception(f"{message} is not an Event or a Command")

    def handle_event(
        self,
        event: events.Event,
    ) -> None:
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug(f"handling event {event} with handler {handler}")
                handler(event)
                self.queue.extend(self.uow.collect_new_events())
            except Exception:
                logging.exception(f"Exception handling event {event}")
                continue

    def handle_command(
        self,
        command: commands.Command,
    ):
        logging.debug(f"handling command {command}")
        try:
            handler = self.command_handlers[type(command)]
            handler(command)
            self.queue.extend(self.uow.collect_new_events())
        except Exception:
            logging.exception(f"Exception handling command {command}")
            raise
