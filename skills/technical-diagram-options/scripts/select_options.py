#!/usr/bin/env python3
"""Rank explicit relational features, not topic keywords or visual styles. No network."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def select(task,limit=3):
    features=set(task.get('features',[])); facts=task.get('known_facts',{})
    known={k for k,v in facts.items() if isinstance(v,dict) and v.get('value') is not None and v.get('status','known')=='known' and v.get('provenance')}
    assumed={k for k,v in facts.items() if isinstance(v,dict) and v.get('status')=='assumed'}
    constraints=task.get('constraints',{});allowed=set(constraints.get('allowed_structures',[]));forbidden=set(constraints.get('forbidden_structures',[]))
    rules=json.loads((ROOT/'references/rules.json').read_text())['rules'];pool=[]
    for r in rules:
        if r['kind'] not in ('structure','composition'):continue
        modes=set(r['structure_modes'])
        if not set(r.get('required_features',[]))<=features:continue
        if modes & forbidden or (allowed and not modes<=allowed):continue
        matched=features & set(r['trigger_features'])
        if not matched:continue
        missing=[x for x in r['required_facts'] if x not in known]
        score=len(matched)/len(r['trigger_features']) + .2*len(matched) - .08*len(missing)
        if r['kind']=='composition' and len(matched)<2:continue
        pool.append({'rule_id':r['id'],'name':r['name'],'structure_modes':r['structure_modes'],'matched_features':sorted(matched),'missing_facts':missing,'assumed_facts_needing_confirmation':sorted(assumed & set(r['required_facts'])),'status':'conditional' if missing else 'facts_available','heuristic_relevance':round(score,4),'question_fit':r['trigger'],'proposed_action':r['action'],'tradeoff':r['boundary'],'alternatives':r['alternatives'],'checks':r['checks'],'evidence_source_ids':[e['source_id'] for e in r['evidence']],'presentation':task.get('presentation',{'selection':'Choose separately for audience and display size; no fixed preset.'})})
    selected=[]
    while pool and len(selected)<limit:
        def priority(c):
            cm=set(c['structure_modes']);overlap=max((len(cm&set(x['structure_modes']))/len(cm|set(x['structure_modes'])) for x in selected),default=0)
            return (c['heuristic_relevance']-.55*overlap,-len(c['missing_facts']),c['rule_id'])
        best=max(pool,key=priority);selected.append(best);pool.remove(best)
    return {'task_id':task.get('task_id'),'status':'options' if selected else 'needs_relational_features_or_relaxed_constraints','options':selected,'notes':['Heuristic shortlist, not an efficacy ranking or automatic factual validation.','Facts marked available still require agent/source review. Missing facts are not guessed.','Different structure modes are proposed; the agent must articulate each reveal/omit trade-off and select geometry.','Source examples support a design hypothesis, not facts about this new mechanism.'],'preserve_constraints':constraints}
def main():
    p=argparse.ArgumentParser();p.add_argument('task',type=Path);p.add_argument('--limit',type=int,default=3);p.add_argument('--out',type=Path);a=p.parse_args()
    if a.limit<1:p.error('--limit must be positive')
    result=select(json.loads(a.task.read_text()),a.limit);s=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.out:a.out.write_text(s)
    else:print(s,end='')
if __name__=='__main__':main()
