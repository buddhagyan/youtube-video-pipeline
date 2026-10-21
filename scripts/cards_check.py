"""Contact sheet of the shots classified as news cards, for eyeballing the detector.

    python scripts/cards_check.py <video_id> [limit]
"""

import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = r"C:\Users\anu15\Downloads\youtube"
ANA = os.path.join(ROOT, ".analysis")


def main():
    vid = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    d = os.path.join(ANA, vid)
    doc = json.load(open(os.path.join(d, "video.json"), encoding="utf-8"))
    cards = [s for s in doc["shots"] if s.get("is_card")]
    print("cards:", len(cards), "of", len(doc["shots"]), "shots")
    pick = cards[:limit]
    if not pick:
        return
    cols, tw, th = 4, 420, 236
    rows = (len(pick) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 24)), (10, 10, 12))
    draw = ImageDraw.Draw(sheet)
    for i, s in enumerate(pick):
        path = os.path.join(d, "frames", f"{s['index']:03d}.jpg")
        img = Image.open(path).convert("RGB")
        img.thumbnail((tw, th))
        x = (i % cols) * tw
        y = (i // cols) * (th + 24)
        sheet.paste(img, (x + (tw - img.width) // 2, y))
        draw.text((x + 6, y + th + 5),
                  f"#{s['index']} {s['start']:.0f}s {s['duration']:.1f}s chars={s['ocr_chars']}",
                  fill=(220, 220, 225))
    out = os.path.join(d, "cards-check.jpg")
    sheet.save(out, quality=88)
    print("wrote", out)


if __name__ == "__main__":
    main()
