from typing import Callable, Optional
from dataclasses import dataclass, field
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    event_type: str
    payload: dict = field(default_factory=dict)


class EventBusInterface:
    """Interface for event bus implementations."""

    async def publish(self, event: DomainEvent, context: dict = None):
        raise NotImplementedError

    def subscribe(self, event_type: str, handler: Callable):
        raise NotImplementedError


class EventBus(EventBusInterface):
    """Default in-process event bus (single-instance)."""

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


class RedisEventBus(EventBusInterface):
    """
    Redis-backed event bus for horizontal scaling.
    Uses Redis pub/sub to distribute events across multiple instances.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self._local_handlers: dict[str, list[Callable]] = {}
        self._pubsub = None
        self._listener_task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._local_handlers:
            self._local_handlers[event_type] = []
        self._local_handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent, context: dict = None):
        # Publish locally first
        handlers = self._local_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event, context)
            except Exception:
                logger.exception("Event handler error (local): %s", event.event_type)

        # Then publish to Redis for cross-instance distribution
        import json
        event_data = {
            "event_type": event.event_type,
            "payload": event.payload,
        }
        await self.redis.publish(f"eventbus:{event.event_type}", json.dumps(event_data))

    async def start_listener(self):
        """Start listening for remote events (call on app startup)."""
        self._pubsub = self.redis.pubsub()
        for event_type in self._local_handlers:
            await self._pubsub.subscribe(f"eventbus:{event_type}")

        async def listen():
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    import json
                    data = json.loads(message["data"])
                    event = DomainEvent(
                        event_type=data["event_type"],
                        payload=data["payload"],
                    )
                    handlers = self._local_handlers.get(event.event_type, [])
                    for handler in handlers:
                        try:
                            await handler(event, None)
                        except Exception:
                            logger.exception("Event handler error (remote): %s", event.event_type)

        self._listener_task = asyncio.create_task(listen())

    async def stop_listener(self):
        """Stop listening (call on app shutdown)."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()


# Use default in-process bus; switch to RedisEventBus for multi-instance deployments
# by replacing event_bus in your app startup:
#   from app.utils.cache import redis_client
#   event_bus = RedisEventBus(redis_client)
event_bus = EventBus()
