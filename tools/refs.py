"""usage: python -I refs.py <exe> <hexval>...  -> instructions loading those 32-bit literals"""
import sys
d=open(sys.argv[1],'rb').read(); B=0x06010000
T={int(x,16) for x in sys.argv[2:]}
lits={o for o in range(0,len(d)-3,4) if int.from_bytes(d[o:o+4],'big') in T}
for o in range(0,len(d)-1,2):
    w=int.from_bytes(d[o:o+2],'big')
    if w>>12==0xD and ((o+4)&~3)+(w&0xff)*4 in lits:
        t=((o+4)&~3)+(w&0xff)*4
        print(hex(B+o), hex(int.from_bytes(d[t:t+4],'big')))
