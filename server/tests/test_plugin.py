from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_petsim import (
    Follows,
    PetComponent,
    PetWorldgenHook,
    TameableComponent,
    petsim_fragments,
)
from bunnyland_petsim.plugin import PLUGIN_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_petsim"])
    assert [p.id for p in plugins] == [f"bunnyland_petsim.{PLUGIN_ID}"]


def test_plugin_declares_its_contributions():
    plugin = load_modules(["bunnyland_petsim"])[0]
    for component in (PetComponent, TameableComponent):
        assert component in plugin.ecs.components
    assert Follows in plugin.ecs.edges
    assert PetWorldgenHook in plugin.content.worldgen_hooks
    assert petsim_fragments in plugin.content.prompt_fragments


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_petsim"]), actor)
    assert applied[0].id == f"bunnyland_petsim.{PLUGIN_ID}"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"tame", "feed-pet", "command-pet", "trick"} <= command_types
