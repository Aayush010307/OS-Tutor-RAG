---
name: OS-Tutor
description: A course-grounded Socratic tutor for threads and synchronization, laid out as a study desk.
colors:
  bg: "#0f1217"
  rail: "#0b0d11"
  surface: "#151920"
  surface-2: "#1b2029"
  surface-3: "#232935"
  line: "#222833"
  line-strong: "#323a48"
  ink: "#e6e9ef"
  ink-2: "#a5adbb"
  ink-3: "#7f8898"
  accent: "#86a8ff"
  accent-strong: "#3b63d6"
  on-accent: "#f6f8ff"
  accent-soft: "rgb(134 168 255 / 0.12)"
  accent-line: "rgb(134 168 255 / 0.35)"
  success: "#6fc79d"
  warning: "#e6b36a"
  danger: "#f2877c"
  success-soft: "rgb(111 199 157 / 0.12)"
  warning-soft: "rgb(230 179 106 / 0.12)"
  danger-soft: "rgb(242 135 124 / 0.12)"
  code-bg: "#0b0e13"
typography:
  title:
    fontFamily: "Atkinson Hyperlegible Next Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 700
    lineHeight: "2.1rem"
    letterSpacing: "-0.015em"
  lead:
    fontFamily: "Atkinson Hyperlegible Next Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: "1.75rem"
  body:
    fontFamily: "Atkinson Hyperlegible Next Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: "1.7rem"
    fontFeature: "tnum"
  ui:
    fontFamily: "Atkinson Hyperlegible Next Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.3rem"
  meta:
    fontFamily: "Atkinson Hyperlegible Next Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.78125rem"
    fontWeight: 400
    lineHeight: "1.1rem"
  mono:
    fontFamily: "Atkinson Hyperlegible Mono Variable, ui-monospace, SF Mono, Menlo, monospace"
    fontSize: "0.86rem"
    fontWeight: 400
    lineHeight: 1.65
rounded:
  control: "8px"
  panel: "12px"
  composer: "14px"
spacing:
  rail-width: "264px"
  sources-width: "360px"
  reading-column: "46rem"
  header-height: "56px"
  message-gap: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent-strong}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.control}"
    size: "36px"
  button-primary-disabled:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.ink-3}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.ui}"
    rounded: "{rounded.control}"
    height: "40px"
    padding: "0 12px"
  button-secondary-hover:
    backgroundColor: "{colors.surface-2}"
  button-ghost:
    textColor: "{colors.ink-3}"
    typography: "{typography.meta}"
    rounded: "{rounded.control}"
    height: "32px"
    padding: "0 8px"
  button-ghost-hover:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.ink}"
  citation-chip:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "5px"
    height: "1.35rem"
    padding: "0 6px"
  citation-chip-hover:
    backgroundColor: "{colors.accent-strong}"
    textColor: "{colors.on-accent}"
  composer:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.composer}"
  student-message:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.panel}"
    padding: "10px 16px"
  source-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
  history-item-active:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 36px 8px 10px"
---

# Design System: OS-Tutor

## Overview

**Creative North Star: "The Study Desk"**

OS-Tutor is a desk, not a chatbot. The lesson sits in a single reading column on a cool charcoal ground, flanked by a darker rail holding the student's lessons and, once a question has been asked, a sources column holding the exact slides and pages the tutor read. In the default Socratic mode the header carries the lesson's state drawn as the process state diagram OS students already know. Everything a student sees answers one of two questions: where is this lesson, and where did this claim come from.

The world is quiet and long-session friendly. Depth comes from tonal steps of the same blue-grey and hairline borders, not from cards or shadows; the tutor's replies sit directly on the ground with no container. One restrained cobalt accent marks action and the current state, and nothing else. Green, amber and red exist only for the evaluator's analysis, finished lessons and errors. Dark is the home theme; light is the same system re-lit through the same semantic tokens (light values live in `.impeccable/design.json` under `colorMeta.*.light`).

One typeface family carries everything: Atkinson Hyperlegible Next for text, its Mono sibling for code, citation refs, model names and counts. Motion is sparse and purposeful: one authored moment (the stage-rail edge drawing itself), plus small state feedback, all collapsed under reduced motion.

**Key Characteristics:**
- Three-column desk: rail (264px), reading column (46rem max), sources column (360px at xl, drawer below).
- Tonal layering on hairlines; no message cards, one soft float shadow on the composer.
- A single cobalt accent with a text tone and a fill tone; semantic colours reserved for analysis and status.
- Atkinson Hyperlegible Next and Mono throughout, tabular numerals by default.
- The stage rail as a state diagram is the signature.

## Colors

Cool blue-grey neutrals stepped by lightness, one cobalt accent, and muted semantic hues reserved for judgement and status.

