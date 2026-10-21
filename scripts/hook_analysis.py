"""Hook analysis: the first 30 seconds of every Mighty Monk film.

    python scripts/hook_analysis.py

Whisper transcribes the opening 30-35 s of each film (whisper.cpp), and the shot
list from .analysis/<id>/video.json gives the cutting rhythm inside the hook.
Contact sheets of the hook stills are written next to the per-film artefacts so
the on-screen content can be inspected frame by frame.
"""

import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = r"C:\Users\anu15\Downloads\youtube"
ANA = os.path.join(ROOT, ".analysis")
OUT = os.path.join(ROOT, "scenes", "hook-patterns.json")
FFDIR = r"C:\Users\anu15\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
FFMPEG = os.path.join(FFDIR, "ffmpeg.exe")
WHISPER = os.path.join(ROOT, ".tools", "whisper", "Release", "whisper-cli.exe")
WMODEL = os.path.join(ROOT, ".tools", "whisper", "ggml-base.bin")

VIDEOS = ["5DTtkRhla3A", "mS9AO-gSfcM", "UDCSmo77FMA", "KhSFC1GNgNM", "-DVr8iA-1F0", "4gZiO9NjSmE"]
HOOK_S = 30


def run(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def whisper_hook(vid):
    d = os.path.join(ANA, vid)
    out_json = os.path.join(d, "hook-whisper.json")
    if os.path.exists(out_json):
        raw = open(out_json, "rb").read().decode("utf-8", errors="replace")
        return json.loads(raw)
    wav = os.path.join(d, "hook-35s.wav")
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin",
         "-t", "35", "-i", os.path.join(d, "audio.wav"),
         "-ar", "16000", "-ac", "1", wav, "-y"])
    base = os.path.join(d, "hook-whisper")
    p = run([WHISPER, "-m", WMODEL, "-f", wav, "-l", "hi", "-t", "4",
             "-oj", "-of", base, "-np"], timeout=1200)
    jpath = base + ".json"
    if not os.path.exists(jpath):
        return {"available": False, "stderr": p.stderr[-300:]}
    raw = open(jpath, "rb").read().decode("utf-8", errors="replace")
    j = json.loads(raw)
    segs = [{"start": round(s["offsets"]["from"] / 1000, 2),
             "end": round(s["offsets"]["to"] / 1000, 2),
             "text": s["text"].strip()} for s in j.get("transcription", [])]
    res = {"available": True,
           "model": "whisper.cpp ggml-base (int8), 4 threads",
           "slice": "0-35 s",
           "segments": segs,
           "text": " ".join(s["text"] for s in segs).strip()}
    json.dump(res, open(out_json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for path in (wav, jpath):
        try:
            os.remove(path)
        except OSError:
            pass
    return res


def caption_hook(vid):
    """Caption words inside the hook window, for a second opinion on the text."""
    vtt = None
    for cand in (f"{vid}.hi-orig.vtt", f"{vid}.hi.vtt"):
        p = os.path.join(ROOT, "footage", "source", cand)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            vtt = p
            break
    if not vtt:
        return []
    stamp = re.compile(r"<(\d{2}):(\d{2}):(\d{2})\.(\d{3})>")

    def sec(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    words = []
    for raw in open(vtt, encoding="utf-8", errors="replace"):
        if "-->" in raw or "<" not in raw:
            continue
        parts = stamp.split(raw.rstrip("\n"))
        for i in range(1, len(parts), 5):
            t = sec(parts[i], parts[i + 1], parts[i + 2], parts[i + 3])
            if t > HOOK_S + 5:
                continue
            chunk = re.sub(r"</?c>", "", parts[i + 4] if i + 4 < len(parts) else "")
            for w in chunk.split():
                words.append((round(t, 2), w))
    words.sort(key=lambda x: x[0])
    return [w for w in words if w[0] <= HOOK_S]


def shots_in_hook(vid):
    doc = json.load(open(os.path.join(ANA, vid, "video.json"), encoding="utf-8"))
    shots = [s for s in doc["shots"] if s["start"] < HOOK_S]
    return doc, shots


def hook_sheet(vid, shots):
    d = os.path.join(ANA, vid)
    out = os.path.join(d, "hook-sheet.jpg")
    cols, tw, th = 4, 460, 258
    rows = (len(shots) + cols - 1) // cols or 1
    sheet = Image.new("RGB", (cols * tw, rows * (th + 26)), (10, 10, 12))
    draw = ImageDraw.Draw(sheet)
    for i, s in enumerate(shots):
        p = os.path.join(d, "frames", f"{s['index']:03d}.jpg")
        if not os.path.exists(p):
            continue
        img = Image.open(p).convert("RGB")
        img.thumbnail((tw, th))
        x = (i % cols) * tw
        y = (i // cols) * (th + 26)
        sheet.paste(img, (x + (tw - img.width) // 2, y))
        draw.text((x + 6, y + th + 5),
                  f"#{s['index']} {s['start']:.1f}-{s['end']:.1f}s ({s['duration']:.1f}s)",
                  fill=(220, 220, 225))
    sheet.save(out, quality=88)
    return out


def deepseek_split(text, max_chars=90):
    """Rough first-sentence: cut on the first sentence end or a comma if long."""
    t = re.sub(r"\s+", " ", text).strip()
    for sep in ("।", "?", "!"):
        i = t.find(sep)
        if 12 <= i <= max_chars:
            return t[:i + 1]
    return t[:max_chars].strip() + ("…" if len(t) > max_chars else "")


def main():
    rows = []
    for vid in VIDEOS:
        print(f"hook: {vid}", flush=True)
        doc, shots = shots_in_hook(vid)
        wh = whisper_hook(vid)
        words = caption_hook(vid)
        sheet = hook_sheet(vid, shots)
        first = deepseek_split(wh.get("text", ""))
        dur_first = shots[0]["duration"] if shots else 0
        rows.append({
            "video_id": vid,
            "title": doc["summary"]["title"],
            "hook_window_s": HOOK_S,
            "transcript_whisper": wh,
            "transcript_caption_words": [w for _, w in words][:80],
            "first_sentence": {
                "text": first,
                "spoken_until_s": shots[0]["end"] if shots else None,
            },
            "shots_in_hook": {
                "count": len(shots),
                "cuts_per_min_in_hook": len(shots),
                "first_shot_s": round(dur_first, 2),
                "list": [{"index": s["index"], "start": s["start"], "end": s["end"],
                          "duration": s["duration"]} for s in shots],
                "median_shot_s": round(float(np.median([s["duration"] for s in shots])), 2) if shots else 0,
            },
            "hook_sheet": os.path.relpath(sheet, ROOT).replace("\\", "/"),
        })
    json.dump({"hook_window_s": HOOK_S, "videos": rows},
              open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", OUT)
    for r in rows:
        print(f"{r['video_id']:12} shots={r['shots_in_hook']['count']:2} "
              f"first_shot={r['shots_in_hook']['first_shot_s']:5}s | {r['first_sentence']['text'][:70]}")


if __name__ == "__main__":
    main()
