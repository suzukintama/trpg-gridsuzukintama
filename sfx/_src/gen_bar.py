"""07_環境音ループ: a bar in the lower district (2026-11-02, for free-roleplay scenes).

Three layers, all looping seamlessly over the same 96 s (32 bars at 80 bpm, so the music loops too):
  - the crowd: real bar chatter recordings without music (rec/bar/, CC0, see rec/bar/CREDITS.md),
    two different rooms layered left and right so it sounds busy and wide
  - the noise of the place: glasses, bottles, ice, a beer tap, chairs on concrete, pool balls,
    darts, an old till, bursts of laughter (also rec/bar/), scattered and placed in the room
  - the music: an original downtempo track synthesized here (FM electric piano, sub bass, dusty
    drums, a detuned lead, vinyl crackle) played through a cheap ceiling speaker into the room
Everything that rings past the end of the loop is wrapped round to its start, so there is no seam.
"""
import numpy as np

from dsp import SR, Gen, ns, lp, hp, bp, sat, compress, make_ir, convolve, crackle
from master import export, lufs
from gen_rec import load

BPM = 80
BEAT = 60.0 / BPM
BAR = BEAT * 4
BARS = 32
L = BAR * BARS            # 96 s
N = ns(L)
TAIL = 6.0


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def wrap_add(buf, x, t, gain=1.0):
    """Add x into the circular buffer buf (len N) at time t, wrapping past the end."""
    i = ns(t) % N
    if x.ndim == 1 and buf.ndim == 2:
        x = np.stack([x, x], 1)
    x = x * gain
    k = 0
    while k < len(x):
        m = min(len(x) - k, N - i)
        buf[i:i + m] += x[k:k + m]
        k += m
        i = 0


def circ_conv(x, ir):
    """Convolve a loop circularly (the reverb tail of the end lands on the start)."""
    y = convolve(np.concatenate([x, x[:ns(TAIL)]]), ir)
    out = y[:N].copy()
    rest = y[N:]
    k = 0
    while k < len(rest):
        m = min(len(rest) - k, N)
        out[:m] += rest[k:k + m]
        k += m
    return out


# ================================================================ the music
def epiano(f, dur, vel, g):
    """FM electric piano: 1:1 carrier/modulator for the body, a fast-decaying 14:1 tine on the attack."""
    n = ns(dur + 1.2)
    t = np.arange(n) / SR
    idx = (1.6 * np.exp(-t / 0.35) + 0.35) * (0.6 + 0.5 * vel)
    mod = np.sin(2 * np.pi * f * t + g.u(0, 6.28))
    tine = np.sin(2 * np.pi * f * 14.02 * t) * np.exp(-t / 0.018) * 0.9 * vel
    y = np.sin(2 * np.pi * f * t + idx * mod + tine)
    y += 0.25 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.4)          # a bit of the bark
    amp = np.exp(-t / (1.8 if f < 300 else 1.2)) * np.minimum(1, t / 0.002)
    rel = np.clip((dur + 0.25 - t) / 0.25, 0, 1)
    return y * amp * rel * vel


def saw(f, n, detune=0.0, g=None):
    ph = (np.arange(n) * f * (1 + detune) / SR + (g.u() if g else 0)) % 1.0
    return 2 * ph - 1


