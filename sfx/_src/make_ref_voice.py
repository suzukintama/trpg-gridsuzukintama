"""Make a ~12 s reference clip of Kokoro's young male voice (am_puck) for Chatterbox to copy the timbre from.
The voice is synthetic (Kokoro), so no real person's voice is cloned.
Usage: python make_ref_voice.py <out.wav>
"""
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

KOKORO_DIR = os.environ.get('KOKORO_DIR', 'C:/Users/owner/Documents/models/kokoro')
k = Kokoro(os.path.join(KOKORO_DIR, 'kokoro-v1.0.onnx'), os.path.join(KOKORO_DIR, 'voices-v1.0.bin'))
text = ("Hey, what's up, night owls! You're tuned in to the late show. "
        "I've got coffee, I've got bad news, and I've got about four hours of records nobody asked for. "
        "So sit back, stay up, and don't touch that dial.")
s, sr = k.create(text, voice='am_puck', speed=1.0, lang='en-us')
sf.write(sys.argv[1], s / np.max(np.abs(s)) * 0.9, sr)
print(sys.argv[1], round(len(s) / sr, 1), 's')
