"""Storyteller integration: a threat erupts, and the pets stampede.

This wires petsim into the core **storyteller** so world pressure is paced centrally rather
than reinvented here. When the storyteller starts a threatening incident (a hostile
encounter, a raid, a kaiju) in a room, any pets *actively following their owner there*
panic:

- calm pets are spooked — they hunker down (``stay``) and turn nervous, their happiness
  dropping; and
- an already-nervous pet **bolts**: it loses its :class:`Follows` edge and becomes a
  *lost pet*, emitting a :class:`PetLostEvent`.

The whole panic is announced as a single :class:`PetStampedeEvent` per room. Because
spooked pets stop following (and bolted pets lose their owner), the consequence naturally
fires once per incident rather than every tick.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.ecs import contents, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.foundation.storyteller.mechanics import IncidentComponent
from relics import Entity, World

from .components import RELOCATING_MODES, STAY, PetComponent, clamp_happiness
from .edges import Follows, owner_id_of
from .events import PetLostEvent, PetStampedeEvent
from .spatial import room_of

#: Storyteller incident kinds violent enough to spook pets into a stampede.
THREAT_INCIDENT_KINDS: frozenset[str] = frozenset(
    {"hostile_encounter", "kaiju_attack", "barbarian_raid"}
)

#: Happiness a spooked pet loses in the panic.
STAMPEDE_HAPPINESS_LOSS = 15.0


def _panicking_pets(world: World, room: Entity) -> list[Entity]:
    """Following/heeling pets sharing ``room`` — the ones out and about to be spooked."""
    pets: list[Entity] = []
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if not entity.has_component(PetComponent):
            continue
        if entity.get_component(PetComponent).mode in RELOCATING_MODES:
            pets.append(entity)
    return pets


def _spook(pet: Entity) -> str | None:
    """Spook one pet. Returns the owner id it bolted from if it became lost, else None."""
    component = pet.get_component(PetComponent)
    was_nervous = component.nervous
    happiness = clamp_happiness(component.happiness - STAMPEDE_HAPPINESS_LOSS)
    replace_component(pet, replace(component, mode=STAY, nervous=True, happiness=happiness))
    if not was_nervous:
        return None
    owner_id = owner_id_of(pet)
    for _edge, target_id in list(pet.get_relationships(Follows)):
        pet.remove_relationship(Follows, target_id)
    return str(owner_id) if owner_id is not None else None


class StampedeConsequence:
    """React to active storyteller threat incidents by stampeding nearby pets."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for incident_entity in world.query().with_all([IncidentComponent]).execute_entities():
            incident = incident_entity.get_component(IncidentComponent)
            if incident.resolved_at_epoch is not None:
                continue
            if incident.kind not in THREAT_INCIDENT_KINDS:
                continue
            room = room_of(world, incident_entity.id)
            if room is None:
                continue
            pets = _panicking_pets(world, room)
            if not pets:
                continue
            lost: list[tuple[str, str]] = []
            pet_ids: list[str] = []
            for pet in pets:
                pet_ids.append(str(pet.id))
                owner_id = _spook(pet)
                if owner_id is not None:
                    lost.append((str(pet.id), owner_id))
            events.append(
                PetStampedeEvent(
                    **event_base(
                        epoch,
                        visibility=EventVisibility.ROOM,
                        actor_id=str(room.id),
                        room_id=str(room.id),
                        target_ids=tuple(pet_ids),
                        pet_ids=tuple(pet_ids),
                        lost_pet_ids=tuple(pet_id for pet_id, _owner in lost),
                        incident_kind=incident.kind,
                    )
                )
            )
            for pet_id, owner_id in lost:
                events.append(
                    PetLostEvent(
                        **event_base(
                            epoch,
                            visibility=EventVisibility.ROOM,
                            actor_id=pet_id,
                            room_id=str(room.id),
                            target_ids=(owner_id,),
                            pet_id=pet_id,
                            owner_id=owner_id,
                        )
                    )
                )
        return events

__all__ = [
    "STAMPEDE_HAPPINESS_LOSS",
    "THREAT_INCIDENT_KINDS",
    "StampedeConsequence",
]
