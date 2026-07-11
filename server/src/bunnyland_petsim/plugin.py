"""Bunnyland plugin entrypoint for the out-of-tree petsim companions extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    DependencyContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .commands import PET_ACTION_DEFINITIONS, PET_ACTION_HANDLERS
from .components import PetComponent, TameableComponent
from .edges import Follows
from .enrichment import PetGenerationEnricher
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
from .fragments import petsim_fragments
from .install import install_petsim
from .mounts import MountComponent, RiddenBy
from .petcare import PetCareComponent, petcare_fragments
from .tracking import TrackerComponent, tracking_fragments
from .training import TrainingComponent
from .worldgen import MountGenerationEnricher

PLUGIN_ID = "bunnyland.petsim"

#: Optional synergy partners — consumed if present, dormant (with a logged warning) if not.
WILDSIM_ID = "bunnyland.wildsim"
LORESIM_ID = "bunnyland.loresim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Petsim",
        version="0.2.0",
        default_enabled=True,
        dependencies=DependencyContribution(recommends=(WILDSIM_ID, LORESIM_ID)),
        ecs=EcsContribution(
            components=(
                PetComponent,
                TameableComponent,
                MountComponent,
                TrainingComponent,
                PetCareComponent,
                TrackerComponent,
            ),
            edges=(Follows, RiddenBy),
        ),
        commands=CommandContribution(
            action_handlers=PET_ACTION_HANDLERS,
            action_definitions=PET_ACTION_DEFINITIONS,
            typed_events=(
                PetTamedEvent,
                PetFedEvent,
                PetCommandedEvent,
                PetTrickEvent,
                PetFollowedEvent,
                MountedEvent,
                DismountedEvent,
                MountTraveledEvent,
                PetTrainedEvent,
                PetPlayedEvent,
                PetGroomedEvent,
                PetStampedeEvent,
                PetLostEvent,
            ),
        ),
        runtime=RuntimeContribution(service_factories=(install_petsim,)),
        content=ContentContribution(
            prompt_fragments=(petsim_fragments, petcare_fragments, tracking_fragments),
            generation_enrichers=(
                PetGenerationEnricher(),
                MountGenerationEnricher(),
            ),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["LORESIM_ID", "PLUGIN_ID", "WILDSIM_ID", "bunnyland_plugins", "plugin"]
