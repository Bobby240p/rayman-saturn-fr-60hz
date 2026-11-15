#!/bin/sh
# Construit video/AFR_final.cpk (intro PS1 en 320x200 pour le lecteur CPK de la Saturn).
# usage : sh tools/make_video.sh "<piste 01 du disque PS1 Rayman (Europe)>"
# Prérequis : ffmpeg (variable FFMPEG ou dans le PATH), Python 3 + numpy.
set -e
PS1="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; T="$ROOT/tools"; V="$ROOT/video"; mkdir -p "$V"
FF="${FFMPEG:-ffmpeg}"
# 1. extraction de /VIDEO/FR_INTRO.STR en secteurs bruts (2352 octets, format lu par ffmpeg)
python -I -c "
import sys; sys.path.insert(0, r'$T')
from isols import walk
img, out = r'$PS1', r'$V/FR_INTRO.STR'
lba, size, p = next(x for x in walk(img, 'FR_INTRO.STR'))
f = open(img, 'rb'); f.seek(lba * 2352); open(out, 'wb').write(f.read(size // 2048 * 2352))
print(p, lba, size)"
# 2. son : stéréo 22050 Hz PCM 16 bits big-endian
"$FF" -v error -y -i "$V/FR_INTRO.STR" -vn -af "aresample=22050:filter_size=64:cutoff=0.95" -ac 2 -c:a pcm_s16be -f s16be "$V/audio22st.raw"
# 3. image : Cinepak 320x200, 1 seule bande (limite du décodeur Sega), image clé toutes les 15
"$FF" -v error -y -i "$V/FR_INTRO.STR" -an -vf format=rgb24 -c:v cinepak -q:v 1 -max_strips 1 -max_extra_cb_iterations 8 -g 15 -f film_cpk "$V/video.cpk"
# 4. compatibilité Sega (blocs 0x3200 -> 0x3000, tailles multiples de 4) + conteneur FILM 1.06, 16,67 i/s, stéréo
python -I -c "
import sys; sys.path.insert(0, r'$T')
import mkfilm, cvidfix
fr, w, h, _ = mkfilm.read_film(r'$V/video.cpk')
mkfilm.build([cvidfix.fix_frame(x) for x in fr], w, h, open(r'$V/audio22st.raw', 'rb').read(), 22050, r'$V/AFR_final.cpk', 36, 2)"
echo "video/AFR_final.cpk prêt : tools/build.sh l'insérera dans l'image"
