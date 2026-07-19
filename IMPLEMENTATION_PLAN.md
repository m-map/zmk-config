# xiao_split_60 — Implementation Plan

## Context

`zmk keyboard new` scaffolded `boards/shields/xiao_split_60/` but every file is still
template boilerplate: a dummy 2×2 matrix, 4 placeholder keys, `&xiao_d 0` repeated for
every GPIO, and a 4-key `A B C D` keymap. `build.yaml` has no build targets at all, so
CI currently produces nothing.

The real hardware is a 60-key wireless split: two Seeed XIAO nRF52840 boards, each
driving its own 5×6 switch matrix, each with its own LiPo. **Long battery life is the
primary design goal.** This plan fills in the real matrix, transform, and keymap, and
applies a power configuration tuned for that goal.

Repo facts established during exploration:
- ZMK pinned to **v0.3** (`config/west.yml`, `.github/workflows/build.yml`); local
  checkout at `.zmk/zmk` is release `0.3.0` and was used to verify every Kconfig symbol
  cited below.
- Board id is `seeeduino_xiao_ble` (`.zmk/zmk/app/boards/arm/seeeduino_xiao_ble/seeeduino_xiao_ble.zmk.yml`),
  exposing the `seed_xiao` interconnect — so `&xiao_d N` is the correct GPIO reference.
- The board overlay `.zmk/zmk/app/boards/seeeduino_xiao_ble.overlay` already provides
  `zmk,battery` (the `vbatt` divider on ADC ch7, gated by a `power-gpios` pin) and the
  QSPI `p25q16h` flash node. No shield-side battery work is needed.

## Decisions made with the user

| Decision | Choice |
|---|---|
| Split transport | **BLE wireless** (see note below) |
| Unassigned matrix positions | `&none` on the base layer, plus one momentary **system layer** |
| Power profile | Balanced-aggressive |
| ZMK Studio | **Off** |

### Note on bidirectionality (the open question from the Q&A)

BLE split in ZMK **is** bidirectional and does exactly what was asked. All keymap
resolution — layers included — happens on the central. The peripheral only reports raw
key *positions*; the central decides what they mean. So a layer key on the **left**
(central) immediately changes what every **right**-half key produces, and vice versa.
There is also an explicit central→peripheral command channel
(`split_bt_invoke_behavior_payload`, `.zmk/zmk/app/src/split/bluetooth/central.c:1109`)
used to run behaviors on the peripheral.

Because of this, **wired UART is not needed** for the function-key use case, and BLE is
the better battery choice here (ZMK's wired split polls a UART continuously; its BLE
split idles the radio with connection latency). Wiring the halves stays available later
as a pure config change.

## Matrix analysis

Rows are `D0..D4`, columns are `D5, D6, D10, D9, D8, D7` — 5 × 6 = 30 per side. Reading
the supplied layout, the two halves are **mirror-wired**, i.e. visual left-to-right
column order differs per side:

- **Left** half, outer → inner: `D7, D8, D9, D10, D6, D5`  (Esc, 1, 2, 3, 4, 5)
- **Right** half, inner → outer: `D5, D6, D10, D9, D8, D7` (6, 7, 8, 9, 0, Del)

This is exploited to keep a **single** matrix transform: the per-side `col-gpios`
ordering absorbs the mirroring, so the transform map is a plain 5×12 grid in reading
order and the right overlay only needs `col-offset = <6>`. This mirrors how
`.zmk/zmk/app/boards/shields/corne/corne.dtsi` handles the same problem.

All 60 positions are included in the transform (not just the 51 assigned ones) so the
9 currently-unused switches can be bound later by editing only the keymap.

## Files to change

All under `boards/shields/xiao_split_60/` unless noted.

### 1. `xiao_split_60.dtsi` — real matrix + transform

Replace the placeholder `kscan` and `default_transform`:

- `kscan`: keep `compatible = "zmk,kscan-gpio-matrix"`, `diode-direction = "col2row"`,
  and `wakeup-source` (the latter is required for deep-sleep wake — do not drop it).
  Set `row-gpios` to `&xiao_d 0` … `&xiao_d 4`, each
  `(GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)`.
- Add `zmk,kscan = &kscan;` to the `chosen` node alongside the existing
  `zmk,physical-layout` (corne sets both; harmless and avoids resolution surprises).
- `default_transform`: `rows = <5>`, `columns = <12>`, map = `RC(r,0)`…`RC(r,11)` for
  `r` in `0..4`, i.e. all 60 positions in visual reading order, left cols `0-5`,
  right cols `6-11`.

**Diode direction is an assumption.** If the physical build is row2col instead, follow
the instructions already in the template comment: swap the polarity flags between
`row-gpios` and `col-gpios` and change `diode-direction`. Verify against the PCB before
the first flash.

### 2. `xiao_split_60_left.overlay` — left columns

`col-gpios` in visual order (index 0 → 5): `&xiao_d 7`, `8`, `9`, `10`, `6`, `5`, each
`GPIO_ACTIVE_HIGH`. No `col-offset`.

