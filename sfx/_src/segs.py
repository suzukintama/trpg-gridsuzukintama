"""Find shots / hits in long raw recordings (onset groups)."""
import numpy as np
from dsp import SR, ns


def onsets(y, rise_db=14.0, floor_db=-32.0, hop=0.004):
    m = y if y.ndim == 1 else np.max(np.abs(y), axis=1)
    h = ns(hop)
    fr = len(m) // h
    e = np.sqrt(np.mean(m[:fr * h].reshape(fr, h) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(e / e.max())
    look = int(0.03 / hop)
    out = []
    for i in range(look, fr):
        if db[i] > floor_db and db[i] - np.min(db[i - look:i]) > rise_db:
            if not out or (i - out[-1]) * hop > 0.04:
                out.append(i)
    return [i * hop for i in out]


def groups(times, gap=0.35):
    gs = []
    for t in times:
        if gs and t - gs[-1][-1] < gap:
            gs[-1].append(t)
        else:
            gs.append([t])
    return gs


def cut(y, t0, t1, pre=0.004, fade=0.08):
    a, b = max(0, ns(t0 - pre)), min(len(y), ns(t1))
    s = y[a:b].copy()
    k = min(ns(fade), len(s) // 3)
    w = np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    s[-k:] = (s[-k:].T * w).T
    k2 = min(ns(0.002), len(s) // 10)
    s[:k2] = (s[:k2].T * np.linspace(0, 1, k2)).T
    return s


def shots(y, gap=0.35, maxlen=4.0, **kw):
    """[(n_transients, segment)] for each shot/burst, each running until just before the next one."""
    gs = groups(onsets(y, **kw), gap)
    out = []
    for i, g in enumerate(gs):
        end = gs[i + 1][0] - 0.03 if i + 1 < len(gs) else len(y) / SR
        end = min(end, g[-1] + maxlen)
        out.append((len(g), g[0], cut(y, g[0], end)))
    return out
