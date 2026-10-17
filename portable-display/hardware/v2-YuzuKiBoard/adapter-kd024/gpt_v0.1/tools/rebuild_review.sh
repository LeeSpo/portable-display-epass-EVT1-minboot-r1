#!/bin/sh
# DESTRUCTIVE to generated review files. Back up manually edited CAD first.
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
"$PYTHON" tools/build_design.py
"$PYTHON" tools/route_candidate.py > reports/router_run.log 2>&1
"$PYTHON" tools/inspect_geometry.py
"$PYTHON" tools/make_envelopes.py
"$PYTHON" tools/write_kicad.py
"$PYTHON" tools/export_review.py
"$PYTHON" tools/validate_review.py
"$PYTHON" tools/render_layout.py
"$PYTHON" tools/make_previews.py
"$PYTHON" tools/write_documentation.py
"$PYTHON" tools/make_manifest.py
printf '%s\n' 'REVIEW ONLY. Native KiCad ERC/DRC not part of this build. DSI remains unrouted.'
