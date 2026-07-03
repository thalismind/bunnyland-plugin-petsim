"""Pet and tameable creature components.

A :class:`PetComponent` marks a companion that follows an owner, has a happiness level, and
knows tricks. A :class:`TameableComponent` marks a wild creature that a character can tame
into a pet. Components are immutable; every mutation swaps a whole value with
``replace_component(entity, replace(component, ...))``.
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from relics import Component

#: Follow modes for a pet. ``follow`` and ``heel`` both relocate the pet to its owner;
#: ``stay`` keeps it where it is.
FOLLOW = "follow"
HEEL = "heel"
STAY = "stay"
PET_MODES: tuple[str, ...] = (FOLLOW, HEEL, STAY)

#: Modes in which a pet chases its owner between rooms.
RELOCATING_MODES: frozenset[str] = frozenset({FOLLOW, HEEL})

#: Happiness bounds. Higher is happier (this is not a "pressing need" meter).
HAPPINESS_MIN = 0.0
HAPPINESS_MAX = 100.0


def clamp_happiness(value: float) -> float:
    """Clamp a happiness value into ``[HAPPINESS_MIN, HAPPINESS_MAX]``."""
    return max(HAPPINESS_MIN, min(HAPPINESS_MAX, value))


@dataclass(frozen=True)
class PetComponent(Component):
    """A tamed companion that follows and bonds with an owner.

    The owner link itself is a :class:`bunnyland_petsim.edges.Follows` edge (pet -> owner),
    so ownership can change without rewriting this component.
    """

    species: str = "creature"
    mode: str = FOLLOW
    tricks: tuple[str, ...] = ()
    happiness: float = 50.0
    nervous: bool = False


@dataclass(frozen=True)
class TameableComponent(Component):
    """A wild creature that can be tamed into a pet.

    ``tame_threshold`` is the bond affinity (creature -> tamer) required to convert the
    creature into a pet. ``skittish`` creatures gain less affinity per attempt.
    """

    species: str = "creature"
    tame_threshold: float = 0.6
    skittish: bool = False
    tricks: tuple[str, ...] = ()


__all__ = [
    "FOLLOW",
    "HAPPINESS_MAX",
    "HAPPINESS_MIN",
    "HEEL",
    "PET_MODES",
    "RELOCATING_MODES",
    "STAY",
    "PetComponent",
    "TameableComponent",
    "clamp_happiness",
]
