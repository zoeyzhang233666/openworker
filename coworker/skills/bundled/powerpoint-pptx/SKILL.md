---

name: powerpoint-pptx
slug: powerpoint-pptx
version: 1.0.1
homepage: https://clawic.com/skills/powerpoint-pptx
description: "Create, inspect, and edit Microsoft PowerPoint presentations and PPTX decks with reliable layouts, templates, placeholders, notes, charts, and visual QA. Use when (1) the task is about PowerPoint or `.pptx`; (2) layouts, placeholders, notes, charts, comments, or template fidelity matter; (3) the deck must render cleanly after edits."
changelog: Rebalanced the skill toward template inventory, layout mapping, and higher-signal QA after a stricter external audit.
metadata: {"clawdbot":{"emoji":"📊","requires":{"bins":[]},"os":["linux","darwin","win32"]}}
---

## When to Use

Use when the main artifact is a Microsoft PowerPoint presentation or `.pptx` deck, especially when layouts, templates, placeholders, notes, comments, charts, extraction, editing, or final visual quality matter.

## Core Rules

### 1. Choose the workflow before touching the deck

- Reading text, editing an existing deck, rebuilding from a template, and creating from scratch are different jobs with different failure modes.
- For text extraction or inspection, read the deck before editing it.
- Text extraction plus thumbnail-style visual inspection is safer than editing from shape assumptions alone.
- For template-driven work, inventory the deck before replacing content.
- For deep edits, remember a `.pptx` file is OOXML with separate parts for slides, layouts, masters, media, notes, and comments.
- If a template exists, template fidelity beats generic slide-design instincts.
- Reusing or duplicating a good existing slide is often safer than rebuilding it and hoping the theme still matches.

### 2. Inventory the deck before replacing content

- Count the reusable layouts, real placeholders, notes, comments, media, and recurring typography or color patterns first.
- Placeholder indexes and layout indexes are not portable assumptions.
- Inspect the actual slide or template before targeting title, body, chart, or image shapes.
- Speaker notes, comments, and linked assets can live outside the visible slide surface.
- A missing or wrong placeholder target can silently land content in the wrong box or wrong layer.
- Master and layout settings can override local slide edits, so the visible problem is not always on the slide you are editing.

### 3. Match content to the actual placeholders

- Count the actual content pieces before choosing a layout.
- Pick layouts based on the real number of ideas, columns, images, or charts the slide needs.
- Do not force two ideas into a three-column slide or cram dense text under a chart.
- Category counts and data series lengths must match or charts will break in ugly ways.
- Explicit sizing beats wishful thinking: text boxes, images, and charts need real space, not "it should fit".
- Do not choose a layout with more placeholders than the content can meaningfully fill.
- Quote layouts are for real quotes, and image-led layouts are for slides that actually have images.
- For chart-, table-, or image-heavy slides, full-slide or two-column layouts are usually safer than stacking dense text above the visual.

### 4. Preserve the deck's visual language

- Theme, master, and layout files usually decide fonts, colors, and hierarchy more than any one slide does.
- Start from the deck's actual theme, fonts, spacing, and aspect ratio instead of improvising a new style.
- Reuse the deck's own alignment and spacing system instead of inventing a second visual language.
- Use common fonts for portability and strong contrast for readability.
- Preserve the template's visual logic first; originality matters less than not breaking the deck's existing language.
- Combining slides from multiple sources requires normalizing themes, masters, and alignment afterward.

### 5. Run content QA and visual QA separately

- Text overflow, bad alignment, clipped shapes, weak contrast, and placeholder leftovers are normal first-pass failures.
- Run both content QA and visual QA; missing text and broken layout are different failure classes.
- Render or inspect the actual deck output before delivery when layout matters.
- Search for leftover template junk, sample labels, and placeholder text before calling the deck finished.
- Check notes, comments, labels, legends, and chart/table semantics separately from the visual pass.
- A deck can pass text extraction and still fail on overlap, clipping, wrong theme inheritance, or broken notes.
- Thumbnail grids and rendered slides usually reveal layout bugs faster than code or text inspection.
- Assume the first render is wrong and do at least one fix-and-verify cycle before calling the deck finished.
- Re-check affected slides after each fix because one spacing change often creates another issue.

### 6. Keep decks portable and review-safe

- Template masters can override direct edits in surprising ways.
- Complex effects may degrade across PowerPoint, LibreOffice, and conversion pipelines, so keep important content robust without them.
- Image sizing, font substitution, and placeholder mismatch are common reasons a deck looks good in code and bad on screen.
- Notes, comments, linked media, and merged decks can stay broken even when the visible slide looks fine.

## Common Traps

