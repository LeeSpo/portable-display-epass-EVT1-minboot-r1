# U2 0.3 fanout try patch

**Canonical patch:** 44438 bytes  
**sha256:** `50d2f2af44ff520d3807213e340ef04e5292027335847879161e1e24488cc470`

## Assemble + apply

```bash
bash reference/decode_u2_patch.sh
# cats part0 + part1a + part1b + part2a + part2b -> gzip+base64 decode
git apply reference/u2_0p3_fanout_try.patch
```

Parts (Git blob SHAs verified on upload):
- `u2_0p3_fanout_try.patch.gz.b64.part0`
- `u2_0p3_fanout_try.patch.gz.b64.part1a` / `part1b`
- `u2_0p3_fanout_try.patch.gz.b64.part2a` / `part2b`

Headers fixed for `a/portable_display_epass.kicad_pcb`.

## Status

- Geometry **PASS** (radius 26)
- Copper **not** re-routed — **connectivity broken until re-route**
- **Not fab-ready**

`reference/u2_0p3_fanout_try.patch` on the branch is a stub until you run the decode script.
