#!/usr/bin/env python3
"""Regenerates xiao_split_60.keymap from layout.txt in this same folder.

Usage: python3 generate-keymap.py
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LAYOUT_PATH = SCRIPT_DIR / "layout.txt"
KEYMAP_PATH = SCRIPT_DIR / "xiao_split_60.keymap"

TOKEN_MAP = {
    "ESC": "&kp ESC", "TAB": "&kp TAB", "BSPC": "&kp BSPC", "DEL": "&kp DEL",
    "ENTER": "&kp ENTER", "SPACE": "&kp SPACE",
    "LSFT": "&kp LSHFT", "RSFT": "&kp RSHFT", "LCTL": "&kp LCTRL",
    "LALT": "&kp LALT", "LGUI": "&kp LGUI",
    "GRAVE": "&kp GRAVE", "MINUS": "&kp MINUS", "EQUAL": "&kp EQUAL",
    "LBKT": "&kp LBKT", "RBKT": "&kp RBKT", "BSLH": "&kp BSLH",
    "SEMI": "&kp SEMI", "SQT": "&kp SQT", "COMMA": "&kp COMMA",
    "DOT": "&kp DOT", "FSLH": "&kp FSLH",
    "END": "&kp END", "UP": "&kp UP", "DOWN": "&kp DOWN",
    "LEFT": "&kp LEFT", "RIGHT": "&kp RIGHT",
    "MUTE": "&kp C_MUTE", "APP": "&kp K_APP",
    "VOLU": "&kp C_VOL_UP", "VOLD": "&kp C_VOL_DN",
    "BRIU": "&kp C_BRI_UP", "BRID": "&kp C_BRI_DN",
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
TOG_RE = re.compile(r"^TOG(\d+)$")
TO_RE = re.compile(r"^TO(\d+)$")


def resolve_token(tok, context):
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
    if m:
        return f"&tog {m.group(1)}"
    m = TO_RE.match(tok)
    if m:
        return f"&to {m.group(1)}"
    raise ValueError(
        f"Unknown token '{tok}' in {context}. Add it to TOKEN_MAP in this script, or check for a typo."
    )


HEADER_RE = re.compile(r"^\[(.+)\]$")


def main():
    lines = LAYOUT_PATH.read_text().splitlines()

    layers = []  # list of {"name": str, "rows": [[tok, ...], ...]}
    current_name = None
    rows = []

    def flush_layer():
        if current_name is None:
            return
        if len(rows) != 5:
            raise ValueError(f"Layer '{current_name}' has {len(rows)} row(s), expected 5")
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

        if current_name is None:
            raise ValueError(f"Found a token line before any [layer] header: {trimmed}")

        tokens = [t.strip("|") for t in trimmed.split()]
        tokens = [t for t in tokens if t != ""]
        if len(tokens) != 12:
            raise ValueError(f"Layer '{current_name}' row has {len(tokens)} token(s), expected 12: {trimmed}")
        rows.append(tokens)

    flush_layer()

    if not layers:
        raise ValueError(f"No layers found in {LAYOUT_PATH}")

    layer_blocks = []
    for layer in layers:
        binding_lines = []
        for row in layer["rows"]:
            resolved = [resolve_token(tok, f"layer '{layer['name']}'") for tok in row]
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
