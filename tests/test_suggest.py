import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import suggest as s


class FakeClient:
    def __init__(self, none=False, fit=0.99, confidence=0.99, fail_after=None, callback=None):
        self.model=s.MODEL
        self.none, self.fit, self.confidence = none, fit, confidence
        self.fail_after, self.callback = fail_after, callback
        self.attempts=0
        self.usage={"input_tokens":0,"output_tokens":0}
    def ask(self, state, questions):
        self.attempts+=1
        if self.fail_after is not None and self.attempts>self.fail_after:
            raise s.ScanError("test failure")
        if self.callback: self.callback()
        answers={}
        for k,q in questions.items():
            if q['type']=='choice':
                pick='none' if self.none else next(x for x in q['criteria'] if x!='none')
                probs={x:float(x==pick) for x in q['criteria']}
                answers[k]={"type":"choice","choice":pick,"confidence":self.confidence,"probabilities":probs}
            else:
                answers[k]={"type":"noul","noul":0.01 if self.none else self.fit}
        self.usage['input_tokens']+=10
        self.usage['output_tokens']+=5
        return {"model":self.model,"answers":answers,"usage":{"input_tokens":10,"output_tokens":5}}


class SuggesterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def skill(self, folder='writer', name='writer', description='Edit provided prose.', body='# Writer\nEdit prose faithfully.', explicit=False):
        d=self.root/folder;d.mkdir(parents=True,exist_ok=True)
        p=d/'SKILL.md';p.write_text(f'---\nname: {name}\ndescription: {description}\n---\n{body}\n')
        if explicit:
            (d/'agents').mkdir(exist_ok=True)
            (d/'agents/openai.yaml').write_text('policy:\n  allow_implicit_invocation: false\n')
        return p
    def args(self,*extra):
        return s.parser().parse_args(['suggest','--root',str(self.root),'--task','Edit this text','--mode','jev',*extra])
    def test_folded_and_quoted_metadata(self):
        m,b=s.metadata('---\nname: "writer"\ndescription: >-\n  Edit prose\n  without new facts.\n---\nBody')
        self.assertEqual(m['description'],'Edit prose without new facts.')
        self.assertEqual(b,'Body')
    def test_duplicate_metadata_rejected(self):
        with self.assertRaises(ValueError):s.metadata('---\nname: a\nname: b\ndescription: okay\n---')
    def test_duplicate_names_keep_distinct_ids(self):
        self.skill('a');self.skill('b')
        entries,_=s.discover([self.root])
        self.assertEqual(len({e['id'] for e in entries}),2)
        r,_=s.run(self.args('--require','writer'),FakeClient())
        self.assertEqual(r['status'],'ambiguous');self.assertIsNone(r['suggestion'])
    def test_symlinks_and_fifo_not_read(self):
        p=self.skill('real')
        (self.root/'link').symlink_to(p.parent,target_is_directory=True)
        q=self.root/'fake';q.mkdir();(q/'SKILL.md').symlink_to(p)
        import os
        f=self.root/'fifo';f.mkdir();os.mkfifo(f/'SKILL.md')
        entries,w=s.discover([self.root])
        self.assertEqual(len(entries),1);self.assertGreaterEqual(len(w),3)
    def test_explicit_linked_directory_is_supported(self):
        p=self.skill('real');(self.root/'link').symlink_to(p.parent,target_is_directory=True)
        entries,w=s.discover([], [self.root/'link/SKILL.md'])
        self.assertEqual(len(entries),1);self.assertEqual(w,[])
    def test_suspected_key_entry_excluded(self):
        self.skill(body='apikey_'+'a'*24+'_'+'b'*40)
        entries,w=s.discover([self.root])
        self.assertEqual(entries,[]);self.assertEqual(w[0]['reason'],'suspected_credential')
    def test_explicit_selection_no_api_and_policy_honored(self):
        self.skill(explicit=True);client=FakeClient()
        entries,_=s.discover([self.root]);self.assertEqual(s.filter_entries(entries),[])
        r,_=s.run(self.args('--require','writer'),client)
        self.assertEqual(r['status'],'explicit_selection');self.assertEqual(client.attempts,0)
    def test_require_cannot_bypass_exclude(self):
        self.skill();client=FakeClient()
        r,_=s.run(self.args('--require','writer','--exclude','writer'),client)
        self.assertEqual(r['status'],'unavailable');self.assertEqual(client.attempts,0)
    def test_self_excluded(self):
        self.skill(name=s.SELF);entries,_=s.discover([self.root])
        self.assertEqual(s.filter_entries(entries),[])
    def test_local_does_not_call_model(self):
        self.skill();client=FakeClient();a=self.args();a.mode='local'
        r,_=s.run(a,client);self.assertEqual(r['status'],'local_only');self.assertEqual(client.attempts,0)
    def test_two_stage_positive(self):
        self.skill();client=FakeClient()
        r,code=s.run(self.args(),client)
        self.assertEqual(r['status'],'suggested');self.assertEqual(client.attempts,2);self.assertEqual(code,0)
        self.assertTrue(r['host_review_required']);self.assertFalse(r['executes_skills'])
    def test_none_short_circuits_second_stage(self):
        self.skill();client=FakeClient(none=True)
        r,_=s.run(self.args(),client)
        self.assertEqual(r['status'],'none');self.assertEqual(client.attempts,1)
    def test_low_absolute_fit_blocks_choice(self):
        self.skill();r,_=s.run(self.args(),FakeClient(fit=0.4))
        self.assertEqual(r['status'],'uncertain');self.assertIsNone(r['suggestion'])
    def test_low_choice_confidence_blocks_selection(self):
        self.skill();r,_=s.run(self.args(),FakeClient(confidence=0.3))
        self.assertEqual(r['status'],'uncertain')
    def test_second_call_failure_removes_recommendation(self):
        self.skill();r,code=s.run(self.args(),FakeClient(fail_after=1))
        self.assertEqual(r['status'],'incomplete');self.assertIsNone(r['suggestion']);self.assertEqual(code,3)
    def test_changed_content_blocks_result(self):
        p=self.skill()
        def change():p.write_text(p.read_text()+'changed\n')
        r,_=s.run(self.args(),FakeClient(callback=change))
        self.assertEqual(r['status'],'incomplete')
    def test_changed_invocation_policy_blocks_result(self):
        p=self.skill()
        def change():
            (p.parent/'agents').mkdir(exist_ok=True)
            (p.parent/'agents/openai.yaml').write_text('policy:\n  allow_implicit_invocation: false\n')
        r,_=s.run(self.args(),FakeClient(callback=change))
        self.assertEqual(r['status'],'incomplete')
    def test_cache_replay_is_zero_calls(self):
        self.skill();a=self.args('--cache-dir',str(self.root/'cache'))
        r,_=s.run(a,FakeClient());client=FakeClient(fail_after=0)
        replay,_=s.run(a,client)
        self.assertEqual(replay['status'],'suggested');self.assertEqual(client.attempts,0)
        self.assertEqual(replay['usage']['input_tokens'],0);self.assertEqual(replay['cache_hits'],2)
    def test_content_change_beyond_excerpt_invalidates_cache(self):
        p=self.skill(body='a'*12000);a=self.args('--cache-dir',str(self.root/'cache'))
        s.run(a,FakeClient());p.write_text(p.read_text()+'new constraint')
        client=FakeClient();s.run(a,client);self.assertEqual(client.attempts,2)
    def test_task_change_invalidates_cache(self):
        self.skill();a=self.args('--cache-dir',str(self.root/'cache'))
        s.run(a,FakeClient());a.task='Different task';client=FakeClient()
        s.run(a,client);self.assertEqual(client.attempts,2)
    def test_invalid_cache_response_not_reused(self):
        self.skill();a=self.args('--cache-dir',str(self.root/'cache'));s.run(a,FakeClient())
        for p in Path(a.cache_dir).glob('*.json'):
            d=json.loads(p.read_text());d['response']['answers']={};p.write_text(json.dumps(d))
        client=FakeClient();s.run(a,client);self.assertEqual(client.attempts,2)
    def test_report_and_cache_are_new_private_files(self):
        import stat
        p=self.root/'r.json';s.write_new(p,{'okay':True})
        self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
        with self.assertRaises(FileExistsError):s.write_new(p,{})
    def test_unknown_allow_selector_fails_closed(self):
        self.skill();entries,_=s.discover([self.root])
        with self.assertRaises(ValueError):s.filter_entries(entries,['typo'])
    def test_paths_absent_from_model_payload(self):
        self.skill();entries,_=s.discover([self.root])
        for state,qs in [s.wide_request('Edit',entries),s.detail_request('Edit',entries)]:
            self.assertNotIn(str(self.root),json.dumps([state,qs]))
    def test_batches_include_every_skill(self):
        entries=[]
        for i in range(25):
            entries.append({'id':f's_{i}','name':f'skill-{i}','description':'x'*2000,'sha256':str(i)})
        groups=s.batches('Task',entries)
        self.assertGreater(len(groups),1)
        self.assertEqual([e['id'] for g in groups for e in g],[e['id'] for e in entries])
        for g in groups:self.assertTrue(s.fits_budget(*s.wide_request('Task',g)))


if __name__=='__main__':unittest.main()
