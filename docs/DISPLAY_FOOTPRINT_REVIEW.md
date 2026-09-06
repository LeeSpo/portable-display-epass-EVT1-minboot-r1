# Display footprint review — 2026-09-06

Engineering candidates; footprint/assembly signoff remains open.

## J4: Molex 502598-4593

The previous single row, 0.5 mm pitch placeholder was incompatible with the
502598 series. The revised `Sameat:FPC45` uses 45 contacts at 0.3 mm mating pitch,
with alternating PCB tails: 0.6 mm within each row and 3.065 mm between pad
centres. Odd pads are 0.30 × 0.67 mm; even pads are 0.30 × 0.50 mm. Two mounting
pads are 0.35 × 1.00 mm at X = ±7.4 mm. Schematic MP1/MP2 are grounded.

For 45 contacts the drawing dimensions are A=15.6, B=13.2, C=15.15, D=12.6 mm.
The board origin of J4 is the centre of the odd contact row, not the body centre.
Check mating-side pin 1, bottom-contact FPC orientation, stiffener thickness,
retention tabs, insertion clearance and enclosure fit against the actual module.

Sources:
- Molex SD-502598-003 Rev A, locally saved as
  `reference/datasheets/molex_SD-502598-003.pdf`;
  [drawing mirror](https://sigma.octopart.com/16405244/technical_drawing/Molex-5025983393.pdf).
- [Current manufacturer drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/502/502598/5025983993_sd.pdf)
  includes the 45-contact -4593 variant and notes the terminal material change
  from the **91 family. The module reference names -4591; the BOM candidate is
  -4593. Compatibility of the actual purchased module and connector is pending.

## U10: TI TPS65631DPDR, DPD WSON-12

The previous 0.5 mm terminal pitch and 1.7 mm square exposed pad were incorrect.
The revised pattern uses 0.45 mm terminal pitch, 0.70 × 0.25 mm outer pads with
centres at X = ±1.45 mm, and a 1.21 × 2.02 mm exposed pad. The package drawing
is rotated to match the left/right pin arrangement in this library.

The source is [TI TPS65631 datasheet](https://www.ti.com/lit/ds/symlink/tps65631.pdf),
local `reference/datasheets/tps65631.pdf`, DPD mechanical/package drawings.
Outer pad extension is a derived engineering land pattern. Exposed-pad paste
has a provisional -15% linear margin ratio in both library and board; it is
not a qualified windowed stencil design. Review stencil coverage, via-in-pad
wicking/fill, assembly process, solder joints and thermal performance with the
assembler. Do not treat unit tests or library parity as this approval.

The generator preserves these two curated footprint files. Regression tests
check key drawing dimensions and ensure that a later regeneration cannot silently
restore the old pitch. Other footprints still require their own review.
