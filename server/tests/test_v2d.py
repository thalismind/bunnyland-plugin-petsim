"""v2 behavior tests: optional connectors (tracking/knowledge), mount worldgen, helpers."""

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
from bunnyland.core.generation import GenerationRequest
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import CharacterSpec, RoomSpec, WorldProposal, instantiate
from pydantic.dataclasses import dataclass
from relics import Component

import bunnyland_petsim.knowledge as knowledge
import bunnyland_petsim.tracking as tracking
from bunnyland_petsim import (
    Follows,
    MountComponent,
    TrackerComponent,
    is_mount,
    is_mountlike,
    is_tracker,
    known_species_bonus,
    knows_species,
    mount_of,
    owned_pets,
    owner_id_of,
    scented_targets,
    set_owner,
    set_rider,
    spawn_pet,
    tracking_fragments,
)
from bunnyland_petsim.knowledge import TAMING_KNOWLEDGE_BONUS
from bunnyland_petsim.plugin import bunnyland_plugins as _plugins
from bunnyland_petsim.spatial import room_of
from bunnyland_petsim.tracking import contents_or_empty
from bunnyland_petsim.worldgen import MOUNT_TERMS


@dataclass(frozen=True)
class FakeScent(Component):
    strength: float = 1.0


@dataclass(frozen=True)
class FakeKnownSpecies(Component):
    species: tuple[str, ...] = ()


def _room(world, title="Field"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _owner(world, room, name="Rhea"):
    owner = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)
    return owner


# --------------------------------------------------------------------------------------
# Tracking connector (consume wildsim Scent)
# --------------------------------------------------------------------------------------


def test_tracking_dormant_without_wildsim():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    hound = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="hound")
    hound.add_component(TrackerComponent())
    assert tracking.Scent is None
    assert scented_targets(actor.world, hound) == []
    assert tracking_fragments(actor.world, owner) == []


def test_is_tracker_predicate():
    actor = WorldActor()
    room = _room(actor.world)
    hound = spawn_pet(actor.world, room_id=room.id, species="hound")
    assert not is_tracker(hound)
    hound.add_component(TrackerComponent())
    assert is_tracker(hound)


def test_tracking_finds_scent_when_wildsim_present(monkeypatch):
    monkeypatch.setattr(tracking, "Scent", FakeScent)
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    hound = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="hound")
    hound.add_component(TrackerComponent())
    quarry = spawn_entity(actor.world, [IdentityComponent(name="hare", kind="character")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), quarry.id)
    quarry.add_component(FakeScent())

    found = scented_targets(actor.world, hound)
    assert [entity.id for entity in found] == [quarry.id]
    lines = tracking_fragments(actor.world, owner)
    assert any("catches a scent" in line for line in lines)


def test_tracking_ignores_scentless_room(monkeypatch):
    monkeypatch.setattr(tracking, "Scent", FakeScent)
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    hound = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="hound")
    hound.add_component(TrackerComponent())
    assert scented_targets(actor.world, hound) == []
    assert tracking_fragments(actor.world, owner) == []


def test_scented_targets_needs_a_room():
    actor = WorldActor()
    hound = spawn_pet(actor.world, species="hound")
    hound.add_component(TrackerComponent())
    # No Scent import, and no room: still empty and no crash.
    assert scented_targets(actor.world, hound) == []


def test_scented_targets_roomless_hound_with_wildsim_present(monkeypatch):
    monkeypatch.setattr(tracking, "Scent", FakeScent)
    actor = WorldActor()
    hound = spawn_pet(actor.world, species="hound")
    hound.add_component(TrackerComponent())
    # wildsim is "present" but the hound is nowhere: no trail to point at.
    assert scented_targets(actor.world, hound) == []


def test_contents_or_empty_handles_roomless_character():
    actor = WorldActor()
    stray = spawn_entity(actor.world, [CharacterComponent()])
    assert contents_or_empty(actor.world, stray) == []


# --------------------------------------------------------------------------------------
# Knowledge connector (consume loresim KnownSpecies)
# --------------------------------------------------------------------------------------


def test_knowledge_dormant_without_loresim():
    actor = WorldActor()
    someone = spawn_entity(actor.world, [CharacterComponent()])
    assert knowledge.KnownSpecies is None
    assert not knows_species(actor.world, someone.id, "fox")
    assert known_species_bonus(actor.world, someone.id, "fox") == 0.0


def test_knowledge_eases_taming_when_loresim_present(monkeypatch):
    monkeypatch.setattr(knowledge, "KnownSpecies", FakeKnownSpecies)
    actor = WorldActor()
    scholar = spawn_entity(actor.world, [CharacterComponent()])
    scholar.add_component(FakeKnownSpecies(species=("fox", "owl")))
    assert knows_species(actor.world, scholar.id, "fox")
    assert not knows_species(actor.world, scholar.id, "toad")
    assert known_species_bonus(actor.world, scholar.id, "fox") == TAMING_KNOWLEDGE_BONUS


