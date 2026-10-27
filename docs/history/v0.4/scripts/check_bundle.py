#!/usr/bin/env python3
"""Validate this specification bundle only; not image or semantic correctness."""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    required = [
        'SKILL.md','README.md','SUMMARY_CN.md','HANDOFF-CODEX.md',
        'references/rules-v0.4.md','references/layout-recipes.md',
        'references/evidence-and-limits.md','references/iteration-plan.md',
        'data/ratings-40.json','data/rules-v0.4.json',
        'templates/diagram-spec.json','templates/case-card.json',
        'templates/review-record.json','eval/tasks-template.json',
    ]
    errors = [f'Missing file: {f}' for f in required if not (ROOT/f).is_file()]
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    try:
        json_files = list(ROOT.rglob('*.json'))
        parsed = {str(p.relative_to(ROOT)):json.loads(p.read_text(encoding='utf-8')) for p in json_files}
        data = parsed['data/ratings-40.json']
        records = data['records']
        ids = [r['sample_id'] for r in records]
        if ids != [f'{i:02d}' for i in range(1,41)]:
            errors.append('Feedback IDs are not exactly 01..40.')
        totals = dict(Counter(r['rating_normalized'] for r in records))
        expected={'good':24,'neutral':10,'bad':6}
        if totals != expected or data['counts'] != expected:
            errors.append(f'Wrong totals: {totals}')
        expected_batch = [(8,1,1),(4,5,1),(6,2,2),(6,2,2)]
        for batch,(good,neutral,bad) in enumerate(expected_batch,1):
            c=Counter(r['rating_normalized'] for r in records if r['batch']==batch)
            if (c['good'],c['neutral'],c['bad'])!=(good,neutral,bad):
                errors.append(f'Wrong batch {batch}: {dict(c)}')
        rules = parsed['data/rules-v0.4.json']['rules']
        if [r['id'] for r in rules] != [f'R{i:02d}' for i in range(1,15)]:
            errors.append('Expected R01..R14.')
        valid_ids=set(ids)
        for rule in rules:
            if not set(rule['feedback_sample_ids']).issubset(valid_ids):
                errors.append(f'Unknown sample in {rule["id"]}')
        for r in records:
            for d in r['possible_same_figure_as']:
                if d not in valid_ids:
                    errors.append(f'Unknown duplicate candidate: {d}')
                elif r['sample_id'] not in records[int(d)-1]['possible_same_figure_as']:
                    errors.append(f'Asymmetric duplicate candidate: {r["sample_id"]}/{d}')
            if r['external_source_verified_this_run'] or r['original_asset_path'] is not None:
                errors.append('This bundle must not claim unavailable original assets.')
        plan=parsed['eval/tasks-template.json']
        planned=(plan['development_papers']+plan['holdout_papers'])*plan['tasks_per_paper']
        if planned!=plan['total_tasks_planned'] or planned!=10:
            errors.append('Planned task count mismatch.')
        spec=parsed['templates/diagram-spec.json']
        if spec['qa']['status']!='not_run' or spec['qa']['rendered']:
            errors.append('Template falsely claims a completed rendering check.')
        skill=(ROOT/'SKILL.md').read_text(encoding='utf-8')
        if not skill.startswith('---\nname: technical-architecture-diagrams\n'):
            errors.append('Missing expected Skill frontmatter.')
        if errors:
            print('\n'.join(errors),file=sys.stderr)
            return 1
        print('PASS: 40 feedback records; totals 24/10/6; four batch counts; 14 rule IDs and references;')
        print('duplicate candidate symmetry; source status; 10 planned tasks; unrun template state; Skill frontmatter.')
        print('Scope: specification/data consistency ONLY. No diagram generation, source-image or quality validation.')
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'Validation error: {exc}',file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
