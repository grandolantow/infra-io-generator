# Third-party materials

## draw.io Graph runtime

`third_party/drawio/app.min.js` is the official draw.io Graph runtime bundle used for native import/render/export. Version, recorded source URL, Git blob identity and SHA256 are retained in `third_party/drawio/graph-runtime.json`.

Upstream: https://github.com/jgraph/drawio

The bundled upstream Apache-2.0 license is in `third_party/drawio/LICENSE.drawio`; the same license accompanies the Skill runtime helpers. Retain upstream headers and license on redistribution. No rights to upstream trademarks are granted by this repository.

## Research references

Paper and blog links in reference indexes are citations. Paper original figure rasters and PDFs are not redistributed here. The diagrams in examples and golden assets are separately authored redraws; their source papers are attributed in fact records. Reference-inspired geometry is described as such and is not represented as blind evaluation.

## Other dependencies

Playwright, Chromium, Inkscape, Python packages, TeX and fonts are separately installed dependencies governed by their upstream licenses. This tree does not include browser binaries or their dependency trees.

## Project license

No project-wide open-source license has yet been selected by the repository owner. Third-party licenses remain in effect for the identified materials.

## Independent reproduction source snapshots

`examples/independent-minimax/source-input/sources/` retains the supplied pinned MiniMax config/model card and content-hashed SGLang model-code snapshot for fact checks. MiniMax's supplied community license is preserved as `LICENSE`; it is not replaced by this project's license. The SGLang file retains its original copyright and Apache-2.0 header, with the Apache license as `LICENSE.sglang`. The snapshot SHA256 and original URLs are in `provenance.json`. No model weights are included.
