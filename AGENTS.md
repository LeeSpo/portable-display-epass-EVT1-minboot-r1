# Repository Guidelines

## Project Structure & Module Organization

This repository contains portable-display hardware designs and Python validation tools; there is no application or firmware build here.

- `portable-display/hardware/v1-WEB6-redesign/split-power-candidate/`: the maintained 38×64 mm KiCad project, local libraries, power requirements, and self-contained validation tools.
- `portable-display/hardware/v2-dev-board/`: YuzukiHD-Lizard learning references; this is not the next revision of the custom PCB.
- `portable-display/docs/` and `portable-display/reference/`: display specifications, mechanical notes, pinout data, source datasheets, and the cleanup/recovery index.
- The candidate's `verification/` contains only the latest verification run and the retained production preview package. Historical designs and reports are recoverable from Git; see `portable-display/docs/PROJECT_STATUS_CN.md`.

## Build, Test, and Development Commands

Use KiCad 10; the current verification and retained production preview use 10.0.6. Keep project-local libraries available through `${KIPRJMOD}`.

From `portable-display/hardware/v1-WEB6-redesign/split-power-candidate/`:

```sh
python3 -m pip install -r requirements.txt
python3 tools/verify_candidate.py --output /tmp/split-power-check
python3 tools/check_wake_domain.py --output /tmp/wake-audit.json
python3 tools/test_wake_domain.py --output /tmp/wake-faults.json
```

The full runner requires a new or empty output directory, uses an isolated project copy, and checks native ERC/DRC/parity, power/FEL/USB/wake contracts, six wake faults, 25 package-integrity cases and production BOM/CPL fields and placements. The default requires exactly one retained `production_*` directory; use `--package PATH` to select explicitly. Set `KICAD_CLI` or pass `--kicad-cli` when needed. DRC acceptance requires `--refill-zones`; saved-fill diagnostics are retained separately. Never use `--save-board` on maintained sources as part of verification.

## Coding Style & Naming Conventions

Use four-space indentation and `snake_case` for new Python functions, variables, and modules. Match surrounding code when editing existing scripts; avoid unrelated reformatting. No repository-wide formatter or linter configuration is present. Use `check_*.py` for audits and `test_*.py` for tests. Preserve component references, net names, and project-local library identifiers across schematics, PCB files, and contracts.

## Testing Guidelines

The wake fault test is a standalone script. No numeric coverage target is configured. Add regression cases for changed validation logic. Hardware changes require relevant contract checks plus native ERC/DRC and schematic parity checks. Keep current dated reports and source hashes matched to the source; older evidence stays accessible through fixed Git references. Static success does not establish physical operation or manufacturing approval.

## Commit & Pull Request Guidelines

History uses `feat:`, `fix:`, and `docs:`, optionally scoped as `fix(pcb):` or `docs(hardware):`. Write concise, imperative subjects. PRs should identify the hardware revision, affected components/nets, validation commands and results, and remaining acceptance items. Link relevant issues and include layout previews for PCB changes.

## Hardware Release Constraints

Treat designs as engineering candidates until documented release gates and physical validation are complete. Do not relax DRC rules or add exemptions merely to obtain passing reports. Keep schematics, PCB files, local libraries, requirements, and review notes synchronized.
