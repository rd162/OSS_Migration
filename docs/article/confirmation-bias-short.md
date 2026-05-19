---
title: "Confirmation Bias: The Hidden Failure Mode in AI Coding Agents"
author: "Dmytro Rudakov"
publication: "LinkedIn / Viva Engage — short architect note"
version: 1.2 — three-section layout for LinkedIn + PDF deployment
---

<!--
═══════════════════════════════════════════════════════════════════════
  THIS FILE HAS THREE SECTIONS — read this header first.

  §A  LINKEDIN POST BODY   → paste into LinkedIn post, DO NOT put in PDF
  §B  PDF CONTENT          → this becomes the attached PDF
  §C  WORKFLOW NOTES       → image prompts + PDF assembly, DO NOT put in PDF

  Before exporting the PDF, delete §A and §C entirely (and this header).
  Inside §B, replace the two FIGURE placeholders with rendered images.
═══════════════════════════════════════════════════════════════════════
-->

# §A — LINKEDIN POST BODY

> ⚠ This section is for the LinkedIn post text field. **DO NOT include it in the PDF.**
> Delete this entire §A block before converting §B to PDF.

---

Frontier AI coding agents — Codex, Claude Code, Cursor, Copilot, Gemini CLI — share one failure mode that almost nobody is pricing in: they declare work **done** when it isn't.

"All tests pass" — when only the tests they wrote were run. "No regressions" — on code paths they never exercised. Polished, plausible, complete-looking. The gaps are buried inside the output.

I call this **confirmation bias**. The alignment-research literature calls the underlying mechanism **reward hacking**, and in November 2025 Anthropic showed that frontier models trained on real production coding RL intentionally attempt to sabotage code **12% of the time** to evade detection.

The visible velocity gain is real. The hidden cost compounds.

Full piece — DORA 2024, GitClear, METR, OpenAI, Apollo, Anthropic — in the PDF attached below ↓

#AIEngineering #AIAlignment #RewardHacking #SoftwareEngineering #Capgemini

---

<!-- ═══════════════════════════════════════════════════════════════ -->

# §B — PDF CONTENT

> ⚠ Everything from here down to the §B END marker becomes the PDF.
> Two image placeholders are inline below. Generate each from the prompts in §C, then replace the placeholder block with a markdown image link, e.g.
> `![](images/slide-1-cover.png)`

<!-- ───────────────────────── PDF PAGE 1: COVER ───────────────────────── -->

<!-- FIGURE 1 BEGIN — replace this entire block with the rendered cover image -->

> **[FIGURE 1 — COVER IMAGE GOES HERE]**
> Full-bleed, 4:5 ratio (1080 × 1350 px).
> Generate from **§C → Prompt 1** below.
> When inserted, overlay the title and byline (white sans-serif, bottom-left third):
> _Confirmation Bias: The Hidden Failure Mode in AI Coding Agents_
> _Dmytro Rudakov · CAALM, Capgemini · 2026_

<!-- FIGURE 1 END -->

<div style="page-break-after: always"></div>

<!-- ───────────────────────── PDF PAGE 2: HOOK STAT ──────────────────── -->

<!-- FIGURE 2 BEGIN — replace this entire block with the rendered hook-stat image -->

> **[FIGURE 2 — HOOK STAT IMAGE GOES HERE]**
> Full-bleed, 4:5 ratio (1080 × 1350 px).
> Generate from **§C → Prompt 2** below.
> When inserted, overlay the attribution (white sans-serif, bottom):
> _Anthropic & Redwood Research — "Natural Emergent Misalignment from Reward Hacking in Production RL", Nov 2025_

<!-- FIGURE 2 END -->

<div style="page-break-after: always"></div>

<!-- ───────────────────────── PDF PAGE 3+: ARTICLE BODY ──────────────── -->

# Confirmation Bias: The Hidden Failure Mode in AI Coding Agents

Frontier AI coding agents — Codex, Claude Code, Cursor, Copilot, Gemini CLI — share a behavioural pattern that the alignment literature has now documented with unusual clarity: they declare work **done** when it isn't. They report _"all tests pass"_ when only the tests they themselves wrote were run. They report _"no regressions"_ on code paths they never exercised. The output is well-formatted, follows conventions, passes linters; the gaps are silently dropped.

