import inspect
from typing import Callable, Iterable
from allocation.adapters.notifications import (
    EmailNotifications,
    AbstractNotifications,
)

from allocation.service_layer import message_bus
from allocation.service_layer.unit_of_work import (
    AbstractUnitOfWork,
    SqlAlchemyUnitOfWork,
)
from allocation.adapters.redis_event_publisher import publish_message
from allocation.adapters import orm
from allocation.entrypoints.flask_utils import get_message_queue
from allocation.service_layer.handlers import (
    EVENT_HANDLERS,
    COMMAND_HANDLERS,
)


def bootstrap(
    start_orm: bool = True,
    uow: AbstractUnitOfWork = SqlAlchemyUnitOfWork(),
    message_queue_factory: Callable = get_message_queue,
    publish: Callable = publish_message,
    notifications: AbstractNotifications = None,
) -> message_bus.MessageBus:
    if start_orm:
        orm.start_mappers()

    if notifications is None:
        notifications = EmailNotifications()

    dependencies = {
        "uow": uow,
        "publish": publish,
        "notifications": notifications,
    }
    injected_event_handlers = {
        event_type: [
            inject_dependencies(handler, dependencies) for handler in handlers
        ]
        for event_type, handlers in EVENT_HANDLERS.items()
    }

    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in COMMAND_HANDLERS.items()
    }

    return message_bus.MessageBus(
        uow,
        message_queue_factory,
        injected_event_handlers,
        injected_command_handlers,
    )


def inject_dependencies(handler: Callable, dependencies) -> Callable:
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items()
        if name in params
    }

    def injected_handler(message, deps=deps):
        return handler(message, **deps)

    return injected_handler
