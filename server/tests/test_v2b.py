"""v2 behavior tests: charming pet-care (play-with / groom), drift consequence, fragments."""

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
from bunnyland.foundation.meters.mechanics import Meter, band
from bunnyland.foundation.social.mechanics import bond_between

from bunnyland_petsim import (
    GroomPetHandler,
    MountComponent,
    PetCareComponent,
    PetCareConsequence,
    PetComponent,
    PetGroomedEvent,
    PetPlayedEvent,
    PlayWithPetHandler,
    care_lines,
    petcare_fragments,
    spawn_pet,
)
from bunnyland_petsim.petcare import SECONDS_PER_DAY, _ensure_care


def _room(world, title="Den"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _owner(world, room, name="Rhea"):
    owner = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
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


def _ctx(actor, epoch=1):
    return HandlerContext(world=actor.world, epoch=epoch)


def _scene():
    actor = WorldActor()
    room = _room(actor.world)
    owner = _owner(actor.world, room)
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="pup")
    return actor, room, owner, pet


def test_play_with_cheers_and_settles_restlessness():
    actor, _room, owner, pet = _scene()
    pet.add_component(PetCareComponent(play_need=Meter(value=60.0)))
    result = PlayWithPetHandler().execute(
        _ctx(actor), _cmd(owner.id, "play-with", {"pet_id": str(pet.id)})
    )
    assert result.ok
    assert isinstance(result.events[0], PetPlayedEvent)
    assert pet.get_component(PetCareComponent).play_need.value == 0.0
    assert pet.get_component(PetComponent).happiness > 50.0
    bond = bond_between(actor.world, pet.id, owner.id)
    assert bond is not None and bond.affinity > 0.0


def test_play_with_bootstraps_care_when_absent():
    actor, _room, owner, pet = _scene()
    assert not pet.has_component(PetCareComponent)
    result = PlayWithPetHandler().execute(
        _ctx(actor), _cmd(owner.id, "play-with", {"pet_id": str(pet.id)})
    )
    assert result.ok
    assert pet.has_component(PetCareComponent)


def test_groom_tidies_and_builds_trust():
    actor, _room, owner, pet = _scene()
    pet.add_component(PetCareComponent(grooming=Meter(value=50.0)))
    result = GroomPetHandler().execute(
        _ctx(actor), _cmd(owner.id, "groom", {"pet_id": str(pet.id)})
    )
    assert result.ok
    assert isinstance(result.events[0], PetGroomedEvent)
    assert pet.get_component(PetCareComponent).grooming.value == 0.0
    bond = bond_between(actor.world, pet.id, owner.id)
    assert bond is not None and bond.trust > 0.0


def test_play_with_rejects_invalid_id():
    actor, _room, owner, _pet = _scene()
    result = PlayWithPetHandler().execute(
        _ctx(actor), _cmd(owner.id, "play-with", {"pet_id": "??"})
    )
    assert not result.ok
    assert result.reason == "invalid pet id"


