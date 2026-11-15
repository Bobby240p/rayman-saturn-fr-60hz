"""Remplace le contenu d'un fichier dans une piste ISO 9660 MODE1/2352, sans le déplacer.
Le nouveau fichier doit tenir dans les secteurs déjà alloués (jusqu'au fichier suivant).
Met à jour la taille dans l'entrée de répertoire (LE et BE) et recalcule EDC/ECC.
usage: python -I replace_file.py <piste01.bin> /VIDEOFR/AFR.CPK <nouveau_fichier>"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edc import fix
from isols import walk

def main(track, path, newfile, *sacrifice):
    """sacrifice : fichiers qui suivent immédiatement (ex. /VIDEOUK/AFINUK.CPK=/VIDEOFR/AFINFR.CPK) dont
    la place est réutilisée ; leur entrée est redirigée vers le fichier indiqué après '='."""
    data = open(newfile, 'rb').read()
    files = sorted(walk(track))
    i = next(k for k, (l, s, p) in enumerate(files) if p.upper() == path.upper())
    lba, size, _ = files[i]
    redirect = []
    for sv in sacrifice:
        victim, target = sv.split('=')
        vi = next(k for k, (l, s, p) in enumerate(files) if p.upper() == victim.upper())
        ti = next(k for k, (l, s, p) in enumerate(files) if p.upper() == target.upper())
        redirect.append((files[vi], files[ti]))
    taken = {f[0] for f, _ in redirect}
    nxt = min(l for l, s, p in files if l > lba and l not in taken)
    room = (nxt - lba) * 2048
    assert len(data) <= room, 'trop gros : %d > %d octets disponibles' % (len(data), room)
    f = open(track, 'r+b')
    nsec = (len(data) + 2047) // 2048
    for k in range((size + 2047) // 2048 if size > len(data) else nsec):
        f.seek((lba + k) * 2352); s = bytearray(f.read(2352))
        chunk = data[k * 2048:(k + 1) * 2048]
        s[16:2064] = chunk + bytes(2048 - len(chunk))
        fix(s); f.seek((lba + k) * 2352); f.write(s)
    f.seek(16 * 2352 + 16); pvd = f.read(2048)
    def sec(n): f.seek(n * 2352 + 16); return f.read(2048)
    def find_dir(lba0, sz0, parts, name):
        d = b''.join(sec(lba0 + k) for k in range((sz0 + 2047) // 2048)); p = 0
        while p < len(d):
            l = d[p]
            if l == 0: p = (p // 2048 + 1) * 2048; continue
            e = d[p:p + l]; nm = e[33:33 + e[32]].split(b';')[0]
            if parts and nm.upper() == parts[0].upper().encode() and e[25] & 2:
                return find_dir(struct.unpack('<I', e[2:6])[0], struct.unpack('<I', e[10:14])[0], parts[1:], name)
            if not parts and nm.upper() == name:
                return lba0 + p // 2048, p % 2048
            p += l
        raise SystemExit('entrée introuvable')
    root = pvd[156:190]
    def set_entry(fpath, old_lba, new_lba, new_size):
        parts = [x for x in fpath.split('/') if x]
        dsec, doff = find_dir(struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0],
                              parts[:-1], parts[-1].upper().encode())
        f.seek(dsec * 2352); s = bytearray(f.read(2352)); e = 16 + doff
        assert struct.unpack('<I', s[e + 2:e + 6])[0] == old_lba
        s[e + 2:e + 6] = struct.pack('<I', new_lba); s[e + 6:e + 10] = struct.pack('>I', new_lba)
        s[e + 10:e + 14] = struct.pack('<I', new_size); s[e + 14:e + 18] = struct.pack('>I', new_size)
        fix(s); f.seek(dsec * 2352); f.write(s)
    set_entry(path, lba, lba, len(data))
    sizes = {p.upper(): (l, s_) for l, s_, p in files}
    sizes[path.upper()] = (lba, len(data))
    for (vl, vs, vp), (tl, ts, tp) in redirect:
        nl, ns = sizes[tp.upper()]
        set_entry(vp, vl, nl, ns)
        print('  %s -> redirigé vers %s' % (vp, tp))
    f.flush(); f.close()
    print('%s remplacé : %d octets (place %d), LBA %d' % (path, len(data), room, lba))

if __name__ == '__main__':
    main(*sys.argv[1:])
