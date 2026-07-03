"""World-generation enrichment: seed tameable wild creatures.

Generated characters expose semantic ``tags``/``wants``/``needs`` and an intent
``description``. This hook scans that text and attaches a :class:`TameableComponent` to
creatures that read as wild animals, so worlds ship with something to tame — without the
core generator knowing this plugin exists.
"""

from __future__ import annotations

from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import CharacterGeneratedEvent, GeneratedEntityEvent
from bunnyland.core.world_actor import WorldActor

from .components import PetComponent, TameableComponent

#: Words that mark a generated character as a tameable wild creature. Concrete species
#: names come first so the matched term makes a sensible pet species; generic descriptors
#: ("wild", "stray", ...) still trigger taming but only name the species as a fallback.
CREATURE_TERMS: tuple[str, ...] = (
    "fox",
    "wolf",
    "cat",
    "kitten",
    "dog",
    "puppy",
    "bird",
    "rabbit",
    "deer",
    "critter",
    "beast",
    "animal",
    "creature",
    "fauna",
    "mount",
    "stray",
    "wild",
    "feral",
    "tameable",
)


def _text(event: GeneratedEntityEvent) -> str:
    generation = event.generation
    return " ".join(
        (
            event.entity_kind,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()


def _matched_species(event: GeneratedEntityEvent) -> str | None:
    text = _text(event)
    for term in CREATURE_TERMS:
        if term in text:
            return term
    return None


class PetWorldgenHook:
    """Attach a ``TameableComponent`` to generated wild creatures."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(CharacterGeneratedEvent, self._on_character)

    def _entity(self, entity_id: str):
        parsed = parse_entity_id(entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return None
        return self._actor.world.get_entity(parsed)

    def _on_character(self, event: CharacterGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None:
            return
        if entity.has_component(TameableComponent) or entity.has_component(PetComponent):
            return
        species = _matched_species(event)
        if species is None:
            return
        skittish = "feral" in _text(event) or "wild" in _text(event)
        replace_component(entity, TameableComponent(species=species, skittish=skittish))


__all__ = ["CREATURE_TERMS", "PetWorldgenHook"]
