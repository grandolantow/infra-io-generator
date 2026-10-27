# Native draw.io runtime

The primary renderer loads the **official draw.io Graph class** from the pinned `app.min.js` bundle (version 32.6.1). `mxCodec` imports the native XML, the actual graph builds shape and connector states, and `mxImageExport`/`mxSvgCanvas2D` exports SVG. No SVG path is manually substituted for the graph engine.

```sh
python scripts/drawio_runtime/fetch_runtime.py --out .cache/drawio/app.min.js

CHROME_BINARY=/path/to/chrome \
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
node scripts/drawio_runtime/export.mjs --input attention_residuals.drawio \
  --out attention_residuals --graph-js .cache/drawio/app.min.js --backend drawio --label-mode plain --move f_layer3
```

Optional arguments: `--chrome PATH`, `--graph-js PATH`, `--page 0`, `--label-mode html`. Supply Chrome explicitly. Playwright may be resolved from PLAYWRIGHT_MODULE, CODEX_PRIMARY_RUNTIME_NODE_MODULES, or the Node module search path. Run from the drawio folder or use absolute paths.

The source bundle hash is checked against `graph-runtime.json` before executing it. `fetch_runtime.py --out /project/.cache/drawio/app.min.js` retrieves the immutable Git blob URL and rejects any bytes that do not match the recorded SHA256. The original rolling dev URL remains in the pin as provenance, not the default download target. For faithful reproduction, retain the exact recorded bundle or provide the exact source bytes by the recorded hash.

`plain` mode explicitly disables HTML labels in the Graph instance, so exported SVG uses native `<text>` instead of `<foreignObject>`. The source labels in this task are plain Unicode and mathematical symbols. This preserves compatibility with Inkscape and typical SVG consumers; it is not an HTML-rich-text renderer. Folding controls are disabled for clean diagram export.

The edit probe selects one child cell using the native selection API, then performs an **actual Playwright mouse drag**. It records geometry changes, attached-edge point changes, unrelated node positions, and reserializes the edited model to `.edited.drawio`. The formal `.drawio` is not overwritten by the edit probe.

Scope: this verifies official draw.io Graph import/render/export/edit operations in a local browser. It does **not** claim full EditorUi, cloud-drive integration, or draw.io Desktop testing. Online app URLs returned 403, so the official GitHub-hosted source bundle was used locally. The legacy mxGraph fallback is not distributed with the Skill.

The principal coordinates, layer-row alignment and routing-corridor waypoints are supplied by the authoring template. This trial cannot attribute those layout decisions to an automatic engine. The engine verifies native shapes, endpoints, live geometry, rendering and serialization.

Distribution: include the runtime JS source with its upstream license, or supply its hash and retrieval script. Exclude browser binaries, test files, temporary native-app probes and the legacy npm source tree from the user deliverable unless explicitly needed.

Canvas: the selected uncompressed mxGraphModel must declare positive integer pageWidth/pageHeight. SVG and PNG follow that page, including portrait and multi-page documents. The runtime no longer assumes 16:9.
