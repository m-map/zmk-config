#!/usr/bin/env python3
"""Regenerates nrf_butterfly_30.keymap from layout.txt in this same folder.

Usage: python3 generate-keymap.py
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LAYOUT_PATH = SCRIPT_DIR / "layout.txt"
KEYMAP_PATH = SCRIPT_DIR / "nrf_butterfly_30.keymap"

TOKEN_MAP = {
    "ESC": "&kp ESC", "TAB": "&kp TAB", "BSPC": "&kp BSPC", "DEL": "&kp DEL",
    "ENTER": "&kp ENTER", "SPACE": "&kp SPACE",
    "LSFT": "&kp LSHFT", "RSFT": "&kp RSHFT", "LCTL": "&kp LCTRL", "RCTL": "&kp RCTRL",
    "LALT": "&kp LALT", "LGUI": "&kp LGUI", "COMMAND": "&kp LGUI",
    "GRAVE": "&kp GRAVE", "MINUS": "&kp MINUS", "EQUAL": "&kp EQUAL",
    "LBKT": "&kp LBKT", "RBKT": "&kp RBKT", "BSLH": "&kp BSLH",
    "SEMI": "&kp SEMI", "SQT": "&kp SQT", "COMMA": "&kp COMMA",
    "DOT": "&kp DOT", "FSLH": "&kp FSLH", "COLON": "&kp LS(SEMI)",
    "END": "&kp END", "UP": "&kp UP", "DOWN": "&kp DOWN",
    "LEFT": "&kp LEFT", "RIGHT": "&kp RIGHT",
    "MUTE": "&kp C_MUTE", "APP": "&kp K_APP",
    "TRNS": "&trans", "NONE": "&none",
    "BOOT": "&bootloader",
    "BT0": "&bt BT_SEL 0", "BT1": "&bt BT_SEL 1", "BT2": "&bt BT_SEL 2",
    "BT3": "&bt BT_SEL 3", "BT4": "&bt BT_SEL 4",
    "OUTTOG": "&out OUT_TOG", "OUTUSB": "&out OUT_USB", "OUTBLE": "&out OUT_BLE",
    "BTCLR": "&bt BT_CLR",
}

LETTER_RE = re.compile(r"^[A-Z]$")
DIGIT_RE = re.compile(r"^[0-9]$")
FKEY_RE = re.compile(r"^F([1-9]|1[0-2])$")
MO_RE = re.compile(r"^MO(\d+)$")
TOG_RE = re.compile(r"^TOG(\w+)$")
TO_RE = re.compile(r"^TO(\w+)$")
COMBO_RE = re.compile(r"^(.+?)(L|K|T)(\d+)$")


def resolve_token(tok, context, layer_index, key_aliases, _stack=()):
    if tok in TOKEN_MAP:
        return TOKEN_MAP[tok]
    if LETTER_RE.match(tok):
        return f"&kp {tok}"
    if DIGIT_RE.match(tok):
        n = "N0" if tok == "0" else f"N{tok}"
        return f"&kp {n}"
    if FKEY_RE.match(tok):
        return f"&kp {tok}"
    m = MO_RE.match(tok)
    if m:
        return f"&mo {m.group(1)}"
    m = TOG_RE.match(tok)
    if m and m.group(1) in layer_index:
        return f"&tog {layer_index[m.group(1)]}"
    m = TO_RE.match(tok)
    if m and m.group(1) in layer_index:
        return f"&to {layer_index[m.group(1)]}"
    if tok in layer_index:
        # A bare layer-name token: hold-only (momentary), per the "L<n> =
        # hold layer" / "T<n> = toggle layer" semantics.
        if tok.startswith("T"):
            return f"&tog {layer_index[tok]}"
        return f"&mo {layer_index[tok]}"

    m = COMBO_RE.match(tok)
    if m:
        if tok in _stack:
            raise ValueError(f"Token '{tok}' in {context} refers to itself")
        base_tok, kind, num = m.group(1), m.group(2), m.group(3)
        base_binding = resolve_token(
            base_tok, f"{context} (base of combo '{tok}')", layer_index, key_aliases, _stack + (tok,)
        )
        if not base_binding.startswith("&kp "):
            raise ValueError(
                f"Combo token '{tok}' in {context}: base '{base_tok}' must resolve to a &kp binding, "
                f"got '{base_binding}'"
            )
        base_keycode = base_binding[len("&kp "):]

        if kind == "L":
            layer_name = f"L{num}"
            if layer_name not in layer_index:
                raise ValueError(f"Combo token '{tok}' in {context} references unknown layer '{layer_name}'")
            return f"&hold_layer {layer_index[layer_name]} {base_keycode}"
        if kind == "T":
            layer_name = f"T{num}"
            if layer_name not in layer_index:
                raise ValueError(f"Combo token '{tok}' in {context} references unknown layer '{layer_name}'")
            return f"&hold_toggle {layer_index[layer_name]} {base_keycode}"
        if kind == "K":
            if num not in key_aliases:
                raise ValueError(f"Combo token '{tok}' in {context} references undefined key alias K{num}")
            alias_binding = resolve_token(
                key_aliases[num], f"{context} (alias K{num})", layer_index, key_aliases, _stack + (tok,)
            )
            if not alias_binding.startswith("&kp "):
                raise ValueError(f"Key alias K{num} must resolve to a &kp binding, got '{alias_binding}'")
            alias_keycode = alias_binding[len("&kp "):]
            return f"&hold_mod {alias_keycode} {base_keycode}"

    raise ValueError(
        f"Unknown token '{tok}' in {context}. Add it to TOKEN_MAP in this script, or check for a typo."
    )


ALIAS_RE = re.compile(r"^K(\d+)\s*=\s*(\S+)$")
HEADER_RE = re.compile(r"^\[(.+)\]$")


def main():
    lines = LAYOUT_PATH.read_text().splitlines()

    layers = []  # list of {"name": str, "rows": [[tok, ...], ...]}
    key_aliases = {}
    current_name = None
    rows = []

    def flush_layer():
        if current_name is None:
            return
        if len(rows) != 3:
            raise ValueError(f"Layer '{current_name}' has {len(rows)} row(s), expected 3")
        layers.append({"name": current_name, "rows": rows})

    for line in lines:
        trimmed = line.strip()
        if trimmed == "" or trimmed.startswith("#"):
            continue

        header = HEADER_RE.match(trimmed)
        if header:
            flush_layer()
            current_name = header.group(1)
            rows = []
            continue

        alias = ALIAS_RE.match(trimmed)
        if alias:
            if current_name is None:
                raise ValueError(f"Found a 'K<n> =' alias line before any [layer] header: {trimmed}")
            key_aliases[alias.group(1)] = alias.group(2)
            continue

        if current_name is None:
            raise ValueError(f"Found a token line before any [layer] header: {trimmed}")

        tokens = [t.strip("|") for t in trimmed.split()]
        tokens = [t for t in tokens if t != ""]
        if len(tokens) != 10:
            raise ValueError(f"Layer '{current_name}' row has {len(tokens)} token(s), expected 10: {trimmed}")
        rows.append(tokens)

    flush_layer()

    if not layers:
        raise ValueError(f"No layers found in {LAYOUT_PATH}")

    layer_index = {layer["name"]: i for i, layer in enumerate(layers)}

    layer_blocks = []
    for layer in layers:
        binding_lines = []
        for row in layer["rows"]:
            resolved = [
                resolve_token(tok, f"layer '{layer['name']}'", layer_index, key_aliases) for tok in row
            ]
            binding_lines.append(" ".join(resolved))
        bindings = "\n".join(binding_lines)
        layer_blocks.append(
            f"        {layer['name']} {{\n            bindings = <\n{bindings}\n            >;\n        }};"
        )

    body = "\n\n".join(layer_blocks)

    output = f"""// GENERATED FILE -- edit layout.txt and run generate-keymap.py instead.
