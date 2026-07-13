from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    container_of,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext
from conftest import execute_handler

from bunnyland_petsim import (
    FollowingConsequence,
    PetComponent,
    PetFollowedEvent,
    set_owner,
    spawn_pet,
)
from bunnyland_petsim.following import CommandPetHandler


def _room(world, title):
    return spawn_entity(world, [RoomComponent(title=title)])


def _owner(world, room):
    owner = spawn_entity(
        world, [IdentityComponent(name="Bram", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)
    return owner


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=0)


def test_following_pet_relocates_into_owner_room():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    garden = _room(actor.world, "Garden")
    owner = _owner(actor.world, kitchen)
    pet = spawn_pet(actor.world, room_id=kitchen.id, owner_id=owner.id, species="fox")

    # Owner walks to the garden.
    kitchen.remove_relationship(Contains, owner.id)
    garden.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)

    events = FollowingConsequence().process(actor.world, 5)

    assert container_of(pet) == garden.id
    followed = [e for e in events if isinstance(e, PetFollowedEvent)]
    assert len(followed) == 1
    assert followed[0].pet_id == str(pet.id)
    assert followed[0].to_room_id == str(garden.id)


def test_staying_pet_does_not_follow():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    garden = _room(actor.world, "Garden")
    owner = _owner(actor.world, kitchen)
    pet = spawn_pet(actor.world, room_id=kitchen.id, owner_id=owner.id)
    from dataclasses import replace

    from bunnyland.core.ecs import replace_component

    replace_component(pet, replace(pet.get_component(PetComponent), mode="stay"))
    kitchen.remove_relationship(Contains, owner.id)
    garden.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)

    events = FollowingConsequence().process(actor.world, 5)

    assert container_of(pet) == kitchen.id
    assert events == []


def test_pet_already_with_owner_does_not_move_or_emit():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    owner = _owner(actor.world, kitchen)
    pet = spawn_pet(actor.world, room_id=kitchen.id, owner_id=owner.id)

    events = FollowingConsequence().process(actor.world, 5)

    assert container_of(pet) == kitchen.id
    assert events == []


def test_ownerless_pet_is_ignored():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    pet = spawn_pet(actor.world, room_id=kitchen.id)  # no owner

    events = FollowingConsequence().process(actor.world, 5)

    assert container_of(pet) == kitchen.id
    assert events == []


def test_command_pet_sets_mode():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    owner = _owner(actor.world, kitchen)
    pet = spawn_pet(actor.world, room_id=kitchen.id, owner_id=owner.id)

    result = execute_handler(
        CommandPetHandler(),
        _ctx(actor),
        _cmd(owner.id, "command-pet", {"pet_id": str(pet.id), "mode": "stay"}),
    )

    assert result.ok
    assert pet.get_component(PetComponent).mode == "stay"


def test_command_pet_rejects_unknown_mode():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    owner = _owner(actor.world, kitchen)
    pet = spawn_pet(actor.world, room_id=kitchen.id, owner_id=owner.id)

    result = execute_handler(
        CommandPetHandler(),
        _ctx(actor),
        _cmd(owner.id, "command-pet", {"pet_id": str(pet.id), "mode": "fetch"}),
    )

    assert not result.ok
    assert result.reason == "unknown pet command"


def test_command_pet_rejects_non_owner():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    owner = _owner(actor.world, kitchen)
    stranger = spawn_entity(
        actor.world, [IdentityComponent(name="Wick", kind="character"), CharacterComponent()]
    )
    kitchen.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), stranger.id)
    pet = spawn_pet(actor.world, room_id=kitchen.id, owner_id=owner.id)

    result = execute_handler(
        CommandPetHandler(),
        _ctx(actor),
        _cmd(stranger.id, "command-pet", {"pet_id": str(pet.id), "mode": "stay"}),
    )

    assert not result.ok
    assert result.reason == "that is not your pet"


def test_command_pet_rejects_non_pet_target():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    owner = _owner(actor.world, kitchen)
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    kitchen.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)

    result = execute_handler(
        CommandPetHandler(),
        _ctx(actor),
        _cmd(owner.id, "command-pet", {"pet_id": str(rock.id), "mode": "stay"}),
    )

    assert not result.ok
    assert result.reason == "that is not a pet"


def test_command_pet_rejects_unreachable_pet():
    actor = WorldActor()
    kitchen = _room(actor.world, "Kitchen")
    garden = _room(actor.world, "Garden")
    owner = _owner(actor.world, kitchen)
    pet = spawn_pet(actor.world, room_id=garden.id)
    set_owner(pet, owner.id)

    result = execute_handler(
        CommandPetHandler(),
        _ctx(actor),
        _cmd(owner.id, "command-pet", {"pet_id": str(pet.id), "mode": "stay"}),
    )

    assert not result.ok
    assert result.reason == "that pet is not here"
