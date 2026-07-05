"""World-generation enrichment (v2): seed rideable mount stock.

Alongside the v1 tameable hook, this scans generated creatures for mount-y language
(a steed, a pony, a wild horse) and attaches a :class:`MountComponent`, so worlds ship with
creatures that can carry a rider once tamed and trained — without the core generator knowing
this plugin exists.
"""

from __future__ import annotations

from bunnyland.core.ecs import parse_entity_id
from bunnyland.core.events import CharacterGeneratedEvent
from bunnyland.core.world_actor import WorldActor

from .enrichment import _text
from .mounts import MountComponent

#: Words that mark a generated creature as rideable mount stock.
MOUNT_TERMS: tuple[str, ...] = (
    "mount",
    "steed",
    "horse",
    "pony",
    "stallion",
    "mare",
    "camel",
    "elk",
    "ridable",
    "rideable",
)


def is_mountlike(event: CharacterGeneratedEvent) -> bool:
    """Whether a generated creature reads as rideable mount stock."""
    text = _text(event)
    return any(term in text for term in MOUNT_TERMS)


class MountWorldgenHook:
    """Attach a ``MountComponent`` to generated creatures that read as mounts."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(CharacterGeneratedEvent, self._on_character)

    def _entity(self, entity_id: str):
        parsed = parse_entity_id(entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return None
        return self._actor.world.get_entity(parsed)

    def _on_character(self, event: CharacterGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None or entity.has_component(MountComponent):
            return
        if is_mountlike(event):
            entity.add_component(MountComponent())


__all__ = ["MOUNT_TERMS", "MountWorldgenHook", "is_mountlike"]
