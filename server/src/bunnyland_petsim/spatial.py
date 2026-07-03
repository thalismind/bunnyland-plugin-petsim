"""Spatial helper: resolve the room an entity is ultimately in.

The core ``container_of`` only returns an entity's *direct* ``Contains`` parent. A pet is
usually directly in a room, but this walks upward to a :class:`RoomComponent` so it also
works when an entity is nested (e.g. carried).
"""

from __future__ import annotations

from bunnyland.core import RoomComponent, container_of
from relics import Entity, World

#: Guard against pathological containment cycles while walking up to a room.
_MAX_CONTAINMENT_DEPTH = 8


def room_of(world: World, entity_id) -> Entity | None:
    """Return the room ``entity_id`` is ultimately in, or ``None``."""
    if not world.has_entity(entity_id):
        return None
    current = world.get_entity(entity_id)
    for _ in range(_MAX_CONTAINMENT_DEPTH):
        parent_id = container_of(current)
        if parent_id is None or not world.has_entity(parent_id):
            return None
        parent = world.get_entity(parent_id)
        if parent.has_component(RoomComponent):
            return parent
        current = parent
    return None


__all__ = ["room_of"]
