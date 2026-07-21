# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A [ZMK](https://zmk.dev) firmware user-config repo for two custom keyboards, both on Seeed XIAO BLE
controllers (`seeeduino_xiao_ble` board):

- `xiao_split_60`: a 5x12 (5 row, 6+6 column) split 60% board, one XIAO BLE per half.
- `nrf_butterfly_30`: a unibody 30-key board (3 rows x 10 columns), a single XIAO BLE, BLE-only (no
  split link).

## Repo layout

- `boards/shields/xiao_split_60/` — the shield definition (this is the actual keyboard-specific code):
  - `xiao_split_60.dtsi` — shared devicetree: kscan matrix (`col2row`, rows on `xiao_d 0-4`), the
    5x12 `default_transform` matrix-transform.
  - `xiao_split_60_left.overlay` / `xiao_split_60_right.overlay` — per-half devicetree: each defines its
    own `col-gpios` pinout; the right half additionally applies `col-offset = <6>` to the transform so its
    physical columns map to logical columns 6-11.
  - `xiao_split_60-layouts.dtsi` — the ZMK physical layout binding kscan + transform together.
  - `Kconfig.shield` / `Kconfig.defconfig` — shield Kconfig plumbing (defines
    `SHIELD_XIAO_SPLIT_60_LEFT/RIGHT`, sets `ZMK_SPLIT_ROLE_CENTRAL=y` on the left half).
  - `xiao_split_60.conf` — shield-level Kconfig defaults shipped with the shield.
  - `xiao_split_60.zmk.yml` — hardware metadata (id, siblings, required feature `seeed_xiao`).
  - `layout.txt` — **source of truth for the keymap.** See below.
  - `generate-keymap.ps1` — generates `xiao_split_60.keymap` from `layout.txt`.
  - `xiao_split_60.keymap` — **generated file, do not hand-edit.** It's overwritten by the generator
    script and carries a "GENERATED FILE" header as a reminder.
- `config/` — the west manifest self-path for this build:
  - `west.yml` — points at `zmkfirmware/zmk` at revision `v0.3`.
  - `xiao_split_60.conf`, `xiao_split_60_left.conf`, `xiao_split_60_right.conf` — build-level Kconfig
    overlays (BLE latency tuning, sleep/idle timeouts, disabling USB/logging on the peripheral half,
    battery reporting). These layer on top of the shield's own `xiao_split_60.conf`.
  - `nrf_butterfly_30.conf` — build-level Kconfig overlay for the 30-key board (sleep/idle timeouts,
    disabling serial logging, battery reporting). No split-link settings, since it's unibody.