def music():
    g = Gen(8801)
    n = ns(L + TAIL)
    drums = np.zeros(n)
    bass = np.zeros(n)
    keys = np.zeros((n, 2))
    pad = np.zeros(n)
    lead = np.zeros(n)
    S16 = BEAT / 4

    def sw(i16):  # swung sixteenths
        return i16 * S16 + (0.035 * S16 * 4 if i16 % 2 else 0) / 2

    # 8-bar progression in A minor: Am9 | Am9 | Fmaj7 | Fmaj7 | Dm9 | Dm9 | E7#9 | E7#9
    prog = [(45, [57, 60, 64, 67, 71]), (45, [57, 60, 64, 67, 71]),
            (41, [57, 60, 64, 67]), (41, [55, 57, 60, 64]),
            (38, [53, 57, 60, 64]), (38, [53, 57, 62, 64]),
            (40, [56, 62, 67]), (40, [56, 59, 62, 67])]
    melody = [  # (bar in phrase, beat, beats, midi)
        (0, 0, 1.5, 76), (0, 1.5, 0.5, 74), (0, 2, 2, 72),
        (1, 0.5, 1, 71), (1, 1.5, 2.5, 69),
        (2, 0, 1, 72), (2, 1, 1, 76), (2, 2, 2, 79),
        (3, 0, 3, 76),
        (4, 0, 1.5, 77), (4, 1.5, 0.5, 76), (4, 2, 2, 74),
        (5, 0.5, 1, 72), (5, 1.5, 2.5, 69),
        (6, 0, 1, 68), (6, 1, 1, 71), (6, 2, 2, 74),
        (7, 0, 2, 76), (7, 2, 1.5, 74),
    ]
    # sections of 8 bars: A keys+bass+drums, B +lead, C break (pad, keys, half-time drums), D everything
    sect = ['A', 'B', 'C', 'D']

    # drum sounds
    tk = np.arange(ns(0.45)) / SR
    kick = np.sin(2 * np.pi * (48 * tk + 70 * (1 - np.exp(-tk * 30)) / 30)) * np.exp(-tk * 7)
    kick += hp(g.r.normal(0, 1, len(tk)), 2000, 2) * np.exp(-tk * 400) * 0.15
    ts = np.arange(ns(0.35)) / SR
    snare = (bp(g.r.normal(0, 1, len(ts)), 1200, 7000, 2) * np.exp(-ts * 16) * 0.8
             + np.sin(2 * np.pi * 185 * ts) * np.exp(-ts * 28) * 0.6)
    th = np.arange(ns(0.08)) / SR
    hat = hp(g.r.normal(0, 1, len(th)), 7000, 2) * np.exp(-th * 60)
    to = np.arange(ns(0.4)) / SR
    ohat = hp(g.r.normal(0, 1, len(to)), 6000, 2) * np.exp(-to * 9)
    tr = np.arange(ns(0.12)) / SR
    rim = (np.sin(2 * np.pi * 820 * tr) * 0.6 + bp(g.r.normal(0, 1, len(tr)), 1500, 5000, 2) * 0.5) * np.exp(-tr * 45)

    def hit(buf, x, t, v):
        i = ns(t + g.u(-0.003, 0.003))
        if 0 <= i < n:
            buf[i:i + len(x)] += x[:n - i] * v

    for bar in range(BARS):
        s = sect[bar // 8]
        pb = bar % 8
        t0 = bar * BAR
        root, chord = prog[pb]
        # ---- drums
        if s == 'C':
            hit(drums, kick, t0, 0.9)
            hit(drums, snare, t0 + 2 * BEAT, 0.7)
            for i16 in range(0, 16, 4):
                hit(drums, hat, t0 + sw(i16), 0.18)
        else:
            for i16 in (0, 7, 10):
                hit(drums, kick, t0 + sw(i16), 1.0 if i16 == 0 else 0.75)
            if pb == 7:
                hit(drums, kick, t0 + sw(14), 0.6)
            for i16 in (4, 12):
                hit(drums, snare, t0 + sw(i16), 0.85)
            hit(drums, snare, t0 + sw(15), 0.12)   # ghost
            for i16 in range(16):
                if i16 == 14 and pb % 2 == 1:
                    hit(drums, ohat, t0 + sw(i16), 0.22)
                elif i16 % 2 == 0:
                    hit(drums, hat, t0 + sw(i16), 0.32 if i16 % 4 == 0 else 0.24)
                elif g.u() < 0.5:
                    hit(drums, hat, t0 + sw(i16), 0.1)
            if pb % 4 == 3:
                hit(drums, rim, t0 + sw(13), 0.3)
        # ---- bass (sub sine + filtered saw)
        bpat = [(0, 3, 0), (3, 1, 0), (6, 2, 12), (10, 3, 0), (14, 2, 7 if pb % 2 else -2)]
        if s == 'C':
            bpat = [(0, 12, 0)]
        for i16, l16, iv in bpat:
            f = mtof(root + iv - 12 if root + iv > 50 else root + iv)
            d = l16 * S16
            m = ns(d + 0.08)
            tt = np.arange(m) / SR
            env = np.minimum(1, tt / 0.006) * np.clip((d + 0.06 - tt) / 0.06, 0, 1) * (0.75 + 0.25 * np.exp(-tt * 4))
            body = np.sin(2 * np.pi * f * tt) + 0.35 * lp(saw(f, m, 0, g), 300 + 900 * 0.5, 2)
            i = ns(t0 + sw(i16))
            bass[i:i + m] += (sat(body * 1.4, 1.0) * env)[:n - i]
        # ---- electric piano comping, a slow stereo tremolo like a suitcase amp
        hits = [(0, 1.6, 0.8), (2.5, 0.4, 0.5), (3.5, 0.5, 0.45)] if s != 'C' else [(0, 3.8, 0.7)]
        for b, d, v in hits:
            for j, mn in enumerate(chord):
                y = epiano(mtof(mn), d * BEAT, v * g.u(0.85, 1.0), g)
                i = ns(t0 + b * BEAT + j * 0.008 + g.u(0, 0.004))
                m = min(len(y), n - i)
                keys[i:i + m, 0] += y[:m]
                keys[i:i + m, 1] += y[:m]
        # ---- pad (break and last section)
        if s in ('C', 'D'):
            m = ns(BAR + 0.3)
            tt = np.arange(m) / SR
            p = np.zeros(m)
            for mn in chord[:4]:
                for dt in (-0.004, 0.0, 0.005):
                    p += saw(mtof(mn - 12 if mn > 62 else mn), m, dt, g)
            env = np.minimum(1, tt / 0.6) * np.clip((BAR + 0.3 - tt) / 0.6, 0, 1)
            i = ns(t0)
            pad[i:i + m] += (lp(p, 1100, 2) * env)[:n - i] * (0.6 if s == 'D' else 1.0)
        # ---- lead (B and D)
        if s in ('B', 'D'):
            for mb, b, d, mn in melody:
                if mb != pb:
                    continue
                f = mtof(mn)
                dd = d * BEAT
                m = ns(dd + 0.2)
                tt = np.arange(m) / SR
                vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * tt) * np.minimum(1, tt / 0.4)
                ph1 = np.cumsum(f * vib / SR)
                ph2 = np.cumsum(f * 1.006 * vib / SR)
                y = (2 * (ph1 % 1) - 1) + (2 * (ph2 % 1) - 1) + 0.5 * np.sin(2 * np.pi * ph1 / 2)
                env = np.minimum(1, tt / 0.03) * np.clip((dd + 0.15 - tt) / 0.15, 0, 1) * (0.8 + 0.2 * np.exp(-tt * 3))
                i = ns(t0 + b * BEAT)
                lead[i:i + m] += (lp(y, 2400, 2) * env)[:n - i]

    # delay on the lead: dotted-eighth echoes
    d = ns(BEAT * 0.75)
    echo = np.zeros(n)
    for k, a in enumerate((0.38, 0.2, 0.1), 1):
        echo[d * k:] += lp(lead, 1800, 1)[:n - d * k] * a
    # mix the band
    nrm = lambda x: x / (np.max(np.abs(x)) + 1e-12)
    drums = lp(compress(nrm(drums), -14, 3, 0.002, 0.08), 9000, 2)
    band = np.zeros((n, 2))
    band += np.stack([drums, drums], 1) * 0.55
    band += np.stack([bass, bass], 1) / (np.max(np.abs(bass)) + 1e-12) * 0.55
    keys = keys / (np.max(np.abs(keys)) + 1e-12)
    tt = np.arange(n) / SR
    trem = 0.5 + 0.5 * np.sin(2 * np.pi * 4.6 * tt)
    band[:, 0] += keys[:, 0] * (0.6 + 0.4 * trem) * 0.42
    band[:, 1] += keys[:, 1] * (0.6 + 0.4 * (1 - trem)) * 0.42
    band += np.stack([pad, pad], 1) / (np.max(np.abs(pad)) + 1e-12) * 0.16
    band[:, 0] += nrm(lead + echo) * 0.24
    band[:, 1] += nrm(lead + np.roll(echo, ns(0.012))) * 0.24
    # an old record: crackle and a dull top
    band += np.stack([crackle(g, n, 18, lo=1500, hi=9000)] * 2, 1) * 0.04
    band = lp(band, 11000, 2)
    # fold the part past the loop end back to the start (the song runs on round the loop)
    out = band[:N].copy()
    out[:n - N] += band[N:]
    return out


