"""Audio X-Ray for the six Mighty Monk films.

    python scripts/audio_xray.py [video_id ...]

For each film it measures, with FFmpeg + numpy and (for validation) Whisper:
  * narration speed  - words per minute, per-minute curve
  * pauses           - gaps between spoken words, the dramatic ones in particular
  * ducking          - how far the music bed drops under the voice, and when it is loud

Word timings come from the YouTube auto-caption word tags (the captions carry
inline `<00:00:01.439>` marks per word, so they are word-accurate); a
whisper.cpp pass over a 2 minute slice per film cross-checks the pace.
"""

import json
import os
import re
import statistics as st
import subprocess
import sys
import wave

import numpy as np

ROOT = r"C:\Users\anu15\Downloads\youtube"
ANA = os.path.join(ROOT, ".analysis")
SRC = os.path.join(ROOT, "footage", "source")
OUT = os.path.join(ROOT, "scenes", "audio-xray.json")
FFDIR = r"C:\Users\anu15\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
FFMPEG = os.path.join(FFDIR, "ffmpeg.exe")
WHISPER = os.path.join(ROOT, ".tools", "whisper", "Release", "whisper-cli.exe")
WMODEL = os.path.join(ROOT, ".tools", "whisper", "ggml-base.bin")

VIDEOS = ["5DTtkRhla3A", "mS9AO-gSfcM", "UDCSmo77FMA", "KhSFC1GNgNM", "-DVr8iA-1F0", "4gZiO9NjSmE"]


def run(cmd, cwd=None, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd, timeout=timeout)


# ----------------------------------------------------------------- word timings
def word_times(vid):
    """[(start, word)] from the caption's inline word timestamps."""
    path = None
    for cand in (f"{vid}.hi-orig.vtt", f"{vid}.hi.vtt"):
        p = os.path.join(SRC, cand)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            path = p
            break
    if not path:
        return []

    def to_sec(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    stamp = re.compile(r"<(\d{2}):(\d{2}):(\d{2})\.(\d{3})>")
    words = []
    cur = None
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.rstrip("\n")
        if "-->" in line:
            cur = None
            continue
        if "<" not in line:
            continue
        parts = stamp.split(line)
        # parts: [text, h, m, s, ms, text, h, m, s, ms, ...]
        for i in range(1, len(parts), 5):
            t = to_sec(parts[i], parts[i + 1], parts[i + 2], parts[i + 3])
            chunk = parts[i + 4] if i + 4 < len(parts) else ""
            chunk = re.sub(r"</?c>", "", chunk).strip()
            for w in chunk.split():
                if w:
                    words.append((round(t, 3), w))
    words.sort(key=lambda x: x[0])
    # de-duplicate repeats caused by the rolling caption window
    out = []
    for t, w in words:
        if out and out[-1][1] == w and abs(t - out[-1][0]) < 0.4:
            continue
        out.append((t, w))
    return out


# ----------------------------------------------------------------- audio bands
def band_levels(vid):
    """Per-100 ms RMS (dB) for voice band and for the bed (everything outside it)."""
    wav = os.path.join(ANA, vid, "audio.wav")
    cache = os.path.join(ANA, vid, "bands.json")
    if os.path.exists(cache):
        d = json.load(open(cache, encoding="utf-8"))
        if "air" in d:
            return (np.array(d["voice"]), np.array(d["bed"]),
                    np.array(d["air"]), 0.1)

    def decode(filt, out):
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", wav,
             "-af", filt, "-ac", "1", "-ar", "16000", "-f", "wav", out, "-y"])

    voice_wav = os.path.join(ANA, vid, "voice.wav")
    low_wav = os.path.join(ANA, vid, "low.wav")
    high_wav = os.path.join(ANA, vid, "high.wav")
    air_wav = os.path.join(ANA, vid, "air.wav")
    decode("highpass=f=250,lowpass=f=3500", voice_wav)
    decode("lowpass=f=250", low_wav)
    decode("highpass=f=3500", high_wav)
    # 4-8 kHz is where music cymbals/air live and Hindi speech has little energy,
    # so it is a cleaner probe for "is the music ducked under the voice?"
    decode("highpass=f=4000,lowpass=f=8000", air_wav)

    def load(p):
        with wave.open(p, "rb") as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        return sr, x.astype(np.float32) / 32768.0

    sr, v = load(voice_wav)
    _, l = load(low_wav)
    _, h = load(high_wav)
    _, a = load(air_wav)
    step = int(sr * 0.1)

    def rms_db(x):
        n = len(x) // step
        frames = x[:n * step].reshape(n, step)
        rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
        return 20 * np.log10(rms + 1e-9)

    vdb = rms_db(v)
    bed_db = 10 * np.log10(10 ** (rms_db(l) / 10) + 10 ** (rms_db(h) / 10) + 1e-12)
    air_db = rms_db(a)
    json.dump({"voice": vdb.tolist(), "bed": bed_db.tolist(), "air": air_db.tolist()},
              open(cache, "w"), default=float)
    for p in (voice_wav, low_wav, high_wav, air_wav):
        try:
            os.remove(p)
        except OSError:
            pass
    return vdb, bed_db, air_db, 0.1


