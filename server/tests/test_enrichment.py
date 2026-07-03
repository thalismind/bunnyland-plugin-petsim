from __future__ import annotations

import asyncio

from bunnyland.core import CharacterComponent, IdentityComponent, WorldActor, spawn_entity
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import CharacterGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_petsim import TameableComponent


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_petsim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def _character(actor, *, tags=(), description=""):
    entity = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    event = CharacterGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="npc",
        entity_kind="character",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        character_key="npc",
        room_id="room_1",
    )
    _publish(actor, event)
    return entity


def test_wild_creature_gets_tameable_from_tags():
    actor = _actor()
    fox = _character(actor, tags=("fox", "wild"))
    assert fox.has_component(TameableComponent)
    assert fox.get_component(TameableComponent).species == "fox"


def test_wild_creature_detected_from_description():
    actor = _actor()
    critter = _character(actor, description="a stray animal skulking in the barn")
    assert critter.has_component(TameableComponent)


def test_feral_creature_is_marked_skittish():
    actor = _actor()
    beast = _character(actor, tags=("feral", "beast"))
    assert beast.get_component(TameableComponent).skittish is True


def test_plain_villager_is_not_tameable():
    actor = _actor()
    villager = _character(actor, tags=("farmer", "friendly"), description="a cheerful baker")
    assert not villager.has_component(TameableComponent)
