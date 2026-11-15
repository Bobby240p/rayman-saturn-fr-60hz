import sys,os,struct
img,out=sys.argv[1],sys.argv[2]
f=open(img,'rb')
def sec(n,c=1):
    d=b''
    for i in range(c):
        f.seek((n+i)*2352+16); d+=f.read(2048)
    return d
os.makedirs(out,exist_ok=True)
# boot header (IP) sector 0..15
open(os.path.join(out,'IP.BIN'),'wb').write(sec(0,16))
pvd=sec(16)
root=pvd[156:156+34]
def walk(lba,size,path):
    data=sec(lba,(size+2047)//2048);i=0
    while i<len(data):
        l=data[i]
        if l==0: i=(i//2048+1)*2048; continue
        e=data[i:i+l]; elba=struct.unpack('<I',e[2:6])[0]; esz=struct.unpack('<I',e[10:14])[0]
        fl=e[25]; nl=e[32]; name=e[33:33+nl]
        if name not in (b'\x00',b'\x01'):
            n=name.decode('latin1').split(';')[0]
            p=os.path.join(path,n)
            if fl&2: os.makedirs(p,exist_ok=True); walk(elba,esz,p)
            else:
                print(elba,esz,p)
                open(p,'wb').write(sec(elba,(esz+2047)//2048)[:esz])
        i+=l
walk(struct.unpack('<I',root[2:6])[0],struct.unpack('<I',root[10:14])[0],out)
