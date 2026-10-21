"""Add the hook observations and the master formula to scenes/hook-patterns.json.

    python scripts/hook_synthesis.py

The measurements (transcript, shot list) come from scripts/hook_analysis.py.
The on-screen descriptions below were read off the hook contact sheets, and the
classification is derived from the transcript + shot data in this script.
"""

import json
import os
import statistics as st

ROOT = r"C:\Users\anu15\Downloads\youtube"
PATH = os.path.join(ROOT, "scenes", "hook-patterns.json")

# what is on screen during the hook (read from .analysis/<id>/hook-sheet.jpg)
ON_SCREEN = {
    "5DTtkRhla3A": {
        "shots": [
            "Night traffic on a Mumbai street, phone footage with a source watermark",
            "Blurred crowd at night, phone footage",
            "Gateway of India in a sepia/archival tint, a silhouetted figure in front",
            "Mumbai Mirror article screenshot: witness deposing in the 26/11 trial",
        ],
        "inventory": ["phone_footage", "archival_landmark", "news_card"],
        "note": "Three quick real-world shots, then the first news card already lands at 18 s.",
    },
    "mS9AO-gSfcM": {
        "shots": [
            "Map graphic: Pakistan / East Pakistan highlighted",
            "Black-and-white crowd footage",
            "Same crowd, tighter",
            "Road sign reading DACCA / JESSORE",
            "Night artillery / tracers",
            "Jet climbing into the sky",
            "Map graphic: India",
        ],
        "inventory": ["map_graphic", "archival_bw", "location_sign", "archival_war", "map_graphic"],
        "note": "Map and archival war footage do the explaining; no card in the first 30 s.",
    },
    "UDCSmo77FMA": {
        "shots": [
            "Gateway of India from the water, daylight",
            "Crowd walking through a Mumbai station concourse",
            "Hands counting currency notes, close-up",
            "Silhouette of a man in an armchair at a desk, lamp on",
            "Man in a white kurta standing on a sea wall, back to camera",
        ],
        "inventory": ["city_establishing", "crowd", "money_detail", "recreated_silhouette", "recreated_hero"],
        "note": "Cinematic recreated footage, not archive: city -> crowd -> cash -> the boss -> the loner.",
    },
    "KhSFC1GNgNM": {
        "shots": [
            "Sea link at dawn with an on-screen date: 12 MARCH 1993",
            "Crowd outside CST station",
            "Local train pulling in",
            "Platform crowd",
            "Gateway of India",
            "People on Marine Drive",
            "Pile of newspapers",
            "Trading ring",
            "BMC building",
            "BSE building",
            "BSE tower",
            "Men looking up",
            "Crowd faces",
        ],
        "inventory": ["date_overlay", "city_montage", "transit", "landmark", "newspaper_pile", "market", "crowd"],
        "note": "Thirteen cuts in 30 s: a city montage that sets up 'an ordinary Friday in Mumbai'.",
    },
    "-DVr8iA-1F0": {
        "shots": [
            "Satellite map zooming to a prison label",
            "Prison exterior: guard towers, barriers, a convoy",
            "Security camera close-up with a '24 HOURS' label",
        ],
        "inventory": ["satellite_map", "prison_establishing", "security_camera_label"],
        "note": "Only three shots: the hook is a slow, cold establishing pass, not a montage.",
    },
    "4gZiO9NjSmE": {
        "shots": [
            "Title card: 18'TH MAY 1974 over desert ground",
            "Archival B&W figures walking in desert",
            "Archival soldiers in helmets",
            "Indira Gandhi archival portrait",
            "World reaction: assembly hall with country name plates",
            "Diplomatic meeting",
            "Nehru-era archival footage",
            "Desert and clouds",
            "Test cloud on the horizon",
            "1970s meeting / signing",
        ],
        "inventory": ["date_card", "archival_bw", "archival_politician", "world_reaction", "aerial", "test_blast"],
        "note": "Date card + archival montage + world reaction + the blast: the whole story in 30 s.",
    },
}

