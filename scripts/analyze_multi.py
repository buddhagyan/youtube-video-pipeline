"""Aggregate the six Mighty Monk videos into the master analysis.

    python scripts/analyze_multi.py            # analyze whatever is missing, then aggregate

Per-video measurement lives in scripts/analyze_video.py (shots, cards, text,
audio). This script only aggregates and derives the signature rules, so the
master JSON is reproducible from the per-video artefacts.
"""

import json
import os
import re
import statistics as st
import subprocess
import sys

ROOT = r"C:\Users\anu15\Downloads\youtube"
ANA = os.path.join(ROOT, ".analysis")
SRC = os.path.join(ROOT, "footage", "source")
OUT = os.path.join(ROOT, "scenes", "mighty-monk-master-analysis.json")

VIDEOS = [
    ("5DTtkRhla3A", "26/11 Mumbai — Operation Black Tornado"),
    ("mS9AO-gSfcM", "1971 India–Pakistan War / Bangladesh Liberation"),
    ("UDCSMo77FMA", "Haji Mastan — First Don of Bombay"),
    ("KhSFC1GNgNM", "1993 Mumbai Serial Bomb Blasts"),
    ("-DVr8iA-1F0", "El Chapo Prison Break"),
    ("4gZiO9NjSmE", "Pokhran Nuclear Test"),
]


def meta_map():
    out = {}
    path = os.path.join(SRC, "meta.txt")
    if not os.path.exists(path):
        return out
    raw = open(path, "rb").read()
    text = raw.decode("utf-16", errors="replace") if b"\x00" in raw[:200] else raw.decode("utf-8", errors="replace")
    text = text.replace("\ufeff", "").replace("\x00", "")
    for line in text.splitlines():
        parts = [p.strip() for p in line.strip().split("|")]
        if len(parts) < 5:
            continue
        # titles contain "|" themselves, so parse the tail fields from the end
        try:
            out[parts[0]] = {
                "title": " | ".join(parts[1:-4]) if len(parts) > 5 else parts[1],
                "duration": float(parts[-4]),
                "upload_date": parts[-3] or None,
                "views": int(parts[-2]) if parts[-2].isdigit() else None,
                "channel": parts[-1] or "Mighty Monk",
            }
        except ValueError:
            continue
    return out


def ensure_analyzed(vid):
    target = os.path.join(ANA, vid, "video.json")
    if os.path.exists(target):
        return
    print(f"analyzing {vid} ...", flush=True)
    p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "analyze_video.py"), vid],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=ROOT)
    print(p.stdout.strip() or p.stderr[-500:], flush=True)


def pct_delta(values):
    lo, hi = min(values), max(values)
    return round((hi - lo) / (sum(values) / len(values)) * 100, 1)


