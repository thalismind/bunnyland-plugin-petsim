"""Spawn factories for pets and tameable creatures.

The loader does not consume ``ContentContribution.prefabs``, so companions are created with
these ``spawn_entity`` helpers (from tests, admin tooling, or a worldgen hook). Pass
``room_id`` to drop the creature into a room, or leave it out to spawn it uncontained.
"""

from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    HealthComponent,
    IdentityComponent,
    spawn_entity,
)
from relics import Entity, EntityId, World

from .components import PetComponent, TameableComponent
from .edges import set_owner


def _link_into_room(world: World, entity: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(
        Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id
    )


def spawn_pet(
    world: World,
    *,
    room_id=None,
    owner_id: EntityId | None = None,
    species: str = "fox",
    tricks: tuple[str, ...] = (),
    nervous: bool = False,
) -> Entity:
    """Spawn a pet creature, optionally placed in ``room_id`` and owned by ``owner_id``."""
    pet = spawn_entity(
        world,
        [
            IdentityComponent(name=species, kind="character", tags=("petsim", "pet")),
            CharacterComponent(),
            HealthComponent(),
            PetComponent(species=species, tricks=tricks, nervous=nervous),
        ],
    )
    _link_into_room(world, pet, room_id)
    if owner_id is not None and world.has_entity(owner_id):
        set_owner(pet, owner_id)
    return pet


def spawn_tameable(
    world: World,
    *,
    room_id=None,
    species: str = "fox",
    tame_threshold: float = 0.6,
    skittish: bool = False,
    tricks: tuple[str, ...] = (),
) -> Entity:
    """Spawn a tameable wild creature, optionally placed in ``room_id``."""
    creature = spawn_entity(
        world,
        [
            IdentityComponent(name=species, kind="character", tags=("petsim", "wild")),
            CharacterComponent(),
            HealthComponent(),
            TameableComponent(
                species=species,
                tame_threshold=tame_threshold,
                skittish=skittish,
                tricks=tricks,
            ),
        ],
    )
    _link_into_room(world, creature, room_id)
    return creature


__all__ = ["spawn_pet", "spawn_tameable"]
