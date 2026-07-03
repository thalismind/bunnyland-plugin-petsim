"""Runtime wiring: register the following consequence on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .following import FollowingConsequence


def install_petsim(actor: WorldActor) -> None:
    """Register the per-tick following consequence (a ``service_factories`` entry)."""
    actor.register_consequence(FollowingConsequence())


__all__ = ["install_petsim"]
