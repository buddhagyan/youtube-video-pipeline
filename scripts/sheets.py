"""Contact sheets for one analyzed video: 20 stills per sheet, labelled.

    python scripts/sheets.py <video_id> [per_sheet]
"""

import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = r"C:\Users\anu15\Downloads\youtube"
ANA = os.path.join(ROOT, ".analysis")


def main():
    vid = sys.argv[1]
    per_sheet = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    d = os.path.join(ANA, vid)
    frames_dir = os.path.join(d, "frames")
    sheets_dir = os.path.join(d, "sheets")
    os.makedirs(sheets_dir, exist_ok=True)
    doc = json.load(open(os.path.join(d, "video.json"), encoding="utf-8"))
    shots = {s["index"]: s for s in doc["shots"]}
    files = sorted(os.listdir(frames_dir))

    cols, tile_w, tile_h = 5, 384, 216
    for si in range(0, len(files), per_sheet):
        chunk = files[si:si + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + 26)), (12, 12, 14))
        draw = ImageDraw.Draw(sheet)
        for i, name in enumerate(chunk):
            img = Image.open(os.path.join(frames_dir, name)).convert("RGB")
            img.thumbnail((tile_w, tile_h))
            x = (i % cols) * tile_w
            y = (i // cols) * (tile_h + 26)
            sheet.paste(img, (x + (tile_w - img.width) // 2, y))
            idx = int(name.split(".")[0])
            s = shots.get(idx, {})
            tag = "CARD" if s.get("is_card") else ("DATE" if s.get("has_date") else "")
            label = f"#{idx} {s.get('start', 0):.1f}-{s.get('end', 0):.1f} {s.get('duration', 0):.1f}s {tag}".strip()
            draw.text((x + 6, y + tile_h + 6), label, fill=(210, 210, 215))
        out = os.path.join(sheets_dir, f"sheet-{si // per_sheet + 1:02d}.jpg")
        sheet.save(out, quality=88)
        print("wrote", out)


if __name__ == "__main__":
    main()
