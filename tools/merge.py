import sys, os, re, shutil
src_cue, out_dir, name = sys.argv[1], sys.argv[2], sys.argv[3]
src_dir = os.path.dirname(src_cue)
os.makedirs(out_dir, exist_ok=True)
def msf2f(s): m,s_,f = map(int,s.split(':')); return (m*60+s_)*75+f
def f2msf(n): return "%02d:%02d:%02d"%(n//4500,(n//75)%60,n%75)
out=[f'FILE "{name}.bin" BINARY']; base=0
with open(os.path.join(out_dir,name+".bin"),'wb') as o:
    cur=None
    for line in open(src_cue, encoding='utf-8', errors='replace'):
        line=line.rstrip()
        m=re.match(r'\s*FILE "(.+)" BINARY',line)
        if m:
            if cur: base += os.path.getsize(cur)//2352
            cur=os.path.join(src_dir,m.group(1))
            with open(cur,'rb') as f: shutil.copyfileobj(f,o,16<<20)
            continue
        m=re.match(r'(\s*INDEX \d+ )(\d+:\d+:\d+)',line)
        if m: out.append(m.group(1)+f2msf(base+msf2f(m.group(2)))); continue
        if line.strip(): out.append(line)
open(os.path.join(out_dir,name+".cue"),'w',newline='\r\n').write("\n".join(out)+"\n")
print("ok", os.path.getsize(os.path.join(out_dir,name+".bin")))
