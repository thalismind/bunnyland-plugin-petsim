from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_petsim import (
    Follows,
    MountComponent,
    MountWorldgenHook,
    PetCareComponent,
    PetComponent,
    PetWorldgenHook,
    RiddenBy,
    TameableComponent,
    TrackerComponent,
    TrainingComponent,
    petcare_fragments,
    petsim_fragments,
    tracking_fragments,
)
from bunnyland_petsim.plugin import LORESIM_ID, PLUGIN_ID, WILDSIM_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_petsim"])
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_declares_its_contributions():
    plugin = load_modules(["bunnyland_petsim"])[0]
    for component in (PetComponent, TameableComponent):
        assert component in plugin.ecs.components
    assert Follows in plugin.ecs.edges
    assert PetWorldgenHook in plugin.content.worldgen_hooks
    assert petsim_fragments in plugin.content.prompt_fragments


def test_plugin_is_v2():
    plugin = load_modules(["bunnyland_petsim"])[0]
    assert plugin.version == "0.2.0"
    for component in (
        MountComponent,
        TrainingComponent,
        PetCareComponent,
        TrackerComponent,
    ):
        assert component in plugin.ecs.components
    assert RiddenBy in plugin.ecs.edges
    assert MountWorldgenHook in plugin.content.worldgen_hooks
    for provider in (petcare_fragments, tracking_fragments):
        assert provider in plugin.content.prompt_fragments
    # Optional synergy with wild/lore packs is a recommendation, never a hard requirement.
    assert plugin.dependencies.recommends == (WILDSIM_ID, LORESIM_ID)
    assert plugin.dependencies.requires == ()


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_petsim"]), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {
        "tame",
        "feed-pet",
        "command-pet",
        "trick",
        "ride",
        "dismount",
        "ride-to",
        "train",
        "play-with",
        "groom",
    } <= command_types
