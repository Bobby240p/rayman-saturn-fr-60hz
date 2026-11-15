"""Rend des images Cinepak d'ffmpeg compatibles avec le décodeur Sega (CPK.BIN) :
les blocs 0x3200 (vecteurs V1 seuls) sont convertis en 0x3000 (V1/V4 avec drapeaux, tous à V1).
Format des images (variante Sega FILM) : en-tête 10 octets + 2 octets nuls, puis les bandes ;
le champ longueur de l'en-tête vaut taille_totale - 8, celui de chaque bande inclut son en-tête (12 octets)."""
import struct

def fix_frame(fr):
    flags, w, h, nstrips = fr[0], *struct.unpack('>HHH', fr[4:10])
    assert fr[10:12] == b'\0\0', 'variante Sega attendue'
    p = 12; strips = []
    for _ in range(nstrips):
        sid, slen = struct.unpack('>HH', fr[p:p + 4])
        y0, x0, y1, x1 = struct.unpack('>HHHH', fr[p + 4:p + 12])
        q = p + 12; chunks = []
        while q < p + slen:
            cid, clen = struct.unpack('>HH', fr[q:q + 4]); data = fr[q + 4:q + clen]
            if cid == 0x3200:                                   # V1 seul -> V1/V4, drapeaux à 0
                nblk = ((x1 - x0) // 4) * ((y1 - y0) // 4)
                assert len(data) >= nblk
                out = bytearray()
                for i in range(0, nblk, 32): out += b'\0\0\0\0' + data[i:i + 32]
                cid, data = 0x3000, bytes(out)
            chunks.append(struct.pack('>HH', cid, len(data) + 4) + data)
            q += clen
        body = b''.join(chunks)
        strips.append(struct.pack('>HH', sid, len(body) + 12) + fr[p + 4:p + 12] + body)
        p += slen
    body = b''.join(strips)
    body += bytes(-(12 + len(body)) % 4)                   # taille multiple de 4 (DMA du lecteur Sega)
    total = 12 + len(body)
    return bytes([flags]) + (total - 8).to_bytes(3, 'big') + fr[4:10] + b'\0\0' + body

def stats(frames):
    import collections
    c = collections.Counter()
    for fr in frames:
        p = 12
        for _ in range(struct.unpack('>H', fr[8:10])[0]):
            sid, slen = struct.unpack('>HH', fr[p:p + 4]); c['strip %04x' % sid] += 1
            q = p + 12
            while q < p + slen:
                cid, clen = struct.unpack('>HH', fr[q:q + 4]); c['chunk %04x' % cid] += 1; q += clen
            p += slen
    return dict(c)
