"""The ``Follows`` relationship edge (pet -> owner) and its small helpers.

Ownership is a repeatable relationship, so it is an :class:`relics.Edge` rather than a
component: a character can own several pets, and a pet's owner can change, without a
second component of the same type ever living on one entity.
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from relics import Edge, Entity, EntityId, World


@dataclass(frozen=True)
class Follows(Edge):
    """pet -> owner. The pet trails this character between rooms while following."""

    since_epoch: int = 0


def set_owner(pet: Entity, owner_id: EntityId, *, since_epoch: int = 0) -> None:
    """Point ``pet`` at ``owner_id`` (replaces any existing owner — one owner per pet)."""
    # add_relationship overwrites an existing edge of the same type+target; to guarantee a
    # single owner we drop every prior Follows edge first.
    for _edge, target_id in list(pet.get_relationships(Follows)):
        pet.remove_relationship(Follows, target_id)
    pet.add_relationship(Follows(since_epoch=since_epoch), owner_id)


def owner_id_of(pet: Entity) -> EntityId | None:
    """Return the id of the entity this pet follows, or ``None`` if it has no owner."""
    for _edge, owner_id in pet.get_relationships(Follows):
        return owner_id
    return None


def owned_pets(world: World, owner_id: EntityId) -> list[Entity]:
    """Return the live pet entities that follow ``owner_id``."""
    if not world.has_entity(owner_id):
        return []
    owner = world.get_entity(owner_id)
    pets: list[Entity] = []
    for source_id, _edge in owner.get_incoming_relationships(Follows):
        if world.has_entity(source_id):
            pets.append(world.get_entity(source_id))
    return pets


__all__ = ["Follows", "owned_pets", "owner_id_of", "set_owner"]
