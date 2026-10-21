"""Measure one Mighty Monk video: shots, cards, text, audio. JSON out.

    python scripts/analyze_video.py <video_id>

Writes .analysis/<video_id>/video.json and caches every intermediate artefact in
the same folder, so re-runs only redo what is missing.
"""

import json
import os
import re
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

ROOT = r"C:\Users\anu15\Downloads\youtube"
ANA = os.path.join(ROOT, ".analysis")
SRC = os.path.join(ROOT, "footage", "source")
FFDIR = r"C:\Users\anu15\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
FFMPEG = os.path.join(FFDIR, "ffmpeg.exe")
FFPROBE = os.path.join(FFDIR, "ffprobe.exe")
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

MONTHS = ("january february march april may june july august september october "
          "november december jan feb mar apr jun jul aug sep sept oct nov dec")
DATE_RE = re.compile(r"\b(19\d{2}|20\d{2})\b", re.I)
MONTH_RE = re.compile(r"\b(" + "|".join(MONTHS.split()) + r")\b", re.I)


def run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd)


def vdir(vid):
    d = os.path.join(ANA, vid)
    os.makedirs(os.path.join(d, "frames"), exist_ok=True)
    return d


def source(vid):
    p = os.path.join(SRC, f"{vid}.mp4")
    if not os.path.exists(p):
        raise SystemExit(f"missing source video: {p}")
    return p


