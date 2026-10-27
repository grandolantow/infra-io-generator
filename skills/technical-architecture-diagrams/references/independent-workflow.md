# Independent drawing-agent workflow

The calling presentation/report agent supplies a content brief: question,
audience, sourced facts and unknowns, use case, theme, preserved content and
available display space. Space is an order constraint, not locked geometry: the
drawing agent may propose a different ratio, local expansion or split when it
improves understanding; the caller adapts the page after receiving the figure.
Theme colors need broadly coordinate, not exact token equality; the drawing
agent may choose restrained functional colors rather than identical gray fills.
The drawing agent owns structure, components, diagram-integrated short English
annotations, terminology and language QA. Generate the figure first. The caller
then decides how much independent explanatory prose to add and how to lay it out;
do not pre-fill every variant with a complete explanation. Optional associated
text is a suggestion, not a mandatory rendered paragraph or host copy.


## Handoff and execution

Use repository `contracts/diagram-brief.schema.json` and
`tools/prepare_diagram_brief.py --input brief.json --out-dir handoff`.
Preparation validates and writes a task, **not** an LLM design or agent execution.
The host actually delegates to an independent drawing agent with this Skill,
brief and accessible inputs. Without delegation capability, mark blocked rather
than silently designing in the caller. Low-level check/render APIs remain useful
for iteration and compatibility, but are not the high-level generation API.

The drawing agent performs these stages:

1. **Inspect applicable knowledge and visual references.** Read the selected
   branch, model layout recipes and relevant golden/backend experience, or report
   selection/rules/calibration material. Open actual reference pixels when making
   visual comparisons. Preserve reference files or task-local excerpts with hashes
   and locations in the private delivery bundle; source citations alone do not
   prove inspection. Do not publish copyrighted assets without authorization.
   Record missing references honestly; don't describe a missing image as reviewed.
2. **Freeze semantics.** Verify facts, IDs, dependencies, visible operators,
   scope and unknowns. A source's design can inform presentation but not supply
   unverified facts about the target model. Select the appropriate branch(s).
3. **Select and design.** For report/mixed tasks run the original report
   `select_options.py` on a fact-grounded task before geometry. Retain its JSON,
   chosen option IDs, reasons, alternatives and applications to actual object IDs;
   don't discard the selector after generating a generic flowchart. For model
   tasks consume the vertical-backbone/side-detail preference and justify deviation.
   Design component shapes by semantic role, relative proportions, hierarchy,
   density, typography, functional color, ports, arrow paths and local expansions.
   Rounded corners alone are not a design process or aesthetic evidence. Different
   diagram categories need different components and layouts.
4. **Render real sources.** Produce editable native objects and invoke the actual
   supported renderer. Retain source and output hashes plus backend QA. Metadata
   or hand-authored preview markup is not evidence that a backend ran. Keep language
   roles and all surrounding explanations in drawing-side QA.
5. **Compare actual figures and revise.** Inspect rendered pixels at intended size
   against the selected reference's hierarchy, component treatment, proportions,
   connection readability and information density—not just palette or pixel
   similarity. Check facts/labels, omissions, overlap and endpoints separately.
   Record observed issues, specific revisions and resulting output IDs. If no
   revision is needed, state the concrete comparison observations; do not invent
   an iteration history. Automated geometry success is not a visual review.
6. **Deliver numbered alternatives and let the caller adapt.** Normally produce
   3–4 materially different numbered designs (brief `variant_count` defaults to 3;
   an explicit count can override). Differences must concern information structure,
   abstraction, grouping or mechanism explanation—not only recoloring, rotation,
   rounded corners or spacing. Preserve the same required facts across alternatives.
   Each variant has its own editable source, render and QA references. Archive all
   variants in one real PDF with their IDs visibly printed on corresponding pages;
   retain `variants[].pdf_pages` and `archive_pdf_artifact_id` in the delivery.
   The caller selects one ID to embed in HTML, links the complete numbered PDF,
   and leaves final choice to the user. Return editable source, rendered figure,
   surrounding text, reference/selector evidence, design decisions and QA via
   `contracts/diagram-delivery.schema.json`. The caller embeds/adapts the completed
   figure, checks page fit, and does not overwrite its structure to fill 16:9.

Run `tools/check_diagram_delivery.py --brief handoff/brief.json
--delivery diagram-delivery.json --root delivery-dir --output contract-qa.json`.
It checks schemas, exact artifact hashes, reference/selection links, requested
variant count and real PDF page/visible-number mappings (Poppler required); it does
not prove that an agent read an asset or that the design is scientifically or
visually correct. Agent visual review is recorded separately from user approval.
Missing stages remain blocked/not_run, never automatically promoted by a passing
schema. This contract is an executable evidence boundary, not a diagram designer.

## Variant evidence contract

`variants[]` records `id`, `structural_difference`, `editable_artifact_ids`,
`rendered_artifact_ids`, `qa_artifact_id`, and one-based `pdf_pages`. A completed
delivery must meet the requested count and bind every PDF page to exactly one
variant; print the matching ID on every assigned page. `selected_variant_id` is
optional before the caller chooses, but must identify an existing variant when
present. The host must select explicitly before HTML embedding, not silently
treat the first variant as approved. Evidence checks do not establish that the
variants are aesthetically good or meaningfully distinct; actual comparative
review must address `structural_difference` and shared factual completeness.