### Primary
- **Periwinkle Signal** (accent): text-weight accent for the current stage, stage tags, citation ref text, links in prose, the caret, focus outlines and the waiting dots. Used as ink and stroke, never as a large fill.
- **Deep Cobalt** (accent-strong): the only filled accent: the send button, the brand mark, the checked switch, a hovered citation chip. Paired with **Accent White** (on-accent) for text on it.
- **Cobalt Wash** (accent-soft) and **Cobalt Hairline** (accent-line): the tinted background and border of citation chips and the active Sources toggle; accent-line also marks a focused composer, a hovered New lesson button, the return arc once a round has been used, text selection and the flash ring on a jumped-to source.

### Tertiary
- **Sage** (success), **Ochre** (warning), **Coral** (danger), each with a 12% soft wash: the evaluator's level tags on student answers, the finished-lesson check in history, the offline banner and failed-reply panels. Never decorative.

### Neutral
- **Desk Charcoal** (bg): the main ground under the reading column and header.
- **Rail Black** (rail): the side rail and the sources column, one step darker than the ground.
- **Slate Surface / Surface 2 / Surface 3** (surface, surface-2, surface-3): rising tonal steps for the composer and source cards, student messages and hover, then active history items and disabled fills.
- **Hairline / Strong Hairline** (line, line-strong): dividers and resting borders; strong hairline for controls, open source cards, stage edges and idle stage nodes.
- **Chalk / Pencil / Graphite** (ink, ink-2, ink-3): primary text, secondary text, and meta text, placeholders and quiet icons.
- **Code Well** (code-bg): code block background, darker than the ground.

### Named Rules
**The One Accent Rule.** Cobalt means action or "you are here". If an element is neither clickable nor the current state, it is not cobalt.
**The Two-Tone Accent Rule.** The light tone (accent) is for text and strokes; fills use accent-strong with on-accent text. In the light theme both resolve to the same cobalt.
**The Judgement Colours Rule.** Green, amber and red appear only for analysis, completion and errors; never for decoration or emphasis.

## Typography

**Body Font:** Atkinson Hyperlegible Next Variable (with ui-sans-serif, system-ui)
**Label/Mono Font:** Atkinson Hyperlegible Mono Variable (with ui-monospace, SF Mono, Menlo)

**Character:** A legibility-first family chosen for long revision sessions; the mono sibling shares its letterforms so refs like `S1` and model names sit in running text without a jolt.

### Hierarchy
- **Title** (700, 1.625rem / 2.1rem, -0.015em, balanced): the welcome headline; the only large type in the product.
- **Lead** (400, 1.125rem / 1.75rem): the welcome intro, max 60ch.
- **Body** (400, 1rem / 1.7rem): tutor prose, student messages, composer and starter questions; the reading column caps line length at 46rem. Prose headings step down to 1.25 / 1.15 / 1.02rem at 650 weight.
- **UI** (400 or 600, 0.875rem / 1.3rem): buttons, lesson titles, source filenames, section labels, tables in prose.
- **Meta** (400 or 600, 0.78125rem / 1.1rem): timestamps, hints, stage-rail labels, tags, ghost actions.
- **Mono** (0.86rem / 1.65 in code blocks; inherits meta size for refs, model names and counts).

### Named Rules
**The Ramp Rule.** Five steps, ratio about 1.15: meta, ui, body, lead, title. New text picks a step; it does not invent a size. The only exceptions are fixed micro marks: the brand wordmark (0.95rem) and mark (0.7rem), the citation chip (0.72rem) and the arc's round count (0.65rem).
**The Mono Means Machine Rule.** Mono is for things a machine names: code, citation refs, model ids, counts. Never for prose or headings.
**The Tabular Rule.** Numerals are tabular everywhere (set on body), so counts and round numbers never jitter.

## Layout

A full-height three-column desk. The rail (264px, bordered right) shows from lg; below lg it becomes a left drawer opened from the header. The main column has a 56px header (lesson title and model on the left, stage rail (Socratic mode only) and Sources toggle on the right; the rail drops to a scrolling compact row under the header below md). Conversation and composer share a centred column, max 46rem, with 16px side padding on mobile and 32px from md. Messages are separated by 32px; a "New topic" hairline separator with centred meta text splits topics. The sources column (360px, rail tone, bordered left) appears at xl once a lesson has sources; below xl the same panel is a right drawer (max min(92vw, 380px)). A faint radial cobalt glow (ambient) sits behind the top of the main column. Spacing follows Tailwind's 4px grid, mostly 8, 10, 12, 16 and 20px inside components.

## Elevation & Depth

Flat by default, layered by tone. Surfaces separate through the rail/bg/surface lightness steps and 1px hairlines. Exactly one shadow token exists, a soft float under the composer so it reads as the desk's working surface; the 3px ring around the current stage node and the flash ring on a source card are state rings, not elevation. Drawers sit on a dimming scrim.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 12px 32px -16px rgb(0 0 0 / 0.7), 0 2px 6px -2px rgb(0 0 0 / 0.4)` dark; softer in light): the composer only.
- **State ring** (`box-shadow: 0 0 0 3px var(--accent-soft)`): the current stage node; `var(--accent-line)` fading out for a jumped-to source card.

