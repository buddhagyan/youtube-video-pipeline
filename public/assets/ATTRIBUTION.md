# Demo assets

These files are only here so the compositions have something real to render.
They are not part of the final video.

All three are works of the U.S. federal government (NASA), public domain.
They were downloaded from Wikimedia Commons at 1920 px wide.

## `assets/voyager-1-launch-1977.jpg`

| | |
|---|---|
| Subject | Voyager 1 lifting off on a Titan IIIE-Centaur, 5 September 1977 |
| Source | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Voyager_1_Launch.jpg) |
| Author | NASA on The Commons |
| License | Public domain |
| Original | 2355×3000 (portrait) |

## `assets/voyager-golden-record-gold-plating.jpg`

| | |
|---|---|
| Subject | Gold-plating one of the Voyager Golden Records, 23 August 1977 |
| Source | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Voyager-golden-record-gold-plating-8-23-77_30217620534_o.jpg) |
| Original | [NASA/JPL — Making of the Golden Record](https://voyager.jpl.nasa.gov/golden-record/making-of-the-golden-record/) |
| Author | NASA/JPL |
| License | Public domain |
| Original | 2828×2172 |

## `assets/pale-blue-dot-1990.jpg`

| | |
|---|---|
| Subject | *Pale Blue Dot* — Earth from 6 billion km, taken by Voyager 1 on 14 February 1990 |
| Source | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Pale_Blue_Dot_from_Voyager_1_-_PIA23645.png) |
| Author | NASA/JPL-Caltech |
| License | Public domain |
| Original | 5230×5175 |

## `assets/news-card-1977.png`

| | |
|---|---|
| What it is | A **synthetic** 1977 newspaper page, drawn from scratch for the `still_card` test |
| Made by | `scripts/make_card_asset.py` (PIL + system fonts) |
| Words | Original text written for this repo — not copied from any publication |
| Photo inside | NASA/JPL launch photo above (public domain) |
| Masthead | "The Daily Record" is a fictional outlet, close to the Mighty Monk card style |

It exists so `NewsCard` has an article-shaped image to hold. Replace it with a
real clipping when the news-card pipeline lands.

## Cropping note

The video is 16:9. The launch photo is portrait (2355×3000) and the other two are
close to square, so `objectFit: cover` crops top and bottom. Per-scene
`focalPoint` in `src/assets.ts` decides which part stays in frame. That is
expected for a stills-driven documentary cut.

`still_card` scenes do **not** crop: `NewsCard` fits the page by height (or width)
inside the 16:9 frame, leaving black around it, exactly as the reference films do.