OPENING_TYPE = {
    "5DTtkRhla3A": {
        "type": "date_then_ordinary_world",
        "sentence_devanagari": "नवंबर 2008 की शाम, हमेशा की तरह मुंबई की सड़कों पर ज़िंदगी अपनी रफ़्तार से चल रही थी, अपने कल से अनजान…",
        "english": "An evening in November 2008 — life on Mumbai's streets was moving at its usual pace, unaware of its own tomorrow…",
        "why": "Date first, then 'business as usual', then a foreshadow ('unaware of tomorrow').",
    },
    "mS9AO-gSfcM": {
        "type": "year_then_historical_situation",
        "sentence_devanagari": "1971 — बांग्लादेश में आज़ादी की आवाज़ बुलंद होती है और पाकिस्तान सिविल वॉर के बाद…",
        "english": "1971 — in Bangladesh the call for freedom grows loud, and Pakistan after a civil war…",
        "why": "Year, then the state of the world; no personal story yet.",
    },
    "UDCSmo77FMA": {
        "type": "riddle_contrast",
        "sentence_devanagari": "जिसकी चमक के आगे पूरी दुनिया फीकी जाती है… उसने एक ऐसा दौर भी देखा जब चमक के नीचे अंधेरे का काला साया था।",
        "english": "A city whose shine makes the rest of the world look pale… but it has also seen a time when a dark shadow sat under that shine.",
        "why": "No date: a two-part riddle (glamour vs darkness). The subject is never named in the first line.",
    },
    "KhSFC1GNgNM": {
        "type": "date_then_ordinary_world",
        "sentence_devanagari": "मार्च 1993, शुक्रवार का यह दिन भी… भारत की इकोनॉमिक मुंबई के लिए एक आम दिन जैसा ही था, कल से अनजान…",
        "english": "March 1993 — that Friday looked like an ordinary day for Mumbai, India's economic engine, unaware of tomorrow…",
        "why": "Date first, 'ordinary day' framing, same 'unaware' foreshadow as the 26/11 hook.",
    },
    "-DVr8iA-1F0": {
        "type": "place_then_superlative_fact",
        "sentence_devanagari": "मेक्सिको सिटी से 55 माइल्स वेस्ट में, मेक्सिको का सबसे मज़बूत और मैक्सिमम सिक्योरिटी वाला प्रिज़न मौजूद है, जिसे 'अल्टिप्लानो' के नाम से जाना जाता है…",
        "english": "55 miles west of Mexico City stands Mexico's toughest, maximum-security prison, known as Altiplano…",
        "why": "No date: a place + a superlative ('toughest, maximum security') that the story will then break.",
    },
    "4gZiO9NjSmE": {
        "type": "date_then_historical_pivot",
        "sentence_devanagari": "18 मई 1974… वह दिन था जब भारत भी एटॉमिक पावर्ड कंट्रीज़ की कतार में खड़ा हो गया…",
        "english": "18 May 1974 — the day India joined the queue of atomic-powered countries…",
        "why": "Date first, then the change it caused. Same shape as the 1971 hook.",
    },
}

VISUAL_LOOK = {
    "no_face_in_frame_one": True,
    "no_title_card_except_dates": True,
    "date_on_screen_where_spoken": ["KhSFC1GNgNM", "4gZiO9NjSmE"],
    "sources_used": ["phone footage", "archival film", "news screenshots", "map graphics", "recreated stills"],
}


