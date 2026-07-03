"""Out-of-tree Bunnyland plugin: a companions & creatures pack (pets, taming, tricks)."""

from .bonding import FEED_PET_DEF, FeedPetHandler, loyalty_band, loyalty_line
from .components import (
    FOLLOW,
    HEEL,
    PET_MODES,
    STAY,
    PetComponent,
    TameableComponent,
    clamp_happiness,
)
from .edges import Follows, owned_pets, owner_id_of, set_owner
from .enrichment import CREATURE_TERMS, PetWorldgenHook
from .events import (
    PetCommandedEvent,
    PetFedEvent,
    PetFollowedEvent,
    PetTamedEvent,
    PetTrickEvent,
)
from .following import COMMAND_PET_DEF, CommandPetHandler, FollowingConsequence
from .fragments import petsim_fragments
from .install import install_petsim
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_pet, spawn_tameable
from .spatial import room_of
from .taming import TAME_DEF, TameHandler, tame_progress
from .tricks import (
    THREAT_TERMS,
    TRICK_DEF,
    TrickHandler,
    is_threat,
    perceived_threats,
    reaction_line,
)

__all__ = [
    "COMMAND_PET_DEF",
    "CREATURE_TERMS",
    "FEED_PET_DEF",
    "FOLLOW",
    "HEEL",
    "PET_MODES",
    "PLUGIN_ID",
    "STAY",
    "TAME_DEF",
    "THREAT_TERMS",
    "TRICK_DEF",
    "CommandPetHandler",
    "FeedPetHandler",
    "Follows",
    "FollowingConsequence",
    "PetCommandedEvent",
    "PetComponent",
    "PetFedEvent",
    "PetFollowedEvent",
    "PetTamedEvent",
    "PetTrickEvent",
    "PetWorldgenHook",
    "TameHandler",
    "TameableComponent",
    "TrickHandler",
    "bunnyland_plugins",
    "clamp_happiness",
    "install_petsim",
    "is_threat",
    "loyalty_band",
    "loyalty_line",
    "owned_pets",
    "owner_id_of",
    "perceived_threats",
    "petsim_fragments",
    "plugin",
    "reaction_line",
    "room_of",
    "set_owner",
    "spawn_pet",
    "spawn_tameable",
    "tame_progress",
]
