import json, os
D = 'C:/Users/owner/AppData/Local/Temp/claude/C--Users-owner-Documents-Claude-Projects--------------------claude-worktrees-trpg-sfx-cc0-recordings-97b95d/7a4c8991-ade2-4dad-bb53-3035ea52a7a5/scratchpad/sfxsite'
data = open(D + '/data.json', encoding='utf-8').read()
t = open(D + '/template.html', encoding='utf-8').read()
open(D + '/index.html', 'w', encoding='utf-8', newline='\n').write(t.replace('__DATA__', data.replace('</', '<\\/')))
# split the audio into publish batches under 55 MB each
files = sorted(os.listdir(D + '/a'))
batches, cur, size = [], [], 0
for f in files:
    s = os.path.getsize(D + '/a/' + f)
    if size + s > 55e6:
        batches.append(cur); cur, size = [], 0
    cur.append(f); size += s
batches.append(cur)
for i, b in enumerate(batches):
    json.dump({f'a/{f}': f'a/{f}' for f in b}, open(f'{D}/batch{i}.json', 'w'))
    print(i, len(b), b[0], b[-1])
