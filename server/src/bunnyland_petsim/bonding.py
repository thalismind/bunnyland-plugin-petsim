"""Bonding & loyalty: the ``feed-pet`` verb and loyalty-band helpers.

Feeding a pet a food item raises its happiness and grows a directed :class:`SocialBond`
from the pet toward the feeder (affinity + trust). That same bond drives the loyalty prompt
fragment, so a well-fed pet reads as devoted. Feeding spends one use of a consumable food
item, destroying it when its uses run out (mirroring the core eat verb).
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import Contains, container_of
from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
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
from bunnyland.foundation.consumables.components import ConsumableComponent, FoodComponent
from bunnyland.foundation.social.mechanics import adjust_bond, bond_between

from .components import PetComponent, clamp_happiness
from .events import PetFedEvent
from .spatial import room_of

#: Bond growth from a single feeding.
FEED_AFFINITY = 0.15
FEED_TRUST = 0.1


def _consume_one_use(ctx: HandlerContext, item) -> None:
    """Spend one use of a consumable food item; destroy it when uses run out."""
    if not item.has_component(ConsumableComponent):
        return
    consumable = item.get_component(ConsumableComponent)
    remaining = consumable.current_uses - 1
    if remaining <= 0:
        holder_id = container_of(item)
        if holder_id is not None and ctx.world.has_entity(holder_id):
            ctx.world.get_entity(holder_id).remove_relationship(Contains, item.id)
        ctx.world.remove(item.id)
    else:
        replace_component(item, replace(consumable, current_uses=remaining))


class FeedPetHandler:
    """Feed a food item to a pet, raising its happiness and loyalty."""

    command_type = "feed-pet"

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
        item_id, item, rejection = require_reachable_entity(
            ctx,
            character,
            command.payload.get("item_id"),
            invalid_reason="invalid food id",
            missing_reason="food does not exist",
            unreachable_reason="that food is not here",
        )
        if rejection is not None:
            return rejection
        if not pet.has_component(PetComponent):
            return rejected("that is not a pet")
        if not item.has_component(FoodComponent):
            return rejected("that is not food")

        food = item.get_component(FoodComponent)
        component = pet.get_component(PetComponent)
        happiness = clamp_happiness(component.happiness + food.satiety)
        replace_component(pet, replace(component, happiness=happiness))
        bond = adjust_bond(
            ctx.world, pet_id, character_id, {"affinity": FEED_AFFINITY, "trust": FEED_TRUST}
        )
        _consume_one_use(ctx, item)

        room = room_of(ctx.world, character_id)
        return ok(
            PetFedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(pet_id), str(item_id)),
                    pet_id=str(pet_id),
                    item_id=str(item_id),
                    happiness=happiness,
                    affinity=bond.affinity,
                )
            )
        )


# Loyalty bands read off the pet -> owner bond affinity, warmest last.
def loyalty_band(affinity: float) -> str:
    """Coarse loyalty label for a pet -> owner affinity in ``[-1, 1]``."""
    if affinity <= 0.0:
        return "wary"
    if affinity < 0.3:
        return "warming"
    if affinity < 0.6:
        return "friendly"
    if affinity < 0.85:
        return "devoted"
    return "inseparable"


_LOYALTY_PHRASES = {
    "wary": "keeps its distance, not yet sure of you",
    "warming": "watches you, slowly warming",
    "friendly": "stays close, comfortable with you",
    "devoted": "pads at your heels, devoted",
    "inseparable": "will not leave your side",
}


def loyalty_line(world, pet, owner_id) -> str | None:
    """Render a first-person loyalty line for ``pet`` toward ``owner_id``, or ``None``."""
    component = pet.get_component(PetComponent)
    bond = bond_between(world, pet.id, owner_id)
    affinity = bond.affinity if bond is not None else 0.0
    phrase = _LOYALTY_PHRASES[loyalty_band(affinity)]
    return f"Your {component.species} {phrase}."


FEED_PET_DEF = ActionDefinition(
    command_type="feed-pet",
    title="Feed pet",
    description="Feed a food item to a pet to raise its happiness and loyalty.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "pet_id": ActionArgument(
            title="Pet", description="The pet to feed.", kind="entity", required=True
        ),
        "item_id": ActionArgument(
            title="Food", description="The food item to feed it.", kind="entity", required=True
        ),
    },
)


__all__ = [
    "FEED_AFFINITY",
    "FEED_PET_DEF",
    "FEED_TRUST",
    "FeedPetHandler",
    "loyalty_band",
    "loyalty_line",
]
