#!/usr/bin/env python3
"""Execute standards-derived semantic reference cases against the frozen package."""
import csv,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dist/limitaware-0.1.4/src'))
from limitaware import canonical,policies
rows=[]
for i,r in enumerate(csv.DictReader(open(ROOT/'evaluation/semantic/reference_cases.csv',newline='')),start=2):
    r['source_row']=i; rows.append(r)
recs,_=canonical.transform(rows,policies.validate(dict(policies.DEFAULT_POLICY)))
exp=json.loads((ROOT/'evaluation/semantic/expected.json').read_text())
out=[]; failures=[]
for r in recs:
    cid=r['_case_id'] if '_case_id' in r else rows[r['source_row']-2]['case_id']
    e=exp[cid]
    got={'case_id':cid,'status':r['status'],'eligible':r['analysis_eligible'],'censored':r['censored'],'observation':r['observation']}
    ok=(got['status']==e['status'] and got['eligible']==e['eligible'] and got['censored']==e['censored'])
    if 'observation' in e and got['observation'] is not None and e['observation'] is not None:
        ok=ok and abs(float(got['observation'])-float(e['observation']))<1e-12
    got['pass']=ok; out.append(got)
    if not ok: failures.append((cid,e,got))
summary={'cases':len(out),'passed':sum(1 for x in out if x['pass']),'failed':len(failures),'statuses':sorted(set(x['status'] for x in out))}
(ROOT/'evaluation/semantic/results.json').write_text(json.dumps({'summary':summary,'cases':out},indent=2))
print(json.dumps(summary,indent=2))
if failures:
    for f in failures: print('FAIL',f)
    raise SystemExit(1)
