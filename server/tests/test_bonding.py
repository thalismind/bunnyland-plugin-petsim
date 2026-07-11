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
from bunnyland.foundation.consumables.components import ConsumableComponent, FoodComponent
from bunnyland.foundation.social.mechanics import bond_between

from bunnyland_petsim import PetComponent, PetFedEvent, spawn_pet
from bunnyland_petsim.bonding import FeedPetHandler, loyalty_band


def _scene():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Den")])
    owner = spawn_entity(
        actor.world, [IdentityComponent(name="Ren", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)
    return actor, room, owner


def _food(actor, owner, *, satiety=10.0, uses=1):
    food = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="kibble", kind="item"),
            FoodComponent(nutrition=satiety, satiety=satiety),
            ConsumableComponent(current_uses=uses, max_uses=uses),
        ],
    )
    owner.add_relationship(Contains(mode=ContainmentMode.INVENTORY), food.id)
    return food


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="feed-pet",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=2)


def test_feeding_raises_happiness_and_bond_and_consumes_food():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)
    before = pet.get_component(PetComponent).happiness
    food = _food(actor, owner, satiety=12.0)

    result = FeedPetHandler().execute(
        _ctx(actor), _cmd(owner.id, {"pet_id": str(pet.id), "item_id": str(food.id)})
    )

    assert result.ok
    event = result.events[0]
    assert isinstance(event, PetFedEvent)
    assert pet.get_component(PetComponent).happiness == before + 12.0
    bond = bond_between(actor.world, pet.id, owner.id)
    assert bond is not None and bond.affinity > 0.0
    assert not actor.world.has_entity(food.id)  # single-use food destroyed


def test_happiness_clamps_at_maximum():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)
    food = _food(actor, owner, satiety=1000.0)

    FeedPetHandler().execute(
        _ctx(actor), _cmd(owner.id, {"pet_id": str(pet.id), "item_id": str(food.id)})
    )

    assert pet.get_component(PetComponent).happiness == 100.0


def test_multi_use_food_survives_one_feeding():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)
    food = _food(actor, owner, uses=3)

    FeedPetHandler().execute(
        _ctx(actor), _cmd(owner.id, {"pet_id": str(pet.id), "item_id": str(food.id)})
    )

    assert actor.world.has_entity(food.id)
    assert food.get_component(ConsumableComponent).current_uses == 2


def test_feed_rejects_non_food_item():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)
    stick = spawn_entity(actor.world, [IdentityComponent(name="stick", kind="item")])
    owner.add_relationship(Contains(mode=ContainmentMode.INVENTORY), stick.id)

    result = FeedPetHandler().execute(
        _ctx(actor), _cmd(owner.id, {"pet_id": str(pet.id), "item_id": str(stick.id)})
    )

    assert not result.ok
    assert result.reason == "that is not food"


def test_feed_rejects_non_pet_target():
    actor, room, owner = _scene()
    crate = spawn_entity(actor.world, [IdentityComponent(name="crate", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), crate.id)
    food = _food(actor, owner)

    result = FeedPetHandler().execute(
        _ctx(actor), _cmd(owner.id, {"pet_id": str(crate.id), "item_id": str(food.id)})
    )

    assert not result.ok
    assert result.reason == "that is not a pet"


def test_feed_rejects_missing_food():
    actor, room, owner = _scene()
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)

    result = FeedPetHandler().execute(
        _ctx(actor), _cmd(owner.id, {"pet_id": str(pet.id), "item_id": "entity_9999"})
    )

    assert not result.ok
    assert result.reason == "food does not exist"


def test_loyalty_band_thresholds():
    assert loyalty_band(-0.5) == "wary"
    assert loyalty_band(0.1) == "warming"
    assert loyalty_band(0.45) == "friendly"
    assert loyalty_band(0.7) == "devoted"
    assert loyalty_band(0.95) == "inseparable"
