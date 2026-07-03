from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext

from bunnyland_petsim import (
    PetComponent,
    PetTamedEvent,
    TameableComponent,
    owner_id_of,
    spawn_tameable,
)
from bunnyland_petsim.taming import TameHandler


def _scene():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Meadow")])
    tamer = spawn_entity(
        actor.world, [IdentityComponent(name="Ivy", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), tamer.id)
    return actor, room, tamer


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="tame",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=1)


def test_taming_takes_multiple_attempts():
    actor, room, tamer = _scene()
    creature = spawn_tameable(actor.world, room_id=room.id, species="fox", tame_threshold=0.6)
    handler = TameHandler()

    first = handler.execute(_ctx(actor), _cmd(tamer.id, {"creature_id": str(creature.id)}))
    assert first.ok
    assert first.events[0].tamed is False
    assert creature.has_component(TameableComponent)
    assert not creature.has_component(PetComponent)

    second = handler.execute(_ctx(actor), _cmd(tamer.id, {"creature_id": str(creature.id)}))
    assert second.ok
    event = second.events[0]
    assert isinstance(event, PetTamedEvent)
    assert event.tamed is True
    assert not creature.has_component(TameableComponent)
    assert creature.has_component(PetComponent)
    assert creature.get_component(PetComponent).species == "fox"
    assert owner_id_of(creature) == tamer.id


def test_taming_transfers_tricks_to_pet():
    actor, room, tamer = _scene()
    creature = spawn_tameable(
        actor.world, room_id=room.id, tame_threshold=0.1, tricks=("sit", "roll")
    )
    result = TameHandler().execute(_ctx(actor), _cmd(tamer.id, {"creature_id": str(creature.id)}))
    assert result.events[0].tamed is True
    assert creature.get_component(PetComponent).tricks == ("sit", "roll")


def test_skittish_creature_needs_more_attempts():
    actor, room, tamer = _scene()
    creature = spawn_tameable(
        actor.world, room_id=room.id, tame_threshold=0.6, skittish=True
    )
    handler = TameHandler()
    # Skittish step is 0.17, so two attempts (0.34) is not enough for a 0.6 threshold.
    handler.execute(_ctx(actor), _cmd(tamer.id, {"creature_id": str(creature.id)}))
    handler.execute(_ctx(actor), _cmd(tamer.id, {"creature_id": str(creature.id)}))
    assert creature.has_component(TameableComponent)


def test_tame_rejects_non_tameable_target():
    actor, room, tamer = _scene()
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)

    result = TameHandler().execute(_ctx(actor), _cmd(tamer.id, {"creature_id": str(rock.id)}))

    assert not result.ok
    assert result.reason == "that creature cannot be tamed"


def test_tame_rejects_unreachable_creature():
    actor, room, tamer = _scene()
    elsewhere = spawn_entity(actor.world, [RoomComponent(title="Far")])
    creature = spawn_tameable(actor.world, room_id=elsewhere.id)

    result = TameHandler().execute(_ctx(actor), _cmd(tamer.id, {"creature_id": str(creature.id)}))

    assert not result.ok
    assert result.reason == "that creature is not here"


def test_tame_rejects_invalid_creature_id():
    actor, _room, tamer = _scene()

    result = TameHandler().execute(_ctx(actor), _cmd(tamer.id, {"creature_id": "???"}))

    assert not result.ok
    assert result.reason == "invalid creature id"
