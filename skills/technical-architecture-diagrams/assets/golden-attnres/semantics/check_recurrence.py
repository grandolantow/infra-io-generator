"""Small deterministic semantic oracle, not a diagram-quality or model benchmark.

Check the source-defined candidate membership and raw-output block accumulation.
No ML library or model weights are used. The arbitrary f_l/w_l are test fixtures.
"""
import json, math
from pathlib import Path

ROOT=Path(__file__).parent
EMBED=[0.7,-0.4]
QUERIES=[[0.6,-0.2],[-0.3,0.8],[0.4,0.1],[0.2,-0.6],[0.9,0.3]]
def plus(a,b):return [x+y for x,y in zip(a,b)]
def layer(l,h):return [math.tanh(h[0]+0.13*l),math.tanh(0.5*h[1]-0.07*l)]
def attn(values,w):
    keys=[[x/math.sqrt(sum(v*v for v in a)/len(a)+1e-6) for x in a] for a in values]
    scores=[sum(x*y for x,y in zip(w,k)) for k in keys]
    p=[math.exp(s-max(scores)) for s in scores];p=[x/sum(p) for x in p]
    return [sum(q*a[j] for q,a in zip(p,values)) for j in range(len(w))]
def full():
    values=[EMBED[:]];counts=[]
    for l in range(1,5):
        counts.append(len(values));h=attn(values,QUERIES[l-1]);values.append(layer(l,h))
    counts.append(len(values));return attn(values,QUERIES[4]),counts
def block(size):
    completed=[EMBED[:]];partial=None;counts=[];raw=[];completed_raw=[]
    for l in range(1,5):
        values=completed+([partial] if partial is not None else [])
        counts.append(len(values));h=attn(values,QUERIES[l-1]);v=layer(l,h);raw.append(v)
        partial=v if partial is None else plus(partial,v)
        if l%size==0:
            completed.append(partial);completed_raw.append(partial);partial=None
    if partial is not None:completed.append(partial);completed_raw.append(partial)
    counts.append(len(completed));return attn(completed,QUERIES[4]),counts,raw,completed_raw
def close(a,b):return all(abs(x-y)<1e-12 for x,y in zip(a,b))

if __name__=='__main__':
    f,fc=full();b,bc,raw,summaries=block(2);s1,c1,_,_=block(1)
    checks={
      'full_candidate_counts':fc==[1,2,3,4,5],
      'block_S2_candidate_counts':bc==[1,2,2,3,3],
      'block_S1_recovers_full':close(f,s1),
      'b1_is_raw_v1_plus_v2':close(summaries[0],plus(raw[0],raw[1])),
      'b2_is_raw_v3_plus_v4':close(summaries[1],plus(raw[2],raw[3])),
      'embedding_not_duplicated_into_b1':not close(summaries[0],plus(EMBED,plus(raw[0],raw[1]))),
      'adding_fake_zero_candidate_changes_softmax':not close(attn([EMBED,summaries[0]],QUERIES[2]),attn([EMBED,summaries[0],[0.,0.]],QUERIES[2])),
    }
    result={'scope':'Synthetic recurrence fixture only; validates interpretation of source formulas, not diagram semantics or real-model numerics.','checks':checks,'passed':all(checks.values()),'full_counts':fc,'block_counts':bc}
    (ROOT/'recurrence-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));assert result['passed']
