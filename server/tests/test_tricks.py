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
from conftest import execute_handler

from bunnyland_petsim import PetComponent, PetTrickEvent, is_threat, perceived_threats, spawn_pet
from bunnyland_petsim.tricks import TrickHandler


def _scene():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Yard")])
    owner = spawn_entity(
        actor.world, [IdentityComponent(name="Sol", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)
    return actor, room, owner


def _threat(actor, room, name="wolf", tags=("hostile",)):
    beast = spawn_entity(actor.world, [IdentityComponent(name=name, kind="character", tags=tags)])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), beast.id)
    return beast


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="trick",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=3)


def test_trick_performs_known_trick_and_raises_happiness():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, tricks=("sit",))
    before = pet.get_component(PetComponent).happiness

    result = execute_handler(
        TrickHandler(), _ctx(actor), _cmd(owner.id, {"pet_id": str(pet.id), "trick": "sit"})
    )

    assert result.ok
    event = result.events[0]
    assert isinstance(event, PetTrickEvent)
    assert event.trick == "sit"
    assert pet.get_component(PetComponent).happiness > before


def test_trick_rejects_unknown_trick():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, tricks=("sit",))

    result = execute_handler(
        TrickHandler(), _ctx(actor), _cmd(owner.id, {"pet_id": str(pet.id), "trick": "backflip"})
    )

    assert not result.ok
    assert result.reason == "your pet does not know that trick"


def test_trick_rejects_non_owner():
    actor, room, owner = _scene()
    other = spawn_entity(
        actor.world, [IdentityComponent(name="Mo", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), other.id)
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, tricks=("sit",))

    result = execute_handler(
        TrickHandler(), _ctx(actor), _cmd(other.id, {"pet_id": str(pet.id), "trick": "sit"})
    )

    assert not result.ok
    assert result.reason == "that is not your pet"


def test_is_threat_classifies_by_identity():
    actor, room, _owner = _scene()
    wolf = _threat(actor, room, name="wolf", tags=())
    baker = spawn_entity(actor.world, [IdentityComponent(name="baker", kind="character")])
    assert is_threat(wolf)
    assert not is_threat(baker)


def test_perceived_threats_lists_room_hostiles_only():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)
    wolf = _threat(actor, room)
    # A friendly item in the room is not a threat.
    spawn_entity(actor.world, [IdentityComponent(name="ball", kind="item")])

    threats = perceived_threats(actor.world, pet)

    assert [t.id for t in threats] == [wolf.id]
