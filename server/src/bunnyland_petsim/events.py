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


__all__ = [
    "PetCommandedEvent",
    "PetFedEvent",
    "PetFollowedEvent",
    "PetTamedEvent",
    "PetTrickEvent",
]
