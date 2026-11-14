"""Phone-friendly audition site for the sfx pack: one page + every MP3 under ASCII paths (a/NN-MMM.mp3)."""
import json, os, shutil, sys
sys.path.insert(0, 'C:/Users/owner/Documents/trpg-gridsuzukintama-sfx/sfx/_src')
from build_index import NOTES, ROOT, dur  # noqa: E402

OUT = 'C:/Users/owner/AppData/Local/Temp/claude/C--Users-owner-Documents-Claude-Projects--------------------claude-worktrees-trpg-sfx-cc0-recordings-97b95d/7a4c8991-ade2-4dad-bb53-3035ea52a7a5/scratchpad/sfxsite'
os.makedirs(OUT + '/a', exist_ok=True)
cats = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)) and d[:2].isdigit())
order = list(NOTES)
data = []
for c in cats:
    files = sorted((f for f in os.listdir(os.path.join(ROOT, c)) if f.endswith('.mp3')),
                   key=lambda f: (order.index(f[:-4]) if f[:-4] in order else len(order), f))
    items = []
    for i, f in enumerate(files):
        src = os.path.join(ROOT, c, f)
        rel = f'a/{c[:2]}-{i:03d}.mp3'
        if not os.path.exists(OUT + '/' + rel) or os.path.getsize(OUT + '/' + rel) != os.path.getsize(src):
            shutil.copyfile(src, OUT + '/' + rel)
        base = f[:-4]
        loop = os.path.exists(os.path.join(ROOT, c, base + '.ogg'))
        items.append(dict(n=base, d=NOTES.get(base, ''), t=round(dur(src), 1), f=rel, l=loop))
    data.append(dict(c=c[3:], k=c[:2], items=items))
json.dump(data, open(OUT + '/data.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(sum(len(x['items']) for x in data), 'sounds;', [(x['c'], len(x['items'])) for x in data])
