"""Écran titre : descend le texte "(c) Ubi Soft 1995" de l'image de fond VIGNET/FD01SATP.BIT
sans toucher au reste (le fond en dégradé est reconstitué sous l'ancienne position).
L'image est stockée en caractères 16x16 (4 cellules 8x8 : HG HD BG BD), 20 par ligne, RGB555.
usage: python -I title_bg.py <track01.bin> [decalage=5] [apercu.png]"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from isofind import find
from edc import fix  # EDC/ECC mode 1

TRACK = sys.argv[1]
DY = int(sys.argv[2]) if len(sys.argv) > 2 else 5
PREVIEW = sys.argv[3] if len(sys.argv) > 3 else None
X0, X1, Y0, Y1 = 112, 210, 3, 19          # zone du texte (lignes 3..18 de l'image PAL)

def decode(raw):
    t = np.frombuffer(raw, '>u2').reshape(-1, 8, 8)
    img = np.zeros((256, 320), np.uint16)
    for c in range(320):
        cx, cy = (c % 20) * 16, (c // 20) * 16
        for k, (dx, dy) in enumerate(((0, 0), (8, 0), (0, 8), (8, 8))):
            img[cy + dy:cy + dy + 8, cx + dx:cx + dx + 8] = t[c * 4 + k]
    return img

def encode(img):
    t = np.zeros((1280, 8, 8), np.uint16)
    for c in range(320):
        cx, cy = (c % 20) * 16, (c // 20) * 16
        for k, (dx, dy) in enumerate(((0, 0), (8, 0), (0, 8), (8, 8))):
            t[c * 4 + k] = img[cy + dy:cy + dy + 8, cx + dx:cx + dx + 8]
    return t.astype('>u2').tobytes()

def split(img):   # -> composantes float (r,g,b) 0..31, bit 15
    return np.stack([(img & 31), (img >> 5) & 31, (img >> 10) & 31], -1).astype(float), img & 0x8000

def join(c, hi):
    c = np.clip(np.rint(c), 0, 31).astype(np.uint16)
    return c[..., 0] | (c[..., 1] << 5) | (c[..., 2] << 10) | hi

def move_text(img):
    c, hi = split(img)
    out = c.copy()
    # fond estimé dans la bande : interpolation verticale entre la ligne au-dessus et au-dessous
    ya, yb = Y0 - 1, Y1 + DY
    for y in range(Y0, Y1 + DY):
        w = (y - ya) / (yb - ya)
        out[y, X0:X1] = c[ya, X0:X1] * (1 - w) + c[yb, X0:X1] * w
    bg_old = out.copy()
    # texte = écart entre l'original et le fond estimé à l'ancienne position
    delta = np.zeros_like(c)
    for y in range(Y0, Y1):
        w = (y - ya) / (yb - ya)
        delta[y, X0:X1] = c[y, X0:X1] - (c[ya, X0:X1] * (1 - w) + c[yb, X0:X1] * w)
    # on ne garde que les pixels nettement plus clairs que le fond (le texte rose pâle)
    mask = delta.sum(-1) > 6
    for y in range(Y0, Y1):
        m = mask[y, X0:X1]
        out[y + DY, X0:X1][m] = bg_old[y + DY, X0:X1][m] + delta[y, X0:X1][m]
    return join(out, hi)

def main():
    lba, size = find(TRACK, 'VIGNET/FD01SATP.BIT')
    assert size == 163840
    f = open(TRACK, 'r+b')
    secs = []
    for i in range(size // 2048):
        f.seek((lba + i) * 2352); secs.append(bytearray(f.read(2352)))
    raw = b''.join(bytes(s[16:2064]) for s in secs)
    img = decode(raw)
    assert encode(img) == raw
    new = move_text(img)
    if PREVIEW:
        from PIL import Image
        def rgb(i):
            c, _ = split(i); return (c * 8).astype(np.uint8)
        a = rgb(img)[0:40, 90:230]; b = rgb(new)[0:40, 90:230]
        Image.fromarray(np.vstack([a, np.zeros((4, 140, 3), np.uint8), b])).resize((560, 336), Image.NEAREST).save(PREVIEW)
    nraw = encode(new)
    n = 0
    for i, s in enumerate(secs):
        chunk = nraw[i * 2048:(i + 1) * 2048]
        if chunk != bytes(s[16:2064]):
            s[16:2064] = chunk; fix(s); f.seek((lba + i) * 2352); f.write(s); n += 1
    print('copyright descendu de %d lignes, %d secteurs réécrits (LBA %d)' % (DY, n, lba))

main()
