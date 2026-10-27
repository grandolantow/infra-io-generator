# Generation and targeted-update contract

## Inputs and outputs

A `task.json` declares goal, audience, use case, relational `features`, known facts, unknowns, constraints, presentation preferences, and requested outputs. See `schemas/task.schema.json`. Map natural language into these fields with stated assumptions; the selector does not parse or verify natural language.

A `diagram.json` separates:

- `semantic.facts`: ID, statement and provenance. For a toy, explicitly say user-provided/invented. A source-rule citation is not proof of this task's mechanism.
- `semantic.nodes`: stable object IDs and type/label/fact references.
- `semantic.edges`: stable relation IDs, typed relation, endpoint IDs and fact references. Name operations such as add, concat, transfer, map, ancestry, wait or update.
- `views`: canvas and scope/omissions, chosen rule IDs, glyph instances and routed paths. Each object/path points back to its semantic ID. Multiple views can show the same object without claiming multiple physical copies.
- `edit_policy`: locked IDs and user-owned fields to preserve. Before an edit, compare the old/new semantic and view models. The renderer does not enforce a previous revision automatically.

No coordinates, palette or fonts are forced by the structure modes. The bundled renderer accepts authored geometry rather than hiding a universal autolayout. SVG and draw.io are generated from the same geometry, but font engines and label placement can differ: inspect **both** requested formats in their actual viewer before declaring visual parity.

## Authoring the lightweight renderer IR

Glyph shape: `rect`, `rounded_rect`, `ellipse`, `diamond`, or `text`. Provide `x,y,w,h`, `label_lines` (explicit line breaks), and `style` (`fill`, `stroke`, `stroke_width`, `font_size`, `font_family`, `text_color`, `dashed`). Use containers only where containment is real; mark `role: container` so intentional boundary crossing is not treated as an unrelated obstruction. Matrix cells, timeline blocks and tree nodes are ordinary glyphs with different relational layout—not fake prebuilt flowchart blocks.

Paths have `source_instance`, `target_instance`, `semantic_ref`, explicit `points`, optional `arrow: end|both|none`, and style. A path label needs an explicit `label_position`. Points may form straight or segmented routes; no mandatory orthogonal edges. The minimal exporter does not support Bézier routes, embedded raster icons, gradient styles or math typesetting. If those are important, author native SVG/draw.io directly while retaining the same semantic/provenance contract; never flatten the whole mechanism to evade source editability.

The default black/white fallback is a renderer fallback, not a preferred visual preset. Choose explicit styles from the user/context. Text labels are escaped as XML; the exporter does not execute code or fetch images. SVG leaves text as text and exposes object groups; draw.io uses native cells/connectors. Containers are visual native rectangles, not editable nested-group semantics; group them in the target editor when needed.

```bash
python scripts/select_options.py examples/toy-mapping.task.json --out options.json
python scripts/diagram_tool.py check examples/toy-mapping.diagram.json
python scripts/diagram_tool.py render examples/toy-mapping.diagram.json --out-dir /tmp/diagram-example
```

Output: one SVG per view, one native `.drawio` with all views, a source IR copy, and structural QA JSON. The script does not create a screenshot or declare visual QA passed.

## Quantitative evidence (S11)

Use a real plotting workflow for measured curves, bars and distributions; retain the data table and plotting source with the editable SVG/PPT. Do not draw invented heights or smooth curves in the generic glyph exporter and label them evidence. Label theoretical/illustrative values distinctly. A mechanism diagram plus chart must keep causal claims separate from measured associations.

## Targeted edits

1. Read the current editable source/IR and current user constraints. Keep IDs even when labels or positions change. If the user edited native SVG/draw.io/PPT after export, that file may be newer than the IR: reconcile its changes first instead of regenerating from a stale sidecar. The exporter is not a lossless native-file importer.
2. Identify fields that must change; protect locked nodes, user annotations and explicit coordinates outside the affected region.
3. Change semantic facts only when requested or verified. A style-only edit must not change semantic facts or edge endpoints.
4. Validate changed geometry plus adjacent connections, render and compare to the prior view. If a local change requires reflowing locked content, present the conflict instead of overwriting it.
5. Return the revised editable source and state what changed. A static preview alone is insufficient.

## Reusing an original figure

When the user chooses an existing paper/blog figure and reuse is authorized within the task scope, preserve its attribution, version and applicable rights. Do not label it an original generated diagram. State whether the delivered source is the original raster, a vector with editable text/objects, or a faithful reconstruction. A raster embedded in SVG/PPT remains a raster, not native-object editability. If the user specifically requires editable mechanism objects, obtain or author a suitable editable version rather than changing the claim on the same image.

## PPT deliverable

If native PPT is selected, use the available presentation-authoring workflow. Create native shapes, text, groups and connectors corresponding to semantic IDs; attach source IDs/assumptions in speaker notes or companion provenance. Verify that text and key mechanism objects can be separately selected and edited in the actual PPT editor. A slide containing one SVG/PNG may look sharp but is **not** a native-shape diagram; an SVG converted to shapes still needs text/connector inspection. Provide the chosen `.pptx` plus source IR and preview; do not substitute draw.io without asking if native PPT editability is a requirement.

## QA gates and honest completion

- **Semantic:** all stated relationships agree with verified facts; dimensions, operators, ancestry, state transitions, versions and legends are consistent.
- **Source:** rule IDs resolve, task facts have their own sources, copied assets have appropriate permission, no unreviewed current claim is imported from an old blog.
- **Structural:** IDs/endpoints parse, glyph references match model relations, positive canvas geometry, no accidental out-of-canvas elements.
- **Visual:** actual final-size rendering inspected, labels/arrowheads readable, crossings purposeful, identity continuity retained, no clipping, text and lines distinguishable.
- **Editable:** native objects/text are actually present and tested in the requested target; file extension alone is insufficient.
- **Comparison:** alternatives differ in explanation or structural composition, not merely colors; unsupported extra views are flagged.

Automated geometry warnings are approximate and may flag purposeful crossing or nested labels. Explain justified exceptions rather than mechanically deleting complexity. If a viewer or renderer is unavailable, deliver the source with that exact verification limitation and do not label it visually approved.

## Shared language profile

New outputs use `language_profile: diagram-en-prose-zh`, glyph/path `text_role`, view `title_text_role`/`scope_text_role`, and optional `surrounding_texts` entries. Read the sibling architecture package's `references/text-language.md`; do not duplicate its role rules here. The generator retains roles in SVG/draw.io and runs the shared checker when a profile is specified. Missing profiles preserve legacy rendering but language QA is explicitly not_run, not a compliance pass. Surrounding entries must be rendered by the caller and checked against the final artifact.