### Named Rules
**The No-Card Rule.** Tutor replies sit on the ground with no border, fill or shadow. Containers are for things the student acts on (composer, source cards, errors), not for speech.
**The One Float Rule.** Only the composer floats. Nothing else gets a drop shadow.

## Shapes

Three named radii carry the system: 8px for controls (buttons, history items, toggles), 12px for messages, panels, source cards and code blocks, 14px for the composer. Small inline marks use 5px (citation chips, stage tags, inline code). Circles are reserved for stage nodes, the switch and waiting dots. Borders are always 1px hairlines; the stage rail's arrowheads are rotated hairline corners, and the return arc is a hairline with an 8px top radius.

## Components

### Buttons
- **Shape:** gently rounded controls (8px).
- **Primary:** the send button, a 36px square of Deep Cobalt with an on-accent arrow; hover brightens 10%, press scales to 95%, disabled drops to surface-3 with graphite icon.
- **Secondary:** New lesson and recovery actions ("Ask again"): surface fill, strong hairline border, ui or meta semibold, 36 to 40px tall; hover lifts to surface-2/surface-3 and New lesson's border turns accent-line.
- **Ghost:** copy, sources count, close and menu buttons: no fill, graphite text, 32 to 40px; hover fills surface-2 or surface-3 and text goes to ink. Destructive ghost (delete lesson) turns coral on hover and is revealed on row hover or focus.
- **Focus:** a 2px accent outline, 2px offset, on every focusable element.

### Chips
- **Citation chip:** inline mono ref (`S1`) in a cobalt wash with accent-line border, 5px radius; hover fills Deep Cobalt with on-accent text. Clicking opens and flashes the matching source card.
- **Stage tag:** meta semibold accent text in a 5px hairline outline, beside "Tutor" in each reply header. Labels follow the turn: Diagnose, Explain, Check, Wrap-up or Full answer, Side question; in answer-first mode Answer, Check, Feedback and Not in the course material. A stage the page does not know is shown as sent.
- **Level tag (evaluator view):** semibold meta on the matching semantic soft wash.

### Cards / Containers
- **Corner Style:** 12px.
- **Background:** surface; error panels use danger-soft with a 30% coral border.
- **Shadow Strategy:** none (see Elevation).
- **Border:** line at rest, line-strong when a source card is open.
- **Internal Padding:** 12px by 14px; source passages render prose one step smaller in pencil grey.

### Inputs / Fields
- **Composer:** surface, strong hairline, 14px radius, float shadow; body-size textarea grows to 220px; footer row holds the mono model select, a meta hint and send. Focus moves the border to accent-line; the caret is cobalt.
- **Switch (Evaluator view):** 36 by 20px pill on surface-3 with a strong hairline ring, knob in ink; checked fills Deep Cobalt.

### Navigation
- **Rail:** brand (cobalt "OS" mono mark plus bold wordmark), New lesson, a "Lessons" list (ui titles, meta timestamps, a sage check on finished lessons), and settings at the foot above a hairline. Active item fills surface-3; hover surface-2.
- **Mobile:** rail and sources become slide-in dialogs (220ms, 24px travel) over the scrim.

### Stage Rail (signature)
The lesson as a process state diagram: Diagnose, Explain, Check, Done as 10px circular nodes joined by hairline transition edges with hairline arrowheads. Idle nodes are hollow strong-hairline rings with graphite labels; visited nodes fill graphite with pencil labels; the current node fills cobalt with a 3px cobalt-wash ring and a semibold cobalt label. A hairline return arc spans Explain and Check, turning accent-line once a round is used and carrying the round count (`1/2`) in mono. The edge into the newly current state draws itself left to right once (520ms, ease-out). A compact variant (12px edges, count trailing) scrolls under the header on small screens. The rail describes the Socratic flow only: when the server runs answer-first (`TUTOR_MODE=answer_first`, reported by the `session` event) it is not shown, because Answer, Check and Feedback are not a lesson state machine to read.

## Do's and Don'ts

### Do:
- **Do** use only the semantic tokens (bg, rail, surface, line, ink, accent...) so both themes stay correct; never a raw colour in a component.
- **Do** keep cobalt for action and the current state; fills use accent-strong with on-accent text.
- **Do** use the three named radii (8px controls, 12px panels, 14px composer) and 1px hairlines.
- **Do** set code, citation refs, model ids and counts in Atkinson Hyperlegible Mono.
- **Do** give every interactive element the 2px accent focus outline and keep animations under the reduced-motion override.

### Don't:
- **Don't** wrap tutor replies in cards, bubbles or shadows.
- **Don't** add drop shadows beyond the composer's float.
- **Don't** use green, amber or red outside analysis, completion and error states.
- **Don't** introduce type sizes outside the five-step ramp beyond the existing micro marks.
- **Don't** add a second authored animation competing with the stage-rail edge draw.
