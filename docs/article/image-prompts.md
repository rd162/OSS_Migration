# Image Prompts — Companion to the Article

This file holds the six image prompts referenced as placeholders in
`ai-modernization-architecture-article.md` (`Image 1` … `Image 6`).
It also gives a short, opinionated recommendation on which generation tool
to use for each image.

---

## Tool recommendation

You asked specifically about **2Slides** versus **Nano Banana** (Gemini 2.5 Flash Image).
Short version:

| Tool                                     | Best for in this article            | Why                                                                                                                                                                                                                                                        |
| ---------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **2Slides**                              | All technical diagrams (Images 2–6) | Slide-style output, clean typography, consistent colour palette, renders boxes/arrows/tables crisply, accepts structured Mermaid-like input. It is purpose-built for the kind of structured infographics this article needs.                               |
| **Nano Banana** (Gemini 2.5 Flash Image) | The hero cover (Image 1)            | Excellent at conceptual / metaphorical imagery, very strong text integration inside images, supports iterative refinement with a single anchor image, and produces results closer to magazine-cover aesthetic than pure-diagram tools.                     |
| **Alternatives**                         | —                                   | _Midjourney v7_: best hero aesthetics but weak at integrating English text into images; _Flux.1 Pro_: closer to Nano Banana for text-in-image; _DALL-E 3_: middle of the road on both; _Mermaid → PNG_: free baseline if generation tools are unavailable. |

**Concrete plan:**

- **Image 1 (hero cover)** → **Nano Banana**.
- **Images 2–6 (architecture diagrams)** → **2Slides** for the highest quality.
  If 2Slides is not available for a given image, the same prompt works in
  Nano Banana with a slight loss of typographic crispness.

Where helpful, every prompt below carries a short Mermaid block that can be
pasted directly into 2Slides as the structural starting point, plus a free-form
prompt for hero / metaphorical imagery.

---

## Image 1 — Hero cover (Nano Banana)

**Use:** full-page cover on page 1, above the title.

**Prompt:**

```
Editorial magazine cover illustration, conceptual / metaphorical.

Foreground: two software-system silhouettes facing each other across a vertical
gap. On the left, a weathered stone building made of densely-stacked code blocks
in a cool slate-gray palette — this represents a legacy source system. On the
right, the same building reassembled from glowing, semi-transparent blue blocks
that are floating into place from above, organised in clean geometric clusters —
this represents the modernized target system.

Between the two buildings, a fine luminous mesh of horizontal threads connects
each block on the left to one or more blocks on the right; the threads form a
clear, ordered fabric, not a chaotic tangle. Faint glowing labels on a few
threads spell short words: "source", "spec", "decision".

Above the buildings: a soft top-light, like dawn, in warm orange-to-cyan gradient.

Below the buildings: small ground-line silhouettes of a human architect, an SME
with a tablet, and a product owner — visible but not dominant — observing the
transfer.

Style: editorial / Capgemini-magazine, minimal palette (slate, cyan, warm amber
accents), painterly but clean, vector-friendly look, 9:16 portrait orientation
suitable for a full-page magazine cover. No raw code text; thread labels are
the only legible text.
```

**Negative prompt:**

```
no garbled text, no realistic faces, no logos, no UI mockups, no screenshots,
no overly busy detail, no rainbow colours, no random typography
```

---

## Image 2 — The four pillars (2Slides; alt Nano Banana)

**Use:** illustrating the "Four Pillars" section.

**Structure (2Slides input):**

```mermaid
flowchart TB
    Top["**Auditable, measurable AI-driven modernization**"]:::cap
    Top --- P1
    Top --- P2
    Top --- P3
    Top --- P4

    P1["**① Dimensions**<br/>Structured source model<br/>migration order respects reality"]:::pillar
    P2["**② Traceability**<br/>SMEs can review fast<br/>every target element cites<br/>source + spec + decision"]:::pillar
    P3["**③ Coverage Validation**<br/>'Done' is a measurable predicate<br/>per-dimension, auditable"]:::pillar
    P4["**④ Modernization-Gap Resolution**<br/>Confidence to iterate<br/>generate new OR enhance existing"]:::pillar

    Base["Source system → modernized target system"]:::base
    P1 --- Base
    P2 --- Base
    P3 --- Base
    P4 --- Base

    classDef cap fill:#0c1c4a,color:#ffffff,stroke:#0c1c4a,stroke-width:2px;
    classDef pillar fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px,color:#0c1c4a;
    classDef base fill:#fed7aa,stroke:#c2410c,stroke-width:2px,color:#3a1a00;
```

**Stylistic guidance for 2Slides:**

- Render as **four vertical columns / pillars** holding up the dark navy capstone
  ("Auditable, measurable AI-driven modernization") and resting on the orange base
  ("Source → target"). The four boxes are the four pillars in blue.
