"""Charming pet-care — gentle need meters, not a survival chore.

A pet carries a :class:`PetCareComponent` holding two core need :class:`Meter` values:
``play_need`` (how restless/bored it is) and ``grooming`` (how scruffy it is). Both drift
*up* slowly via :class:`PetCareConsequence`, and are relieved by warm little verbs:

- ``play-with`` a pet cheers it up (big happiness bump, grows the bond) and settles its
  restlessness.
- ``groom`` a pet tidies it (small happiness, grows trust) and settles its scruffiness.

The pace is deliberately slow and the payoff is affection, so caring for a pet reads as a
delight rather than a decaying-meter obligation.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import reachable_ids
from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_reachable_entity,
)
from bunnyland.mechanics.meter import Meter, band, changed, with_value
from bunnyland.mechanics.social import adjust_bond
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import PetComponent, clamp_happiness
from .edges import owner_id_of
from .events import PetGroomedEvent, PetPlayedEvent
from .mounts import MountComponent
from .spatial import room_of

#: How much restlessness / scruffiness a pet gathers per game day (a gentle drift).
PLAY_NEED_PER_DAY = 8.0
GROOMING_PER_DAY = 5.0

#: How fast a resting mount recovers stamina per game day.
STAMINA_RECOVERY_PER_DAY = 24.0

SECONDS_PER_DAY = 24 * 60 * 60

#: Care rewards.
PLAY_HAPPINESS = 8.0
GROOM_HAPPINESS = 3.0
PLAY_AFFINITY = 0.12
GROOM_TRUST = 0.08


@dataclass(frozen=True)
class PetCareComponent(Component):
    """Gentle upkeep meters for a pet (higher value = more in need of attention)."""

    play_need: Meter = Meter()
    grooming: Meter = Meter()
    last_updated_epoch: int = 0


def care_lines(pet: Entity) -> list[str]:
    """Warm, first-person nudges when a pet's care meters ask for attention."""
    if not pet.has_component(PetCareComponent) or not pet.has_component(PetComponent):
        return []
    care = pet.get_component(PetCareComponent)
    species = pet.get_component(PetComponent).species
    lines: list[str] = []
    if band(care.play_need) != "calm":
        lines.append(f"Your {species} is restless and would love to play.")
    if band(care.grooming) != "calm":
        lines.append(f"Your {species} is looking scruffy and could use a brush.")
    return lines


def petcare_fragments(world: World, character: Entity) -> list[str]:
    """Prompt fragments surfacing gentle care nudges to a pet's owner."""
    lines: list[str] = []
    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        if not entity.has_component(PetCareComponent):
            continue
        if owner_id_of(entity) != character.id:
            continue
        lines.extend(care_lines(entity))
    return sorted(dict.fromkeys(lines))


class PetCareConsequence:
    """Drift care meters up slowly and rest mounts' stamina back down."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        for pet in list(world.query().with_all([PetCareComponent]).execute_entities()):
            care = pet.get_component(PetCareComponent)
            elapsed = max(0, epoch - care.last_updated_epoch)
            fraction = elapsed / SECONDS_PER_DAY
            care = replace(
                care,
                play_need=changed(care.play_need, PLAY_NEED_PER_DAY * fraction),
                grooming=changed(care.grooming, GROOMING_PER_DAY * fraction),
                last_updated_epoch=epoch,
            )
            replace_component(pet, care)
            if pet.has_component(MountComponent):
                mount = pet.get_component(MountComponent)
                rested = changed(mount.stamina, -STAMINA_RECOVERY_PER_DAY * fraction)
                replace_component(pet, replace(mount, stamina=rested))
        return []


def _ensure_care(pet: Entity, epoch: int) -> PetCareComponent:
    if pet.has_component(PetCareComponent):
        return pet.get_component(PetCareComponent)
    care = PetCareComponent(last_updated_epoch=epoch)
    pet.add_component(care)
    return care


class PlayWithPetHandler:
    """Play with a pet you own to cheer it up and settle its restlessness."""

    command_type = "play-with"

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

        care = _ensure_care(pet, ctx.epoch)
        replace_component(pet, replace(care, play_need=with_value(care.play_need, 0.0)))
        component = pet.get_component(PetComponent)
        happiness = clamp_happiness(component.happiness + PLAY_HAPPINESS)
        replace_component(pet, replace(component, happiness=happiness))
        adjust_bond(ctx.world, pet_id, character_id, {"affinity": PLAY_AFFINITY})

        room = room_of(ctx.world, character_id)
        return ok(
            PetPlayedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(pet_id),),
                    pet_id=str(pet_id),
                    owner_id=str(character_id),
                    happiness=happiness,
                )
            )
        )


class GroomPetHandler:
    """Groom a pet you own to tidy it up and deepen its trust."""

    command_type = "groom"

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

        care = _ensure_care(pet, ctx.epoch)
        replace_component(pet, replace(care, grooming=with_value(care.grooming, 0.0)))
        component = pet.get_component(PetComponent)
        replace_component(
            pet,
            replace(component, happiness=clamp_happiness(component.happiness + GROOM_HAPPINESS)),
        )
        adjust_bond(ctx.world, pet_id, character_id, {"trust": GROOM_TRUST})

        room = room_of(ctx.world, character_id)
        return ok(
            PetGroomedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(pet_id),),
                    pet_id=str(pet_id),
                    owner_id=str(character_id),
                )
            )
        )


PLAY_WITH_DEF = ActionDefinition(
    command_type="play-with",
    title="Play with pet",
    description="Play with a pet you own to make it happy.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "pet_id": ActionArgument(
            title="Pet", description="The pet to play with.", kind="entity", required=True
        ),
    },
)

GROOM_DEF = ActionDefinition(
    command_type="groom",
    title="Groom pet",
    description="Groom a pet you own to tidy it up.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "pet_id": ActionArgument(
            title="Pet", description="The pet to groom.", kind="entity", required=True
        ),
    },
)


__all__ = [
    "GROOMING_PER_DAY",
    "GROOM_DEF",
    "GROOM_HAPPINESS",
    "GROOM_TRUST",
    "PLAY_AFFINITY",
    "PLAY_HAPPINESS",
    "PLAY_NEED_PER_DAY",
    "PLAY_WITH_DEF",
    "STAMINA_RECOVERY_PER_DAY",
    "GroomPetHandler",
    "PetCareComponent",
    "PetCareConsequence",
    "PlayWithPetHandler",
    "care_lines",
    "petcare_fragments",
]
