"""Mini-assembleur SH-2 (sous-ensemble) à deux passes, pour les routines du patch.
Syntaxe : liste de tuples ; ('label', nom) ; ('long', valeur) aligne sur 4 ; ('align4',).
Instructions : voir ENC ci-dessous. Les opérandes de branchement sont des noms de label."""

def r(n): return int(n[1:]) if isinstance(n, str) else n

def assemble(prog, base, ext=None):
    labels_final = dict(ext or {})
    for _pass in range(2):
        labels = dict(ext or {}) if _pass == 0 else labels_final
        pc = base; out = []; fix = []
        for ins in prog:
            op = ins[0]
            if op == 'label':
                labels[ins[1]] = pc; continue
            if op == 'align4':
                if pc & 2: out.append(0x0009); pc += 2
                continue
            if op == 'long':
                assert pc % 4 == 0, 'long non aligné'
                out += [(ins[1] >> 16) & 0xffff, ins[1] & 0xffff]; pc += 4; continue
            out.append(enc(ins, pc, labels if _pass else None)); pc += 2
        labels_final = labels
    return b''.join(w.to_bytes(2, 'big') for w in out), labels

def disp(target, pc, bits, scale, labels):
    if labels is None: return 0
    d = (labels[target] - (pc + 4)) // scale
    assert -(1 << (bits - 1)) <= d < (1 << (bits - 1)), ('branchement trop loin', target)
    return d & ((1 << bits) - 1)

def enc(i, pc, L):
    op, a = i[0], i[1:]
    if op == 'mov#':   return 0xE000 | r(a[1]) << 8 | (a[0] & 0xff)
    if op == 'add#':   return 0x7000 | r(a[1]) << 8 | (a[0] & 0xff)
    if op == 'mov':    return 0x6003 | r(a[1]) << 8 | r(a[0]) << 4
    if op == 'sub':    return 0x3008 | r(a[1]) << 8 | r(a[0]) << 4
    if op == 'add':    return 0x300C | r(a[1]) << 8 | r(a[0]) << 4
    if op == 'movl@':  return 0x6002 | r(a[1]) << 8 | r(a[0]) << 4          # mov.l @Rm,Rn
    if op == 'movw@':  return 0x6001 | r(a[1]) << 8 | r(a[0]) << 4          # mov.w @Rm,Rn
    if op == 'movl>@': return 0x2002 | r(a[1]) << 8 | r(a[0]) << 4          # mov.l Rm,@Rn
    if op == 'jsr':    return 0x400B | r(a[0]) << 8
    if op == 'jmp':    return 0x402B | r(a[0]) << 8
    if op == 'neg':    return 0x600B | r(a[1]) << 8 | r(a[0]) << 4
    if op == 'movb@':  return 0x6000 | r(a[1]) << 8 | r(a[0]) << 4          # mov.b @Rm,Rn
    if op == 'movb>@': return 0x2000 | r(a[1]) << 8 | r(a[0]) << 4          # mov.b Rm,@Rn
    if op == 'push':   return 0x2006 | r(a[1]) << 8 | r(a[0]) << 4          # mov.l Rm,@-Rn
    if op == 'pop':    return 0x6006 | r(a[1]) << 8 | r(a[0]) << 4          # mov.l @Rm+,Rn
    if op == 'mova':                                                       # mova @(lbl,PC),R0
        if L is None: return 0xC700
        t = L[a[0]]; d = (t - ((pc & ~3) + 4)) // 4
        assert t % 4 == 0 and 0 <= d < 256; return 0xC700 | d
    if op == 'movw@+': return 0x6005 | r(a[1]) << 8 | r(a[0]) << 4          # mov.w @Rm+,Rn
    if op == 'movw>@': return 0x2001 | r(a[1]) << 8 | r(a[0]) << 4          # mov.w Rm,@Rn
    if op == 'movw@d': assert a[0] % 2 == 0 and a[0] <= 30; return 0x8500 | r(a[1]) << 4 | a[0] // 2   # mov.w @(d,Rm),R0
    if op == 'movw>d': assert a[0] % 2 == 0 and a[0] <= 30; return 0x8100 | r(a[1]) << 4 | a[0] // 2   # mov.w R0,@(d,Rn)
    if op == 'movl@d': assert a[0] % 4 == 0 and a[0] <= 60; return 0x5000 | r(a[2]) << 8 | r(a[1]) << 4 | a[0] // 4  # mov.l @(d,Rm),Rn
    if op == 'movl>d': assert a[0] % 4 == 0 and a[0] <= 60; return 0x1000 | r(a[2]) << 8 | r(a[1]) << 4 | a[0] // 4  # mov.l Rm,@(d,Rn)
    if op == 'movlpc':                                                     # mov.l @(lbl,PC),Rn
        if L is None: return 0xD000
        t = L[a[0]]; d = (t - ((pc & ~3) + 4)) // 4
        assert t % 4 == 0 and 0 <= d < 256; return 0xD000 | r(a[1]) << 8 | d
    if op == 'tst#':   return 0xC800 | (a[0] & 0xff)                       # tst #imm,R0
    if op == 'and#':   return 0xC900 | (a[0] & 0xff)                       # and #imm,R0
    if op == 'tst':    return 0x2008 | r(a[1]) << 8 | r(a[0]) << 4
    if op == 'shll':   return 0x4000 | r(a[0]) << 8
    if op == 'shll2':  return 0x4008 | r(a[0]) << 8
    if op == 'shlr':   return 0x4001 | r(a[0]) << 8
    if op == 'shlr2':  return 0x4009 | r(a[0]) << 8
    if op == 'shlr8':  return 0x4019 | r(a[0]) << 8
    if op == 'dt':     return 0x4010 | r(a[0]) << 8
    if op == 'bt':     return 0x8900 | disp(a[0], pc, 8, 2, L)
    if op == 'bf':     return 0x8B00 | disp(a[0], pc, 8, 2, L)
    if op == 'bfs':    return 0x8F00 | disp(a[0], pc, 8, 2, L)
    if op == 'bra':    return 0xA000 | disp(a[0], pc, 12, 2, L)
    if op == 'bsr':    return 0xB000 | disp(a[0], pc, 12, 2, L)
    if op == 'stspr-': return 0x4022 | r(a[0]) << 8                        # sts.l pr,@-Rn
    if op == 'ldspr+': return 0x4026 | r(a[0]) << 8                        # lds.l @Rn+,pr
    if op == 'rts':    return 0x000B
    if op == 'nop':    return 0x0009
    raise ValueError(op)
