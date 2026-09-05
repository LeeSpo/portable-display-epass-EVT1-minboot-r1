#!/usr/bin/env bash
# Decode reference/u2_0p3_fanout_try.patch.gz.b64 -> u2_0p3_fanout_try.patch
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
base64 -d < "$DIR/u2_0p3_fanout_try.patch.gz.b64" | gzip -dc > "$DIR/u2_0p3_fanout_try.patch"
echo "wrote $DIR/u2_0p3_fanout_try.patch ($(wc -c < "$DIR/u2_0p3_fanout_try.patch") bytes)"
