#!/usr/bin/env python3
"""Conservative routing aid, not a semantic classifier or diagram generator.

Use --intent after Agent semantic review; auto is a keyword suggestion only.
Existing resolve_palette auto defaults are intentionally unchanged.
"""
import argparse
import json
from pathlib import Path
import re
from resolve_palette import resolve, validate_tokens

MODEL = ('模型架构', '模型主干', '完整主干', '模型结构', '整体架构',
         '层结构', '模块组成', 'model architecture', 'model backbone',
         'block structure', 'layer structure', 'moe block', 'attention block')
REPORT = ('通信', '调度', '时间线', '时序', '内存', '映射', '量化', '吞吐', '延迟',
          '性能图', '计算机制', '数据流', '分片', 'communication', 'timeline',
          'scheduling', 'memory', 'mapping', 'quantization', 'throughput',
          'latency', 'all-to-all', 'dispatch', 'dataflow', 'softmax', 'kv cache')
NEGATION = re.compile(r'不要|不画|不需要|无需|仅引用|\b(?:not|without|ignore|rather than)\b', re.I)
DEFAULTS = {'model': {'paper': 'paper-clear', 'ppt': 'paper-clear'},
            'report': {'paper': 'paper-vivid', 'ppt': 'huawei-plain'}}


def route(request, intent='auto', target='paper', palette='auto', custom=None):
    if not isinstance(request, str) or not request.strip():
        raise ValueError('request must be nonempty')
    if intent not in ('auto', 'model', 'report', 'mixed'):
        raise ValueError('Unknown intent')
    if target not in ('paper', 'ppt'):
        raise ValueError('Unknown target')
    # Validate user options even when auto cannot identify a branch.
    resolve(target, 'auto' if palette == 'custom' else palette)
    if palette == 'custom' and custom is None:
        raise ValueError('palette=custom requires nonempty custom overrides')
    if custom is not None:
        validate_tokens(custom, partial=True)
    # Contrast is checked against each chosen branch, not the legacy palette.
    lowered = request.casefold()
    hits = {'model': [x for x in MODEL if x in lowered],
            'report': [x for x in REPORT if x in lowered]}
    needs_review = intent == 'auto' and bool(NEGATION.search(request))
    if intent != 'auto':
        selected = intent
    elif needs_review:
        selected = 'ambiguous'
    elif hits['model'] and hits['report']:
        selected = 'mixed'
    elif hits['model']:
        selected = 'model'
    elif hits['report']:
        selected = 'report'
    else:
        selected = 'ambiguous'
    branches = ('model', 'report') if selected == 'mixed' else (selected,)
    parts = []
    for branch in branches:
        if branch == 'ambiguous':
            continue
        base = DEFAULTS[branch][target] if palette in ('auto', 'custom') else palette
        parts.append({'intent': branch,
                      'guide': ('references/model-architecture.md' if branch == 'model' else '../technical-diagram-options/SKILL.md'),
                      'package': ('technical-architecture-diagrams' if branch == 'model' else 'technical-diagram-options'),
                      'overlay': None if branch == 'model' else 'references/technical-report.md',
                      'runtime': (None if branch == 'model' else {
                          'selector': '../technical-diagram-options/scripts/select_options.py',
                          'generator': '../technical-diagram-options/scripts/diagram_tool.py',
                          'task_schema': '../technical-diagram-options/schemas/task.schema.json',
                          'diagram_schema': '../technical-diagram-options/schemas/diagram.schema.json'}),
                      'palette': resolve(target, base, custom)})
    return {'schema_version': 1, 'intent': selected,
            'status': ('needs_semantic_review' if needs_review else
                       'needs_clarification' if selected == 'ambiguous' else
                       'suggested' if intent == 'auto' else 'explicit'),
            'decision_basis': 'keyword_hint_only' if intent == 'auto' else 'explicit_intent',
            'matched_hints': hits, 'target': target, 'parts': parts,
            'shared_fact_contract': 'references/spec-contract.md',
            'note': 'Review semantic goal before rendering; preserve shared facts when decomposing.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--request', required=True)
    ap.add_argument('--intent', choices=['auto', 'model', 'report', 'mixed'], default='auto')
    ap.add_argument('--target', choices=['ppt', 'paper'], default='paper')
    ap.add_argument('--palette', default='auto')
    ap.add_argument('--custom', type=Path)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    try:
        custom = json.loads(a.custom.read_text()) if a.custom else None
        result = route(a.request, a.intent, a.target, a.palette, custom)
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(content)
    else:
        print(content, end='')


if __name__ == '__main__':
    main()
