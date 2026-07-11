"""Declarative rideable-mount generation enrichment."""

from bunnyland.core.generation import GenerationDelta, GenerationRequest

from .enrichment import generation_text
from .mounts import MountComponent

MOUNT_TERMS = (
    "mount",
    "steed",
    "horse",
    "pony",
    "stallion",
    "mare",
    "camel",
    "elk",
    "ridable",
    "rideable",
)


def is_mountlike(request: GenerationRequest) -> bool:
    return request.entity_kind == "character" and any(
        term in generation_text(request) for term in MOUNT_TERMS
    )


class MountGenerationEnricher:
    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        existing = tuple(request.context.get("base_components", ()))
        if is_mountlike(request) and not any(isinstance(item, MountComponent) for item in existing):
            return GenerationDelta(components=(MountComponent(),))
        return GenerationDelta()


__all__ = ["MOUNT_TERMS", "MountGenerationEnricher", "is_mountlike"]
