"""Route pet moments through core **affect**: an owner's mood shifts with their pet.

Rather than inventing a mood scalar, petsim emits domain events and this reactor drops
core :class:`ThoughtComponent` thoughts (carrying an :class:`AffectDelta`) onto the owner.
Core's affect aggregation then folds them into the owner's multidimensional mood — so a
joyful play session, a proud graduation, or a lost pet each colour how the owner feels.
"""

from __future__ import annotations

from bunnyland.core.components import AffectDelta, CharacterComponent, ThoughtComponent
from bunnyland.core.ecs import parse_entity_id, spawn_entity
from bunnyland.core.edges import HasThought
from relics import World

from .events import PetLostEvent, PetPlayedEvent, PetTrainedEvent

#: How long a pet-driven thought lingers before it decays (game seconds).
THOUGHT_TTL_SECONDS = 4 * 3600


class PetAffectReactor:
    """Turn pet domain events into thoughts on the affected owner."""

    def __init__(self, world: World) -> None:
        self.world = world

    def subscribe(self, bus) -> None:
        bus.subscribe(PetPlayedEvent, self._on_played)
        bus.subscribe(PetTrainedEvent, self._on_trained)
        bus.subscribe(PetLostEvent, self._on_lost)

    def _add_thought(self, owner_id_str, label, text, delta, epoch, source_event_id) -> None:
        owner_id = parse_entity_id(owner_id_str)
        if owner_id is None or not self.world.has_entity(owner_id):
            return
        owner = self.world.get_entity(owner_id)
        if not owner.has_component(CharacterComponent):
            return
        thought = spawn_entity(
            self.world,
            [
                ThoughtComponent(
                    label=label,
                    text=text,
                    affect_delta=delta,
                    created_at_epoch=epoch,
                    expires_at_epoch=epoch + THOUGHT_TTL_SECONDS,
                    source_event_id=source_event_id,
                )
            ],
        )
        owner.add_relationship(HasThought(), thought.id)

    def _on_played(self, event: PetPlayedEvent) -> None:
        self._add_thought(
            event.owner_id,
            "delighted",
            "Playing with my pet was a joy.",
            AffectDelta(valence=8, stress=-4),
            event.world_epoch,
            event.event_id,
        )

    def _on_trained(self, event: PetTrainedEvent) -> None:
        if not event.leveled_up:
            return
        self._add_thought(
            event.actor_id,
            "proud",
            "My pet is really coming along.",
            AffectDelta(valence=6, confidence=4),
            event.world_epoch,
            event.event_id,
        )

    def _on_lost(self, event: PetLostEvent) -> None:
        self._add_thought(
            event.owner_id,
            "worried",
            "My pet bolted — I hope it's alright.",
            AffectDelta(valence=-8, stress=10, sadness=6),
            event.world_epoch,
            event.event_id,
        )


__all__ = ["PetAffectReactor", "THOUGHT_TTL_SECONDS"]
