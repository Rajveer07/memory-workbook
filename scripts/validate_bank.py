"""Validate bank links, blank tokens, audit coverage and question distribution."""
import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.content import load_content
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    catalog,questions,units=load_content(ROOT/'questions')
    audit=json.loads((ROOT/'questions/page-audit.json').read_text())
    qmap={q['id']:q for q in questions}
    expected=set()
    for source in catalog['sources']:
        if source['id']=='society-lecture-03':expected.update(range(1,source['page_count']+1))
    assert {row['page'] for row in audit}==expected
    for row in audit:
        assert row['text_reviewed'] and row['visual_reviewed']
        assert row['unit_ids'] and row['question_ids'],f'Uncovered page {row["page"]}'
        assert all(row['page'] in qmap[qid]['source_pages'] for qid in row['question_ids'])
        assert all(row['page'] in units[uid]['source_pages'] for uid in row['unit_ids'])
    for chapter in catalog['chapters']:
        qs=[q for q in questions if q['chapter_id']==chapter['id']]
        print(chapter['title'],len(qs),'questions;',Counter(q['category'] for q in qs))
    print('PASS:',len(audit),'pages audited;',len(units),'knowledge units;',len(questions),'questions')
