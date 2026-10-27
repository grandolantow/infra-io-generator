#!/usr/bin/env python3
"""Check internal citations; optionally verify frozen corpus and asset hashes. Read only."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check_galleries(sources,roots):
    roots=[Path(x).resolve() for x in (roots if isinstance(roots,(list,tuple)) else [roots])]
    errors=[];warnings=[];verified=set();expected={s['source_id'] for s in sources if s.get('gallery_asset_path')}
    for root in roots:
        if not root.is_dir():errors.append(f'gallery root is not a directory: {root}')
    for source in sources:
        if not source.get('gallery_asset_path'):continue
        for root in roots:
            path=root/source['gallery_asset_path']
            if not path.is_file():continue
            if hashlib.sha256(path.read_bytes()).hexdigest()!=source['asset_sha256']:errors.append(f'gallery asset hash mismatch {source["source_id"]}')
            else:verified.add(source['source_id'])
    missing=expected-verified
    status='complete' if not missing else ('partial' if verified else 'none_found')
    if missing:warnings.append(f'Gallery coverage is {status}: verified {len(verified)}/{len(expected)} selected assets across {len(roots)} root(s); absent topic packs are not corruption and need not be merged.')
    return {'errors':errors,'warnings':warnings,'coverage':{'status':status,'provided_roots':len(roots),'selected_assets_verified':len(verified),'selected_assets_not_provided':len(missing),'selected_assets_expected':len(expected)}}
def check(corpus_root=None,gallery_root=None):
    errors=[];warnings=[]
    if corpus_root or gallery_root:
        return {'valid':False,'errors':['Archive/gallery checks unavailable in minimal public distribution; no private asset metadata is included.'],'warnings':[]}
    sources=json.loads((ROOT/'references/sources.json').read_text())['sources'];by={s['source_id']:s for s in sources}
    rules=json.loads((ROOT/'references/rules.json').read_text())['rules'];cases=json.loads((ROOT/'references/cases.json').read_text())['cases'];annotations={x['id'] for x in json.loads((ROOT/'references/user_annotations.json').read_text())['annotations']}
    if len(by)!=len(sources):errors.append('duplicate source IDs')
    if len({r['id'] for r in rules})!=len(rules):errors.append('duplicate rule IDs')
    taxonomy=json.loads((ROOT/'references/taxonomy.json').read_text());cited=set()
    for r in rules:
        for field in ('trigger','action','required_facts','alternatives','boundary','counterexample','checks','evidence'):
            if field not in r:errors.append(f'{r["id"]}: missing {field}')
        for ev in r['evidence']:
            sid=ev['source_id'];s=by.get(sid)
            if not s:errors.append(f'{r["id"]}: unknown source {sid}');continue
            cited.add(s['case_id'])
            if not s['qualified'] and ev['role']!='counterexample':errors.append(f'{r["id"]}: unqualified positive source {sid}')
        for aid in r.get('user_annotation_ids',[]):
            if aid not in annotations:errors.append(f'{r["id"]}: unknown annotation {aid}')
    for s in sources:
        classification=s.get('normalized_asset_classification',{})
        for code in classification.get('structure_codes',[]):
            if code not in taxonomy['structures']:errors.append(f'{s["source_id"]}: unknown structure code {code}')
        for code in classification.get('presentation_codes',[]):
            if code not in taxonomy['presentations']:errors.append(f'{s["source_id"]}: unknown presentation code {code}')
        if not s.get('url'):errors.append(f'{s["source_id"]}: missing original URL')
        for key in ('asset_path','manifest_path','gallery_asset_path'):
            if s.get(key) and (Path(s[key]).is_absolute() or '..' in Path(s[key]).parts):errors.append(f'{s["source_id"]}: nonportable path {key}')
    if corpus_root:
        root=Path(corpus_root).resolve()
        snap=json.loads((ROOT/'references/corpus_snapshot.json').read_text())
        for f in snap['manifests']:
            p=root/f['path']
            if not p.is_file():errors.append(f'missing frozen manifest {f["path"]}')
            elif hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:errors.append(f'frozen manifest mismatch {f["path"]}')
        for s in sources:
            if not s.get('asset_path'):continue
            p=root/s['asset_path']
            if not p.is_file():errors.append(f'missing asset {s["source_id"]}')
            elif hashlib.sha256(p.read_bytes()).hexdigest()!=s['asset_sha256']:errors.append(f'asset hash mismatch {s["source_id"]}')
    else:warnings.append('Public citation integrity only. Private archive metadata removed; raw assets, collector manifests and visual review are not checked.')
    gallery_coverage={'status':'not_requested'}
    if gallery_root:
        gallery=check_galleries(sources,gallery_root);errors.extend(gallery['errors']);warnings.extend(gallery['warnings']);gallery_coverage=gallery['coverage']
    uncited=sorted({c['case_id'] for c in cases}-cited)
    if uncited:warnings.append('Catalog cases not yet tied to rules: '+', '.join(uncited))
    return {'valid':not errors,'errors':errors,'warnings':warnings,'gallery_coverage':gallery_coverage,'counts':{'cases':len(cases),'sources':len(sources),'rules':len(rules),'cited_cases':len(cited),'classified_selected_assets':sum(bool(s.get('normalized_asset_classification')) for s in sources),'negative_assets':sum(s['source_kind']=='negative_asset' for s in sources)},'limits':'Reference integrity and checksums do not establish factual correctness, independent figure families, license rights or improved diagram quality.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--corpus-root',type=Path);p.add_argument('--gallery-root',type=Path,action='append',help='Repeat for separate topic-pack roots; checks their union without merging folders');a=p.parse_args();r=check(a.corpus_root,a.gallery_root);print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(0 if r['valid'] else 1)
if __name__=='__main__':main()
