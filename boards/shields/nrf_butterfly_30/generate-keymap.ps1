# Regenerates nrf_butterfly_30.keymap from layout.txt in this same folder.
# Usage: powershell -File generate-keymap.ps1

$ErrorActionPreference = 'Stop'

$layoutPath = Join-Path $PSScriptRoot 'layout.txt'
$keymapPath = Join-Path $PSScriptRoot 'nrf_butterfly_30.keymap'

$tokenMap = @{
    'ESC' = '&kp ESC'; 'TAB' = '&kp TAB'; 'BSPC' = '&kp BSPC'; 'DEL' = '&kp DEL'
    'ENTER' = '&kp ENTER'; 'SPACE' = '&kp SPACE'
    'LSFT' = '&kp LSHFT'; 'RSFT' = '&kp RSHFT'; 'LCTL' = '&kp LCTRL'; 'RCTL' = '&kp RCTRL'
    'LALT' = '&kp LALT'; 'LGUI' = '&kp LGUI'
    'GRAVE' = '&kp GRAVE'; 'MINUS' = '&kp MINUS'; 'EQUAL' = '&kp EQUAL'
    'LBKT' = '&kp LBKT'; 'RBKT' = '&kp RBKT'; 'BSLH' = '&kp BSLH'
    'SEMI' = '&kp SEMI'; 'SQT' = '&kp SQT'; 'COMMA' = '&kp COMMA'
    'DOT' = '&kp DOT'; 'FSLH' = '&kp FSLH'; 'COLON' = '&kp LS(SEMI)'
    'END' = '&kp END'; 'UP' = '&kp UP'; 'DOWN' = '&kp DOWN'
    'LEFT' = '&kp LEFT'; 'RIGHT' = '&kp RIGHT'
    'MUTE' = '&kp C_MUTE'; 'APP' = '&kp K_APP'
    'TRNS' = '&trans'; 'NONE' = '&none'
    'BOOT' = '&bootloader'
    'BT0' = '&bt BT_SEL 0'; 'BT1' = '&bt BT_SEL 1'; 'BT2' = '&bt BT_SEL 2'
    'BT3' = '&bt BT_SEL 3'; 'BT4' = '&bt BT_SEL 4'
    'OUTTOG' = '&out OUT_TOG'; 'BTCLR' = '&bt BT_CLR'
    'TSYM' = '&hold_layer 3 T'; 'HNUM' = '&hold_layer 2 H'
}

function Resolve-Token([string]$tok, [string]$context) {
    if ($tokenMap.ContainsKey($tok)) { return $tokenMap[$tok] }
    if ($tok -match '^[A-Z]$') { return "&kp $tok" }
    if ($tok -match '^[0-9]$') {
        $n = if ($tok -eq '0') { 'N0' } else { "N$tok" }
        return "&kp $n"
    }
    if ($tok -match '^F([1-9]|1[0-2])$') { return "&kp $tok" }
    if ($tok -match '^MO(\d+)$') { return "&mo $($Matches[1])" }
    if ($tok -match '^TOG(\d+)$') { return "&tog $($Matches[1])" }
    if ($tok -match '^TO(\d+)$') { return "&to $($Matches[1])" }
    throw "Unknown token '$tok' in $context. Add it to `$tokenMap in this script, or check for a typo."
}

$lines = Get-Content $layoutPath
$layers = New-Object System.Collections.Generic.List[object]
$currentName = $null
$rows = @()

function Flush-Layer {
    if (-not $currentName) { return }
    if ($rows.Count -ne 3) {
        throw "Layer '$currentName' has $($rows.Count) row(s), expected 3"
    }
    $layers.Add([PSCustomObject]@{ Name = $currentName; Rows = $rows })
}

foreach ($line in $lines) {
    $trimmed = $line.Trim()
    if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }

    if ($trimmed -match '^\[(.+)\]$') {
        Flush-Layer
        $currentName = $Matches[1]
        $rows = @()
        continue
    }

    if (-not $currentName) {
        throw "Found a token line before any [layer] header: $trimmed"
    }

    $tokens = $trimmed -split '\s+' | ForEach-Object { $_.Trim('|') } | Where-Object { $_ -ne '' }
    if ($tokens.Count -ne 10) {
        throw "Layer '$currentName' row has $($tokens.Count) token(s), expected 10: $trimmed"
    }
    $rows += , $tokens
}
Flush-Layer

if ($layers.Count -eq 0) {
    throw "No layers found in $layoutPath"
}

$layerBlocks = foreach ($layer in $layers) {
    $bindingLines = foreach ($row in $layer.Rows) {
        $resolved = foreach ($tok in $row) { Resolve-Token $tok "layer '$($layer.Name)'" }
        ($resolved -join ' ')
    }
    $bindings = $bindingLines -join "`n"
    "        $($layer.Name) {`n            bindings = <`n$bindings`n            >;`n        };"
}

$body = $layerBlocks -join "`n`n"

$output = @"
// GENERATED FILE -- edit layout.txt and run generate-keymap.ps1 instead.
#include <behaviors.dtsi>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/bt.h>
#include <dt-bindings/zmk/outputs.h>

/ {
    behaviors {
        // Tap = letter, hold = momentary layer. "hold-preferred" flavor:
        // any other key pressed while T/H is held resolves to the layer
        // (not the letter), matching the original Arduino firmware's
        // layer-tap logic. 200ms tapping term.
        hold_layer: hold_layer {
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "hold-preferred";
            tapping-term-ms = <200>;
            bindings = <&mo>, <&kp>;
            display-name = "Hold Layer";
        };
    };

    keymap {
        compatible = "zmk,keymap";

$body
    };
};
"@

Set-Content -Path $keymapPath -Value $output -NoNewline -Encoding utf8
Write-Output "Generated $keymapPath from $($layers.Count) layer(s): $(($layers | ForEach-Object { $_.Name }) -join ', ')"
