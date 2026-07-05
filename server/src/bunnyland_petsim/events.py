"""Domain events emitted by the pet mechanics."""

from __future__ import annotations

from bunnyland.core.events import DomainEvent


class PetTamedEvent(DomainEvent):
    """A character made a taming attempt on a wild creature."""

    creature_id: str
    tamed: bool
    affinity: float
    species: str = ""


class PetFedEvent(DomainEvent):
    """A character fed a pet, raising its happiness and bond."""

    pet_id: str
    item_id: str
    happiness: float
    affinity: float


class PetCommandedEvent(DomainEvent):
    """A character set a pet's follow mode."""

    pet_id: str
    mode: str


class PetTrickEvent(DomainEvent):
    """A pet performed a trick on command."""

    pet_id: str
    trick: str


class PetFollowedEvent(DomainEvent):
    """A following pet relocated into its owner's room."""

    pet_id: str
    owner_id: str
    from_room_id: str | None = None
    to_room_id: str | None = None


class MountedEvent(DomainEvent):
    """A rider climbed onto a mount."""

    mount_id: str
    rider_id: str
    trust: float = 0.0


class DismountedEvent(DomainEvent):
    """A rider got down off a mount."""

    mount_id: str
    rider_id: str


class MountTraveledEvent(DomainEvent):
    """A mounted rider crossed one or more rooms in a single ride.

    Published so a travel/cartography pack can log or fast-track the journey.
    """

    mount_id: str
    rider_id: str
    from_room_id: str | None = None
    to_room_id: str | None = None
    hops: int = 0
    direction: str | None = None


class PetTrainedEvent(DomainEvent):
    """An owner trained a pet, granting skill experience."""

    pet_id: str
    discipline: str
    level: int
    leveled_up: bool = False
    became_mount: bool = False


class PetPlayedEvent(DomainEvent):
    """An owner played with a pet, cheering it up."""

    pet_id: str
    owner_id: str
    happiness: float


class PetGroomedEvent(DomainEvent):
    """An owner groomed a pet, tidying it up."""

    pet_id: str
    owner_id: str


class PetStampedeEvent(DomainEvent):
    """A storyteller threat spooked pets into a panicked stampede."""

    room_id: str
    pet_ids: tuple[str, ...] = ()
    lost_pet_ids: tuple[str, ...] = ()
    incident_kind: str = ""


class PetLostEvent(DomainEvent):
    """A spooked pet bolted and lost track of its owner."""

    pet_id: str
    owner_id: str
    room_id: str | None = None


__all__ = [
    "DismountedEvent",
    "MountTraveledEvent",
    "MountedEvent",
    "PetCommandedEvent",
    "PetFedEvent",
    "PetFollowedEvent",
    "PetGroomedEvent",
    "PetLostEvent",
    "PetPlayedEvent",
    "PetStampedeEvent",
    "PetTamedEvent",
    "PetTrainedEvent",
    "PetTrickEvent",
]
