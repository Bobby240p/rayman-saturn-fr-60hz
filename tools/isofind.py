"""Trouve un fichier dans l'ISO 9660 d'une piste MODE1/2352 : affiche LBA et taille.
usage: python -I isofind.py <track01.bin> VIGNET/FD01SATP.BIT"""
import sys, struct

def find(img, path):
    f = open(img, 'rb')
    def sec(n, c=1):
        d = b''
        for i in range(c):
            f.seek((n + i) * 2352 + 16); d += f.read(2048)
        return d
    root = sec(16)[156:156 + 34]
    lba, size = struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0]
    for part in path.upper().split('/'):
        data = sec(lba, (size + 2047) // 2048); i = 0; hit = None
        while i < len(data):
            l = data[i]
            if l == 0: i = (i // 2048 + 1) * 2048; continue
            e = data[i:i + l]; nm = e[33:33 + e[32]].decode('latin1').split(';')[0]
            if nm == part: hit = (struct.unpack('<I', e[2:6])[0], struct.unpack('<I', e[10:14])[0]); break
            i += l
        if not hit: raise SystemExit('introuvable: ' + part)
        lba, size = hit
    return lba, size

if __name__ == '__main__':
    print(*find(sys.argv[1], sys.argv[2]))
