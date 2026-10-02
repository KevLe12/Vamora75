# Vamora75

82-key 75 % (exploded Windows ANSI) hot-swap keyboard with an on-board RP2040.
Designed by a Vietnamese, American and Moroccan team.

* Keyboard maintainer: vamora
* Hardware supported: Vamora75 rev 1.1 PCB (RP2040, W25Q16JV, USB-C, Kailh hot-swap)
* Hardware availability: open-source design files

Make example for this keyboard (after setting up your build environment):

    qmk compile -kb vamora75 -km default
    qmk compile -kb vamora75 -km via

Flashing example: copy the `.uf2` file to the `RPI-RP2` drive.

See the [build environment setup](https://docs.qmk.fm/#/getting_started_build_tools) and the
[make instructions](https://docs.qmk.fm/#/getting_started_make_guide) for more information.

## Bootloader

Enter the bootloader in 4 ways:

* **Bootmagic reset**: hold Esc (top-left key) and plug in the keyboard
* **Keycode in layout**: Fn+Esc (`QK_BOOT`)
* **Double-tap reset**: double-tap the RESET button on the PCB
* **Physical**: hold BOOT (pin-hole in the case bottom) while plugging in
