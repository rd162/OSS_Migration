# Domain Knowledge Matrix

Reference tables for the knowledge saturation skill.
Maps domains to CoK expansion patterns, source tiers,
tool selection, and query strategies.

Loaded on demand — not part of the main SKILL.md context.

---

## CoK Patterns by Domain

| Domain     | CoK Expansion Pattern                                                            | Forward-Fill Focus                   |
| ---------- | -------------------------------------------------------------------------------- | ------------------------------------ |
| Technical  | (tool, requires, ?) → (dep, version, ?) → (config, ?)                            | Dependencies, configuration          |
| Scientific | (finding, replicated_by, ?) → (finding, contradicts, ?)                          | Replication, contradictions          |
| Historical | (event, caused_by, ?) → (event, context, ?) → (era, ?)                           | Causation, context                   |
| Debug      | (error, caused_by, ?) → (cause, fixed_by, ?) → (solution, ?)                     | Root cause, solution chain           |
| ML/AI      | (model, trained_on, ?) → (model, outperforms, ?) → (benchmark, ?)                | Training, benchmarks                 |
| Compare    | (X, differs_from, Y) → (X, better_at, ?) → (Y, better_at, ?)                     | Trade-offs, use cases                |
| Psychology | (behavior, caused_by, ?) → (mechanism, modulated_by, ?) → (intervention, ?)      | Mechanisms, interventions            |
| Physics    | (phenomenon, described_by, ?) → (model, predicts, ?) → (experiment, confirms, ?) | Models, experimental evidence        |
| Culinary   | (technique, produces, ?) → (ingredient, reacts_with, ?) → (result, ?)            | Techniques, chemistry, substitutions |
| Business   | (market, driven_by, ?) → (competitor, differentiates_via, ?) → (trend, ?)        | Drivers, competition, trends         |
| Creative   | (style, influenced_by, ?) → (principle, achieves, ?) → (medium, ?)               | Influences, principles, constraints  |
| Education  | (concept, prerequisite, ?) → (method, improves, ?) → (assessment, ?)             | Prerequisites, pedagogy              |
| Policy     | (regulation, mandates, ?) → (compliance, requires, ?) → (enforcement, ?)         | Mandates, compliance, precedent      |
| Medical    | (condition, treated_by, ?) → (treatment, contraindicated_by, ?) → (outcome, ?)   | Treatments, contraindications        |

---

## Source Tiers + Temporal Rules

| Domain     | T1 Sources                          | T2 Sources                 | Temporal Rule     |
| ---------- | ----------------------------------- | -------------------------- | ----------------- |
| Technical  | Official docs, RFCs                 | Expert blogs               | `{current_year}`  |
| Scientific | Peer-reviewed journals              | Preprints, conf            | NO temporal       |
| Historical | Primary archives                    | Scholarly consensus        | `[era]` NOT year  |
| SW-Current | Release notes, changelog            | Production forums          | `{current_year}`  |
| SW-Legacy  | Archive docs                        | Migration guides           | version# only     |
| Debug      | Issue trackers, docs                | Stack Overflow             | recent 2 years    |
| ML/AI      | Papers, official repos              | GitHub, benchmarks         | `{current_year}`  |
| Legal      | Statutes, case law                  | Legal analysis             | jurisdiction+date |
| Medical    | Clinical trials, systematic reviews | Clinical guidelines        | NO temporal       |
| Financial  | SEC filings, annual reports         | Analyst coverage           | quarter/year      |
| Psychology | APA journals, meta-analyses         | Textbooks, review papers   | NO temporal       |
| Physics    | Physical Review, Nature Physics     | arXiv preprints, CERN      | NO temporal       |
| Culinary   | Food science journals, USDA         | Professional chef guides   | NO temporal       |
| Business   | SEC filings, industry reports       | HBR, analyst reports       | `{current_year}`  |
| Creative   | Design systems, style guides        | Award archives, portfolios | trend+year        |
| Education  | Ed research journals, ERIC          | Practitioner guides        | NO temporal       |
| Policy     | Legislation text, court rulings     | Policy analysis orgs       | jurisdiction+date |

---

## Tool Selection + CoK Depth

### Tool Categories

Tools are grouped by **capability**, not by name.
At Δ1, identify which capabilities are available
and map to the best available tool per category.

| Capability          | Preferred Tools (if available)                                  | Fallback                                          |
| ------------------- | --------------------------------------------------------------- | ------------------------------------------------- |
| **Code search**     | `get_code_context_exa()`, `query-docs()` (Context7)             | `grep`, `firecrawl_search()` site-scoped          |
| **Library docs**    | `query-docs()` (Context7), `resolve-library-id()`               | `firecrawl_scrape()` on docs URL                  |
| **Web search**      | `web_search_exa()`, `firecrawl_search()`, `kagi_search_fetch()` | Any tool with web search capability               |
| **Academic search** | `web_search_advanced_exa(category="research paper")`            | `firecrawl_search()` site:arxiv.org, site:nih.gov |
| **Company/market**  | `company_research_exa()`                                        | `web_search_exa(category="company")`              |
| **People/experts**  | `people_search_exa()`                                           | `web_search_exa(category="people")`               |
| **Page content**    | `firecrawl_scrape()`, `crawling_exa()`                          | `fetch()`, `kagi_summarizer()`                    |
| **Summarize**       | `kagi_summarizer()`, `deep_researcher_start()`                  | Manual extraction from scrape                     |
| **Deep research**   | `deep_researcher_start()` (exa-research-pro)                    | Multi-query web search + scrape                   |
| **News/current**    | `firecrawl_search(sources: news)`, `web_search_exa()`           | Any search tool with date filter                  |
| **Embedded search** | Built-in `web_search` (Claude), `search` (Copilot)              | Always available as last resort                   |