def speech_mask(words, n, step=0.1):
    mask = np.zeros(n, dtype=bool)
    for i, (t, _) in enumerate(words):
        end = words[i + 1][0] if i + 1 < len(words) else t + 0.3
        a, b = int(t / step), int(min(end, t + 0.6) / step)
        mask[a:b + 1] = True
    return mask


def analyse(vid):
    doc = json.load(open(os.path.join(ANA, vid, "video.json"), encoding="utf-8"))
    duration = doc["meta"]["duration"]
    words = word_times(vid)
    vdb, bed_db, air_db, step = band_levels(vid)
    n = min(len(vdb), len(bed_db))

    starts = [t for t, _ in words]
    gaps = []
    for i in range(len(words) - 1):
        g = words[i + 1][0] - words[i][0]
        if g > 0.6:
            gaps.append({"at": round(words[i][0], 2), "length_s": round(g, 2),
                         "before": words[i][1]})
    speech_time = (starts[-1] - starts[0]) if len(starts) > 1 else 0

    mask = speech_mask(words, n, step)
    voiced = mask[:n]
    gap_mask = ~voiced
    voice_lvl = float(np.median(vdb[:n][voiced])) if voiced.any() else float("nan")

    # bed level under the voice vs in the gaps (long gaps only, so music has time to swell)
    long_gap = np.zeros(n, dtype=bool)
    for g in gaps:
        if g["length_s"] >= 0.8:
            a = int((g["at"] + 0.2) / step)
            b = int((g["at"] + g["length_s"] - 0.1) / step)
            long_gap[a:b] = True
    # exclude digital silence from the gap measurement
    long_gap &= bed_db[:n] > -55
    bed_under_voice = float(np.median(bed_db[:n][voiced])) if voiced.any() else float("nan")
    bed_in_gaps = float(np.median(bed_db[:n][long_gap])) if long_gap.any() else float("nan")
    air_under_voice = float(np.median(air_db[:n][voiced])) if voiced.any() else float("nan")
    air_in_gaps = float(np.median(air_db[:n][long_gap])) if long_gap.any() else float("nan")

    minutes = int(duration // 60) + 1
    timeline = []
    for m in range(minutes):
        a, b = int(m * 60 / step), int(min((m + 1) * 60, duration) / step)
        if b <= a or b > n:
            continue
        seg_v, seg_b, seg_m = vdb[a:b], bed_db[a:b], mask[a:b]
        timeline.append({
            "minute": m,
            "voice_db": round(float(np.median(seg_v[seg_m])), 1) if seg_m.any() else None,
            "bed_db": round(float(np.median(seg_b)), 1),
            "bed_in_gaps_db": round(float(np.median(seg_b[~seg_m])), 1) if (~seg_m).any() else None,
            "speech_pct": round(float(seg_m.mean()) * 100, 1),
        })

    minute_bed = [m["bed_db"] for m in timeline if m["bed_db"] is not None]
    loud_threshold = float(np.percentile(minute_bed, 90)) if minute_bed else 0.0
    loud_windows = []
    current = None
    for m in timeline:
        if m["bed_db"] is not None and m["bed_db"] >= loud_threshold:
            if current is None:
                current = {"from_s": m["minute"] * 60, "bed_db": m["bed_db"]}
            current["to_s"] = (m["minute"] + 1) * 60
            current["peak_bed_db"] = max(current.get("peak_bed_db", -999), m["bed_db"])
        elif current is not None:
            loud_windows.append(current)
            current = None
    if current is not None:
        loud_windows.append(current)

    wpm = (len(words) / (speech_time / 60)) if speech_time > 0 else 0
    per_minute = []
    for m in timeline:
        a, b = m["minute"] * 60, min((m["minute"] + 1) * 60, duration)
        cnt = sum(1 for t in starts if a <= t < b)
        per_minute.append({"minute": m["minute"], "words": cnt,
                           "wpm": round(cnt / ((b - a) / 60), 1)})

    pauses = [g["length_s"] for g in gaps]
    dramatic = sorted([g for g in gaps if g["length_s"] >= 1.5],
                      key=lambda g: -g["length_s"])[:12]

    # ducking, onset view: bed level just before vs just after a speech onset
    pre, post = [], []
    for i in range(1, len(starts) - 1):
        if starts[i] - starts[i - 1] < 0.8:
            continue
        a, b = int((starts[i] - 0.6) / step), int((starts[i] - 0.1) / step)
        c, d = int((starts[i] + 0.15) / step), int((starts[i] + 0.65) / step)
        if a < 0 or d >= n:
            continue
        pre.append(float(np.median(bed_db[a:b])))
        post.append(float(np.median(bed_db[c:d])))
    onset_delta = (float(np.median(post)) - float(np.median(pre))) if pre and post else None

    duck = bed_in_gaps - bed_under_voice
    air_duck = air_in_gaps - air_under_voice
    duck_verdict = ("no ducking: the bed sits at the same level whether the narrator is "
                    "speaking or silent (|delta| < 2 dB on both probes)"
                    if abs(duck) < 2 and abs(air_duck) < 2 else
                    "the bed moves between speech and silence; see the two probes")

    return {
        "video_id": vid,
        "title": doc["summary"]["title"],
        "duration_s": round(duration, 1),
        "narration": {
            "words": len(words),
            "speech_span_s": round(speech_time, 1),
            "wpm_speaking": round(wpm, 1),
            "wpm_gross": round(len(words) / (duration / 60), 1),
            "speech_pct_of_runtime": round(float(voiced.mean()) * 100, 1),
            "per_minute": per_minute,
        },
        "pauses": {
            "count": len(pauses),
            "median_s": round(float(np.median(pauses)), 2) if pauses else 0,
            "p90_s": round(float(np.percentile(pauses, 90)), 2) if pauses else 0,
            "max_s": round(max(pauses), 2) if pauses else 0,
            "per_minute": round(len(pauses) / (duration / 60), 2),
            "histogram": {
                "0.6-0.8s": sum(1 for p in pauses if p < 0.8),
                "0.8-1.2s": sum(1 for p in pauses if 0.8 <= p < 1.2),
                "1.2-2.0s": sum(1 for p in pauses if 1.2 <= p < 2.0),
                "2.0-3.0s": sum(1 for p in pauses if 2.0 <= p < 3.0),
                "3.0s+": sum(1 for p in pauses if p >= 3.0),
            },
            "dramatic_pauses": dramatic,
            "measurement_note": (
                "True acoustic pauses cannot be isolated here: the music bed fills the "
                "voice band, so an energy-based silence detector finds almost nothing. "
                "These gaps come from caption word onsets, which cover ~75-90% of the "
                "spoken words, so gaps of 0.6-1.0 s are partly caption artefacts. The "
                ">=1.5 s list (with timestamps) is the trustworthy part."
            ),
        },
        "ducking": {
            "voice_level_db": round(voice_lvl, 1),
            "bed_under_voice_db": round(bed_under_voice, 1),
            "bed_in_gaps_db": round(bed_in_gaps, 1),
            "duck_depth_db": round(duck, 1),
            "air_under_voice_db": round(air_under_voice, 1),
            "air_in_gaps_db": round(air_in_gaps, 1),
            "air_duck_db": round(air_duck, 1),
            "bed_onset_delta_db": round(onset_delta, 1) if onset_delta is not None else None,
            "onsets_measured": len(pre),
            "verdict": duck_verdict,
            "bed_loud_threshold_db": round(loud_threshold, 1),
            "loud_music_windows": loud_windows[:12],
            "minute_timeline": timeline,
        },
    }


def whisper_check(vid, words, wpm):
    """Whisper on a 2 minute slice, as an independent pace check."""
    out_json = os.path.join(ANA, vid, "whisper-check.json")
    if os.path.exists(out_json):
        return json.load(open(out_json, encoding="utf-8"))
    if not os.path.exists(WHISPER) or not os.path.exists(WMODEL):
        return {"available": False}
    doc = json.load(open(os.path.join(ANA, vid, "video.json"), encoding="utf-8"))
    dur = doc["meta"]["duration"]
    start = min(max(300, dur * 0.3), dur - 140)
    slice_wav = os.path.join(ANA, vid, "whisper-slice.wav")
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin",
         "-ss", f"{start:.1f}", "-t", "120", "-i", os.path.join(ANA, vid, "audio.wav"),
         "-ar", "16000", "-ac", "1", slice_wav, "-y"])
    base = os.path.join(ANA, vid, "whisper-out")
    run([WHISPER, "-m", WMODEL, "-f", slice_wav, "-l", "hi", "-t", "4",
         "-oj", "-of", base, "-np"], timeout=900)
    jpath = base + ".json"
    if not os.path.exists(jpath):
        return {"available": False}
    raw = open(jpath, "rb").read().decode("utf-8", errors="replace")
    j = json.loads(raw)
    segs = j.get("transcription", [])
    txt_words = sum(len(s.get("text", "").split()) for s in segs)
    span = (segs[-1]["offsets"]["to"] - segs[0]["offsets"]["from"]) / 1000 if segs else 0
    w_gaps = []
    for a, b in zip(segs, segs[1:]):
        gap = (b["offsets"]["from"] - a["offsets"]["to"]) / 1000
        if gap > 0.35:
            w_gaps.append(round(gap, 2))
    res = {
        "available": True,
        "model": "whisper.cpp ggml-base (int8), 4 threads",
        "slice_start_s": round(start, 1),
        "slice_len_s": 120,
        "segments": len(segs),
        "words": txt_words,
        "wpm_whisper": round(txt_words / (span / 60), 1) if span else None,
        "caption_wpm_speaking": wpm,
        "delta_wpm": round((txt_words / (span / 60)) - wpm, 1) if span else None,
        "whisper_pause_median_s": round(float(np.median(w_gaps)), 2) if w_gaps else None,
        "whisper_pauses_over_0_35s": len(w_gaps),
    }
    json.dump(res, open(out_json, "w", encoding="utf-8"), indent=1)
    for p in (slice_wav, jpath):
        try:
            os.remove(p)
        except OSError:
            pass
    return res


