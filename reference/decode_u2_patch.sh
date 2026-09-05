#!/usr/bin/env bash
# Assemble U2 0.3 fanout try patch from gzip+base64 parts on this branch.
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
OUT="$DIR/u2_0p3_fanout_try.patch"
B64="$DIR/u2_0p3_fanout_try.patch.gz.b64"
if [[ -f "$DIR/u2_0p3_fanout_try.patch.gz.b64.part0" && -f "$DIR/u2_0p3_fanout_try.patch.gz.b64.part1a" ]]; then
  cat \
    "$DIR/u2_0p3_fanout_try.patch.gz.b64.part0" \
    "$DIR/u2_0p3_fanout_try.patch.gz.b64.part1a" \
    "$DIR/u2_0p3_fanout_try.patch.gz.b64.part1b" \
    "$DIR/u2_0p3_fanout_try.patch.gz.b64.part2a" \
    "$DIR/u2_0p3_fanout_try.patch.gz.b64.part2b" \
    > "$B64"
elif [[ -f "$B64" ]]; then
  :
else
  echo "missing b64 parts" >&2; exit 1
fi
base64 -d < "$B64" | gzip -dc > "$OUT"
echo "wrote $OUT ($(wc -c < "$OUT") bytes)"
echo "expected sha256: 50d2f2af44ff520d3807213e340ef04e5292027335847879161e1e24488cc470"
sha256sum "$OUT" || shasum -a 256 "$OUT"
