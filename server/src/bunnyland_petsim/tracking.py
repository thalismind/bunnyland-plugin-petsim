"""Connector (consume): a scent-hound tracks wildsim ``Scent`` trails.

A pet marked with a :class:`TrackerComponent` is a scent-hound. When the **wildsim** pack is
loaded it publishes a ``Scent`` component onto trailable entities; a hound that shares a
room with one can point its owner toward the quarry.

This is a *safe, optional* connector: wildsim is imported behind ``try/except ImportError``
and only listed under the plugin's ``recommends``. When wildsim is absent the import yields
``None`` and the whole tracking feature simply stays dormant — petsim runs standalone.
"""

from __future__ import annotations

import logging

from bunnyland.core.ecs import contents
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import PetComponent
from .edges import owner_id_of
from .spatial import room_of

logger = logging.getLogger(__name__)

try:  # pragma: no cover - trivial import guard
    from bunnyland_wildsim import Scent  # type: ignore
except ImportError:  # pragma: no cover - exercised via monkeypatch in tests
    Scent = None
    logger.warning(
        "bunnyland_wildsim not installed; scent-hound tracking is disabled "
        "(petsim runs standalone without it)."
    )


@dataclass(frozen=True)
class TrackerComponent(Component):
    """Marks a pet as a scent-hound able to follow wildsim ``Scent`` trails."""

    keenness: float = 1.0


def is_tracker(entity: Entity) -> bool:
    """Whether ``entity`` is a scent-hound pet."""
    return entity.has_component(PetComponent) and entity.has_component(TrackerComponent)


def scented_targets(world: World, hound: Entity) -> list[Entity]:
    """Entities in the hound's room carrying a wildsim ``Scent`` (empty if wildsim absent)."""
    if Scent is None or not is_tracker(hound):
        return []
    room = room_of(world, hound.id)
    if room is None:
        return []
    found: list[Entity] = []
    for entity_id in contents(room):
        if entity_id == hound.id or not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if entity.has_component(Scent):
            found.append(entity)
    return found


def tracking_fragments(world: World, character: Entity) -> list[str]:
    """Prompt fragments: a hound alerting its owner to a nearby scent (dormant sans wildsim)."""
    if Scent is None:
        return []
    lines: list[str] = []
    for entity_id in contents_or_empty(world, character):
        entity = world.get_entity(entity_id)
        if not is_tracker(entity) or owner_id_of(entity) != character.id:
            continue
        if scented_targets(world, entity):
            species = entity.get_component(PetComponent).species
            lines.append(f"Your {species} catches a scent and strains at the trail.")
    return sorted(dict.fromkeys(lines))


def contents_or_empty(world: World, character: Entity):
    """The character's room contents, or nothing if they are roomless."""
    room = room_of(world, character.id)
    if room is None:
        return []
    return [entity_id for entity_id in contents(room) if world.has_entity(entity_id)]


__all__ = [
    "Scent",
    "TrackerComponent",
    "contents_or_empty",
    "is_tracker",
    "scented_targets",
    "tracking_fragments",
]
