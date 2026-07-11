from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    ExitTo,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    container_of,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.ecs import replace_component
from bunnyland.core.handlers import HandlerContext
from bunnyland.foundation.meters.mechanics import Meter, band

from bunnyland_petsim import (
    DismountHandler,
    MountComponent,
    MountedEvent,
    MountTraveledEvent,
    RideHandler,
    RideToHandler,
    is_mount,
    mount_of,
    owned_mounts,
    rider_of,
    set_owner,
    spawn_pet,
)


def _room(world, title):
    return spawn_entity(world, [RoomComponent(title=title)])


def _owner(world, room, name="Rhea"):
    owner = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), owner.id)
    return owner


def _mount(world, room, owner, *, speed=2, stamina=None):
    pet = spawn_pet(world, room_id=room.id, owner_id=owner.id, species="pony")
    pet.add_component(MountComponent(speed=speed, stamina=stamina or Meter()))
    return pet


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


def _scene(speed=2, stamina=None):
    actor = WorldActor()
    stable = _room(actor.world, "Stable")
    owner = _owner(actor.world, stable)
    mount = _mount(actor.world, stable, owner, speed=speed, stamina=stamina)
    return actor, stable, owner, mount


def test_ride_seats_rider_and_builds_trust():
    actor, _stable, owner, mount = _scene()
    result = RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    assert result.ok
    assert isinstance(result.events[0], MountedEvent)
    assert rider_of(mount) == owner.id
    assert mount_of(actor.world, owner.id).id == mount.id
    assert result.events[0].trust > 0.0


def test_ride_rejects_non_mount():
    actor, stable, owner, _mount = _scene()
    plain = spawn_pet(actor.world, room_id=stable.id, owner_id=owner.id, species="cat")
    result = RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(plain.id)}))
    assert not result.ok
    assert result.reason == "that is not a mount"


def test_ride_rejects_someone_elses_mount():
    actor, stable, owner, mount = _scene()
    stranger = _owner(actor.world, stable, name="Wick")
    result = RideHandler().execute(
        _ctx(actor), _cmd(stranger.id, "ride", {"mount_id": str(mount.id)})
    )
    assert not result.ok
    assert result.reason == "that is not your mount"


def test_ride_rejects_mount_already_ridden():
    actor, stable, owner, mount = _scene()
    from bunnyland_petsim import set_rider

    other = _owner(actor.world, stable, name="Bex")
    set_rider(mount, other.id)
    result = RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    assert not result.ok
    assert result.reason == "someone is already riding that mount"


def test_ride_rejects_when_already_riding_another():
    actor, stable, owner, mount = _scene()
    second = _mount(actor.world, stable, owner)
    RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    result = RideHandler().execute(
        _ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(second.id)})
    )
    assert not result.ok
    assert result.reason == "you are already riding"


def test_ride_rejects_unreachable_mount():
    actor, _stable, owner, _mount = _scene()
    far = _room(actor.world, "Far")
    far_owner_mount = spawn_pet(actor.world, room_id=far.id, species="pony")
    far_owner_mount.add_component(MountComponent())
    set_owner(far_owner_mount, owner.id)
    result = RideHandler().execute(
        _ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(far_owner_mount.id)})
    )
    assert not result.ok
    assert result.reason == "that mount is not here"


def test_ride_rejects_invalid_id():
    actor, _stable, owner, _mount = _scene()
    result = RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": "??"}))
    assert not result.ok
    assert result.reason == "invalid mount id"


def test_dismount_clears_rider():
    actor, _stable, owner, mount = _scene()
    RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    result = DismountHandler().execute(_ctx(actor), _cmd(owner.id, "dismount", {}))
    assert result.ok
    assert rider_of(mount) is None
    assert mount_of(actor.world, owner.id) is None


def test_dismount_rejects_when_not_riding():
    actor, _stable, owner, _mount = _scene()
    result = DismountHandler().execute(_ctx(actor), _cmd(owner.id, "dismount", {}))
    assert not result.ok
    assert result.reason == "you are not riding anything"


def test_ride_to_crosses_multiple_rooms_in_one_action():
    actor, stable, owner, mount = _scene(speed=2)
    yard = _room(actor.world, "Yard")
    field = _room(actor.world, "Field")
    stable.add_relationship(ExitTo(direction="north"), yard.id)
    yard.add_relationship(ExitTo(direction="north"), field.id)

    RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    result = RideToHandler().execute(_ctx(actor), _cmd(owner.id, "ride-to", {"direction": "north"}))
    assert result.ok
    event = result.events[0]
    assert isinstance(event, MountTraveledEvent)
    assert event.hops == 2
    assert container_of(owner) == field.id
    assert container_of(mount) == field.id
    assert mount.get_component(MountComponent).stamina.value > 0.0


