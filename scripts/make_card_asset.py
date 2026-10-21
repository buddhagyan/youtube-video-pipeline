"""Render a synthetic archival newspaper card for the still_card test.

    python scripts/make_card_asset.py

The card is drawn from scratch (own words, system fonts) with one real
public-domain NASA photo inside it, so the NewsCard component has an
article-shaped image to hold. Output: public/assets/news-card-1977.png
"""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = r"C:\Users\anu15\Downloads\youtube"
OUT = os.path.join(ROOT, "public", "assets", "news-card-1977.png")
PHOTO = os.path.join(ROOT, "public", "assets", "voyager-1-launch-1977.jpg")
FONTS = r"C:\Windows\Fonts"

W, H = 1240, 1560
PAPER = (246, 242, 233)
INK = (26, 24, 22)
GREY = (96, 90, 82)

HEAD = """The spacecraft lifted off at 8:56 on the morning of September 5, riding a
Titan IIIE-Centaur away from Cape Canaveral. Twelve seconds later it was gone
into low cloud, and the tracking stations took over."""

BODY = [
    """The Voyager mission was built around a rare alignment of the outer planets
that occurs once every 176 years. Two identical spacecraft would leave Earth a
fortnight apart and use the gravity of Jupiter, Saturn, Uranus and Neptune to
carry themselves outward.""",
    """Each craft carries a gold-plated copper record, a phonograph in a aluminium
case, with 115 images and a selection of music, greetings in 55 languages and the
sounds of the planet it left behind.""",
    """Engineers at the Jet Propulsion Laboratory describe the launch as the easy
part. The instruments must now survive a crossing of the asteroid belt, a passage
through the radiation belts of Jupiter, and four decades of distance.""",
    """By the time the second craft left the launch pad, the first was already
reporting that its systems were nominal. Mission control expected the first
images of Jupiter within eighteen months.""",
]


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def wrap(draw, text, fnt, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def main():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # masthead
    masthead = font("georgiab.ttf", 74)
    d.text((70, 58), "THE DAILY RECORD", font=masthead, fill=INK)
    small = font("georgia.ttf", 20)
    d.text((70, 146), "MORNING EDITION  ·  PRICE TEN CENTS", font=small, fill=GREY)
    d.text((W - 430, 146), "TUESDAY, SEPTEMBER 6, 1977", font=small, fill=GREY)
    d.line([(70, 182), (W - 70, 182)], fill=INK, width=3)
    d.line([(70, 190), (W - 70, 190)], fill=INK, width=1)

    # headline
    headline = font("timesbd.ttf", 78)
    lines = wrap(d, "VOYAGER 1 BEGINS ITS JOURNEY TO THE OUTER PLANETS", headline, W - 140)
    y = 220
    for ln in lines:
        d.text((70, y), ln, font=headline, fill=INK)
        y += 86

    deck = font("georgiai.ttf", 30)
    for ln in wrap(d, HEAD.replace("\n", " "), deck, W - 140)[:3]:
        d.text((70, y + 6), ln, font=deck, fill=GREY)
        y += 40
    y += 22

    # photo
    if os.path.exists(PHOTO):
        ph = Image.open(PHOTO).convert("RGB")
        target_w = W - 140
        target_h = 420
        ratio = max(target_w / ph.width, target_h / ph.height)
        ph = ph.resize((int(ph.width * ratio), int(ph.height * ratio)), Image.LANCZOS)
        left = (ph.width - target_w) // 2
        top = int(ph.height * 0.18)
        ph = ph.crop((left, top, left + target_w, top + target_h))
        img.paste(ph, (70, y))
        d.rectangle([(70, y), (70 + target_w, y + target_h)], outline=(180, 172, 160), width=1)
        y += target_h + 10
        cap = font("georgia.ttf", 19)
        d.text((70, y), "The Voyager 1 launch, Cape Canaveral, 5 September 1977.  NASA", font=cap, fill=GREY)
        y += 40

    d.line([(70, y), (W - 70, y)], fill=(196, 188, 176), width=1)
    y += 24

    # two columns of body text
    body = font("georgia.ttf", 22)
    col_w = (W - 140 - 40) // 2
    chunks = []
    for para in BODY:
        chunks.append(wrap(d, " ".join(para.split()), body, col_w))
    left_col = chunks[:2]
    right_col = chunks[2:]

    def draw_col(col, x, start_y):
        yy = start_y
        for para in col:
            for ln in para:
                d.text((x, yy), ln, font=body, fill=(40, 38, 35))
                yy += 31
            yy += 14

    draw_col(left_col, 70, y)
    draw_col(right_col, 70 + col_w + 40, y)

    img.save(OUT, quality=92)
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()