### High-Stakes Domain Protocol

**⚠ CRITICAL: Some domains carry life-affecting consequences.**

A wrong answer in medicine can cause death.
A wrong answer in psychology can contribute to suicide.
A wrong answer in legal advice can result in imprisonment.
A wrong answer in structural engineering can cause building collapse.
A wrong answer in pharmacology can cause poisoning.

For these domains, standard search is **insufficient**.
Deep research is **mandatory**, not optional.

**High-stakes domains (deep research ALWAYS required):**

| Domain               | Risk                                      | Why deep research is mandatory                                          |
| -------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| Medical              | Harm, death                               | Treatments evolve, drug interactions are complex, guidelines change     |
| Psychology           | Self-harm, suicide, trauma                | Interventions can backfire, debunked therapies persist in popular media |
| Pharmacology         | Poisoning, adverse reactions              | Dosage errors, contraindications, recall notices                        |
| Legal (advisory)     | Imprisonment, financial ruin              | Jurisdiction-specific, precedent changes, statutory amendments          |
| Structural/Civil     | Building collapse, infrastructure failure | Load calculations, material properties, code compliance                 |
| Nutrition (medical)  | Allergic reaction, dietary harm           | Allergen interactions, condition-specific dietary requirements          |
| Childcare/Parenting  | Developmental harm                        | Debunked practices persist (e.g., outdated sleep/feeding guidance)      |
| Financial (advisory) | Bankruptcy, fraud exposure                | Regulatory changes, tax law, investment suitability                     |

**High-stakes detection heuristic:**
If the answer could plausibly influence a decision that affects
someone's physical health, mental health, legal standing, financial security,
or physical safety — treat as high-stakes.
When uncertain whether a domain is high-stakes, **escalate to deep research**.

**Mandatory protocol for high-stakes domains:**

```text
∆1: Detect high-stakes domain (from table above or heuristic)
∆2: Use deep research tool (MANDATORY, not optional)
    → deep_researcher_start(model="exa-research-pro") or equivalent
    → If deep research tool unavailable → run 5-8 targeted searches
      across T1 academic sources with explicit safety focus
∆3: Cross-validate against T1 sources ONLY
    → Peer-reviewed journals, clinical guidelines, official regulatory text
    → T2-T4 sources may inform but NEVER override T1 for high-stakes claims
∆4: Forward-fill CoK to explore consequences and contraindications:
    → (treatment, interacts_with, ?) — what conflicts exist?
    → (intervention, contraindicated_for, ?) — who should NOT receive this?
    → (advice, assuming, ?) — what assumptions might be wrong for this person?
    → (recommendation, superseded_by, ?) — has this been updated?
∆5: Always include safety disclaimers in output:
    → "Consult a qualified [professional] before acting on this information."
    → Mark confidence level explicitly
    → Expose contradictions between sources — NEVER silently resolve them
```

**Forward-Fill CoK for High-Stakes Domains:**

Standard CoK fills gaps: (subject, relation, ?).
High-stakes CoK ALSO fills **consequence and contraindication gaps**:

```text
Standard fill:
  (medication X, treats, condition Y)
  (condition Y, symptoms, ?)         → fill: what symptoms

Forward-consequence fill (HIGH-STAKES ONLY):
  (medication X, interacts_with, ?)  → fill: drug interactions
  (medication X, contraindicated_for, ?) → fill: who should NOT take this
  (medication X, superseded_by, ?)   → fill: newer alternatives
  (medication X, withdrawn_in, ?)    → fill: regulatory actions
  (treatment, assuming, ?)           → fill: what conditions must be true
  (advice, if_wrong, ?)              → fill: what happens if this is wrong
```

This pattern applies to ALL high-stakes domains:

```text
Psychology:
  (intervention, backfires_when, ?)     → when does this make things worse
  (therapy, debunked_by, ?)             → has this been disproven
  (advice, contraindicated_for, ?)      → who should NOT receive this

Legal:
  (statute, amended_by, ?)              → has this law changed
  (precedent, overturned_in, ?)         → is this still valid
  (advice, jurisdiction_limited_to, ?)  → where does this apply

Engineering:
  (calculation, assumes, ?)             → what must be true for this to hold
  (material, fails_under, ?)            → failure conditions
  (design, violates_code, ?)            → regulatory compliance
```

---

### Domain → Tool Capability Mapping