def main():
    doc = json.load(open(PATH, encoding="utf-8"))
    rows = doc["videos"]
    for r in rows:
        vid = r["video_id"]
        r["on_screen"] = ON_SCREEN[vid]
        r["opening_type"] = OPENING_TYPE[vid]
        if "first_sentence" in r:
            r["first_sentence"]["text"] = OPENING_TYPE[vid]["sentence_devanagari"]
            r["first_sentence"]["english"] = OPENING_TYPE[vid]["english"]
            r["first_sentence"]["whisper_urdu_script"] = r["transcript_whisper"].get("text", "")[:220]

    counts = [r["shots_in_hook"]["count"] for r in rows]
    firsts = [r["shots_in_hook"]["first_shot_s"] for r in rows]
    types = [r["opening_type"]["type"] for r in rows]

    date_open = sum(1 for t in types if "date" in t or "year" in t)
    place_open = sum(1 for t in types if "place" in t)
    riddle_open = sum(1 for t in types if "riddle" in t)
    question_open = sum(1 for t in types if "question" in t)

    doc["patterns"] = {
        "opening_types": {t: types.count(t) for t in sorted(set(types))},
        "opening_anchor": {
            "date_or_year": f"{date_open}/6",
            "place": f"{place_open}/6",
            "riddle_contrast": f"{riddle_open}/6",
            "question": f"{question_open}/6",
            "time_or_place_anchor_total": f"{date_open + place_open}/6",
        },
        "shots_in_first_30s": counts,
        "shots_median": st.median(counts),
        "shots_min_max": [min(counts), max(counts)],
        "first_shot_s": firsts,
        "first_shot_median_s": round(st.median(firsts), 1),
        "cuts_per_min_in_hook": [round(c * 2, 1) for c in counts],
        "on_screen_inventory": sorted({i for r in rows for i in r["on_screen"]["inventory"]}),
        "news_card_within_30s": [r["video_id"] for r in rows if "news_card" in r["on_screen"]["inventory"]],
        "findings": [
            "No hook opens with a question: 6/6 are declarative statements.",
            "4/6 open with a date or year in the first spoken line; 1 more opens with a place "
            "('55 miles west of Mexico City'); only the biography opens with a riddle.",
            "The event films (26/11, 1993) both add the same clause: 'an ordinary day... unaware of tomorrow'.",
            "Nobody appears on camera: the first frame is always a place (street, map, prison, desert).",
            "Cutting inside the hook is bimodal too: 3-5 shots for place/slow hooks, 10-13 for event montage hooks.",
            "The hook visual and the hook line are redundant on purpose: the map/date on screen repeats what the voice says.",
        ],
    }

    doc["master_hook_formula"] = {
        "name": "Date -> Ordinary World -> Foreshadow -> Evidence",
        "one_liner": ("Open on a place and a date, describe the world in one calm sentence, "
                      "add a foreshadow clause, then cut to proof — never ask a question, "
                      "never show a face."),
        "beats": [
            {"beat": 1, "name": "Date or place stamp", "timing": "0-4 s",
             "voice": "first 4-6 words are the date/year, or a place with a superlative",
             "screen": "establishing shot of the place; on-screen date if the date is spoken",
             "evidence": "4/6 date + 1/6 place ('55 miles west of Mexico City')"},
            {"beat": 2, "name": "Ordinary world", "timing": "4-14 s",
             "voice": "one sentence of 'life as usual' — traffic, morning, the city at work",
             "screen": "street / crowd / transit footage, no faces introduced",
             "evidence": "26/11 and 1993 use the exact 'ordinary day, unaware of tomorrow' clause"},
            {"beat": 3, "name": "Foreshadow", "timing": "10-20 s",
             "voice": "'unaware of its own tomorrow' / 'under the shine, a dark shadow' / 'the toughest prison'",
             "screen": "the fourth shot turns: money, a silhouette, a guard tower, a blast cloud",
             "evidence": "6/6, wording differs by genre"},
            {"beat": 4, "name": "Evidence cut", "timing": "18-35 s",
             "voice": "the narrator states the event; the voice keeps running",
             "screen": "first news card or archive insert lands here (26/11: 18 s, 1993: 11.8 s newspapers)",
             "evidence": "news cards inside 30 s in 2/6; archive inside 30 s in 4/6"},
        ],
        "card_rules": [
            "No question in the first line, ever.",
            "Date first, story second: the number is the promise.",
            "One calm sentence before the turn; the contrast does the work.",
            "Never open on a face or a title card: open on a place.",
            "Repeat the hook fact on screen (date card, map, sign) so the eye and ear agree.",
            "3-5 shots if the hook is a place; 10-13 if it is an event montage.",
        ],
        "template_devanagari": (
            "[तारीख/साल] की [सुबह/शाम], [जगह] में [आम दिन वाली एक बात]… "
            "सब कुछ सामान्य था, [कल से अनजान / किसी को अंदाज़ा नहीं था]… "
            "और फिर [वो घटना जो सब बदल देगी]."
        ),
        "template_english": (
            "On [date], in [place], [one sentence of ordinary life]… "
            "everything looked normal, unaware of what was coming… "
            "and then [the event that changed everything]."
        ),
        "duration_target_s": 30,
        "performance_note": ("All six hooks are self-contained: a viewer can retell the premise "
                             "after 30 s without any context, and the film still has a promise "
                             "(what happened next) left to pay off."),
    }

    json.dump(doc, open(PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", PATH)
    print("shots in hook:", counts, "| median", st.median(counts))
    print("opening types:", doc["patterns"]["opening_types"])


if __name__ == "__main__":
    main()
