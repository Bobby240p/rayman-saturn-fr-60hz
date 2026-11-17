"""Création / application de patch BPS (format beat, compatible Floating IPS / ROM Patcher JS).
usage : python -I mkbps.py create <source> <cible> <patch.bps>
        python -I mkbps.py apply  <source> <patch.bps> <sortie>"""
import sys, os, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))

def venc(n):
    out = bytearray()
    while True:
        x = n & 0x7f; n >>= 7
        if n == 0: out.append(0x80 | x); return bytes(out)
        out.append(x); n -= 1

def vdec(b, p):
    data, shift = 0, 1
    while True:
        x = b[p]; p += 1
        data += (x & 0x7f) * shift
        if x & 0x80: return data, p
        shift <<= 7; data += shift

def create(src, dst, out):
    import numpy as np
    s = open(src, 'rb').read(); t = open(dst, 'rb').read()
    n = min(len(s), len(t))                         # au-delà de la source : données lues dans le patch
    a = np.frombuffer(s, np.uint8)[:n]; b = np.frombuffer(t, np.uint8)[:n]
    diff = np.flatnonzero(a != b)
    if len(t) > n: diff = np.concatenate([diff, np.arange(n, len(t))])
    # regroupe les octets modifiés en plages (fusion si écart < 8)
    ranges = []
    for i in diff.tolist():
        if ranges and i - ranges[-1][1] < 8: ranges[-1][1] = i + 1
        else: ranges.append([i, i + 1])
    p = bytearray(b'BPS1') + venc(len(s)) + venc(len(t)) + venc(0)
    pos = 0
    for lo, hi in ranges:
        if lo > pos: p += venc(((lo - pos - 1) << 2) | 0)          # SourceRead
        p += venc(((hi - lo - 1) << 2) | 1) + t[lo:hi]             # TargetRead
        pos = hi
    if pos < len(t): p += venc(((len(t) - pos - 1) << 2) | 0)
    p += zlib.crc32(s).to_bytes(4, 'little') + zlib.crc32(t).to_bytes(4, 'little')
    p += zlib.crc32(p).to_bytes(4, 'little')
    open(out, 'wb').write(p)
    print('patch %s : %d octets, %d plages, %d octets modifiés' % (out, len(p), len(ranges), len(diff)))

def apply(src, patch, out):
    s = open(src, 'rb').read(); p = open(patch, 'rb').read()
    assert p[:4] == b'BPS1' and zlib.crc32(p[:-4]) == int.from_bytes(p[-4:], 'little'), 'patch corrompu'
    i = 4; ss, i = vdec(p, i); ts, i = vdec(p, i); ms, i = vdec(p, i); i += ms
    assert zlib.crc32(s) == int.from_bytes(p[-12:-8], 'little'), 'fichier source différent de celui attendu'
    t = bytearray(ts); o = 0; sr = tr = 0
    while i < len(p) - 12:
        d, i = vdec(p, i); cmd, ln = d & 3, (d >> 2) + 1
        if cmd == 0: t[o:o + ln] = s[o:o + ln]
        elif cmd == 1: t[o:o + ln] = p[i:i + ln]; i += ln
        elif cmd == 2:
            d2, i = vdec(p, i); sr += (-1 if d2 & 1 else 1) * (d2 >> 1)
            t[o:o + ln] = s[sr:sr + ln]; sr += ln
        else:
            d2, i = vdec(p, i); tr += (-1 if d2 & 1 else 1) * (d2 >> 1)
            for k in range(ln): t[o + k] = t[tr]; tr += 1
        o += ln
    assert zlib.crc32(t) == int.from_bytes(p[-8:-4], 'little'), 'résultat incorrect'
    open(out, 'wb').write(t); print('ok :', out)

if __name__ == '__main__':
    {'create': create, 'apply': apply}[sys.argv[1]](*sys.argv[2:5])
