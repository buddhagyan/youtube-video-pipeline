# n8n bridge

One HTTP endpoint that takes a voiceover file and returns a rendered video.
It runs on your machine, inside this project folder — nothing is uploaded anywhere
except, in `mode=action`, a workflow dispatch to GitHub.

```
audio_path ──► scripts/transcribe.py (whisper.cpp) ──► audio/timing.json
           └─► render ──► mode=local  : npx remotion render  ──► out/n8n-<job>.mp4
                       └─► mode=action : GitHub Actions workflow_dispatch
```

## Start it

```powershell
cd C:\Users\anu15\Downloads\youtube
python scripts/n8n_bridge.py                 # http://127.0.0.1:5000
python scripts/n8n_bridge.py --port 5010     # other port
python scripts/n8n_bridge.py --host 0.0.0.0  # needed if n8n runs in Docker
```

## Talk to it

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | HTML form — easiest way to test from a browser |
| GET | `/health` | liveness, project path, whether `GH_TOKEN` is set |
| POST | `/generate-video` | JSON or form body, returns `202` + `job_id` |
| GET | `/generate-video?...` | same, straight from the address bar |
| GET | `/status/<job_id>` | state, word count, output file |
| GET | `/jobs` | every job started by this process |

### From a browser

- Form: <http://127.0.0.1:5000/>
- Quick GET (word timings only, no render):
  <http://127.0.0.1:5000/generate-video?audio_path=audio/test-vo.mp3&dry_run=1>
- Status page: `http://127.0.0.1:5000/status/<job_id>`

### From curl / n8n

```powershell
curl -X POST http://127.0.0.1:5000/generate-video `
  -H "Content-Type: application/json" `
  -d '{"audio_path":"audio/vo.mp3","composition":"SampleScenes"}'
```

### Request fields

| Field | Default | Notes |
|---|---|---|
| `audio_path` | — | required; relative to the project root (mp3/wav/m4a/ogg) |
| `composition` | `SampleScenes` | any composition id from `src/Root.tsx` |
| `mode` | `local` | `local` renders here; `action` dispatches GitHub Actions |
| `frames` | full film | e.g. `0-149` for a quick test |
| `dry_run` | false | `1` = only whisper word timings, skip the render |
| `output` | `out/n8n-<job>.mp4` | where the MP4 lands |

### Responses

```json
{"job_id": "3014cf112bbc", "state": "queued",
 "status_url": "/status/3014cf112bbc", "output": "out/n8n-3014cf112bbc.mp4"}
```

`/status/<id>` moves through `queued → transcribing → rendering → done|failed`
and finally carries:

```json
{"state": "done",
 "timing": {"path": "audio/timing.json", "words": 9, "duration_s": 3.87, "language": "auto"},
 "output": {"path": "out/n8n-3014cf112bbc.mp4", "bytes": 89863},
 "log": ".analysis/n8n/3014cf112bbc.log"}
```

## n8n HTTP Request node

1. **HTTP Request** → method `POST`, URL `http://127.0.0.1:5000/generate-video`,
   body type *JSON*:
   ```json
   {"audio_path": "{{ $json.audio_path }}", "composition": "SampleScenes"}
   ```
2. **Wait** node → 30 s.
3. **HTTP Request** → `GET http://127.0.0.1:5000/status/{{ $json.job_id }}`
   → loop until `state` is `done` or `failed`.
4. On `done`, `output.path` is the MP4 (and `timing.path` is the word timing file
   that the caption step in n8n needs).

If n8n runs in Docker, start the bridge with `--host 0.0.0.0` and use
`http://host.docker.internal:5000` inside n8n. Note that `0.0.0.0` exposes the
endpoint to your network — keep it local-only unless you need it.

## GitHub Actions mode

```powershell
$env:GH_TOKEN = "<fine-grained token with actions:write on the repo>"
python scripts/n8n_bridge.py
```

Then `"mode": "action"` dispatches `.github/workflows/render.yml` with the same
`composition` / `output` / `frames` inputs and returns immediately; the MP4 shows
up as a run artifact. Without `GH_TOKEN` the job fails with a clear message and
`mode=local` keeps working.

## Limits

- Audio paths outside the project folder are rejected (`400`).
- The job store is in-memory: restarting the bridge forgets finished jobs
  (their logs stay in `.analysis/n8n/`).
- One render at a time per process is the safe assumption on a laptop; parallel
  requests will queue in Remotion's own bundle lock.
