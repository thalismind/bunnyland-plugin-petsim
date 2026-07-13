"""v2 behavior tests: training & skill-leveling, and graduation into a mount."""

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
from bunnyland.foundation.social.mechanics import bond_between
from conftest import execute_handler

from bunnyland_petsim import (
    MountComponent,
    PetTrainedEvent,
    TrainHandler,
    TrainingComponent,
    is_mount,
    spawn_pet,
)
from bunnyland_petsim.training import MOUNT_TRAINING_LEVEL, _advance


def _room(world, title="Paddock"):
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
    pet = spawn_pet(actor.world, room_id=room.id, owner_id=owner.id, species="pony")
    return actor, room, owner, pet


def test_train_grants_xp_and_bonds():
    actor, _room, owner, pet = _scene()
    result = execute_handler(
        TrainHandler(), _ctx(actor), _cmd(owner.id, "train", {"pet_id": str(pet.id)})
    )
    assert result.ok
    event = result.events[0]
    assert isinstance(event, PetTrainedEvent)
    assert event.discipline == "obedience"
    assert event.level == 1
    assert not event.leveled_up
    training = pet.get_component(TrainingComponent)
    assert training.xp == 4.0
    bond = bond_between(actor.world, pet.id, owner.id)
    assert bond is not None and bond.affinity > 0.0


def test_train_accepts_a_named_discipline():
    actor, _room, owner, pet = _scene()
    result = execute_handler(
        TrainHandler(),
        _ctx(actor),
        _cmd(owner.id, "train", {"pet_id": str(pet.id), "discipline": "agility"}),
    )
    assert result.ok
    assert pet.get_component(TrainingComponent).discipline == "agility"


def test_train_levels_up_over_the_threshold():
    actor, _room, owner, pet = _scene()
    pet.add_component(TrainingComponent(level=1, xp=8.0, xp_per_level=10.0))
    result = execute_handler(
        TrainHandler(), _ctx(actor), _cmd(owner.id, "train", {"pet_id": str(pet.id)})
    )
    assert result.ok
    assert result.events[0].leveled_up
    training = pet.get_component(TrainingComponent)
    assert training.level == 2
    assert training.xp == 2.0  # 8 + 4 - 10 carried over


def test_train_graduates_a_pet_into_a_mount():
    actor, _room, owner, pet = _scene()
    pet.add_component(TrainingComponent(level=MOUNT_TRAINING_LEVEL - 1, xp=8.0, xp_per_level=10.0))
    result = execute_handler(
        TrainHandler(), _ctx(actor), _cmd(owner.id, "train", {"pet_id": str(pet.id)})
    )
    assert result.ok
    event = result.events[0]
    assert event.became_mount
    assert is_mount(pet)
    assert pet.has_component(MountComponent)


def test_train_of_existing_mount_does_not_re_add_component():
    actor, _room, owner, pet = _scene()
    pet.add_component(TrainingComponent(level=MOUNT_TRAINING_LEVEL, xp=0.0))
    pet.add_component(MountComponent(speed=5))
    result = execute_handler(
        TrainHandler(), _ctx(actor), _cmd(owner.id, "train", {"pet_id": str(pet.id)})
    )
    assert result.ok
    assert not result.events[0].became_mount
    assert pet.get_component(MountComponent).speed == 5


def test_train_rejects_invalid_pet_id():
    actor, _room, owner, _pet = _scene()
    result = execute_handler(TrainHandler(), _ctx(actor), _cmd(owner.id, "train", {"pet_id": "??"}))
    assert not result.ok
    assert result.reason == "invalid pet id"


def test_train_rejects_non_pet():
    actor, room, owner, _pet = _scene()
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="object")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)
    result = execute_handler(
        TrainHandler(), _ctx(actor), _cmd(owner.id, "train", {"pet_id": str(rock.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a pet"


def test_train_rejects_someone_elses_pet():
    actor, room, owner, pet = _scene()
    stranger = _owner(actor.world, room, name="Wick")
    result = execute_handler(
        TrainHandler(), _ctx(actor), _cmd(stranger.id, "train", {"pet_id": str(pet.id)})
    )
    assert not result.ok
    assert result.reason == "that is not your pet"


def test_train_rejects_missing_character():
    actor, _room, _owner, pet = _scene()
    result = execute_handler(
        TrainHandler(), _ctx(actor), _cmd("does-not-exist", "train", {"pet_id": str(pet.id)})
    )
    assert not result.ok


def test_advance_rolls_multiple_levels_in_one_step():
    training = TrainingComponent(level=1, xp=0.0, xp_per_level=5.0)
    advanced, leveled = _advance(training, 12.0)
    assert leveled
    assert advanced.level == 3  # 12 / 5 -> two whole levels
    assert advanced.xp == 2.0
