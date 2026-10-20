"""Assemble scenes/mighty-monk-analysis.json from the .analysis/ measurements.

Inputs
    .analysis/shots.json   shot boundaries + luma
    .analysis/subs.json    Hindi auto-caption cues (voiceover timing)
    .analysis/audio.json   music / silence / sfx heuristics
    .analysis/ocr.json     tesseract reading of each still
    VISUALS / TEXT_NOTES    below: what the frames show (read from the sheets)

Run: python scripts/build_analysis.py
"""

import json
import os
import re

ROOT = r"C:\Users\anu15\Downloads\youtube"
ANA = os.path.join(ROOT, ".analysis")
OUT = os.path.join(ROOT, "scenes", "mighty-monk-analysis.json")

# ---------------------------------------------------------------- observations
VISUALS = {
    1: ("Night aerial of a town with fireworks bursting over it; long cold open.", ["night_aerial", "fireworks", "cold_open"]),
    2: ("Night crowd standing under decorative lights, shot on a phone.", ["crowd", "night", "phone_footage"]),
    3: ("Busy night street/market, crowd of locals.", ["crowd", "street", "night"]),
    4: ("Construction workers in hi-vis vests and helmets at night.", ["workers", "construction", "night"]),
    5: ("Welding sparks flying, tight detail shot.", ["welding", "sparks", "detail"]),
    6: ("Map graphic with a 25 km route, markers for Silkyara and Kedarnath.", ["map", "graphic", "infographic"]),
    7: ("Aerial of a forested mountain ridge and valley.", ["aerial", "mountains", "nature"]),
    8: ("Small crowd near the road, daylight.", ["crowd", "road"]),
    9: ("Road seen through a car window, hills ahead (arrival POV).", ["driving", "pov", "road"]),
    10: ("Hindi highway signboard for the Rishikesh/Uttarkashi route.", ["signboard", "road", "location"]),
    11: ("Archive TV shot of PM Modi with a lower-third date card.", ["modi", "archive_tv", "text_overlay"]),
    12: ("PM Modi speaking at a podium, archive footage.", ["modi", "speech", "archive_tv"]),
    13: ("Company logo card: Nayyuga Engineering Construction Limited.", ["logo_card", "graphic"]),
    14: ("Tunnel interior with a news text card floating over it.", ["tunnel_interior", "news_card"]),
    15: ("Aerial of the tunnelled hillside with a date stamp on screen.", ["aerial", "hillside", "text_overlay"]),
    16: ("Workers in orange vests and helmets inside the tunnel.", ["tunnel_interior", "workers"]),
    17: ("Tunnel mouth seen from outside; a man with a radio stands guard.", ["tunnel_portal", "workers"]),
    18: ("Workers walking through the arched tunnel under work lights.", ["tunnel_interior", "workers"]),
    19: ("Close-up of the debris pile, drill marks in the muck.", ["rubble", "debris", "detail"]),
    20: ("Torch beams cutting through a dark tunnel section.", ["tunnel_interior", "dark", "flashlights"]),
    21: ("Backlit workers rigging equipment inside the tunnel.", ["tunnel_interior", "workers"]),
    22: ("Village couple being interviewed, phone-shot.", ["villagers", "interview"]),
    23: ("Very long close-up on a yellow helmet in the tunnel.", ["tunnel_interior", "helmet", "detail"]),
    24: ("Two workers in hard hats and dust masks.", ["workers", "tunnel_interior"]),
    25: ("Rescuer in a red helmet lit from behind.", ["tunnel_interior", "people"]),
    26: ("Rows of workers lined up outside the portal.", ["tunnel_portal", "workers", "queue"]),
    27: ("Dark tunnel interior, work lights far away.", ["tunnel_interior", "dark"]),
    28: ("Rescue crew with an Aaj Tak explainer card on screen.", ["tunnel_interior", "news_card", "workers"]),
    29: ("Close of a worker beside a 4-inch pipe diagram and a news card.", ["pipe", "diagram", "news_card"]),
    30: ("Blurred cluster of workers, shallow focus.", ["workers", "blur"]),
    31: ("Rubble pile with a Hindustan headline card on top.", ["rubble", "news_card"]),
    32: ("Drilling rig working inside the tunnel.", ["machinery", "drilling", "tunnel_interior"]),
    33: ("Group of workers walking out through the forest road.", ["workers", "forest", "walking"]),
    34: ("Aerial of the green valley and the hillside road.", ["aerial", "valley", "nature"]),
    35: ("Blurred meeting / interview, people seated.", ["meeting", "blur"]),
    36: ("Silhouettes of workers at the portal light.", ["workers", "silhouette"]),
    37: ("Steel pipe being pushed in, Aaj Tak card over the frame.", ["pipe", "machinery", "news_card"]),
    38: ("Green tunnel-cam frame from inside.", ["cctv", "tunnel_interior"]),
    39: ("Workers moving through the tunnel under lights.", ["tunnel_interior", "workers"]),
    40: ("Hindi news card ('दिनांक') floating over tunnel footage.", ["news_card", "text_overlay"]),
    41: ("Villagers speaking to a reporter, phone-shot.", ["villagers", "interview"]),
    42: ("IAF C-130 on the ground with relief machinery lined up; very long hold.", ["aircraft", "cargo", "rescue_equipment"]),
    43: ("Expert in headphones speaking, close portrait.", ["expert", "interview"]),
    44: ("Same expert, a half-second flash frame.", ["expert", "interview", "flash_cut"]),
    45: ("Machinery working the face of the tunnel (Trackless loader).", ["machinery", "tunnel_interior"]),
    46: ("The Hindu article card, dense paragraphs, held for 31 seconds.", ["news_card", "text_heavy"]),
    47: ("Workers walking the access road.", ["workers", "site"]),
    48: ("Aerial of workers on the rubble slope.", ["aerial", "workers", "rubble"]),
    49: ("TV screen grab: 'HOPE FLOATS ON 6 INCHES', Mirror Now.", ["tv_screen", "news", "text_overlay"]),
    50: ("Night street scene with playback UI burned in.", ["street", "night", "source_ui"]),
    51: ("Modi and an official in a split-screen archive clip.", ["modi", "archive_tv", "split_screen"]),
    52: ("Two experts in conversation, handheld.", ["interview", "experts"]),
    53: ("Moneycontrol article card over tunnel footage.", ["news_card"]),
    54: ("Aerial of the tunnel portal and the access benches.", ["aerial", "tunnel_portal"]),
    55: ("NDRF card 'SILKYARA TUNNEL COLLAPSE' over the portal.", ["news_card", "logo_card"]),
    56: ("SANY excavator with a worker, Aaj Tak card lower third.", ["excavator", "machinery", "news_card"]),
    57: ("ANI interview: worker in a yellow helmet.", ["interview", "workers"]),
    58: ("Cut-out newspaper collage, torn paper edges.", ["newspaper_collage", "graphic"]),
    59: ("Second newspaper collage frame.", ["newspaper_collage", "graphic"]),
    60: ("Newspaper headline punched up: international tunnelling expert.", ["newspaper", "text_overlay"]),
    61: ("Headline: 'EXPERT ARNOLD DIX ARRIVED IN...', Dainik Bhaskar.", ["newspaper", "text_overlay"]),
    62: ("Newspaper page zooming further in.", ["newspaper"]),
    63: ("Headline reads: arrived in Uttarkashi, survey, two vertical drilling sites.", ["newspaper", "text_overlay"]),
    64: ("Dark tunnel bay lit by one floodlight.", ["tunnel_interior", "dark"]),
    65: ("Pipe end with a lamp inside it, tunnel darkness.", ["pipe", "tunnel_interior", "dark"]),
    66: ("Workers in yellow jackets at the pipe mouth.", ["workers", "tunnel_interior"]),
    67: ("Checkpoint barrier and project signage, night.", ["site", "checkpoint"]),
    68: ("Man welding inside a steel pipe.", ["welding", "pipe", "detail"]),
    69: ("Al Jazeera card: all 41 men now free, plus a pipe diagram.", ["news_card", "diagram"]),
    70: ("Supply icons: medicines, mobile phones, chargers.", ["graphic", "icons"]),
    71: ("Green tunnel-cam frame, workers passing.", ["cctv", "tunnel_interior"]),
    72: ("Two dusty faces filling the frame.", ["faces", "detail"]),
    73: ("Red truck parked among trees, daylight.", ["truck", "road", "forest"]),
    74: ("Aaj Tak card over rockfall debris in the tunnel.", ["news_card", "rubble", "tunnel_interior"]),
    75: ("Workers with machinery at the face.", ["machinery", "workers"]),
    76: ("Green abstract close-up, out of focus.", ["abstract", "blur"]),
    77: ("Container cabins and site offices.", ["site", "containers"]),
    78: ("Sepia collage built from machine and team photos.", ["collage", "graphic"]),
    79: ("Dark chamber with ladders and scaffolding.", ["tunnel_interior", "dark", "ladders"]),
    80: ("Night silhouette of an excavator on the rubble pile.", ["night", "excavator", "rubble"]),
    81: ("Crowd gathered at the site, burned-in playback UI.", ["crowd", "site", "source_ui"]),
    82: ("Crowd, rapid montage frame.", ["crowd", "site"]),
    83: ("Crowd, rapid montage frame.", ["crowd", "site"]),
    84: ("Crowd, rapid montage frame.", ["crowd", "site"]),
    85: ("Crowd, rapid montage frame.", ["crowd", "site"]),
    86: ("Dark tunnel-cam with an on-screen menu.", ["cctv", "tunnel_interior", "source_ui"]),
    87: ("The Hindu card listing 25/26/27 November developments.", ["news_card", "text_heavy"]),
    88: ("Auger drill head with an operator, 'What is Rat-Hole Mining?' card.", ["machinery", "diagram", "news_card"]),
    89: ("Bright tunnel-cam frame.", ["cctv", "tunnel_interior"]),
    90: ("Muddy water running through forest ground.", ["nature", "water", "mud"]),
    91: ("Out-of-focus object, half a second.", ["abstract", "blur"]),
    92: ("Newspaper collage, torn edges.", ["newspaper_collage", "graphic"]),
    93: ("Worker cut-out over a Reuters headline about rat-hole mining.", ["newspaper", "workers", "text_overlay"]),
    94: ("Headline pushed larger.", ["newspaper", "text_overlay"]),
    95: ("'RAT-HOLE MINING IS A HAZARDOUS...' headline.", ["newspaper", "text_overlay"]),
    96: ("'...STATE OF MEGHALAYA' with the Reuters mark.", ["newspaper", "text_overlay"]),
    97: ("'COURT IN 2014 BANNED THE PRACTICE' headline.", ["newspaper", "text_overlay"]),
    98: ("Rat-hole mining footage: worker burrowing with hand tools.", ["mining", "workers", "tunnel_interior"]),
    99: ("Worker with a hand drill against the tunnel face, long hold.", ["drilling", "tunnel_interior", "workers"]),
    100: ("Dark pipe interior, light at the far end.", ["pipe", "tunnel_interior", "dark"]),
    101: ("Workers in yellow vests inside the tunnel.", ["tunnel_interior", "workers"]),
    102: ("Rescued men hugging, 'AFTER 17 DAYS' title on screen.", ["emotion", "people", "text_overlay"]),
    103: ("Hands cradling a white helmet, close detail.", ["detail", "helmet", "emotion"]),
    104: ("Workers pressed together, phone-shot.", ["workers", "crowd"]),
    105: ("Ambulance with red/blue lights at night.", ["ambulance", "night"]),
    106: ("'RESCUE OPERATION' red graphic collage.", ["graphic", "text_overlay", "collage"]),
    107: ("'RAT-HOLE MINERS' spotlight card over a newspaper page.", ["graphic", "newspaper", "text_overlay"]),
    108: ("Blurred figure caring for another person.", ["people", "blur"]),
    109: ("Group photo of the rescue team in orange suits.", ["photo", "team", "people"]),
    110: ("Agency crests: NDRF, Army, ITBP and others.", ["logo_card", "graphic"]),
    111: ("Ambulance on a night street, crowd around.", ["ambulance", "night", "crowd"]),
    112: ("Truck on a foggy mountain road.", ["truck", "road", "fog"]),
    113: ("Times of India card over Atal Tunnel south portal.", ["news_card", "tunnel_portal"]),
    114: ("Atal Tunnel graphic with a map and an article card.", ["graphic", "map", "news_card"]),
    115: ("Atal Tunnel interior, yellow sodium light.", ["tunnel_interior"]),
    116: ("Raw tunnel shell under construction.", ["construction", "tunnel_interior"]),
    117: ("Tunnel interior with machinery at the face.", ["tunnel_interior", "machinery"]),
    118: ("Aerial of excavators cutting a hillside bench.", ["aerial", "excavation", "machinery"]),
    119: ("Wide misty mountains, breather shot.", ["mountains", "nature", "wide"]),
    120: ("Times of India card: the DPR / alignment audit.", ["news_card", "text_heavy"]),
    121: ("Arm reaching into a hole in the rubble.", ["rescue", "detail", "rubble"]),
    122: ("'Proposed Char Dham highway' map graphic.", ["map", "graphic"]),
    123: ("Supreme Court of India building.", ["building", "india"]),
    124: ("White glare / abstract wash, 26 seconds.", ["abstract", "white"]),
    125: ("'WATER POWER' card over an earlier tunnel rescue in water.", ["news_card", "workers", "water"]),
    126: ("End card: Mighty Monk logo, subscribe dots, yellow background.", ["end_card", "logo", "outro"]),
}

