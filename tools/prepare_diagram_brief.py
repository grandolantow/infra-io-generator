#!/usr/bin/env python3
"""Validate a content brief and prepare an independent drawing-agent handoff.

This does not spawn an agent, design geometry, render, or certify a diagram.
"""
import argparse
import hashlib
import json
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[1]

def prepare(input_path, out_dir):
    brief = json.loads(input_path.read_text(encoding='utf-8'))
    schema = json.loads((ROOT / 'contracts/diagram-brief.schema.json').read_text())
    jsonschema.Draft202012Validator(schema).validate(brief)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError('output directory must be empty')
    out_dir.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(brief, ensure_ascii=False, indent=2) + '\n').encode()
    (out_dir / 'brief.json').write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    prompt = f'''# Independent drawing-agent task

Read brief.json (SHA256 `{digest}`) and use the repository Skill entry
`skills/technical-architecture-diagrams/SKILL.md`, then its
`references/independent-workflow.md` and the selected branch's rules.
The brief supplies content and display constraints, not a predesigned scene.

Own the complete drawing workflow: inspect applicable references/goldens,
verify facts and visible semantics, select structure, design components,
proportions, typography and connections, render with a real backend, inspect
actual pixels against applicable references, revise observed failures, and
return editable sources, rendered figures and QA. Normally design 3–4 numbered
alternatives (brief variant_count defaults to 3), archive all in one numbered PDF,
and let the caller select one for HTML. Honor display space without treating it as
locked geometry; coordinate the theme broadly with restrained functional colors.
The caller decides independent explanation content and amount after the figure.
For report/mixed tasks run the original selector before design and bind its
selected options to actual drawing objects and decisions.

Deliver diagram-delivery.json using contracts/diagram-delivery.schema.json.
Bind this exact brief digest, preserve artifact hashes and document limitations.
Run tools/check_diagram_delivery.py against the delivered artifact directory.
Contract validation does not prove visual or technical correctness.

The orchestrating host must actually delegate this task to an independent
agent. This preparation script does not perform delegation. If no such
capability is available, report blocked; do not substitute a pre-authored
scene followed by a renderer call and claim independent generation.
'''
    (out_dir / 'agent-task.md').write_text(prompt, encoding='utf-8')
    return {'status': 'prepared_not_executed', 'brief_sha256': digest,
            'brief': 'brief.json', 'agent_task': 'agent-task.md'}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    a = ap.parse_args()
    try:
        print(json.dumps(prepare(a.input, a.out_dir)))
    except (ValueError, OSError, jsonschema.ValidationError) as exc:
        ap.exit(2, f'brief preparation failed: {exc}\n')

if __name__ == '__main__':
    main()