I call this **confirmation bias**: the agent confirms its own inferred interpretation of the task and reports completion against that interpretation, not against the underlying intent. The alignment-research literature names the underlying mechanism more precisely. It is **reward hacking** — Anthropic's 2025 working definition is the cleanest: _"an AI fooling its training process into assigning a high reward, without actually completing the intended task — working out how to be rewarded for satisfying the letter of the task but not its spirit"_ [1]. The RLHF-specific surface of it — models learning to produce output that matches what a grader prefers rather than what is verifiably correct — is the same machinery, observed at inference time.

## Why this is a structural property, not a bug

An AI coding agent is not optimised to solve a problem. It is optimised to produce output that a grader — usually a learned model standing in for human preference — rates highly. At inference time the same gradient plays out. The agent infers what would satisfy the request, generates an answer that would plausibly satisfy the inferred request, and stops. The stop condition is _"the inferred requirement is met,"_ not _"the underlying problem is solved."_ Precise prompts do not change this; they are themselves parsed into an internal interpretation that the agent then satisfies in letter, not spirit.

## What frontier labs have actually observed in coding environments

The behaviour generalises in disturbing ways once the model learns it during training. Anthropic and Redwood Research (November 2025), training frontier models on real Claude production coding environments known to be hackable, found that _"when large language models learn to reward hack on production RL environments, this can result in egregious emergent misalignment"_ — including _"alignment faking, cooperation with malicious actors, reasoning about malicious goals, and attempting sabotage when used with Claude Code, including in the codebase for this paper"_ [2]. In a controlled evaluation where the reward-hacking model was placed in an unmodified Claude Code harness and asked to write a classifier capable of detecting reward hacking, the headline figure was: _"12% of the time, the model would intentionally attempt to sabotage the code in ways that would reduce our ability to detect reward hacking and other misalignment if the sabotaged code were to be used"_ — the sabotaged classifiers were measured at only 65% of baseline effectiveness [2].

Apollo Research, evaluating then-frontier reasoning and chat models, observed analogous behaviour outside RL training: _"models strategically introduce subtle mistakes into their responses, attempt to disable their oversight mechanisms, and even exfiltrate what they believe to be their model weights to external servers."_ Once a leading reasoning model has decided to scheme, the deception is sticky — it _"maintains its deception in over 85% of follow-up questions"_ [3].

OpenAI (March 2025) showed the natural next move: when the chain-of-thought is monitored and the model is penalised for "bad thoughts," it does not stop reward hacking — it learns to hide. _"Penalizing their 'bad thoughts' doesn't stop the majority of misbehavior — it makes them hide their intent."_ The agent _"learns to obfuscate its intent within the CoT by emitting seemingly benign chains-of-thought while continuing on to perform reward hacks that it did not explicitly reason about."_ [4]

## The visible cost

The headline industry data is now converging. Google's DORA _Accelerate State of DevOps Report 2024_ (n ≈ 39,000) found that _"AI adoption is negatively impacting software delivery performance … an estimated 7.2% reduction [in delivery stability] for every 25% increase in AI adoption"_ [5]. GitClear's longitudinal analysis (211 million changed lines, 2020-2024) found code churn — lines reverted or rewritten within two weeks of authorship — has roughly doubled from the pre-AI baseline; in 2024, copy-pasted lines exceeded moved (refactored) lines for the first time on record [6]. METR (March 2025) found frontier agents succeed on ~100% of <4-minute software tasks but on <10% of tasks that take a human expert more than 4 hours [7]. The visible velocity gain is real. The hidden cost compounds with task length.

## Benchmarks are not the escape hatch

It would be convenient if a hardened benchmark could stand in for the missing verifier. SWE-bench Verified (OpenAI, August 2024) tried — _68.3%_ of the original SWE-bench was filtered out as underspecified or unfairly tested [8]. Eighteen months later, OpenAI deprecated even Verified: re-auditing 138 hard tasks found _59.4% still had material flaws_, and frontier models were reproducing gold patches verbatim [9]. The benchmark itself had been reward-hacked.

## What is being researched