TEXT_NOTES = {
    11: ["DECEMBER, 2016"],
    15: ["12 NOVEMBER"],
    28: ["Aaj Tak explainer card (oxygen/food pipeline)"],
    29: ["4-INCH (pipe diameter callout)", "Aaj Tak explainer card"],
    31: ["Hindustan: 'Rescue operation underway to save workers after tunnel collapse'"],
    37: ["Aaj Tak explainer card"],
    40: ["दिनांक / दिनांक 12 नवंबर 2023 (news card)"],
    46: ["THE HINDU article card"],
    49: ["HOPE FLOATS ON 6 INCHES (Mirror Now)"],
    53: ["moneycontrol card"],
    55: ["NDRF · SILKYARA TUNNEL COLLAPSE"],
    56: ["Aaj Tak lower third"],
    60: ["INTERNATIONAL TUNNEL EXPERT ARNOLD DIX ARRIVED IN UTTARKASHI..."],
    61: ["EXPERT ARNOLD DIX ARRIVED IN UTTARKASHI (Dainik Bhaskar)"],
    63: ["ARNOLD DIX ARRIVED IN..., SURVEY, TWO SITES FOR VERTICAL DRILLING"],
    69: ["ALJAZEERA: India tunnel rescue updates: All 41 men trapped in Uttarakhand now free"],
    70: ["MEDICINES · MOBILE PHONES · CHARGERS"],
    74: ["Aaj Tak card"],
    87: ["THE HINDU: November 25 / 26 / 27 updates"],
    88: ["What is Rat-Hole Mining? (Aaj Tak)"],
    93: ["RAT-HOLE MINING IS HAZARDOUS AND CONTROVERSIAL (Reuters)"],
    95: ["RAT-HOLE MINING IS A HAZARDOUS METHOD USED EXTENSIVELY"],
    96: ["...NORTHEASTERN STATE OF MEGHALAYA (Reuters)"],
    97: ["COURT IN 2014 BANNED THE PRACTICE"],
    102: ["AFTER 17 DAYS"],
    106: ["RESCUE OPERATION"],
    107: ["RAT-HOLE MINERS"],
    113: ["ATAL TUNNEL, SOUTH PORTAL, ROHTANG (The Times of India)"],
    114: ["Atal Tunnel infographic + TOI card"],
    120: ["THE TIMES OF INDIA: DPR audit / alignment card"],
    122: ["Proposed Char Dham highway"],
    125: ["WATER POWER"],
    126: ["MIGHTY MONK (channel end card)"],
}


