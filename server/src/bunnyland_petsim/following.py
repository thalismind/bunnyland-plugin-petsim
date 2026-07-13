"""Following: keep a pet in the same room as its owner, and the ``command-pet`` verb.

The :class:`FollowingConsequence` runs each tick. For every pet whose mode chases its owner
(``follow`` or ``heel``), it relocates the pet into the owner's current room when they have
drifted apart, emitting a :class:`PetFollowedEvent` on the move. Relocation is done purely
by rewriting ``Contains`` edges (remove from the old container, add into the owner's room),
matching how the core movement handler moves characters.

The ``command-pet`` verb lets an owner set a pet's follow mode. It validates in the project
order: invalid id -> missing entity -> unreachable -> wrong kind -> not your pet -> bad mode.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import ContainmentMode, Contains, remove_from_container
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    planned,
    rejected,
    require_character,
    require_reachable_entity,
)
from bunnyland.core.mutations import MutationPlan, SetComponent
from relics import World

from .components import PET_MODES, RELOCATING_MODES, PetComponent
from .edges import owner_id_of
from .events import PetCommandedEvent, PetFollowedEvent
from .spatial import room_of


class FollowingConsequence:
    """Relocate following pets into their owner's room each tick."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for pet in list(world.query().with_all([PetComponent]).execute_entities()):
            component = pet.get_component(PetComponent)
            if component.mode not in RELOCATING_MODES:
                continue
            owner_id = owner_id_of(pet)
            if owner_id is None or not world.has_entity(owner_id):
                continue
            owner_room = room_of(world, owner_id)
            if owner_room is None:
                continue
            pet_room = room_of(world, pet.id)
            if pet_room is not None and pet_room.id == owner_room.id:
                continue
            from_room_id = str(pet_room.id) if pet_room is not None else None
            remove_from_container(world, pet.id)
            owner_room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), pet.id)
            events.append(
                PetFollowedEvent(
                    **event_base(
                        epoch,
                        visibility=EventVisibility.ROOM,
                        actor_id=str(pet.id),
                        room_id=str(owner_room.id),
                        target_ids=(str(owner_id),),
                        pet_id=str(pet.id),
                        owner_id=str(owner_id),
                        from_room_id=from_room_id,
                        to_room_id=str(owner_room.id),
                    )
                )
            )
        return events


class CommandPetHandler:
    """Set a pet's follow mode (``follow`` / ``heel`` / ``stay``)."""

    command_type = "command-pet"

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
        mode = command.payload.get("mode")
        if mode not in PET_MODES:
            return rejected("unknown pet command")
        component = pet.get_component(PetComponent)
        return planned(
            MutationPlan((SetComponent(pet_id, replace(component, mode=mode)),)),
            PetCommandedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room_of(ctx.world, character_id).id)
                    if room_of(ctx.world, character_id) is not None
                    else None,
                    target_ids=(str(pet.id),),
                    pet_id=str(pet.id),
                    mode=mode,
                )
            ),
        )


COMMAND_PET_DEF = ActionDefinition(
    command_type="command-pet",
    title="Command pet",
    description="Tell a pet you own to follow, heel, or stay.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "pet_id": ActionArgument(
            title="Pet", description="The pet to command.", kind="entity", required=True
        ),
        "mode": ActionArgument(
            title="Mode",
            description="One of: follow, heel, stay.",
            kind="string",
            required=True,
        ),
    },
)


__all__ = ["COMMAND_PET_DEF", "CommandPetHandler", "FollowingConsequence"]
