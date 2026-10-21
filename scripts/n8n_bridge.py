"""n8n bridge: one HTTP endpoint that turns a voiceover file into a rendered video.

    python scripts/n8n_bridge.py                # serves http://127.0.0.1:5000
    python scripts/n8n_bridge.py --port 5000

Flow per request:
    audio_path -> scripts/transcribe.py (whisper.cpp word timings -> audio/timing.json)
               -> render, either
                    mode=local  : npx remotion render <composition> out/<file>
                    mode=action : GitHub Actions workflow_dispatch (needs GH_TOKEN)

Endpoints
    GET  /                     small HTML form (browser testing)
    GET  /health               liveness + paths
    POST /generate-video       {"audio_path": "audio/vo.mp3", ...}  -> 202 + job
    GET  /generate-video?...   same, for a quick browser/curl hit
    GET  /status/<job_id>      job state, timing summary, output file
    GET  /jobs                 all jobs of this process

Everything stays inside the project folder: audio paths outside the repo are
rejected, and every output is written under ./out, ./audio or ./.analysis/n8n.
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import uuid

from flask import Flask, jsonify, request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
JOBS_DIR = os.path.join(ROOT, ".analysis", "n8n")
DEFAULT_COMPOSITION = "SampleScenes"
DEFAULT_REPO = "buddhagyan/youtube-video-pipeline"
WORKFLOW_FILE = "render.yml"

app = Flask(__name__)
JOBS = {}
LOCK = threading.Lock()


# --------------------------------------------------------------------- helpers
def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def inside_project(path):
    """Resolve a path and make sure it really is inside the project folder."""
    full = os.path.abspath(path if os.path.isabs(path) else os.path.join(ROOT, path))
    real_root = os.path.abspath(ROOT)
    return full if os.path.commonpath([full, real_root]) == real_root else None


def log_path(job_id):
    os.makedirs(JOBS_DIR, exist_ok=True)
    return os.path.join(JOBS_DIR, f"{job_id}.log")


def append_log(job_id, text):
    with open(log_path(job_id), "a", encoding="utf-8", errors="replace") as fh:
        fh.write(text)


def run(cmd, job_id, extra_env=None, timeout=None):
    env = os.environ.copy()
    # %TEMP% is not writable for child processes on this machine; keep scratch
    # inside the repo (same workaround the render commands use).
    scratch = os.path.join(ROOT, ".tmp")
    os.makedirs(scratch, exist_ok=True)
    env["TEMP"] = scratch
    env["TMP"] = scratch
    if extra_env:
        env.update(extra_env)
    append_log(job_id, f"\n$ {' '.join(cmd)}\n")
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    append_log(job_id, out[-4000:])
    return proc.returncode, out


def set_job(job_id, **fields):
    with LOCK:
        JOBS[job_id].update(fields)


def get_job(job_id):
    with LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None


# ----------------------------------------------------------------- job worker
def transcribe_and_render(job_id, audio_path, composition, mode, frames,
                          output, dry_run):
    try:
        set_job(job_id, state="transcribing", updated_at=now())
        code, out = run([sys.executable, os.path.join(SCRIPTS, "transcribe.py"),
                         audio_path, "--out", os.path.join(ROOT, "audio", "timing.json")],
                        job_id)
        timing_path = os.path.join(ROOT, "audio", "timing.json")
        if code != 0 or not os.path.exists(timing_path):
            set_job(job_id, state="failed", error="transcription failed",
                    finished_at=now())
            return

        timing = json.load(open(timing_path, encoding="utf-8"))
        set_job(job_id,
                timing={
                    "path": os.path.relpath(timing_path, ROOT).replace("\\", "/"),
                    "words": timing.get("word_count"),
                    "duration_s": timing.get("duration_s"),
                    "language": timing.get("language"),
                },
                state="rendering" if not dry_run else "done",
                updated_at=now())
        if dry_run:
            set_job(job_id, finished_at=now())
            return

        if mode == "action":
            ok, detail = dispatch_action(job_id, composition, output, frames)
            set_job(job_id, state="done" if ok else "failed",
                    action=detail,
                    error=None if ok else detail.get("error"),
                    finished_at=now())
            return

        # local render
        os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
        cmd = [os.path.join(ROOT, "node_modules", ".bin", "remotion.cmd"),
               "render", composition, output, "--log=info"]
        if frames:
            cmd.append(f"--frames={frames}")
        code, out = run(cmd, job_id, timeout=3600)
        target = os.path.join(ROOT, output)
        if code != 0 or not os.path.exists(target):
            set_job(job_id, state="failed", error=f"render failed (exit {code})",
                    finished_at=now())
            return
        set_job(job_id, state="done",
                output={"path": output.replace("\\", "/"),
                        "bytes": os.path.getsize(target)},
                finished_at=now())
    except Exception as exc:  # noqa: BLE001 - a job failure must not kill the server
        set_job(job_id, state="failed", error=f"{type(exc).__name__}: {exc}",
                finished_at=now())


def dispatch_action(job_id, composition, output, frames):
    """Trigger .github/workflows/render.yml on GitHub."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO", DEFAULT_REPO)
    if not token:
        return False, {"error": "GH_TOKEN is not set; use mode=local or export a token",
                       "repo": repo}

    payload = json.dumps({"ref": "main", "inputs": {
        "composition": composition,
        "output": os.path.basename(output),
        "frames": frames or "",
    }}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/dispatches",
        data=payload, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "n8n-bridge"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.status
    except urllib.error.HTTPError as exc:
        return False, {"error": f"GitHub returned {exc.code}: {exc.read()[:300]!r}",
                       "repo": repo}
    except Exception as exc:  # noqa: BLE001
        return False, {"error": f"{type(exc).__name__}: {exc}", "repo": repo}

    return True, {"repo": repo, "workflow": WORKFLOW_FILE,
                  "status": code, "note": "check the Actions tab for the artifact"}


# ------------------------------------------------------------------- endpoints
@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "project": ROOT,
        "default_composition": DEFAULT_COMPOSITION,
        "github_repo": os.environ.get("GITHUB_REPO", DEFAULT_REPO),
        "gh_token_set": bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")),
        "jobs": len(JOBS),
    })


