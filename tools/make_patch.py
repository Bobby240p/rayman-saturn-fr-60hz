"""Builds the patch list FR PAL -> 240 lines (60 Hz) and applies it to a copy of Track 01.

Rules:
 - constant that depends on height (US=224 / FR=256): midpoint value  -> 240-line equivalent
 - constant that depends on timing (50 Hz compensation): US value (NTSC)
usage: python -I make_patch.py <scratch> <src_track01.bin> <dst_track01.bin>
"""
import sys, json, os

S, SRC, DST = sys.argv[1], sys.argv[2], sys.argv[3]
MODE = sys.argv[4] if len(sys.argv) > 4 else 'full'   # full | safe (display + timing only)
BASE = 0x06010000
EXE_LBA = 1816           # LBA of file "0" on the FR disc
fr = bytearray(open(os.path.join(S, 'fr/0'), 'rb').read())
rows = json.load(open(os.path.join(S, 'rows.json')))

def sgn(v, k):
    return v - 65536 if k == 'w' and v > 32767 else v

# ---------- 1. list: (FR instruction address, new value, reason)
patches = {}
def add(addr, new, why):
    patches[addr] = (new, why)

add(0x6010552, 1, 'SCL_SetDisplayMode: 256 lines -> 240 lines')

EXCL = set()
EXCL |= {0x603ae34}                                   # stack cluster
EXCL |= {a for a in range(0x6042de0, 0x6042e30)}      # stack offsets (not height)
for k, u, f, ua, fa, lit in rows:
    d = sgn(f, k) - sgn(u, k)
    if fa in EXCL:
        continue
    if d in (32, -32, 16) or (d == -16 and k == 'i7' and not (0x6042de0 <= fa < 0x6042e30)):
        add(fa, (sgn(u, k) + sgn(f, k)) // 2, 'height (US %d / FR %d)' % (sgn(u, k), sgn(f, k)))

# tile row counts: 15/17 -> 16 ; 14/16 -> 15 ; H/4 56/64 -> 60
for k, u, f, ua, fa, lit in rows:
    if (u, f) == (15, 17) and k == 'i7':
        add(fa, 16, 'tile rows (US 15 / FR 17)')
add(0x604027a, 15, 'tile rows (US 14 / FR 16)')
add(0x6038dde, 60, 'H/4 (US 56 / FR 64)')
add(0x6038de8, 60, 'H/4 -> r4 = 4*r5 = 240 (US 224 / FR 256)')

# sites not aligned automatically (checked by hand)
for a in (0x60414f4,):
    add(a, 240, 'height (US 224 / FR 256)')
for a in (0x6041522, 0x603761a, 0x6037ed2, 0x60380d2, 0x60385fe, 0x6036100):
    add(a, 239, 'height-1 (US 223 / FR 255)')
add(0x60360fe, 238, 'height-2 (FR 254)')
for a in (0x603a56e, 0x601b8aa, 0x601b952, 0x60345c2):
    add(a, 120, 'half height (US 112 / FR 128)')

# 50 Hz speed compensation -> NTSC (US) values
for k, u, f, ua, fa, lit in rows:
    if 0x60393e0 <= fa <= 0x6039710:
        add(fa, sgn(u, k), 'timing 50Hz->60Hz (US %d / FR %d)' % (sgn(u, k), sgn(f, k)))
add(0x603988c, 4, 'speed (US 4 / FR 6)')
add(0x6039cda, 20, 'timing (US 20 / FR 16)')
add(0x6039d24, 127, 'timing (US 129 / FR 104; max imm 127)')
add(0x6011f2c, 119, 'timing (US 119 / FR 99)')
add(0x6068712, 195, 'timing (US 195 / FR 159)')
add(0x6068884, 196, 'timing (US 196 / FR 160)')

if MODE.startswith('safe'):
    patches = {a: v for a, v in patches.items()
               if a == 0x6010552 or v[1].startswith(('timing', 'speed'))}

# ---------- 2. resolve to byte locations
def lit_targets(o):
    w = int.from_bytes(fr[o:o + 2], 'big')
    h = w >> 12
    if h == 0x9:
        return ('w', o + 4 + (w & 0xff) * 2)
    if h == 0xD:
        return ('l', ((o + 4) & ~3) + (w & 0xff) * 4)
    if h in (0xE, 0x7):
        return ('i', o + 1)
    raise ValueError('unsupported instruction at %x: %04x' % (BASE + o, w))

# literal -> instructions that reference it (to detect sharing)
refs = {}
for o in range(0, len(fr) - 1, 2):
    w = int.from_bytes(fr[o:o + 2], 'big')
    if w >> 12 == 0x9:
        refs.setdefault(o + 4 + (w & 0xff) * 2, []).append(o)

writes = {}   # offset -> (bytes, old, desc)
log = []
# literal locations that will be modified (must not serve as a retarget source)
refs_patched = set()
for addr in patches:
    o = addr - BASE
    w = int.from_bytes(fr[o:o + 2], 'big')
    if w >> 12 == 0x9:
        refs_patched.add(o + 4 + (w & 0xff) * 2)
for addr, (new, why) in sorted(patches.items()):
    o = addr - BASE
    kind, t = lit_targets(o)
    if kind == 'w':
        old = int.from_bytes(fr[t:t + 2], 'big')
        nb = (new & 0xffff).to_bytes(2, 'big')
        sharers = refs.get(t, [])
        bad = [hex(BASE + s) for s in sharers if (BASE + s) not in patches]
        PAD = {0x603a426: 0x603a5a2, 0x603a962: 0x603aa7a}   # alignment padding 0000, never referenced
        if bad and addr in PAD:
            p = PAD[addr] - BASE
            w = int.from_bytes(fr[o:o + 2], 'big')
            disp = (p - (o + 4)) // 2
            assert fr[p:p + 2] == b'\0\0' and p not in refs and 0 <= disp < 256 and (p - (o + 4)) % 2 == 0
            writes[p] = (nb, 0, why + ' (new literal in padding)')
            writes[o] = (((w & 0xFF00) | disp).to_bytes(2, 'big'), w, why + ' [retarget literal -> %x]' % (BASE + p))
            log.append('%08x  w    @%08x  new literal %s in padding, instruction retargeted   %s' % (addr, BASE + p, hex(new), why))
            continue
        if bad:
            # literal shared with an instruction that must keep the old value:
            # retarget this instruction to another halfword already equal to `new`
            # (mov.w only reads it), within reach of its 8-bit displacement.
            w = int.from_bytes(fr[o:o + 2], 'big')
            cand = None
            for disp in range(256):
                tt = o + 4 + disp * 2
                if fr[tt:tt + 2] == nb and tt not in writes and tt not in refs_patched:
                    cand = (disp, tt); break
            if cand is None:
                # otherwise: move the OTHER users to a halfword holding the old value
                oldb = fr[t:t + 2]
                for s in [x for x in sharers if (BASE + x) not in patches]:
                    ws = int.from_bytes(fr[s:s + 2], 'big'); c2 = None
                    for disp in range(256):
                        tt = s + 4 + disp * 2
                        if tt != t and fr[tt:tt + 2] == oldb and tt not in refs_patched:
                            c2 = (disp, tt); break
                    if c2 is None:
                        raise SystemExit('shared literal %x: no alternative' % (BASE + t))
                    writes[s] = (((ws & 0xFF00) | c2[0]).to_bytes(2, 'big'), ws,
                                 'keep %s [retarget literal -> %x]' % (hex(int.from_bytes(oldb, 'big')), BASE + c2[1]))
                    log.append('%08x  w    @%08x  retarget -> literal @%08x (=%s)   keeps its value' % (
                        BASE + s, BASE + t, BASE + c2[1], oldb.hex()))
                writes[t] = (nb, int.from_bytes(oldb, 'big'), why)
                log.append('%08x  w    @%08x  %6s -> %6s   %s' % (addr, BASE + t, hex(int.from_bytes(oldb, 'big')), hex(new), why))
                continue
            nw = ((w & 0xFF00) | cand[0]).to_bytes(2, 'big')
            writes[o] = (nw, w, why + ' [retarget literal -> %x]' % (BASE + cand[1]))
            log.append('%08x  w    @%08x  retarget -> literal @%08x (=%s)   %s' % (
                addr, BASE + t, BASE + cand[1], hex(new), why))
            continue
    elif kind == 'l':
        old = int.from_bytes(fr[t:t + 4], 'big')
        nb = (new & 0xffffffff).to_bytes(4, 'big')
    else:
        old = fr[t]
        if not -128 <= new <= 127:
            raise SystemExit('immediate out of range at %x' % addr)
        nb = bytes([new & 0xff])
    if t in writes and writes[t][0] != nb:
        raise SystemExit('conflict at %x' % (BASE + t))
    writes[t] = (nb, old, why)
    log.append('%08x  %-4s @%08x  %6s -> %6s   %s' % (addr, kind, BASE + t,
               hex(old), hex(int.from_bytes(nb, 'big')), why))

# ---------- centrage vertical de l'image PAL 256 lignes dans 240 lignes ('center')
# Deux décalages :
#   OFF_FIXE = 7  : écrans fixes (titre, menus, vignettes) ; contenu PAL utile = lignes 8..245
#   OFF_JEU  = 16 : en partie ; les niveaux PAL ont 32 lignes ajoutées en haut par rapport aux
#                   niveaux US -> afficher les lignes 16..255 = vue US + 16 lignes en haut
# La partie est détectée par un "signal de vie" : l'appel de la fonction d'interface 0x601798a
# (exécutée seulement en jeu) passe par le relais D qui met un octet à 3 ; la routine VBlank A
# le décrémente et choisit OFF_JEU tant qu'il est non nul.
RAW = []
OFF_FIXE, OFF_JEU = 7, 16
if 'center' in MODE:
    # interface de jeu (ancrée en haut, affichée seulement en jeu) : +OFF_JEU
    HUD = [(0x60179ba, 5), (0x60179c8, 5), (0x60179d6, 5), (0x60179e6, 5), (0x6017a46, 5), (0x6017a56, 5),
           (0x6017a08, 27), (0x6017a2c, 27),          # 0x601798a : icônes, chiffres, points de vie
           (0x60176fc, 5), (0x6017748, 14)]           # 0x60176c4 : objets d'interface spéciaux
    for a, v in HUD:
        o = a - BASE
        assert fr[o + 1] == v and fr[o] >> 4 == 0xE, hex(a)
        RAW.append((a + 1, v + OFF_JEU, 1, 'interface Y %d -> %d' % (v, v + OFF_JEU)))
    # langue : le jeu lit la langue du BIOS (0 EN, 1 DE, 2 FR ; autre -> EN ou menu).
    # On force 2 = français aux deux lectures (texte RAYFR.TXT, vidéos VIDEOFR).
    for a, old, new in ((0x60552c8, 0x6010, 0xE002),   # mov.b @r1,r0 -> mov #2,r0
                        (0x60122d6, 0x6810, 0xE802)):  # mov.b @r1,r8 -> mov #2,r8
        o = a - BASE
        assert int.from_bytes(fr[o:o + 2], 'big') == old, hex(a)
        RAW.append((a, new, 2, 'langue BIOS -> français forcé'))
    # "press start button" est codé en dur (anglais) dans l'exécutable, même en PAL d'origine ;
    # affiché centré (x=160) par 0x6019080 -> remplacé par "appuyez sur start"
    o = 0x601bea0 - BASE
    oldtxt = b'/press start button/\0\0'
    newtxt = b'/appuyez sur start/\0\0\0'
    assert fr[o:o + len(oldtxt)] == oldtxt and len(newtxt) == len(oldtxt)
    RAW.append((0x601bea0, int.from_bytes(newtxt, 'big'), len(newtxt), 'texte "appuyez sur start"'))
if 'center' in MODE:
    # Place libre : fonctions de bibliothèque jamais référencées (ni littéral, ni bsr/bra) :
    #   A 0x6080f96 (74 o)  B 0x6081e18 (68 o)  C 0x6082578 (84 o)  D 0x6087240 (32 o)
    # A (VBlank, remplace la copie shadow 0x060c11a0 -> VDP2+0x70) : copie, choisit OFF (r9),
    #   écrit -OFF dans le modèle de commande VDP1 "coordonnées locales" (0x6096d0a, recopié
    #   à chaque image par 0x6015f00), appelle B.
    # B : NBG2/NBG3 Y += OFF ; NBG1 puis NBG0 -> C.
    # C : un plan ; si défilement Y par ligne actif, la table LSTA avance de OFF lignes,
    #     sinon SCY += OFF.
    # D : relais de l'appel de l'interface (littéral 0x60139b0) : signal de vie puis saut.
    # Offsets bloc 0x70..0xAF : SCYIN0 +4, SCYIN1 +0x14, SCYN2 +0x22, SCYN3 +0x26, SCRCTL +0x2a,
    # LSTA0 +0x30, LSTA1 +0x34.  S = 0x060c11a0 (shadow) ; V = *(0x060a101c)+0x70 (r8 = &V).
    import sys as _s; _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sh2asm import assemble
    CAVES = {'A': (0x6080f96, 74), 'B': (0x6081e18, 68), 'C': (0x6082578, 84), 'D': (0x6087240, 32)}
    FLAG = 0x6087250                      # octet du signal de vie (dans D, aligné 4)
    TPL_YA = 0x6096d0a                    # Y du modèle "coordonnées locales"
    A = [('stspr-', 'r15'), ('push', 'r9', 'r15'),
         ('movlpc', 'LS', 'r5'), ('movl@', 'r8', 'r4'), ('add#', 112, 'r4'), ('mov#', 32, 'r6'),
         ('label', 'cp'), ('movw@+', 'r5', 'r2'), ('dt', 'r6'), ('movw>@', 'r2', 'r4'), ('bfs', 'cp'), ('add#', 2, 'r4'),
         ('movlpc', 'LF', 'r1'), ('movb@', 'r1', 'r0'), ('mov#', OFF_FIXE, 'r9'),
         ('tst', 'r0', 'r0'), ('bt', 'ng'), ('add#', -1, 'r0'), ('movb>@', 'r0', 'r1'), ('mov#', OFF_JEU, 'r9'),
         ('label', 'ng'), ('add#', -64, 'r5'), ('add#', -64, 'r4'),                 # r5=S r4=V
         ('movlpc', 'LB', 'r0'), ('jsr', 'r0'), ('nop',),
         ('pop', 'r15', 'r9'), ('ldspr+', 'r15'), ('rts',), ('nop',),
         ('align4',), ('label', 'LS'), ('long', 0x060C11A0), ('label', 'LF'), ('long', FLAG),
         ('label', 'LB'), ('long', CAVES['B'][0])]
    B = [('stspr-', 'r15'),
         ('mov', 'r5', 'r3'), ('add#', 16, 'r3'), ('mov', 'r4', 'r2'), ('add#', 16, 'r2'),   # S+16, V+16
         ('movw@d', 18, 'r3'), ('add', 'r9', 'r0'), ('movw>d', 18, 'r2'),             # SCYN2
         ('movw@d', 22, 'r3'), ('add', 'r9', 'r0'), ('movw>d', 22, 'r2'),             # SCYN3
         ('movw@d', 26, 'r3'), ('mov', 'r0', 'r6'), ('shlr8', 'r6'),                  # NBG1 : SCRCTL>>8
         ('mov', 'r3', 'r7'), ('add#', 36, 'r7'), ('mov', 'r2', 'r1'), ('add#', 36, 'r1'),  # LSTA1
         ('add#', 4, 'r3'), ('add#', 4, 'r2'),                                        # SCYIN1
         ('bsr', 'C'), ('nop',),
         ('movw@d', 22, 'r3'), ('mov', 'r0', 'r6'),                                   # NBG0 : SCRCTL
         ('add#', -16, 'r3'), ('add#', -16, 'r2'), ('add#', -4, 'r7'), ('add#', -4, 'r1'),
         ('bsr', 'C2'), ('nop',),                                                     # C2 = Y local VDP1 puis C
         ('ldspr+', 'r15'), ('rts',), ('nop',)]
    C = [('label', 'C'), ('mov', 'r6', 'r0'), ('tst#', 4), ('bf', 'noY'),
         ('movw@', 'r3', 'r0'), ('add', 'r9', 'r0'), ('movw>@', 'r0', 'r2'),          # SCY += OFF
         ('label', 'noY'), ('mov', 'r6', 'r0'), ('mov#', 0, 'r6'),
         ('tst#', 2), ('bt', 's1'), ('add#', 2, 'r6'),                               # X : 4 o = 2 unités
         ('label', 's1'), ('tst#', 4), ('bt', 's2'), ('add#', 2, 'r6'),              # Y
         ('label', 's2'), ('tst#', 8), ('bt', 's3'), ('add#', 2, 'r6'),              # zoom
         ('label', 's3'), ('mov#', 0, 'r5'), ('mov', 'r9', 'r4'),                    # r5 = unités x OFF
         ('label', 'm'), ('add', 'r6', 'r5'), ('dt', 'r4'), ('bf', 'm'),
         ('shlr2', 'r0'), ('shlr2', 'r0'), ('and#', 3),                              # intervalle 1/2/4/8
         ('label', 's4'), ('tst', 'r0', 'r0'), ('bt', 's5'), ('shlr', 'r5'), ('bra', 's4'), ('add#', -1, 'r0'),
         ('label', 's5'), ('movl@', 'r7', 'r0'), ('add', 'r5', 'r0'), ('rts',), ('movl>@', 'r0', 'r1'),
         # C2 : modèle VDP1 "coordonnées locales" Y = -OFF, puis traitement du plan (C)
         ('label', 'C2'), ('movlpc', 'LT', 'r4'), ('neg', 'r9', 'r5'), ('movw>@', 'r5', 'r4'),
         ('bra', 'C'), ('nop',),
         ('align4',), ('label', 'LT'), ('long', TPL_YA)]
    D = [('mova', 'LF'), ('mov#', 3, 'r1'), ('movb>@', 'r1', 'r0'),
         ('movlpc', 'LH', 'r1'), ('jmp', 'r1'), ('nop',),
         ('align4',), ('label', 'LH'), ('long', 0x0601798A), ('label', 'LF'), ('long', 0)]
    blobs = {}
    blobs['C'], lC = assemble(C, CAVES['C'][0])
    blobs['B'], _ = assemble(B, CAVES['B'][0], {'C': lC['C'], 'C2': lC['C2']})
    blobs['A'], _ = assemble(A, CAVES['A'][0])
    blobs['D'], lD = assemble(D, CAVES['D'][0])
    assert lD['LF'] == FLAG, hex(lD['LF'])
    for k, (addr, cap) in CAVES.items():
        assert len(blobs[k]) <= cap, (k, len(blobs[k]), cap)
        o = addr - BASE
        writes[o] = (blobs[k], int.from_bytes(fr[o:o + len(blobs[k])], 'big'), 'routine ' + k)
        log.append('%08x  code %d/%d octets   routine %s' % (addr, len(blobs[k]), cap, k))
    # modèle "coordonnées locales" : valeur initiale -OFF_FIXE (A la réécrit à chaque VBlank)
    RAW.append((TPL_YA, (-OFF_FIXE) & 0xffff, 2, 'VDP1 local coord Y initial -%d' % OFF_FIXE))
    # 2e modèle d'en-tête VDP1 (0x6097fd6) : liste spéciale 0x6036030 (images de chargement,
    # éclatement en morceaux), envoyée directement en VRAM -> coordonnées locales Y = -OFF_FIXE
    o = 0x6098004 - BASE
    assert fr[o - 0xe:o - 0xc].hex() == '000a' and fr[o:o + 2] == b'\0\0'
    RAW.append((0x6098004, (-OFF_FIXE) & 0xffff, 2, 'VDP1 local coord Y liste spéciale -%d' % OFF_FIXE))
    # appel VBlank : 0x607af26..0x607af2e  (mov.l lit,r5 ; mov.l @r8,r4 ; add #112,r4 ; jsr @r9 ; mov #64,r6)
    #      -> mov.l lit,r1 ; nop ; nop ; jsr @r1 ; nop    et le littéral 0x607af94 := A
    o = 0x607af26 - BASE
    assert fr[o:o + 10].hex() == 'd51b64827470490be640'
    writes[o] = (bytes.fromhex('d11b00090009410b0009'), 0, 'appel routine VDP2')
    o = 0x607af94 - BASE
    assert fr[o:o + 4].hex() == '060c11a0'
    writes[o] = (CAVES['A'][0].to_bytes(4, 'big'), 0x060c11a0, 'littéral -> routine A')
    # appel de l'interface : littéral 0x60139b0 (=0x0601798a, seul utilisateur 0x601388a) -> D
    o = 0x60139b0 - BASE
    assert fr[o:o + 4].hex() == '0601798a'
    writes[o] = (CAVES['D'][0].to_bytes(4, 'big'), 0x0601798a, 'littéral interface -> relais D')
    log.append('0607af26  VBlank -> A ; 060139b0 interface -> D')

for addr, val, size, why in RAW:
    o = addr - BASE
    old = int.from_bytes(fr[o:o + size], 'big')
    writes[o] = (val.to_bytes(size, 'big'), old, why)
    log.append('%08x  raw  %6s -> %6s   %s' % (addr, hex(old), hex(val), why))

touched = {off + i for off, (nb, _, _) in writes.items() for i in range(len(nb))}
for off, (nb, old, why) in writes.items():
    if 'retarget' in why:
        src = int(why.split('-> ')[-1].rstrip(']'), 16) - BASE
        if src in writes and 'padding' in writes[src][2]:
            continue
        assert not ({src, src + 1} & touched), 'retarget source modified'

# ---------- 3. EDC/ECC Mode 1
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

def ecc_block(sec, major_count, minor_count, major_mult, minor_inc, dest):
    src = 0xC
    size = major_count * minor_count
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = sec[src + index]
            index += minor_inc
            if index >= size:
                index -= size
            a ^= t; b ^= t; a = ecc_f[a]
        a = ecc_b[ecc_f[a] ^ b]
        sec[dest + major] = a
        sec[dest + major + major_count] = a ^ b

def fix_sector(sec):
    sec[0x810:0x814] = edc(sec[0:0x810]).to_bytes(4, 'little')
    sec[0x814:0x81C] = bytes(8)
    ecc_block(sec, 86, 24, 2, 86, 0x81C)
    ecc_block(sec, 52, 43, 86, 88, 0x8C8)

img = open(SRC, 'rb')
def read_sector(lba):
    img.seek(lba * 2352)
    return bytearray(img.read(2352))

# self-test: recalculating an untouched sector must give the same bytes
for lba in (16, EXE_LBA, EXE_LBA + 100):
    s = read_sector(lba); c = bytearray(s); fix_sector(c)
    assert c == s, 'EDC/ECC self-test failed at LBA %d' % lba
print('EDC/ECC self-test OK')

# ---------- 4. apply
by_sector = {}
for off, (nb, old, why) in writes.items():
    for i, b in enumerate(nb):
        fo = off + i
        by_sector.setdefault(EXE_LBA + fo // 2048, []).append((16 + fo % 2048, b, fr[fo]))

out = {}
for lba, lst in by_sector.items():
    s = read_sector(lba)
    for pos, b, orig in lst:
        assert s[pos] == orig, 'image differs from extracted exe at LBA %d' % lba
        s[pos] = b
    fix_sector(s)
    out[lba] = s

import shutil
shutil.copyfile(SRC, DST)
with open(DST, 'r+b') as f:
    for lba, s in out.items():
        f.seek(lba * 2352); f.write(s)

print('\n'.join(log))
print('\n%d patches, %d bytes, %d sectors rewritten' % (len(patches), sum(len(v[0]) for v in writes.values()), len(out)))
open(os.path.join(S, 'patch_log.txt'), 'w').write('\n'.join(log))