### 3. `xiao_split_60_right.overlay` — right columns

Keep `&default_transform { col-offset = <6>; }` (template already has the node, change
the value from `2` to `6`).
`col-gpios` in visual order: `&xiao_d 5`, `6`, `10`, `9`, `8`, `7`, each
`GPIO_ACTIVE_HIGH`.

### 4. `xiao_split_60-layouts.dtsi` — drop the Studio key coordinates

Keep the `default_layout` node (it binds `transform` + `kscan` and is the target of
`chosen { zmk,physical-layout }`), but **delete the `keys = <...>` property** and its
comment. With Studio off, per-key x/y/w/h coordinates serve no purpose; the
`key_physical_attrs` list is optional per
`.zmk/zmk/app/dts/bindings/zmk,physical-layout.yaml`.

### 5. `xiao_split_60.keymap` — 2 layers, 60 bindings each

Two layers. Bindings listed 12 per row, 5 rows, in the same visual order as the
transform map.

**Layer 0 `base`** — exactly the supplied layout, `&none` at every EMPTY, with one
exception (below):

```
 ESC   N1    N2    N3    N4    N5   │  N6    N7    N8    N9    N0    DEL
 TAB   Q     W     E     R     T    │  Y     U     I     O     P     BSPC
 LSFT  A     S     D     F     G    │  H     J     K     L     SEMI  SQT
 none  Z     X     C     V     B    │  N     M     COMMA DOT   FSLH  RSFT
 LALT  LCTL  MO(1) none  none  none │  none  none  none  SPACE SPACE none
```

The single deviation from "strictly `&none`": **left row 4, column 2 (`D4`/`D9`)**
becomes `&mo 1` — it is the spare position closest to the existing `LCTL`/`LALT` thumb
keys. Changing which spare hosts this is a one-line edit.

**Layer 1 `sys`** — `&trans` everywhere except the number row:

```
 BOOT  BT_SEL0 BT_SEL1 BT_SEL2 BT_SEL3 BT_SEL4 │ OUT_TOG trans trans trans BT_CLR BOOT
 ...all &trans...
```

Two details verified in source:
- `&bootloader` and `&sys_reset` have `BEHAVIOR_LOCALITY_EVENT_SOURCE`
  (`.zmk/zmk/app/src/behaviors/behavior_reset.c:38`) — a `&bootloader` on a *left*
  position only reboots the left half. **Both halves therefore need their own
  `&bootloader` key**, hence one at each end of the row.
- `&bt` and `&out` are central-only behaviors; placing them anywhere is fine.

Requires `#include <dt-bindings/zmk/bt.h>` and `#include <dt-bindings/zmk/outputs.h>`
in addition to the existing includes.

**Heads-up, not changed:** the supplied layout has no `ENTER` key anywhere. The 8
remaining `&none` positions are the obvious home for it.

### 6. `xiao_split_60.zmk.yml` — metadata

Remove `- studio` from `features` (leaving `- keys`). Set a real `url` or drop the key.

### 7. `build.yaml` (repo root) — currently empty, no targets

```yaml
include:
  - board: seeeduino_xiao_ble
    shield: xiao_split_60_left
  - board: seeeduino_xiao_ble
    shield: xiao_split_60_right
```

### 8. Power configuration — new files in `config/`

Config resolution was traced in `.zmk/zmk/app/keymap-module/modules/modules.cmake:160-196`.
For `SHIELD=xiao_split_60_left`, ZMK collects **all** matching conf files, both
`config/xiao_split_60.conf` (shared) and `config/xiao_split_60_left.conf` (side-specific).
Both are applied. Use that split.

**`config/xiao_split_60.conf` (both halves):**

| Setting | Value | Why |
|---|---|---|
| `CONFIG_ZMK_SLEEP` | `y` | Deep sleep. Not on by default. Also auto-selects `PM_DEVICE` and `ZMK_PM_DEVICE_SUSPEND_RESUME` (`.zmk/zmk/app/Kconfig:396-412`), which is what suspends the QSPI flash. |
| `CONFIG_ZMK_IDLE_SLEEP_TIMEOUT` | `900000` | 15 min. Default is already 900000; set explicitly so it is visible and tunable. |
| `CONFIG_ZMK_IDLE_TIMEOUT` | `30000` | Default; no display so this is near-free. |
| `CONFIG_LOG` / `CONFIG_ZMK_USB_LOGGING` | `n` | Logging keeps a UART/USB endpoint and a log thread alive. |
| `CONFIG_SERIAL`, `CONFIG_CONSOLE`, `CONFIG_UART_CONSOLE` | `n` | Already `n` in the board conf; restate so a future change cannot silently re-enable them. |

**`config/xiao_split_60_left.conf` (central):**

