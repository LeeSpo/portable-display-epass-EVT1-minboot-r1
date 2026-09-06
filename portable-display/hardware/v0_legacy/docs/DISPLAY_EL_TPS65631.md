# EL bias candidate: TPS65631DPDR

U10 is a routed engineering candidate, not an approved panel power solution.
See the [TI datasheet](https://www.ti.com/lit/ds/symlink/tps65631.pdf) and
[footprint review](DISPLAY_FOOTPRINT_REVIEW.md).

| Connection | Current design |
|---|---|
| AVIN / PVIN | VSYS; the operating input range is 2.9–4.5 V |
| OUTP / FBS | ELVDD, default +4.6 V |
| OUTN | ELVSS, default −4.0 V |
| CTRL | LCD_EN, also driving U8 VCI load-switch ON |
| Inductors | L5/L6, 4.7 µH; exact current-rated parts remain to be reviewed |
| Capacitors | C46/C47 VIN; C48 ELVDD; C49/C50 ELVSS; C51 CT |
| Panel SWIRE | J4 pin 14 to R31 pad 1; R31 remains DNP |

The panel reference's typical optical test voltages are ±3.6 V. Being inside an
absolute-maximum range does not establish a valid operating point. Obtain panel
vendor confirmation for +4.6/−4.0 V, operating current, sequencing and AOD.
If unsuitable, change the supply/control design before bring-up.

**Do not send voltage-programming pulses on LCD_EN in this topology.** The same
signal controls VCI, so pulses would also toggle the panel's VCI switch. Keep
R31 DNP: fitting it can couple the panel SWIRE output to a host-driven enable.
Separate the controls and review drive direction/timing before enabling SWIRE
programming. Earlier suggestions to fit R31 or simply send nine pulses are
superseded by this restriction.

Before authorizing power, confirm the actual AXP2101 variant/OTP and measure or
bound VSYS across battery, USB, charging and transients. Review inductor saturation,
capacitor effective capacitance, switching loops, feedback routing, ground return
and heat dissipation. Connectivity and DRC do not validate these properties.

A safe firmware sequence cannot yet be finalized: VDDIO is tied through R29 to
1V8 while VCI and EL share LCD_EN. Confirm panel rail sequencing, reset timing,
DSI initialization and power-off timing before implementing the driver.
