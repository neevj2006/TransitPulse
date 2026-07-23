import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class LiveEvent:
    event_id: int
    kind: str
    route_id: str | None
    stop_id: str | None
    payload: str


class EventBroker:
    def __init__(self, limit: int = 100) -> None:
        self.events: list[LiveEvent] = []
        self.limit = limit
        self.next_id = 1
        self.changed = asyncio.Event()

    def publish(
        self, kind: str, payload: str, route_id: str | None = None, stop_id: str | None = None
    ) -> LiveEvent:
        event = LiveEvent(self.next_id, kind, route_id, stop_id, payload)
        self.next_id += 1
        self.events = (self.events + [event])[-self.limit :]
        self.changed.set()
        return event

    def since(self, event_id: int, route_id: str | None, stop_id: str | None) -> list[LiveEvent]:
        return [
            event
            for event in self.events
            if event.event_id > event_id
            and (not route_id or event.route_id == route_id)
            and (not stop_id or event.stop_id == stop_id)
        ]
