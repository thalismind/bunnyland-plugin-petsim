# Bunnyland Petsim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin: an expansion-pack-sized **companions & creatures** pack. Wild animals can be tamed into loyal
pets that follow their owner from room to room, bond over food and attention, perform
tricks, and react to danger.

This repo intentionally keeps all companion work outside the main `bunnyland-server` repo.

## Layout

- `server/` - Python Bunnyland plugin package with the pet/tameable components, the
  `Follows` edge, the following consequence, the taming / feeding / commanding / trick
  verbs, a worldgen enrichment hook, prompt fragments, spawn factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_petsim.bunnyland_plugins()` and contributes:

- **Following** — a `Follows` edge (pet -> owner) and a `PetComponent` carrying the pet's
  species, follow mode (`follow` / `heel` / `stay`), tricks, and happiness. The
  `FollowingConsequence` relocates a following pet into its owner's room each tick when
  they diverge, and contextual `command` sets the follow mode.
- **Taming** — wild creatures carry a `TameableComponent`. The `tame` verb builds a
  `SocialBond` over one or more attempts; once the creature trusts the character enough it
  becomes their pet (adds the `Follows` edge). Worldgen seeds tameable wild creatures.
- **Bonding & loyalty** — the `feed-pet` verb consumes a food item to raise a pet's
  happiness and grow its bond. Loyalty is surfaced in a prompt fragment
  ("Your fox pads at your heels, devoted.").
- **Tricks & reactions** — pets know tricks (the `trick` verb) and react to their
  surroundings in a prompt fragment (a nervous pet cowers when a threat shares its room).

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_petsim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_petsim` package must be importable by the server (installed into the server's
environment, or on `PYTHONPATH`).

## Development

Run server tests against a sibling `bunnyland-server` checkout (no install required —
`server/tests/conftest.py` puts both packages on `sys.path`). From `server/`:

```bash
uv run --project ../../bunnyland-server -m pytest
uv run --project ../../bunnyland-server ruff check src tests
```

See [`server/README.md`](server/README.md) for more detail.

## Contributing & Conduct

This plugin follows the Bunnyland project's
[contribution guidelines](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md),
which point back to the `bunnyland-server` repository.

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
