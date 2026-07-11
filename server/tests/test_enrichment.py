import asyncio

from bunnyland.core import WorldActor
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import CharacterSpec, RoomSpec, WorldProposal, instantiate

from bunnyland_petsim import TameableComponent
from bunnyland_petsim.plugin import bunnyland_plugins as _plugins


def _character(*, name="Creature", description="", traits=()):
    key = name.casefold()
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    result = asyncio.run(
        instantiate(
            actor,
            WorldProposal(
                seed="seed",
                rooms=[RoomSpec(key="room", title="Room")],
                characters=[
                    CharacterSpec(
                        key=key,
                        name=name,
                        room_key="room",
                        description=description,
                        traits=traits,
                    )
                ],
            ),
        )
    )
    return actor.world.get_entity(result.characters[key])


def test_wild_creatures_are_tameable_and_feral_creatures_are_skittish():
    assert _character(name="Fox", traits=("wild",)).has_component(TameableComponent)
    assert _character(name="Beast", traits=("feral",)).get_component(TameableComponent).skittish


def test_description_can_mark_a_stray_animal():
    assert _character(description="a stray animal skulking in the barn").has_component(
        TameableComponent
    )


def test_plain_character_is_ignored():
    assert not _character(name="Farmer").has_component(TameableComponent)
