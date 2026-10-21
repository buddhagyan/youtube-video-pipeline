"""Word-level timestamps for a voiceover file, on Python 3.15.

    python scripts/transcribe.py audio/vo.mp3
    python scripts/transcribe.py audio/vo.mp3 --language hi --out audio/timing.json

Backend: whisper.cpp (the local Whisper build that runs on Python 3.15 - the
faster-whisper / ctranslate2 wheels do not exist for cp315). The model runs on
CPU, reports per-token offsets, and those are merged into words here.

Output (default audio/timing.json) is shaped for caption sync in n8n:

    {
      "source": "audio/vo.mp3",
      "duration_s": 12.4,
      "language": "en",
      "words": [{"index": 1, "word": "Hello", "start": 0.12, "end": 0.48}, ...],
      "segments": [{"start": 0.0, "end": 2.1, "text": "Hello and welcome."}],
      "text": "Hello and welcome."
    }
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, ".tools", "whisper")
BIN = os.path.join(TOOLS, "Release", "whisper-cli.exe")
DEFAULT_MODEL = os.path.join(TOOLS, "ggml-base.bin")

# pinned copies used by --auto-setup (same versions this repo was built with)
BIN_URL = "https://github.com/ggerganov/whisper.cpp/releases/download/b5454/whisper-bin-x64.zip"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"

SPECIAL = re.compile(r"^(\[[^\]]*\]|\([^)]*\)|<\|[^|]*\|>)$")


def find_ffmpeg():
    for cand in (
        os.environ.get("FFMPEG"),
        shutil.which("ffmpeg"),
        r"C:\Users\anu15\AppData\Local\Microsoft\WinGet\Packages"
        r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe",
    ):
        if cand and os.path.exists(cand):
            return cand
    return None


def ensure_tools(auto_setup):
    """Locate the whisper.cpp binary and model; optionally download them."""
    binary = os.environ.get("WHISPER_CLI") or BIN
    model = os.environ.get("WHISPER_MODEL") or DEFAULT_MODEL

    if not os.path.exists(binary):
        found = shutil.which("whisper-cli")
        if found:
            binary = found

    if auto_setup and (not os.path.exists(binary) or not os.path.exists(model)):
        os.makedirs(TOOLS, exist_ok=True)
        if not os.path.exists(binary):
            zip_path = os.path.join(TOOLS, "whisper-bin-x64.zip")
            print(f"downloading whisper.cpp build -> {zip_path}", flush=True)
            urllib.request.urlretrieve(BIN_URL, zip_path)
            shutil.unpack_archive(zip_path, TOOLS)
            os.remove(zip_path)
            binary = BIN
        if not os.path.exists(model):
            print(f"downloading model -> {model}", flush=True)
            urllib.request.urlretrieve(MODEL_URL, model)

    if not os.path.exists(binary):
        sys.exit(
            "whisper.cpp binary not found.\n"
            f"  expected: {BIN}\n"
            "  fix: python scripts/transcribe.py <file> --auto-setup\n"
            "  or set WHISPER_CLI / WHISPER_MODEL."
        )
    if not os.path.exists(model):
        sys.exit(
            "whisper model not found.\n"
            f"  expected: {DEFAULT_MODEL}\n"
            "  fix: python scripts/transcribe.py <file> --auto-setup"
        )
    return binary, model


def to_wav16k(src, dst):
    """whisper.cpp wants 16 kHz mono; ffmpeg does the conversion when present."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return False
    proc = subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
         "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", dst],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0 or not os.path.exists(dst):
        print(f"ffmpeg conversion failed, passing the file as-is:\n{proc.stderr[-300:]}")
        return False
    return True


def probe_duration(path, fallback):
    ffprobe = None
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        candidate = os.path.join(os.path.dirname(ffmpeg), "ffprobe.exe")
        if os.path.exists(candidate):
            ffprobe = candidate
    if not ffprobe:
        return fallback
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return round(float(proc.stdout.strip()), 2)
    except ValueError:
        return fallback


def run_whisper(binary, model, audio, language, threads, dtw, out_base):
    cmd = [
        binary, "-m", model, "-f", audio,
        "-l", language, "-t", str(threads),
        "-ojf",            # full JSON: segments + per-token offsets
        "-sow",            # split on words rather than tokens
        "-ml", "1",        # one word per segment where possible
        "-of", out_base,
        "-np",
    ]
    if dtw:
        cmd += ["-dtw", dtw]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    if proc.returncode != 0:
        sys.exit(f"whisper.cpp failed ({proc.returncode}):\n{proc.stderr[-800:]}")
    json_path = out_base + ".json"
    if not os.path.exists(json_path):
        sys.exit("whisper.cpp produced no JSON output")
    with open(json_path, "rb") as fh:
        raw = fh.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def words_from_tokens(segments):
    """Merge whisper tokens into words using their offsets (ms)."""
    words = []
    current = None

    for seg in segments:
        tokens = seg.get("tokens") or []
        for tok in tokens:
            text = tok.get("text") or ""
            if not text:
                continue
            piece = text.strip()
            if not piece or SPECIAL.match(piece):
                continue
            start = round(tok["offsets"]["from"] / 1000.0, 3)
            end = round(tok["offsets"]["to"] / 1000.0, 3)
            new_word = text[:1].isspace() or current is None
            if new_word and current is not None:
                words.append(current)
                current = None
            if current is None:
                current = {"word": piece, "start": start, "end": end}
            else:
                current["word"] += piece
                current["end"] = max(current["end"], end)
    if current is not None:
        words.append(current)
    return words


