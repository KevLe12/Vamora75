// Copyright 2026 Kevin Le, Sammy DeGraaff, Mohammed-Mehdi Hamdaoui (Vamora)
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// Bare RP2040 + Winbond W25Q16JV (2 MB, QSPI) + 12 MHz crystal.
// The generic 03h boot stage works with every W25Qxx part (and with substitutes).
#define RP2040_FLASH_GENERIC_03H

// Double-tap the RESET button (SW91) to enter the UF2 bootloader without opening the case;
// Fn+Esc (QK_BOOT), holding Esc while plugging in (bootmagic) or BOOT+plug also work.
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 500U
