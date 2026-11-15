"""Construit une vidéo Sega FILM (.CPK) organisée comme celles de Rayman Saturn (lecteur CPK.BIN) :
version 1.06, base de temps 600, Cinepak, son PCM 16 bits big-endian mono, 1er bloc audio de 0,5 s
puis un bloc de 0,25 s dès que l'avance du son sur l'image passe sous 0,37 s (comme AFR.CPK).

usage : python -I mkfilm.py <video_ffmpeg.cpk> <audio.raw> <taux_audio> <sortie.cpk> [duree_image=40] [canaux=1]
  duree_image en 1/600 s : 40 = 15 i/s (Saturn d'origine), 36 = 16,67 i/s (vidéo PS1)
  video_ffmpeg.cpk : Cinepak encodé par ffmpeg (-f film_cpk, sans son), on n'en garde que les images
  audio.raw        : PCM s16be (entrelacé si stéréo)"""
import sys, struct

def read_film(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'FILM'
    hl = struct.unpack('>I', d[4:8])[0]
    p = 16; fdsc = stab = None
    while p < hl:
        tag, ln = d[p:p + 4], struct.unpack('>I', d[p + 4:p + 8])[0]
        if tag == b'FDSC': fdsc = d[p:p + ln]
        if tag == b'STAB': stab = (p, ln)
        p += ln
    sp, sl = stab
    base, n = struct.unpack('>II', d[sp + 8:sp + 16])
    ents = [struct.unpack('>IIII', d[sp + 16 + 16 * k:sp + 32 + 16 * k]) for k in range(n)]
    frames = [d[hl + o:hl + o + s] for o, s, i1, i2 in ents if i1 != 0xFFFFFFFF]
    h, w = struct.unpack('>II', fdsc[12:20])
    return frames, w, h, base

def build(frames, w, h, audio, rate, out, dur=40, ch=1):
    """audio : PCM s16be entrelacé (ch canaux). En stéréo, chaque bloc FILM est planaire :
    tous les échantillons gauches puis tous les droits (format Sega FILM / ffmpeg pcm_s16be_planar)."""
    import array
    BASE = 600; DUR = dur; fps = BASE / DUR          # 40 -> 15 i/s, 36 -> 16,67 i/s
    nsamp = len(audio) // (2 * ch)
    chunks = []                                      # (données, info1, info2)
    spos = 0                                         # position en échantillons (par canal)
    def add_audio(n):
        nonlocal spos
        n = min(n - n % 2, nsamp - spos)                 # nb pair d'échantillons : blocs multiples de 4 octets
        if n <= 0: return
        raw = audio[spos * 2 * ch:(spos + n) * 2 * ch]
        if ch == 2:
            a = array.array('h', raw); a.byteswap()
            l, r = a[0::2], a[1::2]; l.byteswap(); r.byteswap()
            raw = l.tobytes() + r.tobytes()
        chunks.append((raw, 0xFFFFFFFF, 1)); spos += n
    add_audio(rate // 2)                             # 0,5 s d'avance
    quarter = 0
    for i, fr in enumerate(frames):
        t = i / fps
        while spos < nsamp and spos / rate - t < 0.37:
            quarter += 1                             # blocs de 0,25 s à l'échantillon près
            add_audio(int(round((0.5 + quarter * 0.25) * rate)) - spos)
        assert len(fr) % 4 == 0, 'image non alignée sur 4 octets'
        chunks.append((fr, (i * DUR) & 0x7FFFFFFF, DUR))   # bit 31 à 0 comme l'original
    while spos < nsamp: add_audio(rate // 4)
    n = len(chunks)
    hl = 16 + 32 + 16 + 16 * n
    hdr = bytearray(b'FILM' + struct.pack('>I', hl) + b'1.06' + bytes(4))
    hdr += b'FDSC' + struct.pack('>I', 32) + b'cvid' + struct.pack('>II', h, w)
    hdr += bytes([24, ch, 16, 0]) + struct.pack('>H', rate) + bytes(6)
    hdr += b'STAB' + struct.pack('>III', 16 + 16 * n, BASE, n)
    off = 0
    for c, i1, i2 in chunks:
        hdr += struct.pack('>IIII', off, len(c), i1, i2); off += len(c)
    assert len(hdr) == hl
    with open(out, 'wb') as f:
        f.write(hdr)
        for c, _, _ in chunks: f.write(c)
    na = sum(1 for c in chunks if c[1] == 0xFFFFFFFF)
    print('%s : %dx%d, %d images, %d blocs son, %d octets (%.1f s, %.0f Ko/s)' % (
        out, w, h, len(frames), na, hl + off, len(frames) / fps, (hl + off) / (len(frames) / fps) / 1024))
    return hl + off

if __name__ == '__main__':
    frames, w, h, _ = read_film(sys.argv[1])
    audio = open(sys.argv[2], 'rb').read()
    build(frames, w, h, audio, int(sys.argv[3]), sys.argv[4],
          int(sys.argv[5]) if len(sys.argv) > 5 else 40, int(sys.argv[6]) if len(sys.argv) > 6 else 1)
