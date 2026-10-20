"""Frame-by-frame helpers for the Mighty Monk breakdown.

Steps (run individually, output goes to .analysis/):
    python scripts/analyze.py cuts      parse the ffmpeg scene log -> shots.json
    python scripts/analyze.py frames    one still per shot, 1280 wide
    python scripts/analyze.py sheets    contact sheets, 20 shots per sheet
    python scripts/analyze.py audio     voice / music / sfx heuristics -> audio.json
    python scripts/analyze.py luma      per-shot brightness (fade detection)
    python scripts/analyze.py ocr       tesseract on every still -> ocr.json
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
FRAMES = os.path.join(ANA, "frames")
SHEETS = os.path.join(ANA, "sheets")
FPS = 30000 / 1001
SRC_360 = os.path.join(ROOT, "footage", "source", "N71y5expfBo.mp4")
SRC_HD = os.path.join(ROOT, "footage", "source", "hd.mp4")
FFDIR = r"C:\Users\anu15\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
FFMPEG = os.path.join(FFDIR, "ffmpeg.exe")
FFPROBE = os.path.join(FFDIR, "ffprobe.exe")

for d in (ANA, FRAMES, SHEETS):
    os.makedirs(d, exist_ok=True)


def run(cmd, cwd=None):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    if p.returncode != 0:
        print("CMD FAILED:", " ".join(cmd)[:300])
        print(p.stderr[-800:])
    return p


def duration():
    p = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", SRC_HD])
    return float(p.stdout.strip())


def parse_cuts():
    path = os.path.join(ANA, "scene-log.txt")
    cuts, t = [], None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            m = re.match(r"frame:\s*\d+\s+pts:\s*\d+\s+pts_time:([\d.]+)", line)
            if m:
                t = float(m.group(1))
                continue
            m = re.match(r"lavfi\.scene_score=([\d.]+)", line)
            if m and t is not None:
                cuts.append((t, float(m.group(1))))
                t = None
    return cuts


def build_shots():
    total = duration()
    cuts = parse_cuts()
    picks, last = [], -10.0
    for t, score in cuts:
        if t - last >= 0.4:          # ignore twin detections on one cut
            picks.append((t, score))
            last = t
    bounds = [0.0] + [t for t, _ in picks] + [total]
    shots = []
    for i in range(len(bounds) - 1):
        start, end = bounds[i], bounds[i + 1]
        shots.append({
            "index": i + 1,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "start_frame": int(round(start * FPS)),
            "end_frame": int(round(end * FPS)),
            "cut_score": round(picks[i - 1][1], 3) if i > 0 else None,
        })
    with open(os.path.join(ANA, "shots.json"), "w", encoding="utf-8") as fh:
        json.dump({"duration": total, "fps": FPS, "shots": shots}, fh, indent=1)
    print(f"shots: {len(shots)}  cuts: {len(picks)}  duration: {total:.1f}s")
    short = [s for s in shots if s["duration"] < 0.5]
    print("very short shots:", len(short))


def shots_data():
    with open(os.path.join(ANA, "shots.json"), encoding="utf-8") as fh:
        return json.load(fh)


def extract_frames():
    data = shots_data()
    for s in data["shots"]:
        out = os.path.join(FRAMES, f"{s['index']:03d}.jpg")
        if os.path.exists(out):
            continue
        t = s["start"] + (s["end"] - s["start"]) * 0.45
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin",
             "-ss", f"{t:.3f}", "-i", SRC_HD, "-frames:v", "1",
             "-vf", "scale=1280:-2", "-q:v", "2", out])
    print("frames:", len(os.listdir(FRAMES)))


def make_sheets(per_sheet=20, cols=5, tile_w=384, tile_h=216):
    data = shots_data()
    files = sorted(os.listdir(FRAMES))
    for si in range(0, len(files), per_sheet):
        chunk = files[si:si + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + 26)), (12, 12, 14))
        draw = ImageDraw.Draw(sheet)
        for i, name in enumerate(chunk):
            img = Image.open(os.path.join(FRAMES, name)).convert("RGB")
            img.thumbnail((tile_w, tile_h))
            x = (i % cols) * tile_w
            y = (i // cols) * (tile_h + 26)
            sheet.paste(img, (x + (tile_w - img.width) // 2, y))
            idx = int(name.split(".")[0])
            s = data["shots"][idx - 1]
            label = f"#{idx} {s['start']:.2f}-{s['end']:.2f}s {s['duration']:.1f}s"
            draw.text((x + 6, y + tile_h + 6), label, fill=(210, 210, 215))
        out = os.path.join(SHEETS, f"sheet-{si // per_sheet + 1:02d}.jpg")
        sheet.save(out, quality=88)
        print("wrote", out)


def decode_audio():
    wav = os.path.join(ANA, "audio.wav")
    if not os.path.exists(wav):
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", SRC_HD,
             "-ac", "1", "-ar", "16000", "-f", "wav", wav])
    with wave.open(wav, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return sr, x


def audio_features():
    sr, x = decode_audio()
    hop = int(sr * 0.032)          # ~31 ms
    win = 1024
    n = (len(x) - win) // hop
    rms = np.zeros(n)
    flat = np.zeros(n)
    pitch = np.zeros(n)
    centroid = np.zeros(n)
    low = np.zeros(n)
    flux = np.zeros(n)
    window = np.hanning(win).astype(np.float32)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    prev_mag = None
    for i in range(n):
        seg = x[i * hop:i * hop + win] * window
        spec = np.abs(np.fft.rfft(seg)) ** 2 + 1e-12
        mag = np.sqrt(spec)
        rms[i] = np.sqrt(np.mean(seg ** 2) + 1e-12)
        flat[i] = np.exp(np.mean(np.log(spec))) / np.mean(spec)
        centroid[i] = float(np.sum(freqs * spec) / np.sum(spec))
        low[i] = float(np.sum(spec[freqs < 150]) / np.sum(spec))
        ac = np.correlate(seg, seg, mode="full")[win - 1:]
        ac = ac / (ac[0] + 1e-9)
        lo, hi = int(sr / 350), int(sr / 70)
        pitch[i] = float(np.max(ac[lo:hi])) if hi < len(ac) else 0.0
        if prev_mag is None:
            prev_mag = mag
        else:
            flux[i] = float(np.sum(np.maximum(0.0, mag - prev_mag)) / (np.sum(mag) + 1e-9))
            prev_mag = mag

    db = 20 * np.log10(rms + 1e-9)
    floor = float(np.percentile(db, 12))
    voice = (db > floor + 9) & (pitch > 0.28) & (flat < 0.25)
    active = db > floor + 6
    times = np.arange(n) * hop / sr

    # merge voice runs
    def runs(mask, min_len=0.35):
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

    voice_runs = runs(voice)
    silent_runs = runs(~active, min_len=0.5)

    # sfx: spectral-flux onsets that stand out from their neighbourhood
    kernel = max(3, int(1.5 / (hop / sr)) | 1)
    pad = kernel // 2
    padded = np.pad(flux, pad, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, kernel)
    base_flux = np.median(windows, axis=1)
    thresh = float(np.percentile(flux, 96))
    sfx = []
    last = -10
    for i in range(1, len(flux) - 1):
        if flux[i] < thresh or flux[i] < flux[i - 1] or flux[i] < flux[i + 1]:
            continue
        t = times[i]
        if t - last < 1.2:
            continue
        kind = "low_impact" if low[i] > 0.45 else ("bright_hit" if centroid[i] > 3200 else "transient")
        sfx.append({"time": round(float(t), 2), "kind": kind,
                    "flux_over_baseline": round(float(flux[i] / (base_flux[i] + 1e-9)), 1)})
        last = t

    music = []
    # music bed: energy in non-voice regions, sustained, not silent
    for start, end in _complement(voice_runs, times[-1]):
        mask = (times >= start) & (times <= end) & active
        if mask.sum() * (hop / sr) < 1.0:
            continue
        seg_db = db[mask]
        if np.percentile(seg_db, 20) > floor + 8:
            music.append([start, end])

    out = {
        "duration": round(float(times[-1]), 2),
        "noise_floor_db": round(floor, 1),
        "voice_runs": voice_runs,
        "silent_runs": silent_runs,
        "music_runs": music,
        "sfx": sfx,
        "heel": "heuristics from mono 16 kHz RMS, spectral flatness, autocorrelation pitch strength",
    }
    with open(os.path.join(ANA, "audio.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"voice {len(voice_runs)} runs | music {len(music)} runs | sfx {len(sfx)} | silence {len(silent_runs)}")


def _complement(runs, end):
    out, cur = [], 0.0
    for a, b in runs:
        if a - cur > 0.4:
            out.append([round(cur, 2), round(a, 2)])
        cur = b
    if end - cur > 0.4:
        out.append([round(cur, 2), round(end, 2)])
    return out


def luma():
    log = os.path.join(ANA, "luma-log.txt")
    if not os.path.exists(log):
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", SRC_360,
             "-vf", "scale=160:-2,signalstats,metadata=print:file=.analysis/luma-log.txt",
             "-an", "-f", "null", "-"], cwd=ROOT)
    data = shots_data()
    pts, yavg, t = [], [], None
    with open(log, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.match(r"frame:\s*\d+\s+pts:\s*\d+\s+pts_time:([\d.]+)", line)
            if m:
                t = float(m.group(1))
                continue
            m = re.match(r"lavfi\.signalstats\.YAVG=([\d.]+)", line)
            if m and t is not None:
                pts.append(t)
                yavg.append(float(m.group(1)))
                t = None
    pts, yavg = np.array(pts), np.array(yavg)
    for s in data["shots"]:
        mask = (pts >= s["start"]) & (pts < s["end"])
        if not mask.any():
            continue
        seg = yavg[mask]
        s["luma_mean"] = round(float(seg.mean()), 1)
        s["luma_start"] = round(float(seg[:max(3, len(seg) // 8)].mean()), 1)
        s["luma_end"] = round(float(seg[-max(3, len(seg) // 8):].mean()), 1)
    with open(os.path.join(ANA, "shots.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    print("luma annotated for", len(data["shots"]), "shots")


def subs():
    """YouTube auto-caption cues = the authoritative voiceover timing.

    These captions are "rolling": each block repeats the previous line and adds
    the next one, with word-level timestamps inline. So a speech segment is
    [block.start, next_block.start) and its text is the block's first line.
    """
    path = os.path.join(ROOT, "footage", "source", "N71y5expfBo.hi.vtt")
    ts = r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
    blocks = []
    cur = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = re.match(ts + r"\s*-->\s*" + ts, line)
            if m:
                g = [float(v) for v in m.groups()]
                start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
                end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
                cur = {"start": start, "end": end, "lines": []}
                blocks.append(cur)
                continue
            if cur is not None:
                stripped = re.sub(r"<[^>]*>", "", line).strip()
                if stripped and not stripped.startswith(("WEBVTT", "Kind:", "Language:")):
                    cur["lines"].append(stripped)

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

    with open(os.path.join(ANA, "subs.json"), "w", encoding="utf-8") as fh:
        json.dump(segs, fh, indent=1, ensure_ascii=False)
    covered = sum(s["end"] - s["start"] for s in segs)
    last = segs[-1]["end"] if segs else 0
    print(f"speech segments: {len(segs)} | covered {covered:.1f}s of {last:.1f}s "
          f"({covered / last * 100:.1f}%)")
    if segs:
        print("first:", segs[0])
        print("last :", segs[-1])


def ocr():
    exe = None
    for cand in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                 r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.exists(cand):
            exe = cand
            break
    if not exe:
        print("tesseract not found")
        return
    out = {}
    for name in sorted(os.listdir(FRAMES)):
        img = os.path.join(FRAMES, name)
        p = run([exe, img, "stdout", "--psm", "6", "-l", "eng"])
        text = " ".join(line.strip() for line in p.stdout.splitlines() if line.strip())
        out[name.split(".")[0]] = text[:400]
    with open(os.path.join(ANA, "ocr.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("ocr done for", len(out))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cuts"
    {"cuts": build_shots, "frames": extract_frames, "sheets": make_sheets,
     "audio": audio_features, "luma": luma, "ocr": ocr, "subs": subs}[cmd]()
