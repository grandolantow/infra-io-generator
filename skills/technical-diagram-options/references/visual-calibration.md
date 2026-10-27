# Visual calibration from observed failures

## Optional flowchart treatment
For flowchart-like diagrams, one available treatment uses light round corners (roughly 8 px input/output, 12 px operation cards, 10 px grouping at a 1200 px canvas), pale fills, thin subdued borders and no shadow unless the task asks otherwise. Scale sensibly for final size. Matrix/tensor grids retain contiguous cells and meaningful boundaries; do not round every cell or turn all structures into cards. These values are a configurable example, not a universal design law.

## Repairs that change decisions
- **Spatial mechanisms must remain spatial.** If a claim is about tiling, paging or tree sharing, show the tiles, mapping or branches explicitly. A box labelled “tiled compute” does not explain tiling. State axes/dimensions or label a schematic so that block orientation cannot imply the wrong split.
- **Attach set-level operations to the set.** When the whole candidate set/tree is consumed or updated, connect to its boundary or an explicitly named aggregation object. Do not start a line beside an arbitrary leaf, or direct feedback to one arbitrary candidate. A clean-looking line can be a semantic error.
- **Reserve index and routing lanes.** Storage/table indices are data, not decoration. Keep incoming mapping arrows out of labels; move the indices to a dedicated rail rather than erase noncontiguous mappings. Preserve all relevant mapped addresses.
- **Align section labels with actual stage geometry.** A stage title above an unrelated tree leaf misleads the read order. Place the label adjacent to the corresponding region, even when the reading direction changes.
- **Recheck paint order after changing style.** Background containers can cover labels/arrows authored earlier. Inspect the rendered pixels, not just SVG coordinates or XML presence. Preserve the failed first render as evidence when evaluating iterations.
- **Final-size legibility beats decorative whitespace.** Use fewer headline words before reducing mechanism labels. If a mapped payload cannot fit at the intended scale, expand its region or use multiple lines, not tiny glyphs.

## Comparison and stability
Use explicit factual contracts separate from presentation goldens. Compare technical correctness, structural correspondence and legibility before three ordinal judgments: aesthetics, logical clarity and layout comfort. Aesthetic scores are reviewer judgments, not measurements of comprehension. Never compensate a false edge with a good visual score.

Freeze the tested skill and outputs before revealing held-out figure images. Once a test's feedback changes the skill, that test becomes development data. Exact rerenders do not show stability: independently regenerate with a different final-size, language or equivalent content constraint and inspect again. Report the per-case failures, tested set size and untested formats; obey any user-imposed round limit.

