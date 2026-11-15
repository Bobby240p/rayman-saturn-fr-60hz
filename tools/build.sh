#!/bin/sh
# Reconstruit E:\Recomp\Rayman Saturn\FR_60Hz\Rayman FR 60Hz.cue/.bin depuis l'original FR.
# usage: sh tools/build.sh [safe_center|safe|full]   (défaut : safe_center = version livrée)
#   safe_center : 240 lignes + timing 60 Hz + image PAL centrée (8 lignes rognées en haut et en bas),
#                 interface de jeu recalée, tables de défilement par ligne VDP2 décalées
#   full : ANCIEN essai, constantes de hauteur devinées -> casse les menus, ne pas utiliser
#   safe : 240 lignes + timing 60 Hz uniquement (mise en page PAL 256 conservée, bas rogné)
set -e
MODE=${1:-safe_center}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
T="$ROOT/tools"
TMP="${TMPDIR:-/tmp}/rayman_build"; mkdir -p "$TMP"
FR_CUE="$ROOT/FR/Rayman (Europe) (En,Fr,De) (1S).cue"
FR_T1="$ROOT/FR/Rayman (Europe) (En,Fr,De) (1S) (Track 01).bin"
US_BIN="$ROOT/US/Rayman (USA) (DW0856).bin"

python -I "$T/make_patch.py" "$T/data" "$FR_T1" "$TMP/t01.bin" "$MODE" | tail -1
python -I "$T/region_ntsc.py" "$US_BIN" "$TMP/t01.bin"
case "$MODE" in *center*) python -I "$T/title_bg.py" "$TMP/t01.bin" 5 ;; esac

# cue temporaire : piste 1 patchée + pistes audio originales FR
python -I - "$FR_CUE" "$TMP/t01.bin" "$TMP/tmp.cue" <<'EOF'
import sys, os, re
cue, t1, out = sys.argv[1:]
d = os.path.dirname(cue); lines = []
for l in open(cue):
    m = re.match(r'FILE "(.+)" BINARY', l.strip())
    if m:
        p = t1 if '(Track 01)' in m.group(1) else os.path.join(d, m.group(1))
        l = 'FILE "%s" BINARY\n' % p
    lines.append(l)
open(out, 'w').writelines(lines)
EOF
OUT="${OUT:-$ROOT/FR_60Hz}"
python -I "$T/merge.py" "$TMP/tmp.cue" "$OUT" "Rayman FR 60Hz"
rm -f "$TMP/t01.bin" "$TMP/tmp.cue"
echo "$OUT reconstruit (mode $MODE)"