def test_ride_to_stops_at_dead_end():
    actor, stable, owner, mount = _scene(speed=3)
    yard = _room(actor.world, "Yard")
    stable.add_relationship(ExitTo(direction="north"), yard.id)  # yard has no north exit
    RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    result = RideToHandler().execute(_ctx(actor), _cmd(owner.id, "ride-to", {"direction": "north"}))
    assert result.ok
    assert result.events[0].hops == 1
    assert container_of(owner) == yard.id


def test_ride_to_rejects_when_not_riding():
    actor, _stable, owner, _mount = _scene()
    result = RideToHandler().execute(_ctx(actor), _cmd(owner.id, "ride-to", {"direction": "north"}))
    assert not result.ok
    assert result.reason == "you are not riding anything"


def test_ride_to_rejects_no_matching_exit():
    actor, stable, owner, mount = _scene()
    east_room = _room(actor.world, "East")
    stable.add_relationship(ExitTo(direction="east"), east_room.id)
    RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    result = RideToHandler().execute(_ctx(actor), _cmd(owner.id, "ride-to", {"direction": "north"}))
    assert not result.ok
    assert result.reason == "no matching exit"


def test_ride_to_rejects_tired_mount():
    actor, stable, owner, mount = _scene(stamina=Meter(value=95.0))
    yard = _room(actor.world, "Yard")
    stable.add_relationship(ExitTo(direction="north"), yard.id)
    RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    assert band(mount.get_component(MountComponent).stamina) == "crisis"
    result = RideToHandler().execute(_ctx(actor), _cmd(owner.id, "ride-to", {"direction": "north"}))
    assert not result.ok
    assert result.reason == "your mount is too tired"


def test_published_mount_helpers():
    actor, _stable, owner, mount = _scene()
    plain = spawn_pet(actor.world, room_id=None, owner_id=owner.id, species="cat")
    assert is_mount(mount)
    assert not is_mount(plain)
    mounts = owned_mounts(actor.world, owner.id)
    assert [m.id for m in mounts] == [mount.id]


def test_locked_exit_is_not_traversed():
    actor, stable, owner, mount = _scene(speed=2)
    yard = _room(actor.world, "Yard")
    stable.add_relationship(ExitTo(direction="north", locked=True), yard.id)
    RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    result = RideToHandler().execute(_ctx(actor), _cmd(owner.id, "ride-to", {"direction": "north"}))
    assert not result.ok
    assert result.reason == "no matching exit"


def test_ride_to_stops_when_stamina_hits_crisis_midway():
    actor, stable, owner, mount = _scene(speed=5, stamina=Meter(value=80.0))
    rooms = [stable]
    for i in range(5):
        nxt = _room(actor.world, f"Leg{i}")
        rooms[-1].add_relationship(ExitTo(direction="north"), nxt.id)
        rooms.append(nxt)
    RideHandler().execute(_ctx(actor), _cmd(owner.id, "ride", {"mount_id": str(mount.id)}))
    result = RideToHandler().execute(_ctx(actor), _cmd(owner.id, "ride-to", {"direction": "north"}))
    assert result.ok
    # From 80, +20/hop reaches crisis (>=90) after one hop, so it stops early.
    assert result.events[0].hops == 1


def test_mount_component_survives_replace():
    # Guard: MountComponent is a real frozen component usable with replace_component.
    actor, _stable, _owner, mount = _scene()
    component = mount.get_component(MountComponent)
    replace_component(mount, replace(component, speed=4))
    assert mount.get_component(MountComponent).speed == 4


def test_ride_rejects_missing_character():
    actor, _stable, _owner, mount = _scene()
    result = RideHandler().execute(
        _ctx(actor), _cmd("missing", "ride", {"mount_id": str(mount.id)})
    )
    assert not result.ok


def test_dismount_rejects_missing_character():
    actor, _stable, _owner, _mount = _scene()
    result = DismountHandler().execute(_ctx(actor), _cmd("missing", "dismount", {}))
    assert not result.ok


def test_ride_to_rejects_missing_character():
    actor, _stable, _owner, _mount = _scene()
    result = RideToHandler().execute(
        _ctx(actor), _cmd("missing", "ride-to", {"direction": "north"})
    )
    assert not result.ok


def test_ride_to_rejects_when_rider_has_no_room():
    from bunnyland.core import remove_from_container

    from bunnyland_petsim import set_rider

    actor, _stable, owner, mount = _scene()
    set_rider(mount, owner.id)
    remove_from_container(actor.world, owner.id)  # rider is now roomless
    result = RideToHandler().execute(_ctx(actor), _cmd(owner.id, "ride-to", {"direction": "north"}))
    assert not result.ok
    assert result.reason == "you are not in a room"
