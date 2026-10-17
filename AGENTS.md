# Repository Guidelines

## Project Structure & Module Organization

This repository contains portable-display hardware designs and Python validation tools; there is no application or firmware build here.

- `portable-display/hardware/v0_legacy/`: EVT1-minboot KiCad project, local symbol/footprint libraries, `design/` contracts, `tools/`, and historical documentation.
- `portable-display/hardware/v1-WEB6-redesign/`: 38×64 mm redesign, routing utilities, and layout previews. `split-power-candidate/` contains the split-power KiCad project, power requirements, and dedicated checks.
- `portable-display/docs/` and `reference/`: display specifications, pinout data, and reference material.
- Each hardware revision's `verification/` directory holds reports, previews, hashes, and snapshots. Match evidence to the actual source revision.

## Build, Test, and Development Commands

Use KiCad 9/10 for the legacy project; split-power reports document KiCad 10.0.6. Keep project-local libraries available through `${KIPRJMOD}`.

From `portable-display/hardware/v0_legacy/`:

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/verify_evt1.py --static
python3 tools/verify_evt1.py
```

These install Shapely/NumPy, run unit tests, perform static checks, and run native ERC/DRC respectively. Native verification requires `kicad-cli` and checks an isolated project copy.

From `portable-display/hardware/v1-WEB6-redesign/split-power-candidate/`:

```sh
python3 tools/check_wake_domain.py --output /tmp/wake-audit.json
python3 tools/test_wake_domain.py --output /tmp/wake-faults.json
```

These check wake-domain topology and rejection of injected wiring/assembly faults.

## Coding Style & Naming Conventions

Use four-space indentation and `snake_case` for new Python functions, variables, and modules. Match surrounding code when editing existing scripts; avoid unrelated reformatting. No repository-wide formatter or linter configuration is present. Use `check_*.py` for audits and `test_*.py` for tests. Preserve component references, net names, and project-local library identifiers across schematics, PCB files, and contracts.

## Testing Guidelines

Legacy tests use Python `unittest`; the wake fault test is a standalone script. No numeric coverage target is configured. Add regression cases for changed validation logic. Hardware changes require relevant contract checks plus native ERC/DRC and schematic parity checks. Preserve dated reports and source hashes; static success does not establish physical operation or manufacturing approval.

## Commit & Pull Request Guidelines

History uses `feat:`, `fix:`, and `docs:`, optionally scoped as `fix(pcb):` or `docs(hardware):`. Write concise, imperative subjects. PRs should identify the hardware revision, affected components/nets, validation commands and results, and remaining acceptance items. Link relevant issues and include layout previews for PCB changes.

## Hardware Release Constraints

Treat designs as engineering candidates until documented release gates and physical validation are complete. Do not relax DRC rules or add exemptions merely to obtain passing reports. Keep schematics, PCB files, local libraries, requirements, and review notes synchronized.
