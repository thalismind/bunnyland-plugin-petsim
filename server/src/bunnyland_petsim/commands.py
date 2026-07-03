"""Aggregated action handlers and definitions for the pet verbs.

Each verb's handler and player-facing :class:`ActionDefinition` live in its own mechanic
module; this module just gathers them into the tuples the plugin registers.
"""

from __future__ import annotations

from .bonding import FEED_PET_DEF, FeedPetHandler
from .following import COMMAND_PET_DEF, CommandPetHandler
from .taming import TAME_DEF, TameHandler
from .tricks import TRICK_DEF, TrickHandler

PET_ACTION_HANDLERS = (TameHandler, FeedPetHandler, CommandPetHandler, TrickHandler)
PET_ACTION_DEFINITIONS = (TAME_DEF, FEED_PET_DEF, COMMAND_PET_DEF, TRICK_DEF)


__all__ = ["PET_ACTION_DEFINITIONS", "PET_ACTION_HANDLERS"]
