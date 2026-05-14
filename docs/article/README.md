# Article Package — AI-Assisted Software Modernization

This directory contains a standalone, magazine-style article that distills the
full `docs/ai-assisted-migration-architecture.md` design document into a
publication-ready piece, plus the image-generation prompts needed to produce
its six illustrations.

## Files

| File                                       | Purpose                                                                                                                                   |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `ai-modernization-architecture-article.md` | The article body, in Markdown. Designed to render to ~14 PDF pages, matching the format of the reference articles in `Article_Examples/`. |
| `image-prompts.md`                         | Six image prompts (one per `Image N` placeholder in the article) with tool recommendations and structural Mermaid blueprints.             |

## Rendering to PDF

Two recommended paths.

### Path A — Pandoc + LaTeX (highest fidelity)

```bash
brew install pandoc mactex-no-gui
pandoc docs/article/ai-modernization-architecture-article.md \
    --from gfm \
    --pdf-engine=xelatex \
    --variable mainfont="Helvetica Neue" \
    --variable geometry:margin=1in \
    --variable linestretch=1.15 \
    -o docs/article/ai-modernization-architecture-article.pdf
```

Insert the six rendered images at the `> _Image N — …_` placeholders (either
manually in a Word / Pages / InDesign layout, or by replacing each placeholder
line in the Markdown with an `![caption](path/to/image.png)` reference before
running pandoc).

### Path B — Magazine-template Word document (matches the Capgemini SWE Magazine layout)

The existing articles in `Article_Examples/` use a Word template (`Factsheet`
template, per the PDF metadata). To reproduce that layout:

1. Open the Word template provided by the magazine.
2. Paste the article body section by section.
3. Insert each image at its `> _Image N — …_` placeholder.
4. Export to PDF via Word's `Save as PDF`.

## Notes on length and density

- The reference article _How to migrate your code from C to Rust_ runs to
  14 pages with approximately 6,500–7,000 words of body text and 4–5 custom
  diagrams plus one hero cover. The article here is sized to match.
- Section depth, code-sample placement, and diagram captions follow the same
  rhythm as the reference article.
