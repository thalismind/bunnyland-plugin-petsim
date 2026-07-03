"""Prompt fragment provider for pets.

A single ``(world, character) -> list[str]`` provider feeds both the LLM actor context and
the human character-chat prompt. For every pet the character can perceive it renders:

- a **loyalty** line (only for the pet's owner) reading the pet -> owner bond, and
- a **reaction** line whenever a threat shares the pet's room.

The reaction line is shown to anyone present; the loyalty line is first-person to the owner.
"""

from __future__ import annotations

from bunnyland.core import reachable_ids
from relics import Entity, World

from .bonding import loyalty_line
from .components import PetComponent
from .edges import owner_id_of
from .tricks import reaction_line


def petsim_fragments(world: World, character: Entity) -> list[str]:
    lines: list[str] = []
    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        if not entity.has_component(PetComponent):
            continue
        owner_id = owner_id_of(entity)
        first_person = owner_id is not None and owner_id == character.id
        if first_person:
            loyalty = loyalty_line(world, entity, owner_id)
            if loyalty is not None:
                lines.append(loyalty)
        reaction = reaction_line(world, entity, first_person=first_person)
        if reaction is not None:
            lines.append(reaction)
    return sorted(dict.fromkeys(lines))


__all__ = ["petsim_fragments"]
