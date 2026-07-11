"""Declarative tameable-creature generation enrichment."""

from bunnyland.core.generation import GenerationDelta, GenerationRequest

from .components import PetComponent, TameableComponent

CREATURE_TERMS = (
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


def generation_text(request: GenerationRequest) -> str:
    return " ".join(
        (request.source_key, request.entity_kind, request.description, *request.tags)
    ).casefold()


class PetGenerationEnricher:
    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        if request.entity_kind != "character":
            return GenerationDelta()
        existing = tuple(request.context.get("base_components", ()))
        if any(isinstance(item, (TameableComponent, PetComponent)) for item in existing):
            return GenerationDelta()
        text = generation_text(request)
        species = next((term for term in CREATURE_TERMS if term in text), None)
        if species is None:
            return GenerationDelta()
        return GenerationDelta(
            components=(
                TameableComponent(species=species, skittish="feral" in text or "wild" in text),
            )
        )


__all__ = ["CREATURE_TERMS", "PetGenerationEnricher", "generation_text"]
