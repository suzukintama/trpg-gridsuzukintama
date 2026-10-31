"""07 loop: on a train, with long, contentless English announcements / in-car radio.

Bed: a real CC0 train-interior recording (rec/amb/train_ride.ogg).
Voices: Kokoro TTS (Apache-2.0 model, output free to use). The model is not
stored in the repo; download it once:
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
and set KOKORO_DIR (default /home/user/models/kokoro).
"""
import os

import numpy as np
from scipy import signal

from dsp import SR, Gen, ns, lp, hp, bp, seamless, compress, make_ir, convolve
from master import export
from gen_rec import load

KOKORO_DIR = os.environ.get('KOKORO_DIR', '/home/user/models/kokoro')

PA, RADIO, RADIO2 = ('bf_emma', 'en-gb', 0.95), ('am_michael', 'en-us', 1.0), ('af_sarah', 'en-us', 1.0)

# Intentionally bland: nothing in here matters to the story.
SCRIPT = [
    (PA, "Good evening, and welcome aboard the Line Seven express service to Harbor District. "
         "This train will call at all stations except Old Market. "
         "Please keep your belongings with you, and offer your seat to anyone who may need it more than you do."),
    (PA, "The next station is Central Plaza. Doors will open on the left hand side. "
         "Please mind the gap between the train and the platform."),
    (RADIO, "And that's all from the city desk for now. Coming up after the break, a quick look at tomorrow's weather, "
            "which, as usual, looks a lot like today's weather. Mild, a little grey, "
            "with a chance of light rain in the evening. Nothing to worry about."),
    (RADIO, "This service is brought to you by the Metropolitan Transit Authority. Faster connections, cleaner carriages, "
            "and the same friendly schedule you have come to expect. Thank you for choosing to travel with us."),
    (PA, "For your safety, please do not lean against the doors. Smoking, vaping, and the use of unlicensed devices "
         "are not permitted anywhere on this train. Thank you for your cooperation."),
    (RADIO2, "Did you know that the average commuter spends nearly an hour a day in transit? "
             "That's plenty of time to relax, to catch up on your messages, or simply to watch the city go by. "
             "However you spend it, we hope your journey is a comfortable one."),
    (RADIO, "You're listening to City Line Radio. Stay tuned for more of the same, right after this."),
    (PA, "We are now approaching Central Plaza. Central Plaza. "
         "Please take all of your belongings with you when leaving the train. Thank you."),
]


def tts():
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(KOKORO_DIR, 'kokoro-v1.0.onnx'), os.path.join(KOKORO_DIR, 'voices-v1.0.bin'))
    out = []
    for (voice, lang, speed), text in SCRIPT:
        s, sr = k.create(text, voice=voice, speed=speed, lang=lang)
        s = signal.resample_poly(s, SR, sr)
        out.append((voice, s))
    return out


def speaker(y, kind):
    """Small ceiling speaker: band-limited, a touch compressed."""
    if kind == 'pa':
        y = bp(y, 320, 4200, 4)
    else:  # radio through the same speakers, slightly fuller
        y = bp(y, 220, 5500, 3)
    y = compress(y, -24, 3, 0.003, 0.12)
    return y / (np.max(np.abs(y)) + 1e-12)


def train_announcements():
    g = Gen(7801)
    lines = tts()
    # chime before each PA block: two soft recorded bongs
    bong = load('lav/ui_bong_001.ogg')
    bong = bong / np.max(np.abs(bong)) * 0.25
    parts, t = [], 6.0
    for (voice, s) in lines:
        kind = 'pa' if voice == PA[0] else 'radio'
        if kind == 'pa':
            parts.append((t, lp(bong, 3000)))
            parts.append((t + 0.45, lp(bong, 3000) * 0.8))
            t += 1.4
        parts.append((t, speaker(s, kind) * (0.5 if kind == 'pa' else 0.38)))
        t += len(s) / SR + g.u(3.5, 7.0)
    loop_len = float(np.ceil(t + 4.0))
    X = 4.0
    n = ns(loop_len + X)
    voice = np.zeros(n)
    for t0, a in parts:
        i = ns(t0)
        voice[i:i + len(a)] += a[:n - i]
    cabin = make_ir(g, rt60=0.45, predelay=0.003, early=[(g.u(0.003, 0.015), 0.3, 8000) for _ in range(6)],
                    lp_start=9000, lp_end=3000, tail_energy=0.35)
    vs = convolve(voice, cabin)[:n]
    # bed: real train interior, tiled with crossfades to the loop length
    bed = load('amb/train_ride.ogg', mono=False)
    bed = bed / np.sqrt(np.mean(bed ** 2))
    while len(bed) < n:
        k = ns(2.0)
        tt = np.linspace(0, 1, k)[:, None]
        src = load('amb/train_ride.ogg', mono=False)
        src = src / np.sqrt(np.mean(src ** 2))
        bed = np.concatenate([bed[:-k], bed[-k:] * np.cos(tt * np.pi / 2) + src[:k] * np.sin(tt * np.pi / 2), src[k:]])
    bed = bed[:n] * 0.1
    mix = bed + vs * 1.0
    export('07_環境音ループ/電車_車内放送', seamless(mix, loop_len, X), -20, loop=True, ogg=True)


if __name__ == '__main__':
    train_announcements()
