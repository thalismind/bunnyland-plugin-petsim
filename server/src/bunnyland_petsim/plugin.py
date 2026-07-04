"""Bunnyland plugin entrypoint for the out-of-tree petsim companions extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .commands import PET_ACTION_DEFINITIONS, PET_ACTION_HANDLERS
from .components import PetComponent, TameableComponent
from .edges import Follows
from .enrichment import PetWorldgenHook
from .events import (
    PetCommandedEvent,
    PetFedEvent,
    PetFollowedEvent,
    PetTamedEvent,
    PetTrickEvent,
)
from .fragments import petsim_fragments
from .install import install_petsim

PLUGIN_ID = "bunnyland.petsim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Petsim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(PetComponent, TameableComponent),
            edges=(Follows,),
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
            ),
        ),
        runtime=RuntimeContribution(service_factories=(install_petsim,)),
        content=ContentContribution(
            prompt_fragments=(petsim_fragments,),
            worldgen_hooks=(PetWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
