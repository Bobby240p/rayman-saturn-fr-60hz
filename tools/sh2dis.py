import sys,capstone
d=open(sys.argv[1],'rb').read(); base=0x06010000
a=int(sys.argv[2],16); n=int(sys.argv[3])
md=capstone.Cs(capstone.CS_ARCH_SH,capstone.CS_MODE_BIG_ENDIAN|capstone.CS_MODE_SH2)
off=a-base
for i in range(n):
    o=off+2*i; ins=list(md.disasm(d[o:o+2],base+o))
    ex=''
    w=int.from_bytes(d[o:o+2],'big')
    if (w>>12)==0xD: # mov.l @(disp,pc)
        t=((base+o+4)&~3)+(w&0xff)*4; ex=' ; =%08x'%int.from_bytes(d[t-base:t-base+4],'big')
    if (w>>12)==0x9:
        t=base+o+4+(w&0xff)*2; ex=' ; =%04x'%int.from_bytes(d[t-base:t-base+2],'big')
    print('%08x %04x %s %s%s'%(base+o,w,ins[0].mnemonic if ins else '?',ins[0].op_str if ins else '',ex))