def words_from_segments(segments):
    """Fallback: split each segment's text evenly across its span."""
    words = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = seg["offsets"]["from"] / 1000.0
        end = seg["offsets"]["to"] / 1000.0
        parts = [p for p in re.split(r"\s+", text) if p]
        if not parts:
            continue
        step = (end - start) / len(parts)
        for i, part in enumerate(parts):
            words.append({
                "word": part,
                "start": round(start + i * step, 3),
                "end": round(start + (i + 1) * step, 3),
            })
    return words


def clean(words):
    """Drop empties, enforce monotonic times, keep zero-length words sane."""
    out = []
    for w in words:
        word = re.sub(r"\s+", " ", w["word"]).strip()
        if not word:
            continue
        start = max(0.0, float(w["start"]))
        end = max(start + 0.02, float(w["end"]))
        out.append({"word": word, "start": round(start, 3), "end": round(end, 3)})
    out.sort(key=lambda w: (w["start"], w["end"]))
    for i, w in enumerate(out, 1):
        w["index"] = i
    return out


def main():
    ap = argparse.ArgumentParser(description="Word-level timestamps for a voiceover file.")
    ap.add_argument("audio", help="input file (mp3, wav, m4a, ogg ...)")
    ap.add_argument("--out", default=os.path.join(ROOT, "audio", "timing.json"),
                    help="where to write the JSON (default: audio/timing.json)")
    ap.add_argument("--language", default="auto", help="spoken language code, default auto")
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--dtw", default="base",
                    help="token-level DTW model id (base/small/...); pass '' to disable")
    ap.add_argument("--auto-setup", action="store_true",
                    help="download the whisper.cpp build + model into .tools/ if missing")
    args = ap.parse_args()

    if not os.path.exists(args.audio):
        sys.exit(f"input not found: {args.audio}")

    binary, model = ensure_tools(args.auto_setup)

    # Work inside the repo: the machine's %TEMP% is not writable for subprocesses
    # (whisper.cpp cannot create its JSON there), which is also why the Remotion
    # renders set TEMP into the project.
    work_root = os.path.join(ROOT, ".tmp")
    os.makedirs(work_root, exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix="transcribe-", dir=work_root)
    try:
        wav = os.path.join(tmpdir, "audio16k.wav")
        prepared = to_wav16k(args.audio, wav)
        audio_in = wav if prepared else args.audio

        data = run_whisper(binary, model, audio_in, args.language,
                           args.threads, args.dtw, os.path.join(tmpdir, "out"))

        segments = data.get("transcription", [])
        words = words_from_tokens(segments)
        source = "tokens"
        if len(words) < 2 and segments:
            words = words_from_segments(segments)
            source = "segments (tokens were too sparse)"

        words = clean(words)
        text = " ".join((s.get("text") or "").strip() for s in segments).strip()
        duration = probe_duration(args.audio, words[-1]["end"] if words else 0.0)

        # whisper can end a hair past the container duration; clamp for caption sync
        if duration > 0.05:
            for w in words:
                w["start"] = round(min(w["start"], duration - 0.02), 3)
                w["start"] = max(0.0, w["start"])
                w["end"] = round(min(duration, max(w["end"], w["start"] + 0.02)), 3)

        seg_list = [
            {
                "start": round(s["offsets"]["from"] / 1000.0, 3),
                "end": round(s["offsets"]["to"] / 1000.0, 3),
                "text": (s.get("text") or "").strip(),
            }
            for s in segments
        ]

        doc = {
            "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "source": os.path.relpath(os.path.abspath(args.audio), ROOT).replace("\\", "/"),
            "duration_s": duration,
            "language": args.language,
            "backend": "whisper.cpp",
            "model": os.path.basename(model),
            "word_source": source,
            "word_count": len(words),
            "words": words,
            "segments": seg_list,
            "text": text,
            "notes": (
                "start/end are seconds from the beginning of the file; "
                "words are sorted and clipped so start < end; "
                "segment timings are whisper's own, word timings are the merged tokens."
            ),
        }

        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)

        print(f"wrote {args.out}")
        print(f"  {len(words)} words | {len(seg_list)} segments | {duration}s | {args.language}")
        for w in words[:8]:
            print(f"  {w['start']:6.2f} - {w['end']:6.2f}  {w['word']}")
        if len(words) > 8:
            print(f"  ... {len(words) - 8} more")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