def speaker(x):
    """A cheap ceiling speaker: no real low end, a honky middle, a little breakup."""
    m = x.mean(axis=1)
    y = hp(lp(m, 6500, 2), 120, 2)
    y = y + bp(y, 700, 2200, 1) * 0.4
    y = sat(y * 1.5, 1.0)
    return y / (np.max(np.abs(y)) + 1e-12)


# ================================================================ the room
def rec(rel, mono=False):
    y = load(f'bar/{rel}', mono=mono)
    return y / (np.max(np.abs(y)) + 1e-12)


def stereo_of(y):
    return y if y.ndim == 2 else np.stack([y, y], 1)


def chain(parts, X):
    """Join recordings end to end with equal-power crossfades of X samples."""
    t = np.linspace(0, 1, X)[:, None]
    out = parts[0]
    for p in parts[1:]:
        out = np.concatenate([out[:-X], out[-X:] * np.cos(t * np.pi / 2) + p[:X] * np.sin(t * np.pi / 2), p[X:]])
    return out


def crowd_layer(rels, gain):
    """rels: [(file, start_s)], joined in order until there is enough for the loop."""
    X = ns(4.0)
    need = N + X
    parts = [stereo_of(rec(r))[ns(t0):] for r, t0 in rels]
    seg = chain(parts, X)
    while len(seg) < need:
        seg = chain([seg, parts[0]], X)
    seg = seg[:need].copy()
    t = np.linspace(0, 1, X)[:, None]
    out = seg[:N].copy()
    out[:X] = seg[:X] * np.sin(t * np.pi / 2) + seg[N:N + X] * np.cos(t * np.pi / 2)
    return out * gain


