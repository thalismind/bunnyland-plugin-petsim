"""Aggregated action handlers and definitions for the pet verbs.

Each verb's handler and player-facing :class:`ActionDefinition` live in its own mechanic
module; this module just gathers them into the tuples the plugin registers.
"""

from __future__ import annotations

from .bonding import FEED_PET_DEF, FeedPetHandler
from .following import CommandPetHandler
from .mounts import (
    DISMOUNT_DEF,
    RIDE_DEF,
    RIDE_TO_DEF,
    DismountHandler,
    RideHandler,
    RideToHandler,
)
from .petcare import GROOM_DEF, PLAY_WITH_DEF, GroomPetHandler, PlayWithPetHandler
from .taming import TAME_DEF, TameHandler
from .training import TRAIN_DEF, TrainHandler
from .tricks import TRICK_DEF, TrickHandler

PET_ACTION_HANDLERS = (
    TameHandler,
    FeedPetHandler,
    CommandPetHandler,
    TrickHandler,
    RideHandler,
    DismountHandler,
    RideToHandler,
    TrainHandler,
    PlayWithPetHandler,
    GroomPetHandler,
)
PET_ACTION_DEFINITIONS = (
    TAME_DEF,
    FEED_PET_DEF,
    TRICK_DEF,
    RIDE_DEF,
    DISMOUNT_DEF,
    RIDE_TO_DEF,
    TRAIN_DEF,
    PLAY_WITH_DEF,
    GROOM_DEF,
)


__all__ = ["PET_ACTION_DEFINITIONS", "PET_ACTION_HANDLERS"]