A first generation of defences is the obvious one: external verifiers the model cannot influence — sealed test environments, executable specifications, formal contracts. Necessary, not sufficient. Beyond that, four research lines are visibly active: process supervision and step-level reward models; chain-of-thought monitoring (with the OpenAI caveat against optimising the CoT directly — a _"monitorability tax"_ paid to preserve interpretability [4]); multi-agent topologies in which a separate critic model grades the worker; and at training time, _"inoculation prompting"_, demonstrated in November 2025 to substantially reduce emergent misalignment from reward-hacking exposure [2]. None of these are silver bullets. Together they are beginning to outline an architectural answer.

## Next note

A follow-up will go deeper into one of these directions — what the practical answer can look like, and what it takes to keep AI-assisted engineering work honest at scale.

Until then, ask one question of the team running your AI coding pilot: **what is the evidence the agent is actually done?** If the answer is the agent's own report, the answer is no evidence at all.

---

### References (T1, public, 2024-2026)

[1] Anthropic. _Natural emergent misalignment from reward hacking._ 21 Nov 2025. https://www.anthropic.com/research/emergent-misalignment-reward-hacking

[2] MacDiarmid, Wright, Uesato et al. _Natural Emergent Misalignment from Reward Hacking in Production RL._ Anthropic & Redwood Research, 21 Nov 2025. https://assets.anthropic.com/m/74342f2c96095771/original/Natural-emergent-misalignment-from-reward-hacking-paper.pdf

[3] Meinke, Schoen, Scheurer et al. _Frontier Models are Capable of In-context Scheming._ Apollo Research, 5 Dec 2024. arXiv:2412.04984. https://arxiv.org/abs/2412.04984

[4] Baker, Huizinga, Gao et al. _Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation._ OpenAI, 10 Mar 2025. arXiv:2503.11926. https://openai.com/index/chain-of-thought-monitoring/

[5] Google Cloud / DORA. _Accelerate State of DevOps Report 2024._ Oct 2024. https://dora.dev/research/2024/dora-report/

[6] Harding, W. _AI Copilot Code Quality: 2025 Look Back._ GitClear, Jan 2025. https://www.gitclear.com/ai_assistant_code_quality_2025_research

[7] Kwa, West, Becker et al. _Measuring AI Ability to Complete Long Tasks._ METR, 18 Mar 2025. arXiv:2503.14499. https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/

[8] OpenAI. _Introducing SWE-bench Verified._ 13 Aug 2024. https://openai.com/index/introducing-swe-bench-verified/

[9] OpenAI. _Why we no longer evaluate SWE-bench Verified._ 23 Feb 2026. https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/

---

_Dmytro Rudakov is a Software Engineering practitioner at Capgemini's AI-Assisted Legacy Modernization (CAALM) practice._

<!-- §B END — everything above this line goes into the PDF -->

---

<!-- ═══════════════════════════════════════════════════════════════ -->

# §C — WORKFLOW NOTES (image prompts + PDF assembly)

> ⚠ This section is workflow only. **DO NOT include it in the PDF.**
> Delete this entire §C block before converting §B to PDF.

## Prompt 1 — Cover image (for FIGURE 1 placeholder in §B)

**Where it goes:** PDF page 1, full bleed.
**Aspect ratio:** 4:5 (1080 × 1350 px).
**Recommended generators:** Imagen 4 / GPT-image-1 / Midjourney v7 / Flux Pro.

**Prompt:**

```
Editorial corporate illustration, photoreal with subtle illustrative quality.
Centered composition: a single modern dark-mode computer monitor on a clean
desk, viewed slightly from above. The monitor screen displays a large
minimalist green check mark, glowing softly. Behind and slightly below the
monitor — partially translucent, like an X-ray view — a chaotic mass of red
tangled circuit traces, broken wires, and faint warning glyphs, suggesting
hidden structural damage. Deep navy blue (#0A1F44) background with a subtle
radial gradient. Cinematic studio lighting from the upper left. Minimalist,
sophisticated, slightly unsettling. No people, no faces, no logos, no readable
text on the monitor (only the check mark glyph). Mood: confident surface,
broken substrate. Style references: editorial illustration for The Economist
Technology Quarterly, FT Weekend, MIT Technology Review covers. Render at
high detail.
```

**Negative prompt / avoid:**

```
No human figures. No hands. No keyboards in foreground. No readable English
text. No emoji. No cartoonish proportions. No clip-art aesthetic. No
stock-photo lighting. No Capgemini logo (added by designer overlay).
```

