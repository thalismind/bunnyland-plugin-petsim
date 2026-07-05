"""Connector (consume): loresim ``KnownSpecies`` eases taming.

When the **loresim** pack is loaded it publishes a ``KnownSpecies`` component recording the
creatures a character has studied. A tamer who already knows a creature's species handles it
more confidently, so taming gains a small affinity bonus.

Safe and optional: loresim is imported behind ``try/except ImportError`` and only listed
under the plugin's ``recommends``. Absent loresim the import is ``None`` and
:func:`known_species_bonus` returns ``0.0`` — taming behaves exactly as it does standalone.
"""

from __future__ import annotations

import logging

from relics import World

logger = logging.getLogger(__name__)

try:  # pragma: no cover - trivial import guard
    from bunnyland_loresim import KnownSpecies  # type: ignore
except ImportError:  # pragma: no cover - exercised via monkeypatch in tests
    KnownSpecies = None
    logger.warning(
        "bunnyland_loresim not installed; the known-species taming aid is disabled "
        "(petsim runs standalone without it)."
    )

#: Extra taming affinity per attempt when the tamer already knows the species.
TAMING_KNOWLEDGE_BONUS = 0.1


def knows_species(world: World, character_id, species: str) -> bool:
    """Whether ``character_id`` has studied ``species`` (always False without loresim)."""
    if KnownSpecies is None or not world.has_entity(character_id):
        return False
    character = world.get_entity(character_id)
    if not character.has_component(KnownSpecies):
        return False
    known = getattr(character.get_component(KnownSpecies), "species", ())
    return species in tuple(known)


def known_species_bonus(world: World, character_id, species: str) -> float:
    """Affinity bonus a knowledgeable tamer gets for ``species`` (0.0 without loresim)."""
    return TAMING_KNOWLEDGE_BONUS if knows_species(world, character_id, species) else 0.0


__all__ = ["KnownSpecies", "TAMING_KNOWLEDGE_BONUS", "known_species_bonus", "knows_species"]
