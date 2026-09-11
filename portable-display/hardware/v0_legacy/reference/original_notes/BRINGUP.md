# EVT1 bring-up checklist

1. Inspect orientation of U1/U2/U3/U4/U5/U6/U7, J1/J4/J5 and all diodes. Verify the LCD FPC contact side against the physical sample.
2. With no SoC, display or storage fitted, use a current-limited supply and verify VBUS, VBAT/VSYS and the AXP2101 power-key behavior.
3. Fit the PMIC passives and verify 3.3 V, 1.8 V, 1.5 V and 0.93 V in sequence. Stop immediately if any rail is outside +/-3% or rises in the wrong order.
4. Fit V851s and the 24 MHz crystal. Confirm UART0 boot output and USB FEL enumeration before inserting a TF card.
5. Write an MMC/SD boot image at 8 KB (sector 16) on the TF card; then verify MicroSD at conservative speed before enabling high-speed mode. There is no onboard SPI NAND.
6. Power the LCD logic with backlight disabled. Verify DSI lane polarity, RESET and the panel initialization sequence. Increase backlight PWM gradually while measuring LED current; full-scale target is approximately 80 mA.
7. Verify LIS2DW12 and RV-3028-C7 over I2C, then test connected-standby and cold-wake pulses separately.
8. Measure: PMIC-off current (<150 uA target), E907 standby (<8 mA target), active display current, USB charging current and component temperature after 30 minutes of video.
9. Treat any bodge, supplier substitution or failed target as a V1.1 change. Do not mark this revision production-ready without a reviewed test log.
