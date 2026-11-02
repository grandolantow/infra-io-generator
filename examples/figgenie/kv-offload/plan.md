# Drawing plan

One SVG geometry source. Presentation intent, 600 × 330 pt with 11 pt labels. Compact vertical main path on the left; a right-hand inset expands Resolve KV. Main-path and inset arrows are explicit rather than decorative zoom leaders. All solid arrows are data/control dependencies, labels distinguish Hit, Miss, Onload and return data.

Reference: inspected upstream asplos25-101_fig1 panel (a), borrowing the main-stack plus local-expansion device, not source artwork. Blue-gray framing, soft green highlights the expanded node.

Checks: branch conditions visible; resident path joins readiness; miss copy precedes readiness; selected KV returns to attention; no dependency on sampling. The frame is a true SVG group semantic container and every node/edge has a stable ID.