- `boards/shields/nrf_butterfly_30/` — the 30-key shield, structured the same way as `xiao_split_60` but
  unibody (single `.overlay` instead of a shared `.dtsi` + per-half overlays, since there's only one PCB):
  - `nrf_butterfly_30.overlay` — kscan matrix and the `default_transform` matrix-transform. `col2row`
    with 5 row-gpios (sense) on `xiao_d 0-4` and 6 col-gpios (drive) on `xiao_d 5,10,6,9,7,8`, scanned
    **active-low** (drive columns low, sense rows through pull-ups) to match this board's wiring — unlike
    `xiao_split_60`, which is active-high, so do not copy that shield's GPIO flags here. The 6 column pins
    pair up (0&1, 2&3, 4&5) into the 3 physical rows, each pin driving one (mirrored) half of that row's
    10 keys — see the comment at the top of the file for how that maps to the `map` property's RC()
    ordering.
  - `nrf_butterfly_30-layouts.dtsi`, `Kconfig.shield`, `Kconfig.defconfig`, `nrf_butterfly_30.conf`,
    `nrf_butterfly_30.zmk.yml` — same roles as their `xiao_split_60` counterparts.
  - `layout.txt` / `generate-keymap.ps1` / `nrf_butterfly_30.keymap` — same generated-keymap workflow as
    `xiao_split_60` (see "Editing the keymap" below), but for a 3-row x 10-col grid instead of 5x12.
    Four layers: `base` (letters, Colemak-DH), `l2` (toggled by `TOG1` on the top-right key; adds
    ctrl/shift on the `,`/`.` keys), `num` (number row) and `sym` (symbols/brackets). Layer order sets
    priority sym > num > l2 > base. `num`/`sym` are momentary via the `TSYM`/`HNUM` hold-taps on the T/H
    keys (tap = the letter, hold = the layer). This mirrors the board's original Arduino firmware.
- `build.yaml` — GitHub Actions build matrix: builds `seeeduino_xiao_ble` + `xiao_split_60_left`
  `+ xiao_split_60_right`, and `+ nrf_butterfly_30`.
- `.github/workflows/build.yml` — CI entry point; delegates to ZMK's reusable
  `build-user-config.yml@v0.3` workflow. This is the actual way firmware gets built — there is no local
  build tooling checked into the repo.
- `zephyr/module.yml` — sets `board_root: .` so Zephyr/ZMK discovers `boards/shields` at the repo root.
- `.zmk/` — a local, gitignored west workspace (west topdir, vendored `zmk` firmware checkout). It's a
  local build/dev sandbox, not part of the tracked config; don't assume its contents are complete or
  in sync with the tracked `config/` and `boards/` directories.

## Editing the keymap

Each shield's keymap is authored in its own `layout.txt` (`boards/shields/<shield>/layout.txt`), a
plain-text grid format (documented in comments at the top of each file), not directly in devicetree. The
two shields have their own generator script tailored to their grid size (`xiao_split_60` is 5x12,
`nrf_butterfly_30` is 3x10) — they are not shared, so changes to one script don't affect the other. To
change any layer:

1. Edit the shield's `layout.txt`.
2. Regenerate the keymap:
   ```
   powershell -File boards/shields/<shield>/generate-keymap.ps1
   ```
3. Commit both `layout.txt` and the regenerated `.keymap` file.

Key facts about `layout.txt` (using `xiao_split_60`'s 5x12 grid as the example; `nrf_butterfly_30`'s
3x10 grid follows the same rules at its own dimensions):
- Each layer is a 5-row x 12-col grid; columns 0-5 are the left half, 6-11 the right half, laid out in
  physical left-to-right reading order. `|` is a purely visual divider between halves and is ignored by
  the parser.
- Layer order in the file **is** the layer index used by `MO<n>`/`TOG<n>`/`TO<n>` tokens elsewhere in the
  file — inserting or reordering a layer shifts every numeric reference below it.
- The generator (`generate-keymap.ps1`) hard-fails on: a row with != 12 tokens, a layer with != 5 rows,
  and any unrecognized token (with a pointer to add it to `$tokenMap` in the script). Fix the underlying
  `layout.txt` on any of these rather than patching the generated `.keymap`.
- `FHOLD` is a custom hold-tap behavior (`hold_layer`, `balanced` flavor, 200ms tapping term, emitted by
  the generator into the output file) — hold-taps `f` to the `f_hold` layer, tap types the letter `f`.
  If you add more hold-tap keys, extend the behavior block the generator emits, not the `.keymap` output.
  `nrf_butterfly_30`'s generator emits the same `hold_layer` behavior (referenced by the `TSYM`/`HNUM`
  tokens, `hold-preferred` flavor) for its T/H layer-taps.

## Build / CI

There's no local build or test command in this repo. Firmware is built by GitHub Actions on
push/PR/`workflow_dispatch` (`.github/workflows/build.yml`), which calls ZMK's own
`build-user-config.yml` workflow using `build.yaml` as the board/shield matrix. Validating a change means
letting CI build it (or using an out-of-repo west workspace, e.g. the `.zmk/` sandbox, if one is already
set up locally).
