"""Tricks & reactions: the ``trick`` verb and generic threat classification.

A pet knows a set of tricks and can perform one on command. Separately, pets *react* to
their surroundings: a nervous pet cowers when a hostile or threatening entity shares its
room. Threats are classified generically off :class:`IdentityComponent` kind / tags / name,
so this pack never hard-depends on any other plugin (e.g. spectersim).
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import IdentityComponent
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_reachable_entity,
)
from relics import Entity, World

from .components import PetComponent, clamp_happiness
from .edges import owner_id_of
from .events import PetTrickEvent
from .spatial import room_of

#: Happiness a pet gains from successfully performing a trick.
TRICK_HAPPINESS = 4.0

#: Words that mark another entity as something a pet finds threatening.
THREAT_TERMS: tuple[str, ...] = (
    "hostile",
    "enemy",
    "monster",
    "monstrous",
    "predator",
    "threat",
    "threatening",
    "aggressive",
    "dangerous",
    "wolf",
    "bear",
    "snake",
    "ghost",
    "wraith",
    "demon",
    "undead",
    "beast",
)


def _identity_text(entity: Entity) -> str:
    if not entity.has_component(IdentityComponent):
        return ""
    identity = entity.get_component(IdentityComponent)
    return " ".join((identity.name, identity.kind, *identity.tags)).casefold()


def is_threat(entity: Entity) -> bool:
    """Whether ``entity`` reads as a threat by its identity name / kind / tags."""
    text = _identity_text(entity)
    return any(term in text for term in THREAT_TERMS)


def perceived_threats(world: World, pet: Entity) -> list[Entity]:
    """Threatening entities sharing the pet's room (excluding the pet itself)."""
    from bunnyland.core.ecs import contents

    room = room_of(world, pet.id)
    if room is None:
        return []
    threats: list[Entity] = []
    for entity_id in contents(room):
        if entity_id == pet.id or not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if is_threat(entity):
            threats.append(entity)
    return threats


def reaction_line(world: World, pet: Entity, *, first_person: bool) -> str | None:
    """Render a pet's reaction to nearby threats, or ``None`` if calm."""
    component = pet.get_component(PetComponent)
    threats = perceived_threats(world, pet)
    if not threats:
        return None
    subject = f"Your {component.species}" if first_person else f"A {component.species} here"
    threat_name = (
        threats[0].get_component(IdentityComponent).name
        if threats[0].has_component(IdentityComponent)
        else "something"
    )
    if component.nervous:
        return f"{subject} cowers, terrified of the {threat_name}."
    return f"{subject} bristles, wary of the {threat_name}."


class TrickHandler:
    """Have a pet you own perform a trick it knows."""

    command_type = "trick"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        pet_id, pet, rejection = require_reachable_entity(
            ctx,
            character,
            command.payload.get("pet_id"),
            invalid_reason="invalid pet id",
            missing_reason="pet does not exist",
            unreachable_reason="that pet is not here",
        )
        if rejection is not None:
            return rejection
        if not pet.has_component(PetComponent):
            return rejected("that is not a pet")
        if owner_id_of(pet) != character_id:
            return rejected("that is not your pet")
        trick = command.payload.get("trick")
        component = pet.get_component(PetComponent)
        if trick not in component.tricks:
            return rejected("your pet does not know that trick")

        happiness = clamp_happiness(component.happiness + TRICK_HAPPINESS)
        replace_component(pet, replace(component, happiness=happiness))
        room = room_of(ctx.world, pet_id)
        return ok(
            PetTrickEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(pet_id),),
                    pet_id=str(pet_id),
                    trick=trick,
                )
            )
        )


TRICK_DEF = ActionDefinition(
    command_type="trick",
    title="Perform trick",
    description="Ask a pet you own to perform a trick it knows.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "pet_id": ActionArgument(
            title="Pet", description="The pet to command.", kind="entity", required=True
        ),
        "trick": ActionArgument(
            title="Trick",
            description="The name of a trick the pet knows.",
            kind="string",
            required=True,
        ),
    },
)


__all__ = [
    "THREAT_TERMS",
    "TRICK_DEF",
    "TRICK_HAPPINESS",
    "TrickHandler",
    "is_threat",
    "perceived_threats",
    "reaction_line",
]
