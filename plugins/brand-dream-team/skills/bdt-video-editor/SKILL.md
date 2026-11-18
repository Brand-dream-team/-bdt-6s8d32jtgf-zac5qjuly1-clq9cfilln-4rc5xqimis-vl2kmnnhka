---
name: bdt-video-editor
description: Use when a creator sends Brand Dream Team Studio picks ("Brand Dream Team: edit my video", "B-roll Matchmaker", "edit my vlog"), attaches a talking video to edit into a Reel/TikTok/Short, asks to edit everything in their Raw footage folder, or wants several videos or versions edited at once. If they ask how or where to edit but sent no video, use the brand-dream-team-setup skill (Step 5) instead.
---

# Brand Dream Team: Video Editor

You edit a creator's videos into finished vertical (1080×1920) videos in the style they picked in the Brand Dream Team Studio: pauses cut out, captions, an on-screen hook, effects tied to what they say. Their original files are never changed, moved or deleted.

## 0. Where the videos are

- **Attached in the chat** (phone or computer): use the attached files.
- **"Edit everything in Raw footage"** (Claude desktop app): read `Desktop/Brand Dream Team/Raw footage/`. Edit only videos that don't already have a finished version in `Ready to post`. Save finished videos to `Desktop/Brand Dream Team/Ready to post/` named `<YYYY-MM-DD> <short title>.mp4`. If you can't reach their files, tell them to attach the videos or say *Set up my Brand Dream Team folders* in the desktop app.
- B-roll lives in `Desktop/Brand Dream Team/B-roll/` (sorted into topic folders) or comes attached.

Work in a project folder per video (e.g. `projects/<short-name>/`). Deliver finished files in the chat (and to `Ready to post` when using folders).

## 1. Read the picks

Studio picks arrive as lines like `Preset: Pink Pop`, `Colors: Guided Blush (...)`, `Captions: ...`, `Effects: ...`, `Floating cards: ...`, `Post caption: ...`. Follow them. If there are no picks, ask only what's missing with tap options: preset (Soft Glass, Bold Highlight, Pink Pop, Typewriter, Pink Label, Chunky Word) and colors (default: their Brand DNA colors, else Guided Blush). `palettes.json` has every palette's role colors.

## 2. Prepare each video

```
python3 scripts/prepare.py "<video>" "<project>"
```
Works with any phone, camera or laptop video (DJI Osmo, GoPro, iPhone, Android; .mp4 .mov .mts .mkv; HEVC, 10-bit, HDR, landscape or sideways). It makes `<project>/source.mp4` (vertical 1080×1920, 30 fps, SDR) and prints its path: **use `source.mp4` as `src` everywhere, never the original file.** Then it writes `mine.wav` and `words.json` and prints the transcript as `index:word@seconds`. If a phone upload fails because the file is too big (4K camera files often are), tell them to export it at 1080p in their camera app (e.g. DJI Mimo) and attach that, or use the Raw footage folder on their computer. Find where speech starts and ends (`ffmpeg -i <project>/mine.wav -af silencedetect=noise=-32dB:d=0.3 -f null -`). If tools can't install or the speech model can't download, say so plainly and stop. Never fake an edit.

## 3. Storyboard first (always)

Read the transcript like an editor and show the storyboard **in chat**: the hook, highlighted words, each effect and the line it lands on, zoom punches, any floating cards and which clip each uses, and any transcript words you're unsure of. Wait for a yes. Never make a spreadsheet or document for it.

## 4. Write `<project>/edit.json`

