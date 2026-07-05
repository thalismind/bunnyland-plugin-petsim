"""Runtime wiring: register petsim consequences and reactors on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .affect import PetAffectReactor
from .following import FollowingConsequence
from .incidents import StampedeConsequence
from .petcare import PetCareConsequence


def install_petsim(actor: WorldActor) -> None:
    """Register per-tick consequences and the affect reactor (a ``service_factories`` entry)."""
    actor.register_consequence(FollowingConsequence())
    actor.register_consequence(PetCareConsequence())
    actor.register_consequence(StampedeConsequence())
    PetAffectReactor(actor.world).subscribe(actor.bus)


__all__ = ["install_petsim"]
