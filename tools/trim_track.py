"""Raccourcit une piste audio CD (PCM 16 bits stéréo, secteurs de 2352 octets) avec fondu de sortie.
usage: python -I trim_track.py <piste.bin> <sortie.bin> <fin_en_s> [fondu_s=0.4]
Le temps est compté depuis le début du fichier (pré-gap compris). La longueur est arrondie au secteur."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
import numpy as np

src, dst, end = sys.argv[1], sys.argv[2], float(sys.argv[3])
fade = float(sys.argv[4]) if len(sys.argv) > 4 else 0.4
a = np.fromfile(src, '<i2').reshape(-1, 2).astype(float)
nsec = int(round(end * 75))                         # 75 secteurs CD par seconde
n = nsec * 588                                      # 588 échantillons stéréo par secteur
a = a[:n].copy()
f = int(fade * 44100)
a[n - f:] *= np.linspace(1.0, 0.0, f)[:, None]
a.round().astype('<i2').tofile(dst)
print('%s : %.2f s -> %.2f s (%d secteurs), fondu %.1f s' % (os.path.basename(dst), os.path.getsize(src) / 176400, n / 44100, nsec, fade))
