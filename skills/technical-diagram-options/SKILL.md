---
name: technical-diagram-options
description: Choose and generate source-grounded technical mechanism diagrams with materially different structural options, separate visual treatments, and editable SVG/draw.io or native PPT deliverables. Use for architecture, tensor, mapping, scheduling, state, routing, or mechanism-comparison diagrams, not generic illustration or chart styling.
---

# Technical diagram options

Help the user choose a diagram **for this explanation**, not conform every task to one style. This candidate rulepack links structural choices to public technical sources; it is not evidence that a preset improves comprehension or performance. Read `references/corpus_snapshot.json` for the public catalog scope and `references/validation.md` for tested scope.

## Shared drawing-language profile

Read `../technical-architecture-diagrams/references/text-language.md` and its `language-profile.json` even when this package is invoked directly. Default `diagram-en-prose-zh`: diagram-integrated short labels, titles, legends and arrow annotations in English; standalone explanatory prose in Chinese, regardless of geometric position or character count. Preserve technical terms, model names, formulas and variables. Semantic text roles override container geometry. All diagram-surrounding HTML text is part of drawing QA, not deferred to PPT.

Set `language_profile` and explicit `text_role` values in new diagram IR. Use the shared checker from the sibling package; its role/character checks do not prove semantic correctness. Keep manual semantic/render review distinct and never silently translate source text. Existing unprofiled examples are legacy and cannot claim this profile's compliance.

## Work from the question

1. Extract the question, audience, final display size, factual inputs, unknowns, required format, and preserved user edits. Separate **technical structure** (what relations exist), **visual presentation** (how shown), and **use case** (why this audience needs it). Current user/source constraints override examples and presets.
2. Map the question to [structure modes](references/selection.md). Read the matching cards in `references/rules.json`, not all source material. Their triggers, required facts, alternatives, boundaries, counterexamples and checks are part of the rule—not optional footnotes. Compound questions may need combinations rather than one universal layout.
3. Usually offer 2–3 materially different options, but do not force a count or wait when the user already chose or authorized you to choose. Each option says what question it answers, what it reveals/hides, facts still needed, and why it fits. A palette swap is not a structural alternative. Recommend one with a reason; don't invent timings, dimensions, topology or benchmarks to make another option possible.
4. Create a diagram **of the target mechanism** from verified task facts, not a new mechanism or a label-substituted source figure. Distilled sources justify presentation hypotheses, not facts about the new mechanism. Source-sensitive choices require reading the exact asset: `sources.json` gives public URLs and figure/version citations only; private archive paths, hashes and collector observations are excluded. A citation is not pixel inspection. Missing image access means visual validation of that reference is pending.
5. Keep stable semantic IDs, facts, relationships and provenance separate from geometry/style. Use [generation contract](references/generation.md) and the task/IR schemas. Preserve locked user elements; a targeted edit should not silently reflow the whole drawing. Apply only the chosen treatment, not every example's colors.
6. Validate semantics and editability, then render and inspect at final size. Structural parsing alone is not visual QA. Check labels, line/object intersections, arrow destinations, identities across panels, omitted conditions and units. Fix actual failures; no arbitrary iteration limit. Deliver the chosen editable source, preview, and concise assumptions/provenance/QA note. PNG/PDF alone is not editable source.

## Golden-guided calibration

For golden comparison, read [visual calibration](references/visual-calibration.md) and the [full-corpus mechanism contract](references/full-corpus-calibration.md). Before geometry, freeze the factual brief and required visible relations; audit typed dependencies, temporal identities and numerical invariants separately from styling. After edits, run that contract’s required-port, entire-route, arrowhead and task-inventory gate; endpoint metadata alone is insufficient. Match the mechanism and information hierarchy, not pixels. An optional treatment for similar flowcharts is light rounded corners, pale fills, thin low-contrast borders and no shadow; it does not impose a single layout on matrices, timelines, trees or maps. Keep technical identity and visible dependencies ahead of prettiness.

## Practical interface

```bash
python scripts/select_options.py task.json --out options.json
python scripts/diagram_tool.py check diagram.json
python scripts/diagram_tool.py render diagram.json --out-dir output
python scripts/check_package.py                 # catalog/reference integrity
```

`select_options.py` ranks explicit semantic features and reports missing facts; it is an inspectable heuristic, not a learned model or efficacy score. The agent chooses geometry after selecting a structure. `diagram_tool.py` exports editable SVG and uncompressed native `.drawio` from that geometry; it does **not** force automatic flowchart layout. For user-requested native PPT, follow the PPT section in generation.md; do not claim this exporter creates PPT.

## Do not turn local feedback into universal taste

- Dense figures may be appropriate. Preserve necessary indices, crossings and full static mappings when useful; sparse is not automatically better.
- Icons can encode resources, roles or trainability. Arrow quality is local and semantic, not a blanket ban on arrows.
- Structure can be good while formatting is not. Re-style without changing the mechanism.
- Do not present copied source artwork as a newly generated diagram or infer redistribution rights. When the user/task calls for original-figure reuse, retain attribution and authorized scope, and explain its actual editability. Do not copy full blog text or the referenced draw.io repository's code; do not adopt its rigid palette/spacing, mandatory orthogonal routing or fixed feedback-round limits. This package contains compact citations and generated rules, not source artwork.

## Read only when needed

- [selection.md](references/selection.md): structure choices, compositions and presentation axes.
- `references/rules.json`: conditional rule cards with exact case/source IDs (S = structures, C = compositions, V = visual guidance, G = integrity); `references/taxonomy.json` separately defines source-asset S/P tags.
- `references/sources.json`, `references/cases.json`: compact provenance and limitations; no full source text.
- [generation.md](references/generation.md): editable output and update contracts.
- [provenance.md](references/provenance.md): evidence levels, source access, method attribution and version caveats.
- `schemas/task.schema.json`, `schemas/diagram.schema.json`, `schemas/rule.schema.json`, `schemas/case.schema.json`: machine-readable interchange contracts.
- `examples/toy-mapping.task.json`, `examples/toy-mapping.diagram.json`: invented toy mechanism demonstrating the interface, not evidence of effectiveness.