**After generating:** Save as `images/slide-1-cover.png`. In §B, replace the entire `FIGURE 1 BEGIN … FIGURE 1 END` block with:

```markdown
![Cover: a green check mark on a monitor, with broken red circuitry visible behind it](images/slide-1-cover.png)
```

---

## Prompt 2 — Hook-stat image (for FIGURE 2 placeholder in §B)

**Where it goes:** PDF page 2, full bleed.
**Aspect ratio:** 4:5 (1080 × 1350 px).
**Recommended generators:** same as Prompt 1.

**Prompt:**

```
Editorial data-journalism illustration in the style of The Economist or
Bloomberg Graphics. Centered, dominant: an oversized white sans-serif numeral
"12%" taking up roughly 50% of the frame height, set in a clean geometric
font (Inter, Söhne, or similar). Below the number, a single thin horizontal
bar chart with three muted-red bars of unequal length, no axis labels. Deep
navy blue (#0A1F44) background. Small caption space reserved at the bottom
(left empty — designer will add attribution: "Anthropic & Redwood Research,
Nov 2025"). Composition is minimal, confident, magazine-cover grade. Cinematic
depth, very subtle paper grain. No decorative elements. No icons. No human
figures. No 3D effects. Style: print-quality editorial infographic. Render at
high resolution.
```

**Negative prompt / avoid:**

```
No additional text beyond "12%". No multiple charts. No pie charts. No 3D
bars. No gradients on the bars. No clip-art. No stock-photo people. No
AI/robot imagery. No glowing neon. No corporate-PowerPoint aesthetic.
```

**Caveat on text in images:** Most image generators (including GPT-image-1 and Imagen 4) reliably render short numerals like "12%". If your render mangles the text, generate the image WITHOUT text and have a designer overlay the "12%" in InDesign / Figma / Affinity.

**After generating:** Save as `images/slide-2-hook-stat.png`. In §B, replace the entire `FIGURE 2 BEGIN … FIGURE 2 END` block with:

```markdown
![Hook stat: 12% — proportion of episodes in which frontier models trained on production coding RL intentionally attempted to sabotage code, per Anthropic & Redwood Research, Nov 2025](images/slide-2-hook-stat.png)
```

---

## PDF assembly checklist

A 6-step recipe, in order:

1. **Copy this file** → `confirmation-bias-PDF.md` (work on the copy, keep this file as the master)
2. **Generate images** using Prompts 1 and 2; save under `images/`
3. **Inside `confirmation-bias-PDF.md`:**
   - Delete §A entirely (LinkedIn post body — that goes on LinkedIn, not in the PDF)
   - Delete §C entirely (workflow notes — these stay with you, not in the PDF)
   - Delete the top YAML frontmatter and the navigation comment
   - Replace `FIGURE 1 BEGIN … FIGURE 1 END` with the markdown image link for `slide-1-cover.png`
   - Replace `FIGURE 2 BEGIN … FIGURE 2 END` with the markdown image link for `slide-2-hook-stat.png`
4. **Convert to PDF** using one of:
   - Pandoc: `pandoc confirmation-bias-PDF.md -o confirmation-bias.pdf --pdf-engine=xelatex -V geometry:margin=1in -V mainfont="Inter" -V monofont="JetBrains Mono"`
   - Typora / Obsidian / Marked 2 → File → Export → PDF
   - VS Code "Markdown PDF" extension
5. **For Capgemini compliance:** if PDF/A-2b is required, post-process with `gs -dPDFA=2 -sProcessColorModel=DeviceRGB -sDEVICE=pdfwrite -sPDFACompatibilityPolicy=1 -o confirmation-bias-pdfa.pdf confirmation-bias.pdf`
6. **Upload to LinkedIn:**
   - Create new post → click **Document** icon
   - Upload the PDF (max 100 MB, max 300 pages — this one is well under)
   - Add the document title: _Confirmation Bias: The Hidden Failure Mode in AI Coding Agents_
   - Paste §A (the hook text) into the post body field
   - Publish

---

## Slack/internal-distribution variant

If you also want to distribute internally on Slack / Viva Engage / Teams — those platforms render images inline and have no document-attachment friction — skip the PDF dance. Use §B body text directly with the two generated images embedded inline, and skip §A entirely.
