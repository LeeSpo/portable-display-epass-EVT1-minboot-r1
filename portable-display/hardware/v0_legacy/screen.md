# Screen selection (working)

**Primary wiring target:** KD024EGOIN152-01 (2.4″ rigid AMOLED, RM690B0, 450×600, MIPI 1-lane, AOD yes / AOD-RTC no).

- Connector: Molex 502598-4591 (45-pin) → host J4 `Sameat:FPC45`
- Netmap: `docs/DISPLAY_KD024_NETMAP.md`
- Spec pack: `kd024_screen/`

Larger ~4.4″ SD5207-class remains a product preference long-term, but **this branch wires the confirmed 2.4″ AOD pack first**.

EL± bias IC still TBD. Do not fab display island until EL PMIC + land pattern are locked.
