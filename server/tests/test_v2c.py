"""v2 behavior tests: storyteller stampede incident + core-affect reactor."""

from __future__ import annotations

import asyncio

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.edges import HasThought
from bunnyland.core.events import EventVisibility, event_base
from bunnyland.foundation.storyteller.mechanics import IncidentComponent

from bunnyland_petsim import (
    Follows,
    PetAffectReactor,
    PetComponent,
    PetLostEvent,
    PetPlayedEvent,
    PetStampedeEvent,
    PetTrainedEvent,
    StampedeConsequence,
    spawn_pet,
)
from bunnyland_petsim.components import STAY
from bunnyland_petsim.incidents import _room_by_id


def _room(world, title="Square"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _owner(world, room, name="Rhea"):
    owner = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)
    return owner


def _incident(world, room, kind="hostile_encounter", resolved=None):
    return spawn_entity(
        world,
        [
            IncidentComponent(
                kind=kind,
                budget_spent=1.0,
                started_at_epoch=0,
                room_id=str(room.id),
                resolved_at_epoch=resolved,
            )
        ],
    )


# --------------------------------------------------------------------------------------
# Stampede consequence
# --------------------------------------------------------------------------------------


def test_calm_pet_is_spooked_but_stays():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="pup")
    _incident(actor.world, room)

    events = StampedeConsequence().process(actor.world, 10)
    stampedes = [e for e in events if isinstance(e, PetStampedeEvent)]
    assert len(stampedes) == 1
    assert stampedes[0].incident_kind == "hostile_encounter"
    assert stampedes[0].lost_pet_ids == ()
    component = pet.get_component(PetComponent)
    assert component.mode == STAY
    assert component.nervous
    assert component.happiness < 50.0


def test_nervous_pet_bolts_and_is_lost():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="hare", nervous=True)
    _incident(actor.world, room, kind="kaiju_attack")

    events = StampedeConsequence().process(actor.world, 20)
    lost = [e for e in events if isinstance(e, PetLostEvent)]
    assert len(lost) == 1
    assert lost[0].pet_id == str(pet.id)
    assert lost[0].owner_id == str(owner.id)
    # Bolted: it no longer follows anyone.
    assert list(pet.get_relationships(Follows)) == []
    stampede = next(e for e in events if isinstance(e, PetStampedeEvent))
    assert stampede.lost_pet_ids == (str(pet.id),)


def test_resolved_incident_is_ignored():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)
    _incident(actor.world, room, resolved=5)
    assert StampedeConsequence().process(actor.world, 10) == []


def test_non_threat_incident_is_ignored():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_pet(actor.world, room_id=room.id)
    _incident(actor.world, room, kind="good_harvest")
    assert StampedeConsequence().process(actor.world, 10) == []


def test_incident_without_a_room_is_ignored():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_pet(actor.world, room_id=room.id)
    spawn_entity(
        actor.world,
        [IncidentComponent(kind="hostile_encounter", budget_spent=1.0, started_at_epoch=0)],
    )
    assert StampedeConsequence().process(actor.world, 10) == []


def test_staying_pet_is_not_panicked():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)
    from dataclasses import replace

    from bunnyland.core.ecs import replace_component

    replace_component(pet, replace(pet.get_component(PetComponent), mode=STAY))
    _incident(actor.world, room)
    assert StampedeConsequence().process(actor.world, 10) == []


def test_incident_pointing_at_a_vanished_room_is_ignored():
    actor = WorldActor()
    room = _room(actor.world)
    incident = spawn_entity(
        actor.world,
        [
            IncidentComponent(
                kind="barbarian_raid",
                budget_spent=1.0,
                started_at_epoch=0,
                room_id="not-a-real-id",
            )
        ],
    )
    assert incident is not None
    assert StampedeConsequence().process(actor.world, 10) == []
    # And the helper is defensive about junk ids too.
    assert _room_by_id(actor.world, "not-a-real-id") is None
    assert _room_by_id(actor.world, str(room.id)) is not None


# --------------------------------------------------------------------------------------
# Affect reactor
# --------------------------------------------------------------------------------------


def _thoughts(world, owner):
    return [
        world.get_entity(target_id)
        for _edge, target_id in owner.get_relationships(HasThought)
        if world.has_entity(target_id)
    ]


def _played(world, owner_id, epoch=3):
    return PetPlayedEvent(
        **event_base(
            epoch,
            visibility=EventVisibility.ROOM,
            actor_id=str(owner_id),
            pet_id="p",
            owner_id=str(owner_id),
            happiness=60.0,
        )
    )


def test_reactor_adds_a_thought_on_play():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    reactor = PetAffectReactor(actor.world)
    reactor._on_played(_played(actor.world, owner.id))
    thoughts = _thoughts(actor.world, owner)
    assert len(thoughts) == 1


def test_reactor_records_a_proud_thought_only_on_level_up():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    reactor = PetAffectReactor(actor.world)
    not_leveled = PetTrainedEvent(
        **event_base(3, actor_id=str(owner.id), pet_id="p", discipline="obedience", level=1)
    )
    reactor._on_trained(not_leveled)
    assert _thoughts(actor.world, owner) == []
    leveled = PetTrainedEvent(
        **event_base(
            3,
            actor_id=str(owner.id),
            pet_id="p",
            discipline="obedience",
            level=2,
            leveled_up=True,
        )
    )
    reactor._on_trained(leveled)
    assert len(_thoughts(actor.world, owner)) == 1


def test_reactor_records_worry_when_a_pet_is_lost():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    reactor = PetAffectReactor(actor.world)
    lost = PetLostEvent(**event_base(3, actor_id="p", pet_id="p", owner_id=str(owner.id)))
    reactor._on_lost(lost)
    assert len(_thoughts(actor.world, owner)) == 1


def test_reactor_ignores_a_missing_owner():
    actor = WorldActor()
    reactor = PetAffectReactor(actor.world)
    reactor._on_played(_played(actor.world, "missing"))  # no such entity, no crash


def test_reactor_ignores_a_non_character_owner():
    actor = WorldActor()
    thing = spawn_entity(actor.world, [IdentityComponent(name="statue", kind="object")])
    reactor = PetAffectReactor(actor.world)
    reactor._on_played(_played(actor.world, thing.id))
    assert _thoughts(actor.world, thing) == []


def test_reactor_subscribes_to_the_bus():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    reactor = PetAffectReactor(actor.world)
    reactor.subscribe(actor.bus)
    asyncio.run(actor.bus.publish(_played(actor.world, owner.id)))
    assert len(_thoughts(actor.world, owner)) == 1
