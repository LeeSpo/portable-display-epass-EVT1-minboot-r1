# U2 0.3 fanout try patch

Canonical source on disk was `u2_0p3_fanout_try.patch` (44438 bytes, sha256 `50d2f2af44ff520d3807213e340ef04e5292027335847879161e1e24488cc470`).

## Decode (preferred)

```bash
bash reference/decode_u2_patch.sh
# or:
base64 -d < reference/u2_0p3_fanout_try.patch.gz.b64 | gzip -dc > reference/u2_0p3_fanout_try.patch
```

Then: `git apply reference/u2_0p3_fanout_try.patch`

Headers are already fixed for `a/portable_display_epass.kicad_pcb`.

**Note:** PCB connectivity is broken until copper re-route; geometry-only experiment (radius 26 PASS). Not fab-ready.
