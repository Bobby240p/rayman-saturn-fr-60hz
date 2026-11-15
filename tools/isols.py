"""Liste les fichiers d'une piste ISO 9660 (MODE1/2352 ou MODE2/2352 XA) : LBA, taille, chemin.
usage: python -I isols.py <piste.bin> [filtre]"""
import sys, struct

def walk(img, flt=''):
    f = open(img, 'rb')
    f.seek(16 * 2352 + 15); mode = f.read(1)[0]
    off = 16 if mode == 1 else 24          # MODE2 form1 : 8 octets de sous-en-tête
    def sec(n, c=1):
        d = b''
        for i in range(c):
            f.seek((n + i) * 2352 + off); d += f.read(2048)
        return d
    root = sec(16)[156:156 + 34]
    out = []
    def rec(lba, size, path):
        data = sec(lba, (size + 2047) // 2048); i = 0
        while i < len(data):
            l = data[i]
            if l == 0: i = (i // 2048 + 1) * 2048; continue
            e = data[i:i + l]; nm = e[33:33 + e[32]]
            if nm not in (b'\0', b'\1'):
                n = nm.decode('latin1').split(';')[0]; p = path + '/' + n
                elba, esz = struct.unpack('<I', e[2:6])[0], struct.unpack('<I', e[10:14])[0]
                if e[25] & 2: rec(elba, esz, p)
                elif flt.upper() in p.upper(): out.append((elba, esz, p))
            i += l
    rec(struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0], '')
    return out

if __name__ == '__main__':
    for lba, sz, p in walk(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ''):
        print(lba, sz, p)