def test_play_with_rejects_non_pet():
    actor, room, owner, _pet = _scene()
    thing = spawn_entity(actor.world, [IdentityComponent(name="ball", kind="object")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), thing.id)
    result = PlayWithPetHandler().execute(
        _ctx(actor), _cmd(owner.id, "play-with", {"pet_id": str(thing.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a pet"


def test_play_with_rejects_someone_elses_pet():
    actor, room, owner, pet = _scene()
    stranger = _owner(actor.world, room, name="Wick")
    result = PlayWithPetHandler().execute(
        _ctx(actor), _cmd(stranger.id, "play-with", {"pet_id": str(pet.id)})
    )
    assert not result.ok
    assert result.reason == "that is not your pet"


def test_play_with_rejects_missing_character():
    actor, _room, _owner, pet = _scene()
    result = PlayWithPetHandler().execute(
        _ctx(actor), _cmd("missing", "play-with", {"pet_id": str(pet.id)})
    )
    assert not result.ok


def test_groom_rejects_invalid_id():
    actor, _room, owner, _pet = _scene()
    result = GroomPetHandler().execute(_ctx(actor), _cmd(owner.id, "groom", {"pet_id": "??"}))
    assert not result.ok
    assert result.reason == "invalid pet id"


def test_groom_rejects_non_pet():
    actor, room, owner, _pet = _scene()
    thing = spawn_entity(actor.world, [IdentityComponent(name="post", kind="object")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), thing.id)
    result = GroomPetHandler().execute(
        _ctx(actor), _cmd(owner.id, "groom", {"pet_id": str(thing.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a pet"


def test_groom_rejects_someone_elses_pet():
    actor, room, owner, pet = _scene()
    stranger = _owner(actor.world, room, name="Wick")
    result = GroomPetHandler().execute(
        _ctx(actor), _cmd(stranger.id, "groom", {"pet_id": str(pet.id)})
    )
    assert not result.ok
    assert result.reason == "that is not your pet"


def test_groom_rejects_missing_character():
    actor, _room, _owner, pet = _scene()
    result = GroomPetHandler().execute(
        _ctx(actor), _cmd("missing", "groom", {"pet_id": str(pet.id)})
    )
    assert not result.ok


def test_consequence_drifts_care_up_and_rests_mounts():
    actor, _room, _owner, pet = _scene()
    pet.add_component(PetCareComponent(last_updated_epoch=0))
    pet.add_component(MountComponent(stamina=Meter(value=40.0)))
    PetCareConsequence().process(actor.world, SECONDS_PER_DAY)
    care = pet.get_component(PetCareComponent)
    assert care.play_need.value > 0.0  # drifted up
    assert care.grooming.value > 0.0
    assert care.last_updated_epoch == SECONDS_PER_DAY
    # A mount's stamina rests back down over the same span.
    assert pet.get_component(MountComponent).stamina.value < 40.0


def test_consequence_leaves_non_mount_pets_alone():
    actor, _room, _owner, pet = _scene()
    pet.add_component(PetCareComponent(last_updated_epoch=0))
    events = PetCareConsequence().process(actor.world, SECONDS_PER_DAY)
    assert events == []
    assert not pet.has_component(MountComponent)


def test_care_lines_only_when_a_meter_asks():
    actor, _room, _owner, pet = _scene()
    calm = spawn_pet(actor.world, species="cat")
    calm.add_component(PetCareComponent())
    assert care_lines(calm) == []
    pet.add_component(PetCareComponent(play_need=Meter(value=60.0), grooming=Meter(value=60.0)))
    lines = care_lines(pet)
    assert any("restless" in line for line in lines)
    assert any("scruffy" in line for line in lines)


def test_care_lines_empty_for_non_pet_carecomponent_holder():
    actor = WorldActor()
    bare = spawn_entity(actor.world, [PetCareComponent(play_need=Meter(value=90.0))])
    assert care_lines(bare) == []


def test_petcare_fragments_surface_owned_pets_only():
    actor, room, owner, pet = _scene()
    pet.add_component(PetCareComponent(play_need=Meter(value=80.0)))
    other = spawn_pet(actor.world, room_id=room.id, species="stray")
    other.add_component(PetCareComponent(play_need=Meter(value=80.0)))
    lines = petcare_fragments(actor.world, owner)
    assert any("restless" in line for line in lines)
    # The unowned stray's needs are not surfaced to this character.
    assert len(lines) == 1


def test_ensure_care_returns_existing_component():
    actor, _room, _owner, pet = _scene()
    existing = PetCareComponent(play_need=Meter(value=12.0), last_updated_epoch=3)
    pet.add_component(existing)
    assert _ensure_care(pet, 99) is existing


def test_meter_band_helper_used_by_care():
    # Sanity check that the care threshold maps to a non-calm band.
    assert band(Meter(value=60.0)) != "calm"
