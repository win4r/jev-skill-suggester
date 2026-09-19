"""Evaluate the suggester on a declared local roster; no recommended action is executed."""
import argparse
import getpass
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import suggest as s


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',action='append',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():p.error('new output directory required')
    entries,warnings=s.discover(a.root)
    if warnings:p.error('catalog warnings; inspect and choose roots explicitly')
    key=getpass.getpass('TypeSafe API key (hidden): ')
    if not key:p.error('key required')
    client=s.JevClient(key,model=s.MODEL,max_calls=96)
    a.out.mkdir(parents=True,exist_ok=False)
    cases=json.loads((ROOT/'examples/evaluation-cases.json').read_text())['cases']
    files=[ROOT/'scripts/suggest.py',ROOT/'scripts/jev_client.py',ROOT/'examples/evaluation-cases.json']
    s.write_new(a.out/'manifest.before.json',{'version':s.VERSION,'model':s.MODEL,'thresholds':{'fit':0.8,'confidence':0.65},'case_count':len(cases),'independent_labels':False,'hashes':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'catalog':[s.public_entry(e) for e in entries]})
    rows=[]
    for c in cases:
        argv=['suggest','--task',c['task'],'--mode','jev','--trace','--cache-dir',str(a.out/'cache')]
        for r in a.root:argv+=['--root',r]
        args=s.parser().parse_args(argv)
        start=time.monotonic()
        report,exit_code=s.run(args,client)
        elapsed=round((time.monotonic()-start)*1000,2)
        picked=report.get('suggestion',{}).get('name') if report.get('suggestion') else None
        exact=(report['status']=='suggested' and picked==c['expected']) if c['expected'] else report['status']=='none'
        wrong=report['status']=='suggested' and picked!=c['expected']
        result={'case':c,'report':report,'elapsed_ms':elapsed,'exit_code':exit_code,'evaluation':{'expected_outcome':exact,'wrong_suggestion':wrong}}
        s.write_new(a.out/(c['id']+'.json'),result)
        rows.append(result)
        print(json.dumps({'id':c['id'],'status':report['status'],'pick':picked,'expected':c['expected'],'exact':exact,'calls':report.get('http_attempts'),'ms':elapsed},ensure_ascii=False),flush=True)
    # One actual replay demonstrates cache accounting with zero network calls.
    replay_case=cases[0]
    argv=['suggest','--task',replay_case['task'],'--mode','jev','--trace','--cache-dir',str(a.out/'cache')]
    for r in a.root:argv+=['--root',r]
    replay,_=s.run(s.parser().parse_args(argv),client)
    s.write_new(a.out/'cache-replay.json',replay)
    summary={'cases':len(rows),'positive_cases':sum(c['expected'] is not None for c in cases),
             'expected_outcomes':sum(r['evaluation']['expected_outcome'] for r in rows),
             'wrong_suggestions':sum(r['evaluation']['wrong_suggestion'] for r in rows),
             'abstentions_on_positive':sum(r['case']['expected'] is not None and r['report']['status']!='suggested' for r in rows),
             'none_on_negative':sum(r['case']['expected'] is None and r['report']['status']=='none' for r in rows),
             'failed':[r['case']['id'] for r in rows if r['report']['status']=='incomplete'],
             'http_attempts':client.attempts,'usage':client.usage,
             'elapsed_ms_median':statistics.median(r['elapsed_ms'] for r in rows),
             'cache_replay_http_attempts':replay['http_attempts'],'cache_replay_hits':replay['cache_hits'],
             'estimated_input_cost_usd':client.usage['input_tokens']*0.042/1_000_000,
             'limits':'Same-host synthetic requests on real catalog; no baseline agent task-success comparison, thresholds not calibrated.'}
    s.write_new(a.out/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return 3 if summary['failed'] else 0


if __name__=='__main__':raise SystemExit(main())
