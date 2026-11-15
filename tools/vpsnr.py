"""PSNR moyen (RGB) d'une vidéo encodée par rapport à la source, sur une image sur N.
usage: python -I vpsnr.py <source> <encodée.cpk> [pas=10]"""
import sys, os, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
import numpy as np
FF = os.environ.get('FFMPEG', 'ffmpeg')
W, H = 320, 200

def frames(path):
    p = subprocess.run([FF, '-v', 'error', '-i', path, '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       capture_output=True, check=True).stdout
    return np.frombuffer(p, np.uint8).reshape(-1, H, W, 3)

src, enc = frames(sys.argv[1]), frames(sys.argv[2])
step = int(sys.argv[3]) if len(sys.argv) > 3 else 10
n = min(len(src), len(enc))
ps = []
for i in range(0, n, step):
    mse = np.mean((src[i].astype(float) - enc[i].astype(float)) ** 2)
    ps.append(99 if mse == 0 else 10 * np.log10(255 ** 2 / mse))
print('%s : PSNR moyen %.2f dB (min %.2f) sur %d images' % (os.path.basename(sys.argv[2]), np.mean(ps), np.min(ps), len(ps)))