def probe(path):
    p = run([FFPROBE, "-v", "error", "-show_entries",
             "format=duration,size,bit_rate",
             "-show_entries", "stream=codec_type,width,height,r_frame_rate",
             "-of", "json", path])
    j = json.loads(p.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    return {
        "duration": float(j["format"]["duration"]),
        "size_bytes": int(j["format"]["size"]),
        "width": v["width"], "height": v["height"],
        "fps": round(float(num) / float(den), 3),
    }


def cuts(vid):
    d = vdir(vid)
    log = os.path.join(d, "cuts.txt")
    if not os.path.exists(log):
        r = run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin",
                 "-i", source(vid),
                 "-vf", f"scale=480:-2,select=gt(scene\\,0.24),metadata=print:file={os.path.relpath(log, ROOT).replace(chr(92), '/')}",
                 "-an", "-f", "null", "-"], cwd=ROOT)
        if not os.path.exists(log):
            raise SystemExit(f"scene detection failed: {r.stderr[-400:]}")
    out, t = [], None
    for line in open(log, encoding="utf-8", errors="replace"):
        line = line.strip()
        m = re.match(r"frame:\s*\d+\s+pts:\s*\d+\s+pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1)); continue
        m = re.match(r"lavfi\.scene_score=([\d.]+)", line)
        if m and t is not None:
            out.append((t, float(m.group(1)))); t = None
    return out


def build_shots(vid, cut_list, duration):
    picked, last = [], -10.0
    for t, s in cut_list:
        if t - last >= 0.4:
            picked.append((t, s)); last = t
    bounds = [0.0] + [t for t, _ in picked] + [duration]
    shots = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        shots.append({"index": i + 1, "start": round(a, 3), "end": round(b, 3),
                      "duration": round(b - a, 3),
                      "cut_score": round(picked[i - 1][1], 3) if i else None})
    return shots


def luma(vid, shots):
    """Brightness at 2 fps, YAVG only — enough to spot fades to/from black."""
    d = vdir(vid)
    log = os.path.join(d, "luma.txt")
    done = os.path.join(d, "luma.done")
    if not os.path.exists(done):
        if os.path.exists(log):
            os.remove(log)
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", source(vid),
             "-vf", ("fps=2,scale=160:-2,signalstats,"
                     "metadata=print:key=lavfi.signalstats.YAVG:file="
                     + os.path.relpath(log, ROOT).replace(chr(92), "/")),
             "-an", "-f", "null", "-"], cwd=ROOT)
        open(done, "w").close()
    pts, vals, t = [], [], None
    if os.path.exists(log):
        for line in open(log, encoding="utf-8", errors="replace"):
            m = re.match(r"frame:\s*\d+\s+pts:\s*\d+\s+pts_time:([\d.]+)", line)
            if m:
                t = float(m.group(1)); continue
            m = re.match(r"lavfi\.signalstats\.YAVG=([\d.]+)", line)
            if m and t is not None:
                pts.append(t); vals.append(float(m.group(1))); t = None
    pts, vals = np.array(pts), np.array(vals)
    for s in shots:
        if not len(pts):
            break
        m = (pts >= s["start"]) & (pts < s["end"])
        if not m.any():
            continue
        seg = vals[m]
        s["luma_mean"] = round(float(seg.mean()), 1)
        s["luma_start"] = round(float(seg[:max(3, len(seg) // 8)].mean()), 1)
        s["luma_end"] = round(float(seg[-max(3, len(seg) // 8):].mean()), 1)


def frames(vid, shots):
    """One still per shot at 45% of its length, seek-then-grab per shot."""
    fdir = os.path.join(vdir(vid), "frames")
    todo = [s for s in shots
            if not os.path.exists(os.path.join(fdir, f"{s['index']:03d}.jpg"))]
    for n, s in enumerate(todo):
        t = s["start"] + s["duration"] * 0.45
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin",
             "-ss", f"{t:.3f}", "-i", source(vid), "-frames:v", "1",
             "-vf", "scale=1280:-2", "-q:v", "2",
             os.path.join(fdir, f"{s['index']:03d}.jpg")])
        if n % 40 == 0:
            print(f"  frames {n}/{len(todo)}", flush=True)


def ocr_shot(vid, shots):
    d = os.path.join(vdir(vid), "frames")
    out = os.path.join(vdir(vid), "ocr.json")
    if os.path.exists(out):
        cached = json.load(open(out, encoding="utf-8"))
        # a cache written before frames finished must not be trusted
        if len(cached) >= len([f for f in os.listdir(d) if f.endswith(".jpg")]):
            return cached
    res = {}
    for s in shots:
        img = os.path.join(d, f"{s['index']:03d}.jpg")
        if not os.path.exists(img):
            continue
        p = run([TESSERACT, img, "stdout", "--psm", "6", "tsv"])
        chars, confs, ys, xs, words = 0, [], [], [], []
        for line in p.stdout.splitlines()[1:]:
            f = line.split("\t")
            if len(f) < 12 or f[0] != "5":
                continue
            txt = f[11].strip()
            if not txt:
                continue
            conf = float(f[10])
            chars += len(txt)
            confs.append(conf)
            ys.append((int(f[7]) + int(f[9]) / 2))
            xs.append(int(f[6]) + int(f[8]) / 2)
            words.append(txt)
        h = 1080 if not ys else max(ys) * 1.05
        res[str(s["index"])] = {
            "chars": chars,
            "mean_conf": round(float(np.mean(confs)), 1) if confs else 0.0,
            "y_frac": round(float(np.mean(ys)) / h, 3) if ys else None,
            "x_frac": round(float(np.mean(xs)) / 1920, 3) if xs else None,
            "text": " ".join(words)[:300],
        }
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return res


def audio(vid):
    d = vdir(vid)
    wav = os.path.join(d, "audio.wav")
    if not os.path.exists(wav):
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", source(vid),
             "-ac", "1", "-ar", "16000", "-f", "wav", wav])
    with wave.open(wav, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    hop, win = int(sr * 0.032), 1024
    n = (len(x) - win) // hop
    rms = np.zeros(n); flat = np.zeros(n); pitch = np.zeros(n)
    window = np.hanning(win).astype(np.float32)
    for i in range(n):
        seg = x[i * hop:i * hop + win] * window
        spec = np.abs(np.fft.rfft(seg)) ** 2 + 1e-12
        rms[i] = np.sqrt(np.mean(seg ** 2) + 1e-12)
        flat[i] = np.exp(np.mean(np.log(spec))) / np.mean(spec)
        # autocorrelation through the FFT is ~10x faster than np.correlate
        ac = np.fft.irfft(np.abs(np.fft.rfft(seg, n=2 * win)) ** 2)[:win]
        ac = ac / (ac[0] + 1e-9)
        lo, hi = int(sr / 350), int(sr / 70)
        pitch[i] = float(np.max(ac[lo:hi])) if hi < len(ac) else 0.0
    db = 20 * np.log10(rms + 1e-9)
    times = np.arange(n) * hop / sr
    floor = float(np.percentile(db, 12))
    voice = (db > floor + 9) & (pitch > 0.28) & (flat < 0.25)
    active = db > floor + 6

    def runs(mask, min_len=0.4):
        out, start = [], None
        for i, v in enumerate(mask):
            if v and start is None:
                start = times[i]
            elif not v and start is not None:
                if times[i] - start >= min_len:
                    out.append([round(start, 2), round(times[i], 2)])
                start = None
        if start is not None and times[-1] - start >= min_len:
            out.append([round(start, 2), round(times[-1], 2)])
        return out

    return {
        "duration": round(float(times[-1]), 2),
        "noise_floor_db": round(floor, 1),
        "voice_runs": runs(voice),
        "silent_runs": runs(~active, min_len=0.8),
        "active_pct": round(float(active.mean()) * 100, 1),
    }


def captions(vid):
    d = vdir(vid)
    out = os.path.join(d, "subs.json")
    if os.path.exists(out):
        return json.load(open(out, encoding="utf-8"))
    vtt = None
    for cand in (f"{vid}.hi-orig.vtt", f"{vid}.hi.vtt", f"{vid}.en.vtt"):
        p = os.path.join(SRC, cand)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            vtt = p; break
    if not vtt:
        json.dump([], open(out, "w", encoding="utf-8"))
        return []
    ts = r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
    blocks, cur = [], None
    for raw in open(vtt, encoding="utf-8", errors="replace"):
        line = raw.rstrip("\n")
        m = re.match(ts + r"\s*-->\s*" + ts, line)
        if m:
            g = [float(v) for v in m.groups()]
            cur = {"start": g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000,
                   "end": g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000, "lines": []}
            blocks.append(cur); continue
        if cur is not None:
            s = re.sub(r"<[^>]*>", "", line).strip()
            if s and not s.startswith(("WEBVTT", "Kind:", "Language:")):
                cur["lines"].append(s)
    segs = []
    for i, b in enumerate(blocks):
        if not b["lines"]:
            continue
        text = b["lines"][0]
        end = blocks[i + 1]["start"] if i + 1 < len(blocks) else b["end"] + 1.0
        if end <= b["start"]:
            end = b["start"] + 0.5
        seg = {"start": round(b["start"], 2), "end": round(end, 2), "text": text}
        if segs and segs[-1]["text"] == text:
            segs[-1]["end"] = seg["end"]
        else:
            segs.append(seg)
    json.dump(segs, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return segs


def classify(shots, ocr, segs, duration):
    def speech_at(t):
        return any(c["start"] - 0.1 <= t <= c["end"] + 0.1 for c in segs)

    for s in shots:
        o = ocr.get(str(s["index"]), {})
        chars = o.get("chars", 0)
        conf = o.get("mean_conf", 0.0)
        y = o.get("y_frac")
        text = o.get("text", "")
        luma_mean = s.get("luma_mean", 100)

        s["ocr_chars"] = chars
        s["ocr_conf"] = conf
        s["text_y_frac"] = y
        s["text_sample"] = text[:160]

        s["is_card"] = bool(chars >= 120 and conf >= 45) or bool(chars >= 60 and luma_mean >= 150)
        s["has_bottom_text"] = bool(chars >= 8 and y is not None and y >= 0.6)
        years = DATE_RE.findall(text)
        s["years"] = sorted(set(years))
        s["has_date"] = bool(years) or bool(MONTH_RE.search(text))
        s["voiceover"] = speech_at(s["start"] + s["duration"] / 2)

        ls, le, lm = s.get("luma_start"), s.get("luma_end"), luma_mean
        if s["index"] == 1:
            t = "fade_in_from_black" if (ls is not None and ls < 30) else "hard_cut"
        elif ls is not None and ls < 24 and lm > 45:
            t = "fade_in_from_black"
        elif le is not None and le < 24 and lm > 45:
            t = "fade_out_to_black"
        elif (s["cut_score"] or 0) >= 0.45:
            t = "hard_cut"
        else:
            t = "soft_cut"
        s["transition_in"] = {"type": t, "cut_score": s["cut_score"]}
    return shots


def summarise(vid, meta, shots, audio_data, segs):
    durs = np.array([s["duration"] for s in shots])
    cards = [s for s in shots if s["is_card"]]
    fast = [s for s in shots if s["duration"] <= 2]
    slow = [s for s in shots if s["duration"] >= 10]
    dated = [s for s in shots if s["has_date"]]
    bottom = [s for s in shots if s["has_bottom_text"] and not s["is_card"]]
    trans = {}
    for s in shots:
        trans[s["transition_in"]["type"]] = trans.get(s["transition_in"]["type"], 0) + 1

    total_speech = sum(c["end"] - c["start"] for c in segs)
    words = sum(len(re.findall(r"\S+", c["text"])) for c in segs)
    span = segs[-1]["end"] - segs[0]["start"] if len(segs) > 1 else 1

    card_gaps = []
    for a, b in zip(cards, cards[1:]):
        card_gaps.append(round(b["start"] - a["start"], 1))

    # where do the fast cuts sit in the runtime?
    fast_pos = [round((s["start"] + s["duration"] / 2) / meta["duration"], 3) for s in fast]

    return {
        "video_id": vid,
        "title": meta.get("title"),
        "url": meta.get("url"),
        "duration_s": round(meta["duration"], 1),
        "resolution": f'{meta["width"]}x{meta["height"]}',
        "fps": meta["fps"],
        "shots": {"count": len(shots),
                  "cuts_per_min": round((len(shots) - 1) / (meta["duration"] / 60), 2),
                  "median_s": round(float(np.median(durs)), 2),
                  "mean_s": round(float(durs.mean()), 2),
                  "min_s": round(float(durs.min()), 2),
                  "max_s": round(float(durs.max()), 2),
                  "first_shot_s": round(shots[0]["duration"], 1),
                  "last_shot_s": round(shots[-1]["duration"], 1)},
        "fast_cuts_0_2s": {"count": len(fast),
                           "pct": round(len(fast) / len(shots) * 100, 1),
                           "positions": fast_pos},
        "slow_holds_10s": {"count": len(slow),
                           "pct": round(len(slow) / len(shots) * 100, 1),
                           "median_s": round(float(np.median([s["duration"] for s in slow])), 1) if slow else 0},
        "news_cards": {"count": len(cards),
                       "pct_shots": round(len(cards) / len(shots) * 100, 1),
                       "pct_runtime": round(sum(s["duration"] for s in cards) / meta["duration"] * 100, 1),
                       "median_hold_s": round(float(np.median([s["duration"] for s in cards])), 1) if cards else 0,
                       "mean_gap_s": round(float(np.mean(card_gaps)), 1) if card_gaps else None,
                       "first_card_at_s": round(cards[0]["start"], 1) if cards else None},
        "text": {"shots_with_bottom_text": len(bottom),
                 "pct": round(len(bottom) / len(shots) * 100, 1),
                 "bottom_text_y_frac": round(float(np.median([s["text_y_frac"] for s in bottom])), 3) if bottom else None},
        "dates": {"shots_with_dates": len(dated),
                  "pct": round(len(dated) / len(shots) * 100, 1),
                  "year_tokens": sorted({y for s in dated for y in s["years"]})[:12]},
        "transitions": trans,
        "audio": {"voiceover_coverage_pct": round(min(100.0, total_speech / meta["duration"] * 100), 1),
                  "words_per_min": round(words / (span / 60), 1) if words else 0,
                  "words_total": words,
                  "active_audio_pct": audio_data["active_pct"],
                  "silent_runs": len(audio_data["silent_runs"]),
                  "longest_silence_s": round(max([b - a for a, b in audio_data["silent_runs"]] or [0]), 1),
                  "noise_floor_db": audio_data["noise_floor_db"]},
        "caption_source": "youtube auto captions (hi)" if segs else "none",
    }


def main():
    vid = sys.argv[1]
    d = vdir(vid)
    meta_path = os.path.join(d, "meta.json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
    else:
        meta = probe(source(vid))
        meta.update({"video_id": vid,
                     "url": f"https://youtu.be/{vid}",
                     "title": None})
        json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=1)

    cut_list = cuts(vid)
    shots = build_shots(vid, cut_list, meta["duration"])
    luma(vid, shots)
    frames(vid, shots)
    ocr = ocr_shot(vid, shots)
    segs = captions(vid)
    audio_data = audio(vid)
    shots = classify(shots, ocr, segs, meta["duration"])
    summary = summarise(vid, meta, shots, audio_data, segs)

    json.dump({"meta": meta, "summary": summary, "shots": shots},
              open(os.path.join(d, "video.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print(f"{vid}: {summary['shots']['count']} shots | median "
          f"{summary['shots']['median_s']}s | cards {summary['news_cards']['count']} | "
          f"dates {summary['dates']['shots_with_dates']} | "
          f"VO {summary['audio']['voiceover_coverage_pct']}% | "
          f"wpm {summary['audio']['words_per_min']}")


if __name__ == "__main__":
    main()