def main():
    vids = sys.argv[1:] or VIDEOS
    rows = []
    for vid in vids:
        print(f"analyzing {vid} ...", flush=True)
        r = analyse(vid)
        r["whisper_check"] = whisper_check(vid, None, r["narration"]["wpm_speaking"])
        print(f"  {vid}: {r['narration']['words']} words | "
              f"{r['narration']['wpm_speaking']} wpm | pauses {r['pauses']['count']} | "
              f"duck {r['ducking']['duck_depth_db']} dB | "
              f"whisper {r['whisper_check'].get('wpm_whisper')}", flush=True)
        rows.append(r)

    if len(rows) > 1:
        summary = {
            "wpm_speaking": [r["narration"]["wpm_speaking"] for r in rows],
            "wpm_gross": [r["narration"]["wpm_gross"] for r in rows],
            "words": [r["narration"]["words"] for r in rows],
            "pause_median_s": [r["pauses"]["median_s"] for r in rows],
            "pause_max_s": [r["pauses"]["max_s"] for r in rows],
            "pauses_per_min": [r["pauses"]["per_minute"] for r in rows],
            "duck_depth_db": [r["ducking"]["duck_depth_db"] for r in rows],
            "air_duck_db": [r["ducking"]["air_duck_db"] for r in rows],
            "speech_pct": [r["narration"]["speech_pct_of_runtime"] for r in rows],
        }
        summary["medians"] = {
            k: round(st.median(v), 2) for k, v in summary.items() if isinstance(v, list)
        }
        doc = {"method": {
            "audio": "ffmpeg band split per film: voice 250-3500 Hz, bed = <250 Hz + >3500 Hz, air = 4-8 kHz, 100 ms RMS",
            "word_timings": "YouTube auto-caption inline word timestamps (hi)",
            "pauses": "gaps between consecutive caption word onsets > 0.6 s (proxy: the continuous music bed makes acoustic silence detection unusable)",
            "ducking": "median bed/air level in speech gaps (>0.8 s) minus median under speech, plus bed level before vs after a speech onset",
            "whisper": "whisper.cpp ggml-base (int8), 120 s slice per film — independent speed check, not full-length transcription",
        }, "summary": summary, "videos": rows}
    else:
        doc = {"videos": rows}

    json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