def test_knowledge_false_for_missing_or_bare_character(monkeypatch):
    monkeypatch.setattr(knowledge, "KnownSpecies", FakeKnownSpecies)
    actor = WorldActor()
    bare = spawn_entity(actor.world, [CharacterComponent()])
    assert not knows_species(actor.world, bare.id, "fox")  # no KnownSpecies component
    assert not knows_species(actor.world, "missing-id", "fox")  # no such entity


def test_taming_folds_in_the_knowledge_bonus(monkeypatch):
    import bunnyland_petsim.taming as taming

    monkeypatch.setattr(taming, "known_species_bonus", lambda *a, **k: 1.0)
    from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
    from bunnyland.core.handlers import HandlerContext

    from bunnyland_petsim import TameHandler, spawn_tameable

    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    creature = spawn_tameable(actor.world, room_id=room.id, species="fox", skittish=True)
    command = build_submitted_command(
        character_id=str(owner.id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="tame",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload={"creature_id": str(creature.id)},
    )
    result = TameHandler().execute(HandlerContext(world=actor.world, epoch=1), command)
    # Even a skittish creature is tamed in one attempt once the huge bonus lands.
    assert result.ok
    assert result.events[0].tamed


# --------------------------------------------------------------------------------------
# Mount worldgen hook
# --------------------------------------------------------------------------------------


def _generated(*, tags=(), description="", name="beast"):
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    result = asyncio.run(
        instantiate(
            actor,
            WorldProposal(
                seed="seed",
                rooms=[RoomSpec(key="room", title="Room")],
                characters=[
                    CharacterSpec(
                        key="npc",
                        name=name,
                        room_key="room",
                        description=description,
                        traits=tuple(tags),
                    )
                ],
            ),
        )
    )
    return actor.world.get_entity(result.characters["npc"])


def test_mount_worldgen_marks_mountlike_creatures():
    steed = _generated(tags=("horse", "wild"), description="a sturdy steed")
    assert steed.has_component(MountComponent)
    assert is_mount(steed)


def test_mount_worldgen_ignores_non_mounts():
    songbird = _generated(tags=("bird",), description="a tiny songbird")
    assert not songbird.has_component(MountComponent)


def test_is_mountlike_reads_every_mount_term():
    for term in MOUNT_TERMS:
        request = GenerationRequest(
            entity_kind="character",
            tags=(term,),
        )
        assert is_mountlike(request)


# --------------------------------------------------------------------------------------
# Edge & spatial helper mop-up
# --------------------------------------------------------------------------------------


def test_set_owner_replaces_a_prior_owner():
    actor = WorldActor()
    room = _room(actor.world)
    first = _owner(actor.world, room, name="A")
    second = _owner(actor.world, room, name="B")
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=first.id)
    set_owner(pet, second.id)
    assert owner_id_of(pet) == second.id
    assert owned_pets(actor.world, first.id) == []
    assert [p.id for p in owned_pets(actor.world, second.id)] == [pet.id]


def test_owner_id_of_is_none_for_a_stray():
    actor = WorldActor()
    stray = spawn_pet(actor.world, species="stray")
    assert owner_id_of(stray) is None


def test_owned_pets_empty_for_unknown_owner():
    actor = WorldActor()
    assert owned_pets(actor.world, "nobody") == []


def test_set_rider_replaces_a_prior_rider():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    mount = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="pony")
    mount.add_component(MountComponent())
    rider_a = _owner(actor.world, room, name="A")
    rider_b = _owner(actor.world, room, name="B")
    set_rider(mount, rider_a.id)
    set_rider(mount, rider_b.id)
    from bunnyland_petsim import rider_of

    # Exactly one rider survives: the replacement drops the prior edge.
    assert rider_of(mount) == rider_b.id
    assert mount_of(actor.world, rider_a.id) is None
    assert mount_of(actor.world, rider_b.id).id == mount.id


def test_mount_of_is_none_for_unknown_rider():
    actor = WorldActor()
    assert mount_of(actor.world, "nobody") is None


def test_room_of_walks_up_nested_containers():
    actor = WorldActor()
    room = _room(actor.world)
    crate = spawn_entity(actor.world, [IdentityComponent(name="crate", kind="object")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), crate.id)
    trinket = spawn_entity(actor.world, [IdentityComponent(name="trinket", kind="object")])
    crate.add_relationship(Contains(mode=ContainmentMode.CONTAINER), trinket.id)
    assert room_of(actor.world, trinket.id).id == room.id


def test_room_of_none_for_missing_or_roomless():
    actor = WorldActor()
    assert room_of(actor.world, "missing") is None
    loose = spawn_entity(actor.world, [IdentityComponent(name="loose", kind="object")])
    assert room_of(actor.world, loose.id) is None


def test_follows_edge_type_is_the_relationship_index():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id)
    assert any(True for _edge, _target in pet.get_relationships(Follows))