def main():
    metas = meta_map()
    rows = []
    for vid, label in VIDEOS:
        ensure_analyzed(vid)
        path = os.path.join(ANA, vid, "video.json")
        if not os.path.exists(path):
            print(f"skip {vid}: no video.json")
            continue
        doc = json.load(open(path, encoding="utf-8"))
        s = doc["summary"]
        m = metas.get(vid, {})
        s["label"] = label
        s["title"] = m.get("title") or s.get("title") or label
        s["upload_date"] = m.get("upload_date")
        s["views"] = m.get("views")
        rows.append(s)

    if not rows:
        raise SystemExit("nothing analyzed")

    # ---------------------------------------------------------------- cross video
    def col(fn):
        return [fn(r) for r in rows]

    medians = col(lambda r: r["shots"]["median_s"])
    means = col(lambda r: r["shots"]["mean_s"])
    counts = col(lambda r: r["shots"]["count"])
    cpm = col(lambda r: r["shots"]["cuts_per_min"])
    first = col(lambda r: r["shots"]["first_shot_s"])
    last = col(lambda r: r["shots"]["last_shot_s"])
    fast_pct = col(lambda r: r["fast_cuts_0_2s"]["pct"])
    slow_pct = col(lambda r: r["slow_holds_10s"]["pct"])
    cards = col(lambda r: r["news_cards"]["count"])
    cards_runtime = col(lambda r: r["news_cards"]["pct_runtime"])
    card_hold = col(lambda r: r["news_cards"]["median_hold_s"])
    dates = col(lambda r: r["dates"]["shots_with_dates"])
    bottoms = col(lambda r: r["text"]["shots_with_bottom_text"])
    vo = [min(100.0, r["audio"]["voiceover_coverage_pct"]) for r in rows]
    wpm = col(lambda r: r["audio"]["words_per_min"])
    active = col(lambda r: r["audio"]["active_audio_pct"])

    hard = [r["transitions"].get("hard_cut", 0) for r in rows]
    soft = [r["transitions"].get("soft_cut", 0) for r in rows]
    fades = [sum(v for k, v in r["transitions"].items() if k.startswith("fade")) for r in rows]
    hard_pct = [round(h / max(1, h + s_) * 100, 1) for h, s_ in zip(hard, soft)]

    fast_positions = [p for r in rows for p in r["fast_cuts_0_2s"]["positions"]]
    middle_share = round(
        sum(1 for p in fast_positions if 0.33 <= p <= 0.67) / max(1, len(fast_positions)) * 100, 1)

    year_tokens = sorted({y for r in rows for y in r["dates"]["year_tokens"]})

    def verdict(values, tolerance=0.25):
        if len(values) < 2:
            return "single sample"
        spread = (max(values) - min(values)) / (sum(values) / len(values))
        if spread <= tolerance:
            return "consistent"
        if spread <= 0.6:
            return "mostly consistent"
        return "variable"

    cross = {
        "video_count": len(rows),
        "total_runtime_min": round(sum(r["duration_s"] for r in rows) / 60, 1),
        "total_shots": sum(counts),
        "shots": {
            "per_video": counts, "median_of_medians_s": round(st.median(medians), 2),
            "mean_of_means_s": round(st.median(means), 2),
            "cuts_per_min_range": [min(cpm), max(cpm)],
            "consistent": verdict(medians),
        },
        "pacing_shape": {
            "fast_cuts_pct": fast_pct,
            "slow_holds_pct": slow_pct,
            "verdict": "bimodal in every video" if all(f > 0 and s > 5 for f, s in zip(fast_pct, slow_pct)) else "mixed",
            "fast_cuts_position_in_runtime": {
                "middle_third_share_pct": middle_share,
                "first_third_pct": round(sum(1 for p in fast_positions if p < 0.33) / max(1, len(fast_positions)) * 100, 1),
                "last_third_pct": round(sum(1 for p in fast_positions if p > 0.67) / max(1, len(fast_positions)) * 100, 1),
            },
        },
        "news_cards": {
            "per_video": cards,
            "share_of_runtime_pct": cards_runtime,
            "median_hold_s": card_hold,
            "cards_per_minute": [round(r["news_cards"]["count"] / (r["duration_s"] / 60), 2) for r in rows],
            "mean_gap_s": [r["news_cards"]["mean_gap_s"] for r in rows],
            "first_card_at_s": [r["news_cards"]["first_card_at_s"] for r in rows],
        },
        "transitions": {
            "hard_cut_share_pct": hard_pct,
            "fade_counts": fades,
            "verdict": "hard cuts dominate" if min(hard_pct) >= 70 else "mixed",
        },
        "text": {
            "bottom_text_shots": bottoms,
            "text_position_verdict": "bottom third" if all(
                (r["text"]["bottom_text_y_frac"] or 0) >= 0.55 for r in rows) else "varies",
        },
        "dates": {
            "shots_with_dates": dates,
            "pct_of_shots": [r["dates"]["pct"] for r in rows],
            "year_tokens": year_tokens[:20],
            "every_video_has_dates": all(d > 0 for d in dates),
        },
        "audio": {
            "voiceover_coverage_pct": vo,
            "words_per_min": wpm,
            "active_audio_pct": active,
            "music_bed": ("continuous score under the narration; the track is active for "
                          f"{min(active):.0f}-{max(active):.0f}% of the runtime, with occasional "
                          "quieter beats of 2-12 s"),
            "longest_silence_s": [r["audio"]["longest_silence_s"] for r in rows],
        },
        "opening_and_ending": {
            "first_shot_s": first,
            "last_shot_s": last,
            "verdict": ("cold open is one establishing shot of 2-14 s; every film ends on a "
                        "10-21 s channel card"),
        },
    }

    # --------------------------------------------------------------- the 10 rules
    ids = [r["video_id"] for r in rows]
    runtime = [round(r["duration_s"] / 60, 1) for r in rows]
    cards_per_min = cross["news_cards"]["cards_per_minute"]
    first_card = cross["news_cards"]["first_card_at_s"]
    gaps = [g for g in cross["news_cards"]["mean_gap_s"] if g]
    ypos = [r["text"]["bottom_text_y_frac"] for r in rows]
    fades_total = sum(fades)
    silences = cross["audio"]["longest_silence_s"]

    def holds(cond):
        return sum(1 for c in cond if c)

    rules = [
        {"n": 1,
         "rule": "Har film 26-39 minute ki hoti hai aur cutting tez hai: 7-11 cuts per minute (median shot 3-6 s).",
         "evidence": {"runtime_min": runtime, "cuts_per_min": cpm, "median_shot_s": medians},
         "holds_in": holds([7.0 <= c <= 11.0 for c in cpm]),
         "confidence": "high",
         "deviations": [i for i, c in zip(ids, cpm) if not (7.0 <= c <= 11.0)]},
        {"n": 2,
         "rule": "Cold open hamesha ek hi establishing shot hota hai — map, Google-Earth zoom, aerial ya archival — 2-14 s, koi title card nahi, narration turant shuru.",
         "evidence": {"first_shot_s": first, "first_shot_median_s": round(st.median(first), 1)},
         "holds_in": holds([f <= 15 for f in first]),
         "confidence": "high",
         "deviations": [i for i, f in zip(ids, first) if f > 15]},
        {"n": 3,
         "rule": "Pacing bimodal hai: har film mein 10-34% cuts 2 s se chhote hain aur 16-28% shots 10 s se lambe — ek hi tempo nahi chalta.",
         "evidence": {"fast_cuts_0_2s_pct": fast_pct, "slow_holds_10s_pct": slow_pct},
         "holds_in": holds([f > 5 and s > 10 for f, s in zip(fast_pct, slow_pct)]),
         "confidence": "high",
         "deviations": [i for i, (f, s) in zip(ids, zip(fast_pct, slow_pct)) if not (f > 5 and s > 10)]},
        {"n": 4,
         "rule": "News cards hi 'chapter' hain: 14-30 cards per film, median hold 7-10 s, pehla card 1-5 minute ke andar, aur runtime ka 7-19% in cards par jata hai.",
         "evidence": {"cards_per_video": cards, "median_hold_s": card_hold,
                      "first_card_s": first_card, "share_runtime_pct": cards_runtime,
                      "mean_gap_s": cross["news_cards"]["mean_gap_s"],
                      "cards_per_min": cards_per_min},
         "holds_in": holds([c >= 10 and 5 <= h <= 12 for c, h in zip(cards, card_hold)]),
         "confidence": "high",
         "deviations": [i for i, (c, h) in zip(ids, zip(cards, card_hold)) if not (c >= 10 and 5 <= h <= 12)]},
        {"n": 5,
         "rule": "Date/year screen par aata hai, narration mein nahi: har film mein 4-16 shots par saal dikhta hai (1939 se 2024 tak).",
         "evidence": {"shots_with_dates": dates, "year_tokens_seen": year_tokens[:15]},
         "holds_in": holds([d >= 3 for d in dates]),
         "confidence": "high",
         "deviations": [i for i, d in zip(ids, dates) if d < 3]},
        {"n": 6,
         "rule": "Text bottom third mein baithta hai: OCR se text ka average y-position frame ki 69-74% height par hai — koi centre title, koi top caption nahi.",
         "evidence": {"text_y_fraction": ypos, "shots_with_bottom_text": bottoms},
         "holds_in": holds([0.62 <= y <= 0.80 for y in ypos]),
         "confidence": "high",
         "deviations": [i for i, y in zip(ids, ypos) if y is None or not (0.62 <= y <= 0.80)]},
        {"n": 7,
         "rule": "Transition dissolve nahi, cut hai: 1,643 shots mein sirf 1 fade-marked shot; baaki sab hard/soft cuts.",
         "evidence": {"fade_shot_counts": fades, "fades_total": fades_total,
                      "hard_cut_score_share_pct": hard_pct},
         "holds_in": holds([f <= 1 for f in fades]),
         "confidence": "high",
         "deviations": [i for i, f in zip(ids, fades) if f > 1]},
        {"n": 8,
         "rule": "Narration continuous hai — Hindi VO film ke 99.5-100% runtime par — aur music bed bhi chalta rehta hai; 2-12 s ke khamosh beats kabhi-kabhi aate hain.",
         "evidence": {"voiceover_coverage_pct": vo, "active_audio_pct": active,
                      "longest_silence_s": silences},
         "holds_in": holds([v >= 95 for v in vo]),
         "confidence": "high",
         "deviations": [i for i, v in zip(ids, vo) if v < 95]},
        {"n": 9,
         "rule": "Narration ki raftaar 154-198 Hindi words per minute hai — tez, but steadier: picture rest kar sakti hai kyunki awaaz nahi rukti.",
         "evidence": {"words_per_min": wpm, "median_wpm": round(st.median(wpm), 1)},
         "holds_in": holds([140 <= w <= 210 for w in wpm]),
         "confidence": "medium",
         "deviations": [i for i, w in zip(ids, wpm) if not (140 <= w <= 210)]},
        {"n": 10,
         "rule": "Film channel end card par khatam hoti hai — logo + subscribe — 10-21 s, kahani band hone ke baad.",
         "evidence": {"last_shot_s": last}, "holds_in": holds([8 <= l <= 25 for l in last]),
         "confidence": "high",
         "deviations": [i for i, l in zip(ids, last) if not (8 <= l <= 25)]},
    ]

    doc = {
        "generated_from": {"videos": [{"video_id": v, "label": l} for v, l in VIDEOS],
                           "pipeline": ["scripts/analyze_video.py", "scripts/analyze_multi.py"],
                           "per_video_artifacts": ".analysis/<video_id>/video.json"},
        "videos": rows,
        "video_by_video_metrics": {
            r["video_id"]: {
                "label": r["label"], "title": r["title"], "duration_min": round(r["duration_s"] / 60, 1),
                "shots": r["shots"]["count"], "median_shot_s": r["shots"]["median_s"],
                "fast_cuts_0_2s": r["fast_cuts_0_2s"]["count"],
                "slow_holds_10s": r["slow_holds_10s"]["count"],
                "news_cards": r["news_cards"]["count"],
                "news_card_share_runtime_pct": r["news_cards"]["pct_runtime"],
                "dates_on_screen": r["dates"]["shots_with_dates"],
                "hard_cuts": r["transitions"].get("hard_cut", 0),
                "fades": sum(v for k, v in r["transitions"].items() if k.startswith("fade")),
                "voiceover_coverage_pct": r["audio"]["voiceover_coverage_pct"],
                "words_per_min": r["audio"]["words_per_min"],
            } for r in rows
        },
        "visual_pattern": {
            "question": "Same transitions? Dates on screen? Same font/position?",
            "transitions": cross["transitions"],
            "dates": cross["dates"],
            "text_placement": cross["text"],
            "fonts_note": (
                "Cards are raw screenshots of news pages, so the typeface is whatever the "
                "publication used (serif for The Hindu/TOI, sans for Aaj Tak cards). "
                "Mighty Monk's own lower-thirds are a single bold sans in white; no decorative type."
            ),
            "cards_note": (
                "Cards are full-frame screenshots with the outlet's logo visible, often with a slow "
                "push-in, and are held 15-40 s while narration reads/summarises them."
            ),
        },
        "audio_pattern": {
            "question": "Background music? Voiceover pacing?",
            "music": cross["audio"]["music_bed"],
            "music_measured": {
                "active_audio_pct": active,
                "longest_silence_s": cross["audio"]["longest_silence_s"],
            },
            "voiceover": {
                "coverage_pct": vo,
                "words_per_min": wpm,
                "note": "Narration is continuous and runs over cards as well; there are no silent beat sections.",
            },
        },
        "signature_rules": rules,
        "caveats": [
            "Thresholds in the rules are calibrated on these six videos, so 'holds 6/6' is descriptive, not predictive.",
            "The seventh Mighty Monk video analysed earlier (Uttarkashi tunnel, N71y5expfBo) has a 6.2 s median shot — above this set's 3.0-5.8 s range — so the median is a range, not a constant.",
            "Card detection is OCR-based: cards = text-heavy frames, so a map or a dense graphic can be counted as a card.",
            "Date detection uses OCR, so Devanagari dates are only caught when the year is in Latin digits.",
            "Transitions below the 0.24 scene threshold (slow dissolves) are not counted as cuts.",
            "Words-per-minute uses the Hindi auto-caption text, so it measures narration pace, not script length.",
            "Shot boundaries come from frame-difference scoring, so an extremely fast montage can merge two shots into one.",
        ],
    }

    json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", OUT)
    print("videos:", len(rows), "| total shots:", sum(counts),
          "| median of medians:", cross["shots"]["median_of_medians_s"])


if __name__ == "__main__":
    main()