| Domain     | Primary Capability       | Secondary Capability  | Deep Research | CoK Depth |
| ---------- | ------------------------ | --------------------- | ------------- | --------- |
| Code/API   | Code search              | Library docs          | Optional      | L0-L2     |
| Technical  | Web search               | Page content          | Optional      | L0-L3     |
| Research   | Academic search          | Page content          | Recommended   | L0-L4     |
| Current    | News/current             | Web search            | Optional      | L0-L2     |
| Debug      | Code search              | Web search            | Optional      | L0-L2     |
| Visual     | Web search (images)      | Page content (vision) | Optional      | L0-L1     |
| Deep       | Deep research            | Multi-tool sweep      | **YES**       | L0-L4     |
| Psychology | Academic search          | Deep research         | **MANDATORY** | L0-L4     |
| Physics    | Academic search          | Page content          | Recommended   | L0-L4     |
| Culinary   | Web search               | Page content          | Optional      | L0-L2     |
| Business   | Company/market           | News/current          | Situational   | L0-L3     |
| Creative   | Web search               | Page content          | Optional      | L0-L2     |
| Education  | Academic search          | Web search            | Recommended   | L0-L3     |
| Policy     | Web search (site-scoped) | Deep research         | **MANDATORY** | L0-L4     |
| Medical    | Academic search          | Deep research         | **MANDATORY** | L0-L4     |
| Financial  | Company/market           | Deep research         | **MANDATORY** | L0-L4     |
| Legal      | Academic search          | Deep research         | **MANDATORY** | L0-L4     |

**Tool availability varies by session.**
Always scan available tools at Δ1 before planning.
Map domain to capability, then capability to best available tool.
If preferred tool unavailable, use the fallback from the capability table.
If no external tools at all, use embedded search or training knowledge with disclaimer.

**⚠ For MANDATORY deep research domains:**
If deep research tool is unavailable,
compensate with 5-8 targeted searches on T1 sources,
forward-fill CoK with consequence/contraindication patterns,
and always include safety disclaimers.
Never present high-stakes answers without explicit T1 source citations.

---

## Query Patterns + Fallback

| Domain       | Primary Query                       | Fallback Query                   | Broaden Strategy   |
| ------------ | ----------------------------------- | -------------------------------- | ------------------ |
| Technical    | `"[X] docs"`                        | `"[X] tutorial guide"`           | parent_category    |
| Scientific   | `"[X] peer-reviewed"`               | `"[X] preprint meta"`            | related_field      |
| Historical   | `"[X] primary source [era]"`        | `"[X] scholarly consensus"`      | broader_period     |
| Debug        | `"[Error] exact message"`           | `"[Error] similar type"`         | error_category     |
| Compare      | `"[X] vs [Y] benchmark"`            | `"[X] alternative to [Y]"`       | solution_space     |
| ML/AI        | `"[X] paper implementation"`        | `"[X] benchmark {year}"`         | model_family       |
| SW-Implement | `"[X] guide production"`            | `"[X] examples real"`            | framework_category |
| Psychology   | `"[X] meta-analysis APA"`           | `"[X] systematic review"`        | broader_construct  |
| Physics      | `"[X] Physical Review arXiv"`       | `"[X] experiment measurement"`   | related_phenomenon |
| Culinary     | `"[X] technique food science"`      | `"[X] recipe professional chef"` | cuisine_family     |
| Business     | `"[X] market analysis {year}"`      | `"[X] industry report"`          | adjacent_market    |
| Creative     | `"[X] design principles examples"`  | `"[X] style guide portfolio"`    | design_system      |
| Education    | `"[X] pedagogy evidence-based"`     | `"[X] teaching method research"` | learning_theory    |
| Policy       | `"[X] regulation legislation text"` | `"[X] compliance guide"`         | jurisdiction       |
| Medical      | `"[X] clinical trial systematic"`   | `"[X] treatment guidelines"`     | condition_category |
| Financial    | `"[X] SEC filing annual report"`    | `"[X] analyst coverage {year}"`  | sector             |
| Legal        | `"[X] case law statute"`            | `"[X] legal analysis precedent"` | jurisdiction       |

**Broadening Chain:** topic → synonyms → parent_category → domain

---

## LLM Pattern Files Protocol

Always check for `llms*.txt` files in current directory first.

```text
⚠ WARNING: llms*.txt files can be EXTREMELY LARGE
  → NEVER read entire file
  → NEVER attempt to outline contents
  → NEVER load into context directly

PROTOCOL:
1. Check existence: ls llms*.txt
2. Build/use section index:
   → grep "^##" llms*.txt > llms_sections_index.json
   → Parse ## headings into JSON structure
3. Search for matching patterns:
   → Use grep with L2-L3 heading breakdown
   → Match query against section titles
4. Extract ONLY relevant sections:
   → Read specific section by line range
   → Never exceed token budget
```

**Index Structure:**

```json
{
  "file": "llms.txt",
  "sections": [
    { "level": 2, "title": "Section Name", "line": 42 },
    { "level": 3, "title": "Subsection", "line": 58 }
  ]
}
```

**Pattern Matching Flow:**

```text
Query → grep sections index → identify L2/L3 matches → extract targeted section only
```