| Setting | Value | Why |
|---|---|---|
| `CONFIG_ZMK_SPLIT_BLE_PREF_LATENCY` | `99` | Default 30 (`.zmk/zmk/app/src/split/bluetooth/Kconfig`). With `PREF_INT=6` (7.5 ms) and `PREF_TIMEOUT=400` (4 s), the safe ceiling is ~265; 99 gives ~750 ms of skipped idle connection events on the split link without risking supervision timeout. **Does not add keypress latency** — latency only applies when the peripheral has nothing to send. |
| `CONFIG_ZMK_SPLIT_BLE_PREF_INT` | leave at `6` | Raising it *would* add real keypress latency. Not worth it. |
| host-link `BT_PERIPHERAL_PREF_*` | leave at ZMK defaults | Already tuned (`min 6 / max 12 / latency 30 / timeout 400`, `.zmk/zmk/app/Kconfig:225-235`) and these are host-compatibility sensitive. |

**`config/xiao_split_60_right.conf` (peripheral):**

| Setting | Value | Why |
|---|---|---|
| `CONFIG_ZMK_USB` | `n` | The peripheral never presents HID. Board conf sets `y`; override it. UF2 flashing is unaffected — that is the Adafruit bootloader, reached by double-tapping reset, independent of the app. |
| `CONFIG_ZMK_BATTERY_REPORTING` | `y` | Cheap: the `vbatt` divider is gated by `power-gpios` so it only draws current during a sample. |

Optionally on the central: `CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y` +
`..._PROXY=y` to see the right half's battery on the host. Low cost; include it.

### QSPI flash — measure, do not guess

The XIAO nRF52840 carries a P25Q16H QSPI flash that ZMK does not use (settings live in
internal-flash NVS). It is widely blamed for idle drain on this board, but the actual
magnitude depends on whether Zephyr's `nordic,qspi-nor` driver issues the deep-power-down
command at init. The board overlay already declares `has-dpd`, `t-enter-dpd`, and
`t-exit-dpd`, and enabling `CONFIG_ZMK_SLEEP` brings in `PM_DEVICE`, which is the
mechanism that suspends it.

**Do not add speculative QSPI Kconfig.** Build with the above, then measure idle current
(see verification). If idle sits near ~1 mA rather than tens of µA, the flash is the
culprit; the two candidate remedies are `CONFIG_PM_DEVICE_RUNTIME=y`, or disabling the
node outright via a `config/*.overlay` (`&p25q16h { status = "disabled"; };` plus
`CONFIG_NORDIC_QSPI_NOR=n`). Pick based on the measurement, not in advance.

## Files NOT changed

- `Kconfig.shield` — correct as generated.
- `Kconfig.defconfig` — correct: left is central, `ZMK_SPLIT=y` on both.
  `ZMK_SPLIT_BLE_CENTRAL_PERIPHERALS` already defaults to `1`
  (`.zmk/zmk/app/src/split/bluetooth/Kconfig.defaults`).
- `xiao_split_60.conf` (the one *inside the shield dir*) — this is the commented
  template copied into downstream users' configs. Leave it as documentation; real
  settings go in `config/` per §8.
- `.github/workflows/build.yml`, `config/west.yml`, `zephyr/module.yml` — all correct.

## Verification

1. **Build locally** (fastest failure signal, catches devicetree errors):
   ```
   cd .zmk && west build -p -s zmk/app -b seeeduino_xiao_ble -- \
     -DSHIELD=xiao_split_60_left -DZMK_CONFIG="<repo>/config"
   ```
   Repeat with `xiao_split_60_right`. Confirm in the CMake output:
   `ZMK Config Kconfig:` lines for **both** `xiao_split_60.conf` and the side-specific
   conf, and `Using keymap file:` pointing at the intended keymap.
2. **Confirm the transform took**: check the generated
   `build/zephyr/zephyr.dts` for a `zmk,matrix-transform` with 60 map entries and the
   right half's `col-offset = <6>`.
3. **Push and let CI build** — `.github/workflows/build.yml` produces
   `xiao_split_60_left-seeeduino_xiao_ble-zmk.uf2` and the right equivalent.
4. **Flash both halves**, double-tap reset to enter the bootloader, drag the UF2.
   Flash the **right/peripheral first**, then the left.
5. **Matrix check**: with only the left half connected over USB, press every key and
   confirm each produces the intended character — this is where a wrong
   `diode-direction` or a transposed column order shows up. Then power the right half
   and repeat. A whole row or column dead ⇒ GPIO order wrong; every key shifted by a
   fixed amount ⇒ `col-offset` wrong.
6. **Bidirectionality check** (the thing that drove the transport decision): hold the
   left `&mo 1` key and press right-half keys — they must produce layer-1 bindings.
7. **Power measurement**: with the halves connected and idle, measure current on the
   battery lead of each half (USB unplugged — USB masks battery draw). Expect tens of
   µA once deep sleep engages after 15 min, low single-digit mA while actively
   connected and typing. If idle > ~500 µA, apply the QSPI investigation above.
8. **Deep-sleep wake**: leave idle past 15 min, press a key, confirm it wakes and
   reconnects. If it does not wake, `wakeup-source` was lost from the `kscan` node.