def clean_caption(text):
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def load(name):
    with open(os.path.join(ANA, name), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    shots = load("shots.json")["shots"]
    subs = [{"start": c["start"], "end": c["end"], "text": clean_caption(c["text"])}
            for c in load("subs.json") if clean_caption(c["text"])]
    audio = load("audio.json")
    ocr = load("ocr.json")

    def overlaps(a, b, c, d):
        return a < d and c < b

    speech = [(c["start"], c["end"]) for c in subs]

    def under_speech(t):
        return any(a - 0.12 <= t <= b + 0.12 for a, b in speech)

    # Onsets inside a caption cue are speech articulation, not sound design.
    sfx_kept = [e for e in audio["sfx"] if not under_speech(e["time"])]
    sfx_dropped = len(audio["sfx"]) - len(sfx_kept)

    onset_times = [e["time"] for e in audio["sfx"]]
    cut_onsets = sum(
        1 for s in shots[1:]
        if any(abs(t - s["start"]) <= 0.15 for t in onset_times)
    )

    voice_total = 0.0
    for s in shots:
        cues = [c for c in subs if overlaps(c["start"], c["end"], s["start"], s["end"])]
        voice_total += sum(min(c["end"], s["end"]) - max(c["start"], s["start"]) for c in cues)
        s["voiceover"] = bool(cues)
        s["voiceover_cues"] = [{"start": c["start"], "end": c["end"], "text": c["text"]} for c in cues[:4]]

        s["music"] = any(overlaps(m[0], m[1], s["start"], s["end"]) for m in audio["music_runs"])
        s["sfx"] = [e for e in sfx_kept if s["start"] <= e["time"] < s["end"]]

        prev_end = None
        idx = s["index"]
        if idx == 1:
            trans = {"type": "fade_in_from_black"}
        elif s["luma_start"] is not None and s["luma_start"] < 24 and s["luma_mean"] > 45:
            trans = {"type": "fade_in_from_black", "cut_score": s.get("cut_score")}
        elif s["luma_end"] is not None and s["luma_end"] < 24 and s["luma_mean"] > 45:
            trans = {"type": "fade_out_to_black", "cut_score": s.get("cut_score")}
        elif (s.get("cut_score") or 0) >= 0.45:
            trans = {"type": "hard_cut", "cut_score": s.get("cut_score")}
        else:
            trans = {"type": "cut_or_soft_cut", "cut_score": s.get("cut_score")}
        s["transition_in"] = trans

        texts = [{"text": t, "position": "news_card" if "card" in t.lower() or "article" in t.lower() else "lower_third",
                  "persistence": "whole_shot", "source": "observer"}
                 for t in TEXT_NOTES.get(idx, [])]
        raw = ocr.get(f"{idx:03d}", "")
        s["ocr_text_sample"] = raw[:160] if raw else ""
        s["text_overlays"] = texts

        visual, tags = VISUALS.get(idx, ("(no description captured)", []))
        s["visual"] = visual
        s["visual_tags"] = tags

        # drop helper fields we do not want in the deliverable
        for k in ("luma_mean", "luma_start", "luma_end", "cut_score"):
            s.pop(k, None)

    durs = sorted(s["duration"] for s in shots)
    n = len(durs)
    median = durs[n // 2] if n % 2 else (durs[n // 2 - 1] + durs[n // 2]) / 2
    buckets = {"0-1s": 0, "1-3s": 0, "3-6s": 0, "6-10s": 0, "10-20s": 0, "20s+": 0}
    for d in durs:
        if d < 1: buckets["0-1s"] += 1
        elif d < 3: buckets["1-3s"] += 1
        elif d < 6: buckets["3-6s"] += 1
        elif d < 10: buckets["6-10s"] += 1
        elif d < 20: buckets["10-20s"] += 1
        else: buckets["20s+"] += 1

    doc = {
        "source": {
            "url": "https://youtu.be/N71y5expfBo",
            "title": "India's Biggest Tunnel Rescue: Uttarkashi Tunnel Disaster",
            "channel": "Mighty Monk",
            "video_id": "N71y5expfBo",
            "upload_date": "2026-10-07",
            "view_count_at_analysis": 105443,
            "duration_s": 1322.353,
            "fps": 29.97,
            "analyzed_resolution": "1920x1080 (frames), 640x360 (luma), audio 48k stereo",
        },
        "method": {
            "download": "yt-dlp 2026.08.19 (bestvideo<=1080p + bestaudio, merged to mp4)",
            "shot_detection": "ffmpeg select=gt(scene\\,0.24) at 480px, twin detections merged at 0.4 s",
            "frames": "one still per shot at 45% of the shot, 1280 px wide",
            "transitions": "cut score + per-shot luma start/end vs mean (fade-to-black detection)",
            "voiceover": "YouTube Hindi auto-captions (522 deduped cues) — cue windows, not speaker diarisation",
            "audio_events": "mono 16 kHz: RMS, spectral flatness, autocorrelation pitch strength; music/sfx are heuristics",
            "text": "tesseract OCR on every still + manual read of the contact sheets",
            "limitations": [
                "Slow dissolves/fades are gradual, so a boundary that ffmpeg scores below 0.24 is missing from the shot list.",
                "Music/SFX labels are heuristic: a continuous score under narration reads as music; isolated sound design is indistinguishable from speech onsets in a loudness-normalised mix.",
                "Only 1 onset survived outside the narration windows, so per-shot SFX should be read as 'none detected', not 'none exists'.",
                "Text timings are 'whole shot' — the exact in/out of a text card was not measured frame by frame.",
                "OCR of Hindi cards is unreliable; Hindi strings above were read by eye from the stills.",
                "Shots containing burned-in source UI (playlist overlay, 'SP', timestamps) are marked source_ui.",
            ],
        },
        "summary": {
            "shot_count": n,
            "cut_count": n - 1,
            "cuts_per_minute": round((n - 1) / (shots[-1]["end"] / 60), 2),
            "median_shot_s": round(median, 2),
            "mean_shot_s": round(sum(durs) / n, 2),
            "shortest_s": round(min(durs), 2),
            "longest_s": round(max(durs), 2),
            "duration_histogram": buckets,
            "voiceover_coverage_pct": round(voice_total / shots[-1]["end"] * 100, 1),
            "music_runs": len(audio["music_runs"]),
            "silence_runs": len(audio["silent_runs"]),
            "sfx_events": len(sfx_kept),
            "sfx_onsets_under_narration_discarded": sfx_dropped,
            "cuts_with_audio_onset_within_150ms": cut_onsets,
            "cuts_with_audio_onset_pct": round(cut_onsets / max(1, len(shots)) * 100, 1),
            "pacing_note": (
                f"Median shot is {median:.1f}s, which sits inside a 5-8 s design window, but the "
                "distribution is bimodal rather than uniform: "
                f"{buckets['10-20s'] + buckets['20s+']} shots run 10 s or longer "
                f"({buckets['20s+']} over 20 s, max {max(durs):.0f} s) while "
                f"{buckets['0-1s'] + buckets['1-3s']} shots are shorter than 3 s. "
                "The short ones cluster around newspaper headlines; the long ones sit on a single "
                "news card or a still photo. Narration is near continuous, so the picture is allowed "
                "to rest while the voice carries the story."
            ),
            "style_notes": [
                "Cold open: 31 s night aerial of fireworks before any context lands.",
                "Still-heavy: news-article cards (The Hindu, TOI, moneycontrol, Al Jazeera, Aaj Tak) held 10-40 s, often with a slow push.",
                "Archive TV and phone footage used raw, with burned-in watermarks, timestamps and playback UI left in.",
                "Dates arrive as on-screen text, not as narration: 'DECEMBER, 2016', '12 NOVEMBER', 'AFTER 17 DAYS'.",
                "Graphics carry the facts: 25 km route map, '4-INCH' pipe callout, supply icons, agency crests.",
                "Emotional peak at 1090 s (rescue, 'AFTER 17 DAYS'), then back to context: Atal Tunnel, Char Dham, Supreme Court.",
                "Ends on an 18 s channel card (logo, subscribe dots).",
            ],
            "comparison_to_our_schema": {
                "our_scene_length": "5-8 s per scene, 16:9, 1920x1080@30, one image + optional lower third",
                "their_scene_length": f"median {median:.1f} s, mean {sum(durs) / n:.1f} s, range {min(durs):.1f}-{max(durs):.1f} s",
                "gap": (
                    "Our schema's 5-8 s is right for the median, but it has no way to express what this "
                    "video does with the other 40% of its shots: hold one still or one news card for "
                    "10-50 s while narration explains it. Nor does it cover the 0.4-1 s headline bursts."
                ),
                "feed_for_schema": [
                    "Add a `still_card` (or `hold`) animation_type for article/headline cards; they are ~30% of this video.",
                    "Allow a scene to carry multi-line card text, not just one lower-third line.",
                    "Keep Ken Burns as the default treatment: most shots here are slow pushes on stills, archive stills and phone frames.",
                    "Add `source_credit` per scene: archive TV, phone footage, news screenshot, agency graphic.",
                    "Add an optional `card_image` field so the news card itself is the visual (they are literal screenshots with logos).",
                    "Bimodal pacing needs a per-scene override, not one global scene length: 5-8 s for montage, 15-40 s for explainer cards.",
                ],
            },
        },
        "shots": shots,
        "voiceover_segments": subs,
        "music_segments": audio["music_runs"],
        "silent_segments": audio["silent_runs"],
        "sfx_events": audio["sfx"],
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote", OUT)
    print("shots:", n, "| median:", median, "| voiceover %:", doc["summary"]["voiceover_coverage_pct"])


if __name__ == "__main__":
    main()
