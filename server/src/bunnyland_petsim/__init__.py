"""Out-of-tree Bunnyland plugin: a companions & creatures pack (pets, taming, tricks).

v2 adds the **mounts & riding** headline plus training/skill-leveling and charming
pet-care, wires core social bonds / ``Meter`` / movement / affect / storyteller, and
consumes optional wildsim ``Scent`` and loresim ``KnownSpecies`` synergies.
"""

from .affect import PetAffectReactor
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
from .enrichment import CREATURE_TERMS, PetGenerationEnricher
from .events import (
    DismountedEvent,
    MountedEvent,
    MountTraveledEvent,
    PetCommandedEvent,
    PetFedEvent,
    PetFollowedEvent,
    PetGroomedEvent,
    PetLostEvent,
    PetPlayedEvent,
    PetStampedeEvent,
    PetTamedEvent,
    PetTrainedEvent,
    PetTrickEvent,
)
from .following import CommandPetHandler, FollowingConsequence
from .fragments import petsim_fragments
from .incidents import THREAT_INCIDENT_KINDS, StampedeConsequence
from .install import install_petsim
from .knowledge import known_species_bonus, knows_species
from .mounts import (
    DISMOUNT_DEF,
    RIDE_DEF,
    RIDE_TO_DEF,
    DismountHandler,
    MountComponent,
    RiddenBy,
    RideHandler,
    RideToHandler,
    is_mount,
    mount_of,
    owned_mounts,
    rider_of,
    set_rider,
)
from .petcare import (
    GROOM_DEF,
    PLAY_WITH_DEF,
    GroomPetHandler,
    PetCareComponent,
    PetCareConsequence,
    PlayWithPetHandler,
    care_lines,
    petcare_fragments,
)
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_pet, spawn_tameable
from .spatial import room_of
from .taming import TAME_DEF, TameHandler, tame_progress
from .tracking import (
    TrackerComponent,
    is_tracker,
    scented_targets,
    tracking_fragments,
)
from .training import TRAIN_DEF, TrainHandler, TrainingComponent
from .tricks import (
    THREAT_TERMS,
    TRICK_DEF,
    TrickHandler,
    is_threat,
    perceived_threats,
    reaction_line,
)
from .worldgen import MOUNT_TERMS, MountGenerationEnricher, is_mountlike

__all__ = [
    "CREATURE_TERMS",
    "DISMOUNT_DEF",
    "FEED_PET_DEF",
    "FOLLOW",
    "GROOM_DEF",
    "HEEL",
    "MOUNT_TERMS",
    "PET_MODES",
    "PLAY_WITH_DEF",
    "PLUGIN_ID",
    "RIDE_DEF",
    "RIDE_TO_DEF",
    "STAY",
    "TAME_DEF",
    "THREAT_INCIDENT_KINDS",
    "THREAT_TERMS",
    "TRAIN_DEF",
    "TRICK_DEF",
    "CommandPetHandler",
    "DismountHandler",
    "DismountedEvent",
    "FeedPetHandler",
    "Follows",
    "FollowingConsequence",
    "GroomPetHandler",
    "MountComponent",
    "MountTraveledEvent",
    "MountGenerationEnricher",
    "MountedEvent",
    "PetAffectReactor",
    "PetCareComponent",
    "PetCareConsequence",
    "PetCommandedEvent",
    "PetComponent",
    "PetFedEvent",
    "PetFollowedEvent",
    "PetGroomedEvent",
    "PetLostEvent",
    "PetPlayedEvent",
    "PetStampedeEvent",
    "PetTamedEvent",
    "PetTrainedEvent",
    "PetTrickEvent",
    "PetGenerationEnricher",
    "PlayWithPetHandler",
    "RiddenBy",
    "RideHandler",
    "RideToHandler",
    "StampedeConsequence",
    "TameHandler",
    "TameableComponent",
    "TrackerComponent",
    "TrainHandler",
    "TrainingComponent",
    "TrickHandler",
    "bunnyland_plugins",
    "care_lines",
    "clamp_happiness",
    "install_petsim",
    "is_mount",
    "is_mountlike",
    "is_threat",
    "is_tracker",
    "known_species_bonus",
    "knows_species",
    "loyalty_band",
    "loyalty_line",
    "mount_of",
    "owned_mounts",
    "owned_pets",
    "owner_id_of",
    "perceived_threats",
    "petcare_fragments",
    "petsim_fragments",
    "plugin",
    "reaction_line",
    "rider_of",
    "room_of",
    "scented_targets",
    "set_owner",
    "set_rider",
    "spawn_pet",
    "spawn_tameable",
    "tame_progress",
    "tracking_fragments",
]