- Use the colour palette: navy `#0c1c4a`, pillar fill `#dbeafe`, pillar border
  `#1d4ed8`, base fill `#fed7aa`, base border `#c2410c`.
- The pillar numbers (① ② ③ ④) should be large and bold inside each pillar.
- Title above the figure: **"The Four Pillars"**.

**Free-form prompt (if rendering in Nano Banana instead):**

```
Clean editorial infographic: a stylised Greek temple with four blue columns,
each labelled with a circled number ① ② ③ ④. The columns hold up a dark navy
capstone labelled "Auditable, measurable AI-driven modernization", and rest
on a warm-amber base labelled "Source system → modernized target system".
Each column is annotated with a short phrase in clean sans-serif type:
"Dimensions", "Traceability", "Coverage Validation", "Modernization-Gap
Resolution". Minimal, flat, magazine-infographic style; navy / blue / amber
palette; 16:9 horizontal layout. Crisp text rendering.
```

---

## Image 3 — The five phases at a glance (2Slides)

**Use:** main pipeline diagram in the "Pipeline" section.

**Structure (2Slides input — Mermaid):**

```mermaid
flowchart TB
    Src[(Source system)]

    subgraph P1 ["**Phase 1 · Knowledge Extraction & Source Specification**"]
      direction TB
      L1[LLM analyses source]:::ai --> O1[Source architecture specs,<br/>requirements document,<br/>divergence catalogue]:::art
    end

    subgraph P2 ["**Phase 2 · Architect, Product, SME Decisions**"]
      direction TB
      L2[LLM proposes options]:::ai --> H2[Product team, Architect, SMEs<br/>review specs + accept decisions]:::human
      H2 --> O2[Decision records]:::art
    end

    subgraph P3 ["**Phase 3 · Target Specifications**"]
      direction TB
      L3[LLM drafts target-architecture<br/>and migration specs]:::ai --> H3[Architect reviews]:::human
      H3 --> O3[Migration-phase spec sets]:::art
    end

    subgraph P4 ["**Phase 4 · Modernization**"]
      direction TB
      L4[LLM implements code with<br/>traceability; runs coverage<br/>+ semantic verification]:::ai --> V4[Unit + integration +<br/>end-to-end tests]:::valid
      V4 --> O4[Target artifacts +<br/>coverage / semantic reports]:::art
    end

    subgraph P5 ["**Phase 5 · Hybrid Deployment & Cutover**"]
      direction TB
      L5[LLM generates IaC,<br/>deployment, cutover scripts]:::ai --> H5[Operations + Product<br/>approve traffic shifts]:::human
      H5 --> O5[Coexistence architecture,<br/>cutover plan, sunset schedule]:::art
    end

    Tgt[(Target system in production)]

    Src --> P1 --> P2 --> P3 --> P4 --> P5 --> Tgt

    P4 == "deferred decision" ==> P2
    P4 == "next migration-phase spec" ==> P3
    P4 == "new dimension or divergence" ==> P1
    P5 -. "overlap: target runs alongside source" .-> P4

    classDef ai fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px,color:#0c1c4a;
    classDef human fill:#fed7aa,stroke:#c2410c,stroke-width:2px,color:#3a1a00;
    classDef valid fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#064e3b;
    classDef art fill:#f3f4f6,stroke:#6b7280,stroke-width:1px,color:#111827;
```

**Stylistic guidance for 2Slides:**

- Render top-to-bottom, five subgraph blocks, each titled in bold with the phase number and name.
- Use the colour key:
  - **Blue** (`#dbeafe` fill, `#1d4ed8` border) — LLM / agent work
  - **Orange** (`#fed7aa` fill, `#c2410c` border) — human judgement
  - **Green** (`#d1fae5` fill, `#059669` border) — automated validation
  - **Grey** (`#f3f4f6` fill, `#6b7280` border) — artifacts produced
- Bold thick arrows (`==>`) for the three mid-phase re-entries from Phase 4
  back to Phase 1 / 2 / 3, drawn so the loop is visually obvious.
- Dotted arrow for Phase 5 ↔ Phase 4 overlap.
- Below the diagram, a small colour-legend caption.
- Title above figure: **"The Five Phases at a Glance"**.

---

## Image 4 — The Phase-4 modernization loop (2Slides)

**Use:** inner-loop diagram in the "Phase 4 — Modernization" section.

**Structure (2Slides input):**

```mermaid
flowchart TD
    Start(["**Migration-phase<br/>spec / plan / tasks**"]):::art --> A["**a. Produce target code<br/>with traceability links**"]:::ai
    A --> B["**b. Coverage analysis<br/>per dimension**"]:::valid
    B --> C{"**Gaps?**"}
    C -- yes --> D["**c. Gap resolution**<br/>generate new OR enhance existing"]:::ai
    D --> A
    C -- no --> E["**d. Semantic verification**<br/>on high-risk elements"]:::valid
    E --> F["**e. Unit / integration / E2E tests**"]:::valid
    F --> G{"**All pass?**"}
    G -- no --> A
    G == "yes" ==> Exit(["**Migration-phase exit gate**"]):::art

    classDef ai fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px,color:#0c1c4a;
    classDef valid fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#064e3b;
    classDef art fill:#f3f4f6,stroke:#6b7280,stroke-width:1px,color:#111827;
```

