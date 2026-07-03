# bunnyland-petsim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_petsim` — a companions & creatures pack.

## Development

Tests run against a sibling `bunnyland-server` checkout without installing anything —
`tests/conftest.py` puts both this package's `src/` and `../bunnyland-server/src` on
`sys.path`. From this `server/` directory:

```bash
# uses the sibling bunnyland-server's virtualenv/deps
uv run --project ../../bunnyland-server -m pytest
# or, if bunnyland + relics are already importable:
python -m pytest
```

Lint:

```bash
uv run ruff check src tests
```

## Loading into the server

```bash
bunnyland serve --module bunnyland_petsim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

- **Components** — `PetComponent` (species, follow mode, tricks, happiness);
  `TameableComponent` (wild creature that can be tamed).
- **An edge** — `Follows` (pet -> owner).
- **A following consequence** that relocates a following pet into its owner's room each
  tick when they diverge, emitting a `PetFollowedEvent` on the room change.
- **Prompt fragments** rendering pet loyalty and threat reactions into human and AI
  prompts.
- **A worldgen hook** tagging generated wild creatures with `TameableComponent`.
- **Four verbs** — `tame`, `feed-pet`, `command-pet`, and `trick`.
- **Spawn factories** — `spawn_pet`, `spawn_tameable`.
