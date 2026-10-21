"""Diagnostics for the pause/ducking measurement on one video.

    python scripts/audio_diag.py <video_id>
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_xray as ax  # noqa: E402

vid = sys.argv[1]
words = ax.word_times(vid)
starts = [t for t, _ in words]
gaps = [b - a for a, b in zip(starts, starts[1:])]
g = np.array(gaps)
print("words", len(words), "| gap buckets:")
for lo, hi in [(0.2, 0.35), (0.35, 0.5), (0.5, 0.8), (0.8, 1.2), (1.2, 2), (2, 4), (4, 99)]:
    print(f"  {lo}-{hi}s: {int(((g >= lo) & (g < hi)).sum())}")

vdb, bed_db, step = ax.band_levels(vid)
n = min(len(vdb), len(bed_db))
print("bands: n =", n, "= ", round(n * step / 60, 1), "min")

# bed behaviour around speech onsets (ducking signature)
pre, post = [], []
for i in range(1, len(starts) - 1):
    if starts[i] - starts[i - 1] < 0.8:
        continue
    a = int((starts[i] - 0.6) / step)
    b = int((starts[i] - 0.1) / step)
    c = int((starts[i] + 0.15) / step)
    d = int((starts[i] + 0.65) / step)
    if a < 0 or d >= n:
        continue
    pre.append(float(np.median(bed_db[a:b])))
    post.append(float(np.median(bed_db[c:d])))
print(f"onsets measured: {len(pre)}")
if pre:
    print(f"  bed before onset: {np.median(pre):.1f} dB")
    print(f"  bed after  onset: {np.median(post):.1f} dB")
    print(f"  delta            : {np.median(post) - np.median(pre):+.1f} dB")
    print(f"  voice band before: {np.median([np.median(vdb[int((starts[i] - .6) / step):int((starts[i] - .1) / step)]) for i in range(1, min(len(starts), 200)) if starts[i] - starts[i-1] >= .8]):.1f} dB")

# music swell inside long gaps
swells = []
for i in range(len(starts) - 1):
    gap = starts[i + 1] - starts[i]
    if gap < 2.0:
        continue
    a = int((starts[i] + 0.3) / step)
    b = int((starts[i + 1] - 0.3) / step)
    if a < 0 or b >= n or b - a < 3:
        continue
    swells.append(float(np.median(bed_db[b - 5:b]) - np.median(bed_db[a:a + 5])))
print("long gaps (>=2s):", len(swells),
      "| median bed change across gap:", f"{np.median(swells):+.1f} dB" if swells else "n/a")
print("bed level overall median:", round(float(np.median(bed_db[:n])), 1), "dB",
      "| p90:", round(float(np.percentile(bed_db[:n], 90)), 1))
