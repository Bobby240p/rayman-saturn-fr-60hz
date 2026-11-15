"""EDC/ECC des secteurs CD-ROM mode 1 (2352 octets) : fix(secteur) recalcule les deux."""
ecc_f = [0] * 256; ecc_b = [0] * 256; edc_lut = [0] * 256
for i in range(256):
    j = ((i << 1) ^ (0x11D if i & 0x80 else 0)) & 0xff
    ecc_f[i] = j; ecc_b[i ^ j] = i
    e = i
    for _ in range(8):
        e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    edc_lut[i] = e

def edc(buf):
    e = 0
    for b in buf:
        e = (e >> 8) ^ edc_lut[(e ^ b) & 0xff]
    return e

def ecc_block(sec, mc, nc, mm, inc, dest):
    size = mc * nc
    for major in range(mc):
        index = (major >> 1) * mm + (major & 1); a = b = 0
        for _ in range(nc):
            t = sec[0xC + index]; index += inc
            if index >= size: index -= size
            a ^= t; b ^= t; a = ecc_f[a]
        a = ecc_b[ecc_f[a] ^ b]
        sec[dest + major] = a; sec[dest + major + mc] = a ^ b

def fix(sec):
    sec[0x810:0x814] = edc(sec[0:0x810]).to_bytes(4, 'little')
    ecc_block(sec, 86, 24, 2, 86, 0x81C)
    ecc_block(sec, 52, 43, 86, 88, 0x8C8)

