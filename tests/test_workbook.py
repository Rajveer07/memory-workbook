import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from app import ROOT, create_app
from app.content import load_content
from app.progress import connect, get_states, update


class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=str(Path(self.tmp.name)/'progress.sqlite3')
        self.app=create_app({'TESTING':True,'SECRET_KEY':'test-only','DATABASE':self.db})
        self.client=self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as session:self.csrf=session['csrf']
        self.headers={'X-CSRF-Token':self.csrf}
        self.questions=self.app.extensions['workbook']['questions']
        self.q=self.questions[0]

    def tearDown(self):self.tmp.cleanup()

    def post(self,qid,payload):return self.client.post('/api/progress/'+qid,json=payload,headers=self.headers)

    def test_full_bank_and_page_audit(self):
        catalog,questions,units=load_content(ROOT/'questions')
        self.assertEqual(len(questions),333)
        self.assertEqual([(c['page_start'],c['page_end']) for c in catalog['chapters']],[(1,39),(40,72)])
        audit=json.loads((ROOT/'questions/page-audit.json').read_text())
        self.assertEqual([x['page'] for x in audit],list(range(1,73)))
        for row in audit:
            self.assertTrue(row['visual_reviewed'] and row['text_reviewed'])
            self.assertTrue(row['unit_ids'] and row['question_ids'])
            self.assertTrue(set(row['unit_ids'])<=set(units))
        for chapter in ['women','population']:
            qs=[q for q in questions if q['chapter_id']==chapter]
            first_chapter=next(i for i,q in enumerate(qs) if q['scope']=='chapter')
            self.assertTrue(all(q['scope']=='chapter' for q in qs[first_chapter:]))
            self.assertGreater(sum(q['category'] in ('reasoning','relationship') for q in qs),15)

    def test_image_only_material_present(self):
        result=self.client.get('/api/workbook?chapter=population&page=44').json
        self.assertTrue(any('wasting' in q['prompt'].lower() for q in result['questions']))
        result=self.client.get('/api/workbook?chapter=population&page=46').json
        self.assertTrue(any('five stages' in q['prompt'] for q in result['questions']))
        chart=[q for q in self.questions if 'page-51 Lancet' in q['prompt']]
        self.assertEqual([q['blanks'][0]['answer'] for q in chart],['6.18','4.60','1.91','1.29','1.04'])

    def test_reveal_does_not_create_mastery(self):
        self.client.get('/api/workbook')
        self.post(self.q['id'],{'draft':'My recalled keywords'})
        state=self.client.get('/api/workbook').json['states'][self.q['id']]
        self.assertIsNone(state['rating'])
        self.assertEqual(state['draft'],'My recalled keywords')
        self.assertEqual(self.client.get('/api/history/'+self.q['id']).json['attempts'],[])

    def test_rating_history_persistence_and_mastery(self):
        qid=self.q['id']
        for rating in ['again','hard','good']:
            result=self.post(qid,{'rating':rating,'draft':'recall '+rating})
            self.assertEqual(result.status_code,200)
        app2=create_app({'TESTING':True,'SECRET_KEY':'test-only','DATABASE':self.db})
        result=app2.test_client().get('/api/workbook').json
        self.assertEqual(result['states'][qid]['rating'],'good')
        self.assertEqual(result['mastery']['women']['strong'],1)
        self.assertEqual(result['mastery']['women']['unseen'],171)
        history=self.client.get('/api/history/'+qid).json['attempts']
        self.assertEqual([h['rating'] for h in history],['good','hard','again'])
        self.assertEqual(history[0]['response'],'recall good')

    def test_schedule_intervals_and_reset(self):
        fixed=datetime(2026,10,7,10,tzinfo=timezone.utc)
        with patch('app.progress.now',return_value=fixed):
            for days in [3,7,14,30,30]:
                state=self.post(self.q['id'],{'rating':'good'}).json['state']
                due=datetime.fromisoformat(state['due_at'])
                self.assertEqual((due-fixed).days,days)
            state=self.post(self.q['id'],{'rating':'again'}).json['state']
            self.assertEqual(state['good_streak'],0)
            self.assertEqual((datetime.fromisoformat(state['due_at'])-fixed).total_seconds(),600)
            state=self.post(self.q['id'],{'rating':'hard'}).json['state']
            self.assertEqual((datetime.fromisoformat(state['due_at'])-fixed).days,1)

    def test_weak_and_bookmark_filters(self):
        self.assertEqual(self.client.get('/api/workbook?mode=weak').json['questions'],[])
        self.post(self.q['id'],{'rating':'again','bookmarked':True})
        for mode in ['weak','bookmarked']:
            self.assertEqual([q['id'] for q in self.client.get('/api/workbook?mode='+mode).json['questions']],[self.q['id']])
        self.post(self.q['id'],{'rating':'good'})
        self.assertEqual(self.client.get('/api/workbook?mode=weak').json['questions'],[])
        self.assertEqual(len(self.client.get('/api/workbook?mode=bookmarked').json['questions']),1)

    def test_global_search_crosses_filters_and_searches_answers(self):
        result=self.client.get('/api/workbook?chapter=women&page=1&mode=weak&search=fertility').json
        self.assertTrue(any(q['chapter_id']=='population' for q in result['questions']))
        self.assertTrue(any(q['chapter_id']=='women' for q in result['questions']))
        result=self.client.get('/api/workbook?search=Gargi').json
        self.assertTrue(any('early Vedic' in q['prompt'] for q in result['questions']))

    def test_each_revision_mode(self):
        for mode in ['learn','quick','data','concepts','institutions','chapter','weak','bookmarked']:
            response=self.client.get('/api/workbook?mode='+mode)
            self.assertEqual(response.status_code,200)
        data=self.client.get('/api/workbook?mode=data').json['questions']
        self.assertEqual(len(data),145)
        self.assertTrue(all(q['format']=='fill_blank' for q in data))
        chapter=self.client.get('/api/workbook?mode=chapter').json['questions']
        self.assertEqual(len(chapter),18)
        self.assertTrue(all(q['scope']=='chapter' for q in chapter))
        quick=self.client.get('/api/workbook?mode=quick').json['questions']
        self.assertTrue(all(q['quick_recall'] and q['scope']!='chapter' for q in quick))

    def test_multiple_blank_drafts(self):
        q=next(q for q in self.questions if q['format']=='fill_blank' and len(q['blanks'])>1)
        draft={b['id']:'remembered '+str(i) for i,b in enumerate(q['blanks'])}
        self.assertEqual(self.post(q['id'],{'draft':draft}).status_code,200)
        self.assertEqual(self.client.get('/api/workbook').json['states'][q['id']]['draft'],draft)
        self.assertEqual(self.post(q['id'],{'draft':{'unknown':'5'}}).status_code,400)

    def test_bad_requests_and_csrf(self):
        self.assertEqual(self.client.post('/api/progress/'+self.q['id'],json={'rating':'good'}).status_code,403)
        for payload in [{'rating':'viewed'},{'bookmarked':'true'},{'draft':[]},{'unknown':1}]:
            self.assertEqual(self.post(self.q['id'],payload).status_code,400)
        self.assertEqual(self.post('nonexistent',{'rating':'good'}).status_code,404)
        self.assertEqual(self.client.get('/api/workbook?mode=bogus').status_code,400)

    def test_revision_change_resets_mastery_but_retains_bookmark(self):
        self.post(self.q['id'],{'rating':'good','bookmarked':True,'draft':'old answer'})
        changed=dict(self.q,revision=self.q['revision']+1)
        state=get_states(self.db,[changed])[self.q['id']]
        self.assertIsNone(state['rating']);self.assertTrue(state['bookmarked']);self.assertEqual(state['draft'],'')
        update(self.db,changed,{'rating':'hard'})
        with connect(self.db) as db:
            row=db.execute('SELECT * FROM progress WHERE question_id=?',(self.q['id'],)).fetchone()
            self.assertEqual(row['revision'],changed['revision'])
        self.assertEqual(len(self.client.get('/api/history/'+self.q['id']).json['attempts']),2)

    def test_export_and_source(self):
        self.post(self.q['id'],{'rating':'hard'})
        export=self.client.get('/api/export')
        self.assertEqual(export.json['schema_version'],1)
        self.assertEqual(len(export.json['attempts']),1)
        self.assertIn('attachment',export.headers['Content-Disposition'])
        # Private PDFs must not be required to run tests from a GitHub clone.
        with patch('app.ROOT',Path(self.tmp.name)):
            sources=Path(self.tmp.name)/'sources'
            sources.mkdir()
            fixture=sources/'Indian Society Lecture 03 PPT (1).pdf'
            fixture.write_bytes(b'%PDF-1.4\n'+b'local-route-fixture\n'*100)
            response=self.client.get('/source/society-lecture-03',headers={'Range':'bytes=0-1023'})
            self.assertEqual(response.status_code,206)
            self.assertTrue(response.data.startswith(b'%PDF'))
            response.close()
            fixture.unlink()
            self.assertEqual(self.client.get('/source/society-lecture-03').status_code,404)
            self.assertEqual(self.client.get('/api/workbook').status_code,200)
        self.assertEqual(self.client.get('/source/unknown').status_code,404)


if __name__=='__main__':unittest.main()