#include <behaviors.dtsi>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/bt.h>
#include <dt-bindings/zmk/outputs.h>

/ {{
    behaviors {{
        // Tap = base key, hold = momentary-activate a layer. "tap-preferred"
        // flavor: an interrupting key press only resolves to the layer if
        // the hold-tap key is still held past the tapping term; fast rolls
        // (e.g. "to", "ti") resolve as taps instead of misfiring into the
        // layer. Drives every "<base>L<n>" combo token.
        hold_layer: hold_layer {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "tap-preferred";
            tapping-term-ms = <300>;
            bindings = <&mo>, <&kp>;
            display-name = "Hold Layer";
        }};

        // Tap = base key, hold = toggle a layer on/off. Same tap-preferred
        // timing as hold_layer. Drives every "<base>T<n>" combo token.
        hold_toggle: hold_toggle {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "tap-preferred";
            tapping-term-ms = <300>;
            bindings = <&tog>, <&kp>;
            display-name = "Hold Toggle Layer";
        }};

        // Tap = base key, hold = a different key (used for modifiers, e.g.
        // Z taps 'z' but held acts as left shift). Drives every "<base>K<n>"
        // combo token, where K<n> is defined by a "K<n> = <token>" alias
        // line in layout.txt.
        //
        // "balanced" + hold-trigger-on-release: if another key is pressed
        // AND released while this key is still held, that resolves to hold
        // as soon as the other key releases -- no waiting out the tapping
        // term -- so holding B and tapping C for Cmd+C feels like a real
        // chord instead of a laggy timeout. require-prior-idle-ms keeps
        // ordinary fast typing safe: if this key is pressed within 150ms of
        // any other keypress, it resolves as a tap immediately, no hold
        // ever considered. retro-tap is deliberately NOT set: holding a
        // modifier alone and releasing it with nothing else pressed must
        // keep producing no output, same as holding a real shift key.
        hold_mod: hold_mod {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "balanced";
            tapping-term-ms = <200>;
            require-prior-idle-ms = <150>;
            hold-trigger-on-release;
            bindings = <&kp>, <&kp>;
            display-name = "Hold Mod";
        }};
    }};

    keymap {{
        compatible = "zmk,keymap";

{body}
    }};
}};
"""

    KEYMAP_PATH.write_text(output)
    print(f"Generated {KEYMAP_PATH} from {len(layers)} layer(s): {', '.join(l['name'] for l in layers)}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
