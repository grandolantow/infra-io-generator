# Figure brief

## Purpose
Conceptual operator-generation workflow requested for wrapper validation, not an implementation trace or a measured performance claim.

## Components
Workload contract, mature Cube reuse, Vector generation, C+V composition, correctness/performance validation, delivery. Components are existing conceptual building blocks; no novelty claim.

## Main and secondary flow
Workload constraints feed two branches: reuse Cube for MatMul and generate Vector for epilogue. Both meet at C+V composition. Validation passes to delivery, or returns feedback to Vector/tiling. The return edge intentionally bypasses unrelated nodes.

## Assumptions
The example illustrates the user-described C+V approach, not a claim that every failure can be fixed solely in Vector. A real task may revise Cube choice or workload constraints. No fixed speedup or delivery time is promised.

## Caption
Mature Cube computation and generated Vector logic form one validated operator path; failed checks drive iteration.

## Revision
Clarify Vector generation is workload-driven. No other semantic changes.