@app.get("/")
def index():
    return f"""<!doctype html>
<meta charset="utf-8">
<title>n8n bridge</title>
<style>
 body {{ font: 15px/1.5 system-ui, sans-serif; max-width: 720px; margin: 40px auto; }}
 code, input, select {{ font-family: ui-monospace, monospace; }}
 input, select {{ padding: 6px; width: 100%; box-sizing: border-box; margin: 4px 0 14px; }}
 button {{ padding: 10px 18px; font-size: 15px; }}
 .row {{ display: flex; gap: 12px; }}
 .row > div {{ flex: 1; }}
</style>
<h2>Generate a video</h2>
<p>Audio path is relative to <code>{ROOT}</code>.</p>
<form method="post" action="/generate-video">
  <label>audio_path (mp3/wav)</label>
  <input name="audio_path" value="audio/test-vo.mp3" required>
  <div class="row">
    <div>
      <label>composition</label>
      <select name="composition">
        <option>SampleScenes</option><option>HelloWorld</option>
        <option>KenBurnsTest</option><option>TextOverlayTest</option>
        <option>TimelineBarTest</option>
      </select>
    </div>
    <div>
      <label>mode</label>
      <select name="mode"><option>local</option><option>action</option></select>
    </div>
  </div>
  <label>frames (optional, e.g. 0-149)</label>
  <input name="frames" placeholder="">
  <label><input type="checkbox" name="dry_run" value="1" style="width:auto">
    dry run — only word timings, skip the render</label>
  <p><button type="submit">Generate</button></p>
</form>
<p><a href="/health">/health</a> · <a href="/jobs">/jobs</a></p>
"""


def start_job(payload):
    audio = payload.get("audio_path")
    if not audio:
        return jsonify({"error": "audio_path is required"}), 400
    audio_full = inside_project(audio)
    if not audio_full:
        return jsonify({"error": "audio_path must be inside the project folder"}), 400
    if not os.path.exists(audio_full):
        return jsonify({"error": f"audio file not found: {audio}"}), 404

    composition = payload.get("composition") or DEFAULT_COMPOSITION
    mode = (payload.get("mode") or "local").lower()
    if mode not in ("local", "action"):
        return jsonify({"error": "mode must be 'local' or 'action'"}), 400
    frames = (payload.get("frames") or "").strip() or None
    dry_run = str(payload.get("dry_run", "")).lower() in ("1", "true", "yes", "on")

    job_id = uuid.uuid4().hex[:12]
    output = payload.get("output") or f"out/n8n-{job_id}.mp4"
    with LOCK:
        JOBS[job_id] = {
            "id": job_id, "state": "queued", "created_at": now(),
            "request": {"audio_path": audio, "composition": composition,
                        "mode": mode, "frames": frames, "dry_run": dry_run,
                        "output": output},
            "log": os.path.relpath(log_path(job_id), ROOT).replace("\\", "/"),
        }
    threading.Thread(target=transcribe_and_render,
                     args=(job_id, os.path.relpath(audio_full, ROOT), composition,
                           mode, frames, output, dry_run),
                     daemon=True).start()
    return jsonify({"job_id": job_id, "state": "queued",
                    "status_url": f"/status/{job_id}",
                    "output": None if dry_run else output}), 202


@app.post("/generate-video")
def generate_video_post():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    return start_job(payload)


@app.get("/generate-video")
def generate_video_get():
    return start_job(request.args.to_dict())


@app.get("/status/<job_id>")
def status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job)


@app.get("/jobs")
def jobs():
    with LOCK:
        items = [{"id": j["id"], "state": j["state"], "created_at": j["created_at"]}
                 for j in JOBS.values()]
    return jsonify({"count": len(items), "jobs": items})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="HTTP bridge for n8n -> transcribe -> render")
    ap.add_argument("--port", type=int, default=int(os.environ.get("N8N_BRIDGE_PORT", 5000)))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    os.makedirs(JOBS_DIR, exist_ok=True)
    print(f"n8n bridge on http://{args.host}:{args.port}  (project: {ROOT})")
    print(f"  browser form : http://{args.host}:{args.port}/")
    print(f"  POST target  : http://{args.host}:{args.port}/generate-video")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