**Stylistic guidance:**

- Same colour key as Image 3.
- The two diamonds (`Gaps?` / `All pass?`) should be visually distinct.
- The bold `==>` arrow to "Migration-phase exit gate" should stand out as the success path.
- Title above figure: **"The Phase-4 Modernization Loop"**.

---

## Image 5 — Coverage + Gap Resolution mechanism (2Slides)

**Use:** illustrating "The Core Mechanism" section.

**Structure (2Slides input):**

```mermaid
flowchart TB
    Src["**Source inventory**"]:::art --> V["**Coverage validator**"]:::valid
    Tgt["**Target code + traceability**"]:::art --> V
    V == "per dimension" ==> R{"**Status**"}
    R == "covered ∪ eliminated" ==> OK(["**Accounted for**"]):::valid
    R == "unmatched" ==> GAP["**Gap report**"]:::valid
    GAP --> AI["**AI agent**"]:::ai
    AI == "add new<br/>OR enhance existing<br/>OR correct previous" ==> Tgt
    Tgt -. "revalidate" .-> V

    classDef ai fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px,color:#0c1c4a;
    classDef valid fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#064e3b;
    classDef art fill:#f3f4f6,stroke:#6b7280,stroke-width:1px,color:#111827;
```

**Stylistic guidance:**

- This is the article's most important conceptual diagram — give it visual weight.
- Two boxes feed the validator (Source inventory + Target traceability).
- The validator emits two outputs: "Accounted for" and "Gap report".
- "Gap report" routes back into "AI agent" which writes back into "Target code".
- Title above figure: **"The Core Mechanism: Coverage + Gap Resolution Loop"**.
- Below the diagram, a one-line caption: _"The agent is never told to translate
  lines. It is told which source element has not yet been accounted for, and
  decides where it belongs in the target."_

---

## Image 6 — Artifact flow (2Slides)

**Use:** illustrating the reference-project walkthrough section.

**Structure (2Slides input):**

```mermaid
flowchart TB
    P1["**Phase 1**<br/>Knowledge Extraction"]:::phase ==>|"source architecture specs<br/>requirements + RTM<br/>divergence catalogue"| P2["**Phase 2**<br/>Decisions"]:::phase
    P2 ==>|"decision records<br/>decision index"| P3["**Phase 3**<br/>Target Specs"]:::phase
    P3 ==>|"migration-phase specs<br/>plans + tasks"| P4["**Phase 4**<br/>Modernization"]:::phase
    P4 ==>|"target artifacts<br/>traceability<br/>coverage + semantic reports"| P5["**Phase 5**<br/>Hybrid Deployment"]:::phase
    P4 -. "new divergences" .-> P1
    P4 -. "deferred decision needed" .-> P2
    P4 -. "next migration-phase" .-> P3

    GF["**AGENTS.md**<br/>Governing Principles<br/>Skills"]:::gov
    GF -. "consulted by every phase" .-> P1
    GF -. "consulted by every phase" .-> P2
    GF -. "consulted by every phase" .-> P3
    GF -. "consulted by every phase" .-> P4
    GF -. "consulted by every phase" .-> P5

    classDef phase fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px,color:#0c1c4a;
    classDef gov fill:#fef3c7,stroke:#b45309,stroke-width:2px,color:#3a1a00;
```

**Stylistic guidance:**

- Five blue phase boxes, vertical chain top to bottom.
- A yellow "AGENTS.md / Governing Principles / Skills" box on the right side,
  with dotted arrows fanning out to all five phases.
- Bold thick arrows for the main flow (`==>`), dotted arrows for re-entries and
  governance consultations.
- Title above figure: **"Artifact Flow Across the Pipeline"**.

---

## Production checklist

Before sending images for layout, double-check the following per image:

- [ ] Title and caption text in image matches the article body verbatim.
- [ ] Colour palette is consistent across Images 2–6 (navy / blue / orange / green / grey / amber-yellow).
- [ ] No legacy logos or screenshots.
- [ ] No raw code text inside figures (use the article body for code samples).
- [ ] Figure proportions: Image 1 = portrait 9:16 for full-page cover;
      Images 2–6 = landscape 16:9 (or 4:3 if the layout calls for it).
- [ ] Bold subgraph / phase headings are visibly bolder than node body text.
- [ ] Every arrow has a label (no unlabelled arrows except the obvious
      sequential chain in Image 3).
