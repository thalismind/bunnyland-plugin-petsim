"""Training & skill-leveling: raise a pet's discipline, and graduate it into a mount.

Each ``train`` session grows a pet's :class:`TrainingComponent` experience. Crossing a
level threshold levels the pet up (deterministically, no RNG); the surplus carries over.
Once a pet reaches :data:`MOUNT_TRAINING_LEVEL` it *graduates into a mount* — a
:class:`bunnyland_petsim.mounts.MountComponent` is attached — which is how the training
support mechanic feeds the mounts headline. Training also warms the pet -> owner bond
(core :class:`SocialBond`).
"""

from __future__ import annotations

from dataclasses import replace

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
from bunnyland.mechanics.social import adjust_bond
from pydantic.dataclasses import dataclass
from relics import Component

from .components import PetComponent, clamp_happiness
from .edges import owner_id_of
from .events import PetTrainedEvent
from .mounts import MountComponent
from .spatial import room_of

#: Experience granted by one training session.
TRAIN_XP_STEP = 4.0

#: Bond affinity growth from a training session.
TRAIN_AFFINITY = 0.08

#: Happiness a pet gains from a training session.
TRAIN_HAPPINESS = 2.0

#: Level at which a trained pet graduates into a rideable mount.
MOUNT_TRAINING_LEVEL = 3


@dataclass(frozen=True)
class TrainingComponent(Component):
    """A pet's training progress in a named discipline."""

    discipline: str = "obedience"
    level: int = 1
    xp: float = 0.0
    xp_per_level: float = 10.0


def _advance(training: TrainingComponent, gained: float) -> tuple[TrainingComponent, bool]:
    """Add ``gained`` xp, rolling whole levels over. Returns (new training, leveled?)."""
    xp = training.xp + gained
    level = training.level
    leveled = False
    while xp >= training.xp_per_level:
        xp -= training.xp_per_level
        level += 1
        leveled = True
    return replace(training, level=level, xp=xp), leveled


class TrainHandler:
    """Run a training session with a pet you own."""

    command_type = "train"

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

        discipline = command.payload.get("discipline") or "obedience"
        training = (
            pet.get_component(TrainingComponent)
            if pet.has_component(TrainingComponent)
            else TrainingComponent(discipline=discipline)
        )
        training, leveled = _advance(training, TRAIN_XP_STEP)
        if pet.has_component(TrainingComponent):
            replace_component(pet, training)
        else:
            pet.add_component(training)

        became_mount = False
        if training.level >= MOUNT_TRAINING_LEVEL and not pet.has_component(MountComponent):
            pet.add_component(MountComponent())
            became_mount = True

        component = pet.get_component(PetComponent)
        replace_component(
            pet,
            replace(component, happiness=clamp_happiness(component.happiness + TRAIN_HAPPINESS)),
        )
        adjust_bond(ctx.world, pet_id, character_id, {"affinity": TRAIN_AFFINITY})

        room = room_of(ctx.world, character_id)
        return ok(
            PetTrainedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(pet_id),),
                    pet_id=str(pet_id),
                    discipline=training.discipline,
                    level=training.level,
                    leveled_up=leveled,
                    became_mount=became_mount,
                )
            )
        )


TRAIN_DEF = ActionDefinition(
    command_type="train",
    title="Train pet",
    description="Run a training session with a pet you own to raise its skill.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "pet_id": ActionArgument(
            title="Pet", description="The pet to train.", kind="entity", required=True
        ),
        "discipline": ActionArgument(
            title="Discipline",
            description="Optional discipline name (defaults to obedience).",
            kind="string",
            required=False,
        ),
    },
)


__all__ = [
    "MOUNT_TRAINING_LEVEL",
    "TRAIN_AFFINITY",
    "TRAIN_DEF",
    "TRAIN_HAPPINESS",
    "TRAIN_XP_STEP",
    "TrainHandler",
    "TrainingComponent",
]
