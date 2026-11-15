"""Phone-friendly audition site for the sfx pack: one page + every MP3 under ASCII paths (a/NN-MMM.mp3).

Usage: python3 make_site.py <out-dir>
Writes <out-dir>/index.html (template.html with the sound list filled in), copies every
MP3 of the pack unchanged to <out-dir>/a/, and writes batchN.json files that split the
audio into publish batches (at most 250 files and 55 MB each).
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import soundfile as sf  # noqa: E402
from build_index import NOTES, ROOT, dur  # noqa: E402

OUT = os.path.abspath(sys.argv[1])
os.makedirs(os.path.join(OUT, 'a'), exist_ok=True)
cats = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)) and d[:2].isdigit())
order = list(NOTES)
data, paths = [], []
for c in cats:
    files = sorted((f for f in os.listdir(os.path.join(ROOT, c)) if f.endswith('.mp3')),
                   key=lambda f: (order.index(f[:-4]) if f[:-4] in order else len(order), f))
    items = []
    for i, f in enumerate(files):
        src = os.path.join(ROOT, c, f)
        rel = f'a/{c[:2]}-{i:03d}.mp3'
        dst = os.path.join(OUT, rel)
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
            shutil.copyfile(src, dst)
        paths.append(rel)
        base = f[:-4]
        ogg = os.path.join(ROOT, c, base + '.ogg')
        it = dict(n=base, d=NOTES.get(base, ''), t=round(dur(src), 1), f=rel, l=os.path.exists(ogg))
        if it['l']:
            # exact loop length from the OGG (the MP3 carries encoder padding)
            info = sf.info(ogg)
            it['x'] = round(info.frames / info.samplerate, 5)
            it['t'] = round(it['x'], 1)
        items.append(it)
    data.append(dict(c=c[3:], k=c[:2], items=items))
total = sum(len(x['items']) for x in data)
page = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
page = page.replace('__TOTAL__', str(total))
page = page.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8', newline='\n').write(page)
# publish batches
batches, cur, size = [], [], 0
for rel in paths:
    s = os.path.getsize(os.path.join(OUT, rel))
    if cur and (size + s > 55e6 or len(cur) >= 250):
        batches.append(cur)
        cur, size = [], 0
    cur.append(rel)
    size += s
batches.append(cur)
for i, b in enumerate(batches):
    json.dump({p: os.path.join(OUT, p) for p in b}, open(os.path.join(OUT, f'batch{i}.json'), 'w'))
    print('batch', i, len(b), 'files', round(sum(os.path.getsize(os.path.join(OUT, p)) for p in b) / 1e6, 1), 'MB')
print(total, 'sounds;', [(x['c'], len(x['items'])) for x in data])
