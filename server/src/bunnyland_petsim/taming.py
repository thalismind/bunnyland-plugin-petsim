"""Taming: turn a wild creature into a pet over one or more attempts.

Each ``tame`` attempt grows a directed :class:`SocialBond` from the creature toward the
character (how the animal feels about the person). Once the creature's affinity reaches its
``tame_threshold`` it is converted: the :class:`TameableComponent` is swapped for a
:class:`PetComponent` and a :class:`Follows` edge (pet -> owner) is added. A skittish
creature warms more slowly, so it needs more attempts.
"""

from __future__ import annotations

from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_reachable_entity,
)
from bunnyland.foundation.social.mechanics import adjust_bond, bond_between

from .components import PetComponent, TameableComponent
from .edges import set_owner
from .events import PetTamedEvent
from .knowledge import known_species_bonus
from .spatial import room_of

#: Affinity gained per taming attempt (halved for skittish creatures).
TAME_AFFINITY_STEP = 0.34
SKITTISH_AFFINITY_STEP = 0.17


class TameHandler:
    """Attempt to tame a reachable wild creature into a pet."""

    command_type = "tame"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        creature_id, creature, rejection = require_reachable_entity(
            ctx,
            character,
            command.payload.get("creature_id"),
            invalid_reason="invalid creature id",
            missing_reason="creature does not exist",
            unreachable_reason="that creature is not here",
        )
        if rejection is not None:
            return rejection
        if not creature.has_component(TameableComponent):
            return rejected("that creature cannot be tamed")

        tameable = creature.get_component(TameableComponent)
        step = SKITTISH_AFFINITY_STEP if tameable.skittish else TAME_AFFINITY_STEP
        # Optional loresim synergy: knowing the species eases the taming (0.0 sans loresim).
        step += known_species_bonus(ctx.world, character_id, tameable.species)
        bond = adjust_bond(
            ctx.world, creature_id, character_id, {"affinity": step, "trust": step / 2}
        )
        tamed = bond.affinity >= tameable.tame_threshold
        if tamed:
            creature.remove_component(TameableComponent)
            creature.add_component(PetComponent(species=tameable.species, tricks=tameable.tricks))
            set_owner(creature, character_id, since_epoch=ctx.epoch)

        room = room_of(ctx.world, character_id)
        return ok(
            PetTamedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(creature_id),),
                    creature_id=str(creature_id),
                    tamed=tamed,
                    affinity=bond.affinity,
                    species=tameable.species,
                )
            )
        )


def tame_progress(world, creature_id, character_id) -> float:
    """Current creature -> tamer affinity, or ``0.0`` if they have never interacted."""
    bond = bond_between(world, creature_id, character_id)
    return bond.affinity if bond is not None else 0.0


TAME_DEF = ActionDefinition(
    command_type="tame",
    title="Tame creature",
    description="Coax a wild creature toward becoming your pet. May take several attempts.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "creature_id": ActionArgument(
            title="Creature",
            description="The wild creature to tame.",
            kind="entity",
            required=True,
        ),
    },
)


__all__ = [
    "SKITTISH_AFFINITY_STEP",
    "TAME_AFFINITY_STEP",
    "TAME_DEF",
    "TameHandler",
    "tame_progress",
]