- Placeholder text and sample charts often survive template reuse if not explicitly replaced.
- Directly editing one slide can fail if the real issue lives in the master or layout.
- Charts, icons, and text boxes need enough space; near-collisions are usually visible only after rendering.
- Layout indexes vary by template, so built-in assumptions from one deck often break in another.
- A missing placeholder or wrong shape target can silently put content in the wrong place.
- Counting the text ideas after choosing the layout usually leads to empty placeholders, weak hierarchy, or leftover template junk.
- Font substitution can move line breaks and wreck careful spacing.
- Speaker notes, comments, and linked media can stay broken even when the visible slide looks fine.
- A deck can pass text inspection and still fail visually because of overlap, contrast, or edge clipping.
- Editing from one slide alone can miss the real source of truth in the theme, master, or layout definitions.
- Choosing a quote, comparison, or multi-column layout without matching content usually makes the deck look templated rather than intentional.
- Combining or duplicating slides without checking masters and themes can create subtle inconsistency slide by slide.
- Aspect-ratio mismatches like `16:9` versus `4:3` can shift every placement decision even when each slide looks locally reasonable.

## Related Skills
Install with `clawhub install <slug>` if user confirms:
- `documents` — Document workflows that often feed presentation content.
- `design` — Visual direction and layout decisions.
- `brief` — Concise business messaging for slide narratives.

## Local Generation Path

- On Windows, prefer the local script `scripts/new_presentation.ps1` for creating a new `.pptx` from scratch.
- This path uses installed Microsoft PowerPoint via COM automation and avoids relying on `python-pptx`, `Pillow`, or ad hoc OOXML assembly.
- Before using Python-based generation, verify the runtime can actually import its packages; `pip show` alone is not enough.
- If PowerPoint COM is available, use it as the default fallback for simple title-and-bullets decks.
- For Chinese, Japanese, or other non-ASCII content, pass the deck through a UTF-8 JSON file or `-DeckJsonBase64Utf8` instead of embedding text directly in a shell one-liner.
- Do not build multilingual decks by inlining slide text inside `powershell -Command "..."`; that path is fragile and commonly causes mojibake.

### JSON Deck Format

- The script accepts `title`, optional `subtitle`, and a non-empty `slides` array.
- Supported slide `layout` values are `title`, `bullets`, and `text`.
- `bullets` should be an array of strings; `notes` is optional and also accepts an array of strings.
- `DeckJsonPath` should point to a UTF-8 encoded JSON file when the deck contains Chinese text.
- `DeckJsonBase64Utf8` is the safer fallback when shell quoting or terminal encoding is unreliable.

### Example Commands

```powershell
powershell -ExecutionPolicy Bypass -File .\openclaw-extensions\skills\powerpoint-pptx\scripts\new_presentation.ps1 `
  -DeckJsonPath .\openclaw-extensions\skills\powerpoint-pptx\scripts\example-deck.json `
  -OutputPath .\artifacts\example-deck.pptx
```

```powershell
powershell -ExecutionPolicy Bypass -File .\openclaw-extensions\skills\powerpoint-pptx\scripts\new_presentation.ps1 `
  -Title "Weekly Report" `
  -Subtitle "Single-slide example" `
  -OutputPath .\artifacts\weekly-report.pptx
```

```powershell
$json = Get-Content .\openclaw-extensions\skills\powerpoint-pptx\scripts\example-deck.json -Raw -Encoding UTF8
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
powershell -ExecutionPolicy Bypass -File .\openclaw-extensions\skills\powerpoint-pptx\scripts\new_presentation.ps1 `
  -DeckJsonBase64Utf8 $b64 `
  -OutputPath .\artifacts\example-deck-b64.pptx
```

### Multilingual Safety Rules

- For decks containing Chinese content, first write the slide structure into a UTF-8 JSON file in the workspace, then pass that file path to the script.
- If the shell mangles non-ASCII characters, switch to `-DeckJsonBase64Utf8` instead of retrying inline command variants.
- Prefer editing the JSON file with `apply_patch` over generating a temporary script through echoed shell text.

### OOXML Safety Rules

- Do not hand-build `.pptx` by zipping a guessed folder tree unless the task is explicitly about low-level OOXML repair.
- A valid `.pptx` package must have required parts like `[Content_Types].xml` and `_rels/.rels` at the ZIP root, not under an extra wrapper directory.
- Avoid manual OOXML generation as a fallback when COM automation is available; partial packages often trigger PowerPoint repair dialogs even if they have the `.pptx` extension.
- If a generated deck is unusually tiny, inspect the ZIP entry list before delivery; a size around a few kilobytes is a strong sign the package is incomplete.

### Delivery Rules

- Always return a real `.pptx` file path, not raw XML, Base64, or a placeholder link.
- If generation fails because local PowerPoint is unavailable, say so clearly instead of switching to an unverified OOXML hand-build.
- After generation, do a quick open/save validation when layout correctness matters.

## Feedback

- If useful: `clawhub star powerpoint-pptx`
- Stay updated: `clawhub sync`
