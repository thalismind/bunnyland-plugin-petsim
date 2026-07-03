from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component
from bunnyland.mechanics.social import adjust_bond

from bunnyland_petsim import PetComponent, petsim_fragments, spawn_pet


def _scene():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Hall")])
    owner = spawn_entity(
        actor.world, [IdentityComponent(name="Ada", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)
    return actor, room, owner


def test_owner_reads_devoted_loyalty_line():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="fox")
    adjust_bond(actor.world, pet.id, owner.id, {"affinity": 0.7})  # devoted band

    lines = petsim_fragments(actor.world, owner)

    assert "Your fox pads at your heels, devoted." in lines


def test_nervous_pet_reaction_to_threat():
    actor, room, owner = _scene()
    spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="fox", nervous=True)
    beast = spawn_entity(
        actor.world, [IdentityComponent(name="wolf", kind="character", tags=("hostile",))]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), beast.id)

    lines = petsim_fragments(actor.world, owner)

    assert "Your fox cowers, terrified of the wolf." in lines


def test_calm_pet_has_no_reaction_line():
    actor, room, owner = _scene()
    spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="fox")

    lines = petsim_fragments(actor.world, owner)

    assert all("wary" not in line and "cowers" not in line for line in lines)


def test_non_owner_sees_third_person_reaction_but_no_loyalty():
    actor, room, owner = _scene()
    bystander = spawn_entity(
        actor.world, [IdentityComponent(name="Kip", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), bystander.id)
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="fox")
    replace_component(pet, replace(pet.get_component(PetComponent), nervous=False))
    beast = spawn_entity(
        actor.world, [IdentityComponent(name="bear", kind="character", tags=("predator",))]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), beast.id)

    lines = petsim_fragments(actor.world, bystander)

    assert "A fox here bristles, wary of the bear." in lines
    assert all("devoted" not in line and "heels" not in line for line in lines)