HOP = ns(0.01)


def env_db(y):
    m = y.mean(axis=1) if y.ndim == 2 else y
    k = len(m) // HOP
    r = np.sqrt(np.mean(m[:k * HOP].reshape(k, HOP) ** 2, axis=1))
    return 20 * np.log10(r + 1e-9)


def events_of(y, merge=0.12, rel_thr=26, abs_thr=10, min_len=0.05, max_len=4.0, tail=0.35):
    """Every stand-out event in a recording, cut clean (a few ms before the onset, a short tail, fades)."""
    db = env_db(y)
    floor, top = np.percentile(db, 10), np.max(db)
    thr = max(top - rel_thr, floor + abs_thr)
    act = db > thr
    out, i, k = [], 0, len(db)
    while i < k:
        if not act[i]:
            i += 1
            continue
        j = i
        while j < k and (act[j] or np.any(act[j:j + int(merge * 100)])):
            j += 1
        s, e = i * 0.01, j * 0.01
        if min_len <= e - s <= max_len:
            a, b = max(0, ns(s - 0.01)), min(len(y), ns(e + tail))
            x = stereo_of(y[a:b].copy())
            f = min(ns(tail), len(x) // 2)
            x[-f:] *= np.cos(np.linspace(0, np.pi / 2, f))[:, None] ** 2
            q = ns(0.003)
            x[:q] *= np.linspace(0, 1, q)[:, None]
            out.append(x)
        i = j
    return out


def window(y, t0, dur, fin=0.05, fout=0.4):
    x = stereo_of(y[ns(t0):ns(t0 + dur)].copy())
    a, b = ns(fin), ns(fout)
    x[:a] *= np.linspace(0, 1, a)[:, None]
    x[-b:] *= np.cos(np.linspace(0, np.pi / 2, b))[:, None] ** 2
    return x


def pan(x, p):
    x = stereo_of(x).copy()
    x[:, 0] *= np.sqrt((1 - p) / 2) * 1.414
    x[:, 1] *= np.sqrt((1 + p) / 2) * 1.414
    return x


def bar_noise():
    g = Gen(8802)
    buf = np.zeros((N, 2))
    pools = {
        'clink': sum((events_of(rec(f), max_len=1.5) for f in
                      ('glass-clink-wine.mp3', 'glass-clink-assorted.mp3', 'glass-wine-clink.mp3')), []),
        'bottle': sum((events_of(rec(f), max_len=1.5) for f in
                       ('bottle-empty-clank.mp3', 'bottle-clinking-1.mp3', 'bottle-clinking-2.mp3')), []),
        'handle': events_of(rec('glass-handling.mp3'), max_len=2.0) + events_of(rec('glass-slide-bar.mp3'), max_len=2.5)
        + events_of(rec('glass-pull-counter.mp3'), max_len=2.5),
        'ice': events_of(rec('ice-cubes-glass.mp3'), max_len=2.5, merge=0.3) + events_of(rec('ice-serving.mp3'), max_len=3, merge=0.3),
        'opener': events_of(rec('bottle-open-beer.mp3'), max_len=1.5) + events_of(rec('bottle-unseal-beer.mp3'), max_len=1.5),
        'chair': events_of(rec('chair-metal-concrete.mp3'), max_len=3, merge=0.25) + events_of(rec('chair-scrape-floor.mp3'), max_len=3, merge=0.25)
        + events_of(rec('chair-old-concrete.mp3'), max_len=3, merge=0.25),
        'pool': events_of(rec('pool-balls.mp3'), max_len=3, merge=0.4) + events_of(rec('pool-shots.mp3'), max_len=3, merge=0.4)
        + events_of(rec('pool-cue-table.mp3'), max_len=2),
        'dart': events_of(rec('darts-board.mp3'), max_len=1.0),
        'laugh': events_of(rec('laugh-group-medium.mp3'), min_len=0.8, max_len=5, merge=0.4)
        + events_of(rec('laugh-crowd.mp3'), min_len=0.8, max_len=5, merge=0.4)
        + events_of(rec('laugh-restaurant.mp3'), min_len=0.8, max_len=5, merge=0.4),
    }
    for k, v in pools.items():
        print(f'  {k:7s} {len(v)} events')
    # longer actions taken whole
    pour = [window(rec('pour-beer-tap.mp3'), 0.0, 6.0), window(rec('pour-beer-pint.mp3'), 0.0, 8.0)]
    till = [window(rec('till-old-register.mp3'), 0.0, 4.5), window(rec('till-drawer-receipt.mp3'), 0.0, 2.3)]
    stool = events_of(rec('stool-fall.mp3'), max_len=1.2)
    # (pool, count, gain range, distance 0 near .. 1 far)
    plan = [('clink', 26, (0.25, 0.55)), ('bottle', 16, (0.25, 0.5)), ('handle', 14, (0.2, 0.4)),
            ('ice', 6, (0.2, 0.35)), ('opener', 5, (0.25, 0.4)), ('chair', 9, (0.2, 0.4)),
            ('pool', 6, (0.2, 0.35)), ('dart', 7, (0.15, 0.3)), ('laugh', 7, (0.2, 0.35))]
    for name, count, (a, b) in plan:
        pool = pools[name]
        if not pool:
            continue
        for _ in range(count):
            x = pool[int(g.u(0, len(pool)))]
            wrap_add(buf, pan(x, g.u(-0.8, 0.8)), g.u(0, L), g.u(a, b))
    for x in pour:
        for _ in range(2):
            wrap_add(buf, pan(x, g.u(-0.3, 0.3)), g.u(0, L), g.u(0.15, 0.25))
    for x in till:
        wrap_add(buf, pan(x, g.u(0.3, 0.7)), g.u(0, L), 0.18)
    if stool:   # once a loop somebody knocks a stool over
        wrap_add(buf, pan(stool[0], -0.5), 61.0, 0.3)
    return buf


def bar():
    g = Gen(8803)
    # crowd: two rooms, one leaning left, one right, plus a third quieter one in the middle
    # (only recordings with no music in them; the song in this loop is our own)
    a = crowd_layer([('crowd-small-bar-loud.mp3', 8.0)], 1.0)
    b = crowd_layer([('crowd-belgrade-no-music.mp3', 0.0), ('crowd-indoors-no-music.mp3', 0.0)], 0.9)
    c = crowd_layer([('crowd-bar-loop.mp3', 0.0), ('crowd-thessaloniki-no-music.mp3', 0.0)], 0.7)
    crowd = np.zeros((N, 2))
    crowd[:, 0] += a.mean(1) * 0.85 + b.mean(1) * 0.35
    crowd[:, 1] += a.mean(1) * 0.35 + b.mean(1) * 0.85
    crowd += c * 0.6
    crowd /= np.max(np.abs(crowd)) + 1e-12
    noise = bar_noise()
    noise /= np.max(np.abs(noise)) + 1e-12
    # music: speaker in a low-ceilinged concrete room
    spk = speaker(music())
    ir_m = make_ir(g, rt60=0.9, predelay=0.012, lp_start=7000, lp_end=2200, tail_energy=0.6)
    wet = circ_conv(np.stack([spk, spk], 1), ir_m)
    mus = np.stack([spk, spk], 1) * 0.45 + wet / (np.max(np.abs(wet)) + 1e-12) * 0.75
    # the clatter gets a smaller, shorter room so it sits in the same space without washing out
    ir_n = make_ir(g, rt60=0.6, predelay=0.006, lp_start=9000, lp_end=3000, tail_energy=0.3)
    noise = noise * 0.8 + circ_conv(noise, ir_n) * 0.25
    # levels by loudness, relative to the crowd: the song clearly there a little under the talk,
    # the clatter sparse but heard (its peaks stand out well above its average)
    def at(x, db):
        return x * 10 ** ((db - lufs(x)) / 20)
    # 2026-11-02 GM: the song up front, the crowd and clatter pushed back
    mus = at(mus, -20.0)
    mix = at(crowd, -25.5) + mus + at(noise, -29.0)
    export('07_環境音ループ/下層のバー', mix, -20, loop=True, ogg=True, note='96s loop: crowd + clatter + an original downtempo song')
    # the song on its own, for the VTT when the crowd is not wanted
    export('07_環境音ループ/下層のバー_曲だけ', mus, -20, loop=True, ogg=True, note='96s loop: the bar song through the speaker')


if __name__ == '__main__':
    bar()