```json
{
 "src": "<project>/source.mp4", "output": "<name>.mp4",
 "start": 0.3, "end": 59.8,
 "fixes": {"12": "everyone's", "13": ""},
 "emphasis": ["purpose", "today", "yes"],
 "palette": {"accent": "#F5BACB", "on_accent": "#0A0A0A", "accent_on_dark": "#F5BACB", "ghost": "#F5BACB"},
 "hook": {"line1": "Stop waiting for", "line2": "clarity.", "dur": 3.0},
 "cards": [],
 "zoom_punch": [{"at": "move your feet", "hold": 0.8}]
}
```
- **fixes:** correct misheard words by index (`""` deletes). Obvious fixes only.
- **emphasis:** 6 to 12 strong words.
- **palette:** the 4 role colors from `palettes.json`. For `Colors: My brand (#a, #b, #c, #d)` (their own Brand DNA colors, in the order main, second, light, dark), build it from those codes: `accent` = main, `on_accent` = dark if it reads on main (else white), `accent_on_dark` = main (the scripts lighten it if it's too dark for video), `ghost` = main.
- **look:** always set it to their preset (soft_glass, bold_highlight, pink_pop, typewriter, pink_label, chunky_word). Every effect, card and caption draws in that preset's fonts.
- **hook_font:** the `Hook font:` line from their Studio picks, copied exactly (e.g. `"hook_font": "Wide + Flourish"`). It sets the hook title and every big accent word (captions' accent words, effect titles, the YouTube look); regular captions stay the preset's. All 25 Studio fonts ship in fonts/, so this works offline. Always set it when the picks include a font.
- **brand_fonts (optional):** when their Brand DNA names their own fonts, run `python3 scripts/get_font.py "<Font Name>"` (Google Fonts) or use a font file they attach, then set `"brand_fonts": {"bold", "black", "semi", "med", "accent"}` (file names in fonts/ or full paths; `[file, weight]` for variable fonts, e.g. `["Montserrat[wght].ttf", 700]`). Captions, cards, all 35 effects and the YouTube look then use their fonts. Symbols their font lacks (♡ ✓) fall back automatically.
- **Brand rule:** colors and fonts always come from the creator's own palette and preset (scripts/brand.py). Never hand-pick Destiny's pinks or fonts for someone else. Dark accents are lightened automatically for text over video, and text on accent buttons stays readable.
- **hook (always):** a short title tied to the video. Soft Glass: `line1`, `line2` (+ optional `emoji_left`, `emoji_right`), `dur` ≈ 3. Bold Highlight: `line1`, `line2` (highlight box), optional `sub`, `dur` ≈ 6. Pink Pop: the last word of `line2` becomes the giant pop word; optional `pink_sub`.
- **zoom_punch:** 2 to 4 on the strongest lines.

## 5. Render by preset

Build the cut base once per video, then render the preset:
```
python3 scripts/make_base.py "<project>"     # Pink Pop, Typewriter, Pink Label and Chunky Word (Soft Glass / Bold build it themselves)
python3 scripts/soft_glass.py "<project>"
python3 scripts/bold_highlight.py "<project>"
python3 scripts/pinkpop.py "<project>"
python3 scripts/pink_label.py "<project>"
python3 scripts/chunky_word.py "<project>"
python3 scripts/typewriter.py "<project>/timeline_words.json" "<project>/base.mp4" "<project>/plan.json" "<project>/out/<name>.mp4"
```
Output goes to `<project>/out/`.

### Soft Glass and Bold Highlight: `cards`
3 to 6 pop-ups, each tied to a phrase (`at` = exact lowercase words from the transcript; optional `after`, `offset`, `dur`). Types:
- Both: `search` (`queries`: [{`text`, `at`}]), `progress` (`label`), `notification` (`title`, `body`), `bubble` (`text`, `mine`, `right`, `tilt`), `pill` (`text`, `tilt`, `y`).
- Bold Highlight adds: `dark_pill` (`text`), `dark_note` (`title`, `body`), `icon_pop` (`kind`: cross or sparkle), `calendar` (`chips`: [{`text`, `at`}]).
Keep pop-ups out of the hook's first seconds. Never stack two at once. Don't use `sticky`.

### Studio effects (`fx`, any preset): all 35 are automatic
When the picks name effects from the Studio library, add an `fx` list to edit.json and burn them into the base **before** the preset:
```
python3 scripts/make_base.py "<project>"
python3 scripts/fx_live.py "<project>"     # keeps base_clean.mp4, writes base.mp4 with the effects
python3 scripts/<preset>.py "<project>"
```
Each entry has `type` and `at` (exact lowercase words from the transcript; optional `after`, `offset`, `dur`). All text comes from what they say; all colors come from their palette accent. Studio names work as types too (e.g. "Push-back reveal").

Also add to edit.json when used:
- `brand`: {`name`, `first_name`, `handle`, `bio`}, taken from their HQ or picks. Used by Phone mock-up, Frame break and Name intro.
- `photos`: paths to any pictures or screenshots they attached. A `photos/` folder in the project works too.
- `broll`: a few of their B-roll videos from the library. Sharp stills are pulled from them when there aren't enough photos, and from their own video as a last resort.

**Cards and text**
- `timer` (Timer card): `line`, `accent`, `done`, `from_secs`, `to_secs`
- `chart` (Chart grow): `title`, `labels`, `values` (0 to 1)
- `graph` (Glass graph): `label`, `value`
- `sales` (Sale notifications): `app`, `title`, `body`, `count`
- `notify` (iPhone notification): `app`, `title`, `body`
- `comment` (Pinned comment): `handle`, `text`
- `prompt` (Prompt box): `text`, optional `header`
- `terminal` (Terminal): `title`, `command`, `items`, `tag`
- `article` (Highlighted article): `lines`, `highlight`
- `step` (Step header): `step`, `title`, `sub`
- `led` (LED word): `word`
- `checklist` (Checklist): `title`, `items` (up to 5, tick off one by one)
- `labels` (Labels): `items` (2 to 3 short qualities)
- `feature_tags` (Feature tags): `items` (strings or {`text`, `icon`})
- `keyword_cloud` (Keyword cloud): `words` (up to 8 things they list)
- `text_thread` (Text thread): `contact`, `messages` [{`text`, `mine`}]
- `style_cards` (Style cards): `names` (2 to 4 options), optional `tag`; pictures from photos
- `before_after` (Before / after): `before` and `after`, each {`big`, `sub`}
- `name_intro` (Name intro): `name`, optional `hi`; two of their photos beside it
- `phone` (Phone mock-up): `name`, `bio`, `button`; avatar and grid from photos
- `screenshot` (Screenshot drop): `image` (their screenshot; otherwise one of their photos)
- `white_page` (White Page): `title`, `lines` (typed on a plain page while they keep talking)

**Camera (they're cut out so graphics can sit behind them)**
- `orbit` (Orbit): `word`; 3 photos circle them
- `glass_type` (Glass type): `word` rises behind them
- `cover_story` (Cover story): `title` masthead behind their head, `sub`, `side`
- `photo_wall` (Photo wall): 6 photos pin up behind them
- `doodle` (Doodle): white outline plus hand-drawn doodles
- `green_screen` (Green screen): `image` becomes the background, or a title card from `title`
- `frame_break` (Frame break): a frame drops and they stay in front of it; `handle`
- `paper_cut` (Paper cut): they become a cut-out on a notebook page; `tag`
- `vertigo` (Vertigo): the room pushes away behind them
- `push_back` (Push-back reveal): the video shrinks to a card with photos around it
- `zoom_through` (Zoom-through cut): zoom-blur into a flash, for a topic change
- `digital_zoom` (Digital zoom): black-and-white punch-in; `word`
- `shutter` (Shutter strike): flash, and the moment drops in as a print

Rules:
- One effect at a time (fx_live trims overlaps).
- None in the hook's first 3 seconds.
- 3 to 8 effects per video, each on the line it fits (the Studio's "best for" note).
- Captions hide automatically under full-screen and big-card effects.
- Camera effects need `onnxruntime` (the script installs it if missing). Without it they still render, just without the cutout.
- Text thread, Checklist and Labels can also be the preset's own `cards` (`bubble`, `pill`) if they asked for that look.

### Pink Pop: floating photo cards (`photos`)
Cards float in **right when the creator talks about that moment**, so they mean something. Never use stills of the creator's own talking video.
```json
"photos": [
 {"src": "<B-roll clip or photo>", "at": "living their life", "ss": 0.8},
 {"src": "<B-roll clip or photo>", "at": "move your feet", "ss": 1.0}
]
```
- `Floating cards: ... from my B-roll` → look at frames of their B-roll (`ffmpeg -ss 1 -i clip -frames:v 1 f.jpg`) and match 2 to 5 clips to things they actually say (family → family clip, "moving forward" → driving or walking clip). `ss` = the best moment in the clip.
- `... photos or clips I'm attaching` → use those, each at the line it fits.
- `none`, or no B-roll available → leave `photos` out. If B-roll is missing but they wanted cards, say so and offer to add them once they attach some.
- At most 2 cards on screen at once; each stays about 2.6 s.

### Typewriter: `plan.json`
```json
{"face_y": 330,
 "pages": [{"a": 0.0, "b": 2.3, "big": "CLARITY?", "small": "STOP WAITING FOR A SIGN"}],
 "splits": [{"a": 16.3, "b": 18.2, "broll": "<B-roll clip>", "crop_y": 360, "ss": 0}]}
```
Times are in the **cut** timeline (`timeline_words.json` `t` values). Pages: 1 to 3 white title pages (big word + small line) on key moments, the first one as the hook. Splits: 1 to 3 B-roll-on-top moments that match what they say (skip if no B-roll). Captions are typed on automatically.

### Pink Label
Caps captions 2 to 3 words at a time, pink text on solid black label boxes, centered just under the face; the hook shows in the same style, bigger, near the top for the first seconds. Text color = the palette `accent` (falls back to pink #F79EBB if the accent is too dark to read on black). Optional in `edit.json`: `label_text`, `label_box` (HEX), `caption_size` (small, medium, large), `caption_y` (default 1250), `hook_y` (default 360). Move `caption_y` up or down if a frame check shows the label covering the mouth or chin. No pop-up cards in this preset; zoom punches still apply.

### Chunky Word
One huge word at a time, tightly spaced, centered above the head (`word_y`, default 440; move it if a frame check shows it on the face). Words in `emphasis` switch to the creator's chosen color (the palette `accent`, or `word_accent` to override) and get a period when a pause follows: pick 4 to 8 punchline words. Hook: `line1` white, `line2` in their color, `dur` about 1.8.
Optional: `"name_intro": {"at": "hi I'm", "line": "i'm Destiny", "script": "Alexis", "dur": 2.2}` when they introduce themselves (big white line bottom right, script name in their color).

## 6. Check, then deliver

Grab 6 to 8 frames (`ffmpeg -ss <t> -i out.mp4 -frames:v 1 f.png`) and look at them: captions readable and off the face, nothing overlapping, hook not cut off, cards on the right moments. Fix and re-render if needed.

Deliver each video with a short note: preset, colors, hook, effects and where they land, any transcript guesses. Offer one tweak. If the picks include `Post caption`, write it from **their transcript** (what they actually said in this video, in their Brand DNA voice; never reuse the Studio's example caption) after they approve the edit, show it ready to copy, and save it to their HQ's `library` collection (Title, Type "Reel", Preset, Hook, Caption, Status "Ready to post", Created) if you have their **Dream Team HQ**.

**Close it out on their HQ board.** When the edits are delivered, find the matching Video Editor task in their HQ's `tasks` (Status "In progress", e.g. "Batch edit 5 videos") and set Status "Done" and DoneAt (now), plus an `activity` line "Finished: <task>". If you can't reach their HQ from this chat, end with: "All done! Tap Done on '<task>' in your HQ, and your Content Strategist will offer captions."

## 7. Batch and versions

- **Several videos at once:** prepare all, show one combined storyboard (one short block per video), wait for one yes, then render one at a time and deliver each as it finishes. Suggest 3 to 5 videos per sitting; more uses a lot of the creator's Claude usage.
- **"Give me 3 versions"** (or 2 to 5): same video, different hooks and opening, a different pick of effects, and (if asked) a different order of their own sentences. Name them `-v1`, `-v2`, `-v3`. Show all hooks in the storyboard first.
- Default is 1 version per video.

## 8. B-roll Matchmaker

For "Brand Dream Team: B-roll Matchmaker". The B-roll library is `Desktop/Brand Dream Team/B-roll/` (or a `B-roll` folder in the project when clips are attached). `library.json` there lists every sorted clip.

1. **Look:** `python3 scripts/broll_look.py <work>/look <new clips and photos...>` makes contact sheets (3 frames per clip, numbered) and `clips.json`. Read every sheet.
2. **Sort:** write `<work>/sort.json` (format at the top of `scripts/broll_sort.py`): a folder for each clip (their folder names if given, otherwise ones like Business, Motherhood, Faith, Lifestyle, Outfits, Food, Outside, Studio Spaces, Photos), a short `about` line, and `best` = [start, length] of its nicest steady 2 to 3 seconds. Mark clips that already have captions burned in, or are unusable, `"skip": true`. Then `python3 scripts/broll_sort.py <work>/sort.json`. It copies (never moves), never duplicates, and updates `library.json`. Tell them in one line what went where.
3. **Write first:** pick clips from the folder asked for (or the best fit) using `library.json` `about` lines, and write the text in their voice from their Brand DNA. Show the 3 versions (text plus which clips, in order) and wait for a yes.
   - **POV:** one line starting "POV:", 3 to 5 clips, about 2.2 s each.
   - **Prayer reel ("Girl pray" style):** when the creator asks for a prayer reel and their saved style is this one (Destiny's), set `"style": "girl_pray"` in `text`: a short header like "Girl pray," in a heavy rounded font in their pink (`header_color`) with a white outline, then the whole prayer in bold white (`body_color` "white") or light pink ("accent", `body_hex`), centered, tight lines, light dim. One line break between sentences, no blank lines, unless they ask.
   - **Long Thought:** two ways. **Full prayer** (default for prayers and longer thoughts): the whole text on screen at once, centered, footage dimmed, with an optional big header in the brand color with a white outline ("Girl pray,"); set `"body_color"` to white or accent, and `"font": "rounded"` if their brand uses a soft rounded font. Give about 1 s of screen time per 3 to 4 words (3 to 5 clips). **Line by line:** 3 to 5 short parts, one per clip, about 2.6 s each.
   - **Tips list:** a title (first clip) plus one tip per following clip, about 2.4 s each.
   - **On-screen hook:** one bold line (use `\n` to choose the line break) over a quick montage of 5 to 7 clips at 1.2 to 1.4 s; `accent_words` turn their brand color.
4. **Make:** one `reel.json` per version (format at the top of `scripts/broll_reel.py`; `ss` = the clip's `best` start), then `python3 scripts/broll_reel.py reel.json`.
   - **Look = their preset** (`"look"`: soft_glass, bold_highlight, pink_pop, typewriter, pink_label, chunky_word) so the reel matches their brand: white words in that preset's fonts, no boxes or highlights, with 1 to 3 `accent_words` in their brand color (and the preset's accent font, e.g. Playfair italic for Soft Glass). Colors come from their palette.
   - Use **their own clips and photos** from their library (photos too: give each about 1.6 s with a slow zoom). Never use sample or stock media. No library yet (phone users)? Ask them to attach 10 to 30 clips and photos in this chat, then sort and use those.
   - The script places the words off faces, dims the footage a touch when it's bright, and adds a thin black outline only over very bright footage. Override with `text_y`, `dim` (0 to 0.3) and `outline` (true or false) if a frame check says so.
   - No music unless they attach some, so they can add Instagram audio. Versions differ in text and clip order. Name them `-v1`, `-v2`, `-v3`.
5. Check 3 frames of each (text readable, off faces, nothing cut off) and deliver all 3, with a post caption if the picks ask for one.

## YouTube look (coming soon, for the creator's own testing)
Wide (16:9) talking videos: dark frosted-glass cards, a dark split panel the speaker slides away from, bold white type with pink italic serif accent words, and two-line subtitles at the bottom left.
```
python3 scripts/prepare.py "<video>" "<project>"
# edit.json: "size": [1920, 1080], "punch": 1.06, plus a "yt" block (see the top of scripts/yt_look.py)
python3 scripts/make_base.py "<project>"
python3 scripts/yt_look.py "<project>"
```
`yt` holds: `accent` (subtitle words in pink serif), `titles` (big title + serif word), `checklist` (frosted card that ticks), `list` (numbered split panel), `compare` (split panel rows, optional `thumbs`), and `fx`, a list of {type, at or start, dur, ...}: `clock`, `calc` (counting number + pills), `meter` (big number + filling blocks), `plan` (Claude quick plan with Yes/No and cursor), `prompt` (typing box), `note`, `message`, `days` (white "7 days" card), `name` (name intro), `corner` (corner word), `cta` (frosted pill + bouncing arrow), `phone` (vertical clip in a phone frame + pills), `folder`, `timeline`, `presets` (full white page of cards), `panel_check` (split panel checklist + screenshot), `panel_app` (split panel app window + pills). Put each on the line it fits; one at a time.
Brand: colors come from their `palette` (accent → the light accent on dark glass and a deeper shade on white cards; `on_accent` → text on accent pills), and fonts follow their reel preset (`"look"`: soft_glass, bold_highlight, pink_pop, typewriter, pink_label, chunky_word). Their `brand_fonts` apply here too (or `yt.fonts` to override just the YouTube look). Never use Destiny's pinks for someone else's video unless their palette is pink.

## 9. Vlogs

For "Brand Dream Team: edit my vlog": order clips by when they were filmed, keep the best moments to the length asked (30, 60 or 90 s), and add only the pieces picked: Timestamps (small time labels), Montage intro (6 quick moments in about 2 s), Title card (series name, optional typed-on line), Subtitles (when they talk), Light flash transitions, Sit-down ending, Day in order. Storyboard first. If they ticked the voiceover script, write short lines, one per clip, timed to the finished vlog, for them to read in CapCut. Offer to turn it into a carousel when done.

## Carousels ("make it a carousel")

1080×1350 slides in the creator's look: cover, one slide per point, closer with a save/comment line, their handle and a 1/N → counter. Never grab stills at a fixed time: use `best_still(src, out)` from `scripts/best_still.py`, which samples the clip and picks the sharpest frame with a clear front-facing face (`need_face=True` when the slide is about them). Crop so the face sits in the top third and never cut off the eyes. Check every slide before sending; replace any that is blurry or has a half-turned face.

## Rules

- iPhone clips are often HDR. Every script converts them to normal (SDR) video with one neutral setting (scripts/sdr.py), so brand colors and white text look right on phones. In B-roll reels every clip is also matched to the same brightness and color, so the whole reel looks like one shoot. Never skip or tweak this per video.

- Never post, upload or send anything for them.
- Never delete or change their originals.
- No sound effects (not in this version).
- If something fails, say what happened in one line and what you'll try next.
