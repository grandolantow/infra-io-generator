# Selection guide

The taxonomy describes relations, not compulsory looks. Use task evidence to choose features; never infer device topology from a paper title or an intended style.

| Mode | Central question | Distinguishing facts |
|---|---|---|
| S01 hierarchy/boundaries | What belongs where? | entities, containment |
| S02 dataflow/branch-merge | What transforms or combines? | operations, typed dependencies |
| S03 matrix/tensor/block | Which axes, shapes, partitions? | tensor axes and transforms |
| S04 logical/physical mapping | Where is the same object represented? | stable IDs, mapping cardinality |
| S05 timeline/pipeline | When, on which resource, with what wait? | actors, events, dependencies, time basis |
| S06 distribution/topology | Who owns/transfers which object? | devices, ownership, transfer direction |
| S07 recurrence/state | What persists or changes per step? | initial state, update rule, state identity |
| S08 tree/routing/filtering | Who branches, chooses, accepts or bypasses? | candidate ancestry, policy, outcomes |
| S09 controlled comparison | What is fixed and what changes? | invariants, variants, changed variables |
| S10 equations/worked example | How do symbols become operations? | equations, symbol mapping, valid example |
| S11 quantitative/distribution comparison | What measured/theoretical values or distributions differ? | metrics, axes, units, conditions and data provenance |

## Composition is not decorative complexity

- **C01 matrix + memory hierarchy:** connect a computation block with storage level and movement; FlashAttention is an observed example.
- **C02 topology/hierarchy + local focus:** keep ownership context while enlarging one mechanism; GShard, DistServe, Alpa.
- **C03 comparison + timeline:** identical requests/resources, contrasting schedules; GPipe, PipeDream, Sarathi-Serve.
- **C04 tree + mask:** common candidate indices connect ancestry to implementation; Medusa, SpecInfer.
- **C05 mapping + state snapshots:** distinguish layout changes from content changes; PagedAttention, streaming/eviction examples. A single static view may still be the best option.
- **C06 matrix + recurrence:** same mathematical terms in parallel and sequential forms; Mamba-2, RetNet. Preserve equivalence conditions.
- **C07 numeric example + branches:** precision/rank paths with a valid small example; QLoRA, LLM.int8, DoRA.
- **C08 stack + causal positions:** overview plus shifted/shared local path; DeepSeek-V3 MTP, EAGLE. Repeated modules are not necessarily independent.

Use the full card for required facts and any mandatory trigger features. C07 specifically requires the `worked_example` feature and a `numeric_example` fact containing concrete values and numerical conventions; symbolic shape/formula mapping is not a numerical example. If a composition's extra view is unsupported, offer it conditionally or use the supported simpler structure. If all options lack a necessary fact, ask about the fact rather than synthesizing a plausible diagram.

## Presentation and use case stay independent

The same mapping may be paper-compact, a teaching sequence, or a focused engineering slide. The same teaching presentation may use a tree, matrix, or timeline. Choose per task:

- Scope: full overview, progressive detail, local focus, adjacent snapshots.
- Encoding: labels/indices, color, texture, icons, shape, line style. Use redundant identity cues where colors alone are ambiguous.
- Density: only as much as the explanation and final-size legibility justify. Explicit indices or cross-links may be essential.
- Geometry: aligned, radial, nested, matrix, free-routing, small multiples; follow the relation, not an all-purpose flowchart.
- Tone: source-faithful technical, restrained presentation, hand-drawn intuition, or a user's existing design language. None is a default promise of quality.

Use cases such as technical reading, implementation/debugging, architecture overview, optimization comparison, beginner teaching, and cross-team review set priorities. They do not fix palettes, fonts, node counts or layout.

## Option card contract

Each proposed option should include:

1. Structural mode/composition and question answered.
2. What is included, omitted, and preserved from the same fact set.
3. Presentation treatment chosen separately; editable output format.
4. Why it fits this audience and display size; trade-off against alternatives.
5. Missing facts/assumptions and the exact evidence references used for design inspiration.

A recommendation is a reasoned choice, not a measured ranking. If the user has chosen a structure, give treatment alternatives only if useful and label them honestly as treatments. Two differently colored copies of the same geometry do not fulfill a request for different structural options.
