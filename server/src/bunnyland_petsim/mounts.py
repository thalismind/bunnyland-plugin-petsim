"""Mounts & riding — the v2 headline mechanic.

A trained pet can become a *mount*: a rideable creature that carries its owner between
rooms far faster than walking. Riding is a repeatable relationship (a mount can carry a
different rider over its life, and a rider can switch mounts), so it is modelled as its own
:class:`RiddenBy` typed edge (mount -> rider) with its own index — never a list on a
component.

Three verbs:

- ``ride`` mounts a reachable mount you own.
- ``dismount`` gets you back off.
- ``ride-to`` is the payoff: while mounted you cross up to the mount's ``speed`` exits in a
  single action, spending mount stamina (a core :class:`Meter`). This is the surface a
  travel/cartography pack consumes for fast-travel — :class:`MountComponent` is published,
  and :class:`MountTraveledEvent` announces each ride.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    ContainmentMode,
    Contains,
    ExitTo,
    remove_from_container,
)
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
from bunnyland.foundation.meters.mechanics import Meter, band, changed
from bunnyland.foundation.social.mechanics import adjust_bond
from pydantic.dataclasses import dataclass
from relics import Component, Edge, Entity, EntityId, World

from .edges import owner_id_of
from .events import DismountedEvent, MountedEvent, MountTraveledEvent
from .spatial import room_of

#: Tiredness a mount accrues per exit crossed (raises its stamina need meter).
STAMINA_PER_HOP = 20.0

#: Trust a rider builds with a mount each time they ride it.
RIDE_TRUST = 0.05


@dataclass(frozen=True)
class MountComponent(Component):
    """Marks a pet as a rideable mount (published for travel/cartography packs).

    ``speed`` is the number of exits a single ``ride-to`` crosses. ``stamina`` is a core
    need :class:`Meter` where a higher value means a more tired mount; it rests back down
    on its own via :class:`bunnyland_petsim.petcare.PetCareConsequence`.
    """

    speed: int = 2
    stamina: Meter = Meter()


@dataclass(frozen=True)
class RiddenBy(Edge):
    """mount -> rider. A mount carries at most one rider at a time."""

    since_epoch: int = 0


def set_rider(mount: Entity, rider_id: EntityId, *, since_epoch: int = 0) -> None:
    """Seat ``rider_id`` on ``mount`` (replaces any existing rider — one rider per mount)."""
    for _edge, target_id in list(mount.get_relationships(RiddenBy)):
        mount.remove_relationship(RiddenBy, target_id)
    mount.add_relationship(RiddenBy(since_epoch=since_epoch), rider_id)


def clear_rider(mount: Entity) -> None:
    """Remove any rider from ``mount``."""
    for _edge, target_id in list(mount.get_relationships(RiddenBy)):
        mount.remove_relationship(RiddenBy, target_id)


def rider_of(mount: Entity) -> EntityId | None:
    """The id of the rider currently on ``mount``, or ``None``."""
    for _edge, rider_id in mount.get_relationships(RiddenBy):
        return rider_id
    return None


def mount_of(world: World, rider_id: EntityId) -> Entity | None:
    """The mount ``rider_id`` is currently riding, or ``None``."""
    if not world.has_entity(rider_id):
        return None
    rider = world.get_entity(rider_id)
    for mount_id, _edge in rider.get_incoming_relationships(RiddenBy):
        if world.has_entity(mount_id):
            return world.get_entity(mount_id)
    return None


def is_mount(entity: Entity) -> bool:
    """Whether ``entity`` is a rideable mount (the published connector predicate)."""
    return entity.has_component(MountComponent)


def owned_mounts(world: World, owner_id: EntityId) -> list[Entity]:
    """Rideable mounts owned by ``owner_id`` — the surface a travel pack reads."""
    from .edges import owned_pets

    return [pet for pet in owned_pets(world, owner_id) if is_mount(pet)]


class RideHandler:
    """Mount a rideable pet you own."""

    command_type = "ride"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        mount_id, mount, rejection = require_reachable_entity(
            ctx,
            character,
            command.payload.get("mount_id"),
            invalid_reason="invalid mount id",
            missing_reason="mount does not exist",
            unreachable_reason="that mount is not here",
        )
        if rejection is not None:
            return rejection
        if not mount.has_component(MountComponent):
            return rejected("that is not a mount")
        if owner_id_of(mount) != character_id:
            return rejected("that is not your mount")
        current = rider_of(mount)
        if current is not None and current != character_id:
            return rejected("someone is already riding that mount")
        if mount_of(ctx.world, character_id) is not None:
            return rejected("you are already riding")

        set_rider(mount, character_id, since_epoch=ctx.epoch)
        bond = adjust_bond(ctx.world, mount_id, character_id, {"trust": RIDE_TRUST})
        room = room_of(ctx.world, character_id)
        return ok(
            MountedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(mount_id),),
                    mount_id=str(mount_id),
                    rider_id=str(character_id),
                    trust=bond.trust,
                )
            )
        )


class DismountHandler:
    """Get off the mount you are currently riding."""

    command_type = "dismount"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, _character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        mount = mount_of(ctx.world, character_id)
        if mount is None:
            return rejected("you are not riding anything")
        clear_rider(mount)
        room = room_of(ctx.world, character_id)
        return ok(
            DismountedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(mount.id),),
                    mount_id=str(mount.id),
                    rider_id=str(character_id),
                )
            )
        )


def _relocate(world: World, entity: Entity, destination: Entity) -> None:
    remove_from_container(world, entity.id)
    destination.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id)


def _exit_toward(room: Entity, direction: str | None):
    """Return the destination room id reachable from ``room`` in ``direction``."""
    for edge, target_id in room.get_relationships(ExitTo):
        if edge.locked:
            continue
        if direction is None or edge.direction == direction:
            return target_id, edge.direction
    return None, None


class RideToHandler:
    """Ride your mount across several rooms in one action (mounts speed travel)."""

    command_type = "ride-to"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        mount = mount_of(ctx.world, character_id)
        if mount is None:
            return rejected("you are not riding anything")
        component = mount.get_component(MountComponent)
        if band(component.stamina) == "crisis":
            return rejected("your mount is too tired")

        start_room = room_of(ctx.world, character_id)
        if start_room is None:
            return rejected("you are not in a room")

        direction = command.payload.get("direction")
        stamina = component.stamina
        current_room = start_room
        hops = 0
        chosen_direction: str | None = None
        for _ in range(max(0, component.speed)):
            if band(stamina) == "crisis":
                break
            destination_id, edge_direction = _exit_toward(current_room, direction)
            if destination_id is None or not ctx.world.has_entity(destination_id):
                break
            destination = ctx.world.get_entity(destination_id)
            _relocate(ctx.world, character, destination)
            _relocate(ctx.world, mount, destination)
            stamina = changed(stamina, STAMINA_PER_HOP)
            current_room = destination
            chosen_direction = edge_direction
            hops += 1

        if hops == 0:
            return rejected("no matching exit")

        replace_component(mount, replace(component, stamina=stamina))
        return ok(
            MountTraveledEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(current_room.id),
                    target_ids=(str(mount.id),),
                    mount_id=str(mount.id),
                    rider_id=str(character_id),
                    from_room_id=str(start_room.id),
                    to_room_id=str(current_room.id),
                    hops=hops,
                    direction=chosen_direction,
                )
            )
        )


RIDE_DEF = ActionDefinition(
    command_type="ride",
    title="Ride mount",
    description="Climb onto a trained mount you own so it can carry you.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "mount_id": ActionArgument(
            title="Mount", description="The mount to ride.", kind="entity", required=True
        ),
    },
)

DISMOUNT_DEF = ActionDefinition(
    command_type="dismount",
    title="Dismount",
    description="Get down off the mount you are riding.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={},
)

RIDE_TO_DEF = ActionDefinition(
    command_type="ride-to",
    title="Ride to",
    description="Ride your mount through several rooms in a single burst of travel.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "direction": ActionArgument(
            title="Direction",
            description="The exit direction to ride toward.",
            kind="string",
            required=True,
        ),
    },
)


__all__ = [
    "DISMOUNT_DEF",
    "RIDE_DEF",
    "RIDE_TO_DEF",
    "RIDE_TRUST",
    "STAMINA_PER_HOP",
    "DismountHandler",
    "MountComponent",
    "RiddenBy",
    "RideHandler",
    "RideToHandler",
    "clear_rider",
    "is_mount",
    "mount_of",
    "owned_mounts",
    "rider_of",
    "set_rider",
]
