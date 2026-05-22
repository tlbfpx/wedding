from typing import Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    event_type: str
    payload: dict = field(default_factory=dict)


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent, context: dict = None):
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event, context)
            except Exception:
                logger.exception("Event handler error: %s, handler: %s", event.event_type, handler.__name__)
                raise


event_bus = EventBus()
