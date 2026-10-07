"""Content validation and data-driven revision filters."""
import json
import re
from pathlib import Path
MODES = {'learn': 'Learn', 'weak': 'Weak', 'quick': 'Quick Recall', 'data': 'Data Drill',
         'concepts': 'Concepts & Reasoning', 'institutions': 'Institutions',
         'chapter': 'Chapter Recall', 'bookmarked': 'Bookmarked'}


def load_content(directory):
    directory = Path(directory)
    catalog = json.loads((directory / 'catalog.json').read_text())
    questions, units = [], []
    assert catalog['schema_version'] == 1, 'Unsupported schema'
    chapter_ids = {c['id'] for c in catalog['chapters']}
    source_ids = {s['id'] for s in catalog['sources']}
    subject_ids = {s['id'] for s in catalog['subjects']}
    assert len(chapter_ids) == len(catalog['chapters'])
    for chapter in catalog['chapters']:
        assert chapter['source_id'] in source_ids and chapter['subject_id'] in subject_ids
        for key, target in [('bank_file', questions), ('units_file', units)]:
            name = chapter[key]
            assert Path(name).name == name, 'Content filenames must be basenames'
            target.extend(json.loads((directory / name).read_text()))
    unit_map = {u['id']: u for u in units}
    assert len(unit_map) == len(units), 'Duplicate unit ID'
    assert len({q['id'] for q in questions}) == len(questions), 'Duplicate question ID'
    chapter_map = {c['id']: c for c in catalog['chapters']}
    source_map = {s['id']: s for s in catalog['sources']}
    for source in source_map.values():
        assert Path(source['private_filename']).name == source['private_filename']
    for unit in units:
        assert unit['chapter_id'] in chapter_ids
        assert unit['source_pages'] and unit['recall_points']
    for q in questions:
        chapter = chapter_map[q['chapter_id']]
        assert q['format'] in {'recall', 'fill_blank'}
        assert q['scope'] in {'unit', 'chapter'}
        assert q['category'] in {'concept', 'keywords', 'reasoning', 'relationship', 'list', 'data', 'institution', 'synthesis'}
        assert q['importance'] in {'high', 'standard'}
        assert isinstance(q['revision'], int) and q['revision'] > 0
        assert q['source_pages'] and len(q['source_pages']) == len(set(q['source_pages']))
        assert all(isinstance(p, int) and 1 <= p <= source_map[chapter['source_id']]['page_count'] for p in q['source_pages'])
        assert any(chapter['page_start'] <= p <= chapter['page_end'] for p in q['source_pages'])
        if q['scope'] == 'unit':
            assert all(chapter['page_start'] <= p <= chapter['page_end'] for p in q['source_pages'])
        assert q['prompt'] and q['expected_answer']['items']
        assert q['expected_answer']['style'] in {'bullets', 'chain', 'definition'}
        assert all(isinstance(a, str) and a for a in q['expected_answer']['items'])
        for uid in q['unit_ids']:
            assert uid in unit_map
            assert unit_map[uid]['chapter_id'] == q['chapter_id']
            assert set(unit_map[uid]['source_pages']) <= set(q['source_pages'])
        tokens = re.findall(r'\{\{(\w+)\}\}', q['prompt'])
        if q['format'] == 'fill_blank':
            blanks = q['blanks']
            assert len(tokens) == len(blanks) and set(tokens) == {b['id'] for b in blanks}
            assert all(b['answer'] and b['label'] for b in blanks)
        else:
            assert not tokens
        q['chapter_number'] = chapter['number']
        q['chapter_title'] = chapter['title']
        q['subject_id'] = chapter['subject_id']
        q['source_id'] = chapter['source_id']
        institution_text = ' '.join([q['prompt'], *q['tags']]).lower()
        q['institution'] = q['category'] == 'institution' or any(word in institution_text for word in ['nfhs', 'unfpa', 'gender gap', 'plfs', 'srs ', 'aishe', 'lancet', 'national health policy'])
    return catalog, questions, unit_map


def matches_mode(question, state, mode):
    rating = state.get('rating')
    return {'learn': True,
            'weak': rating in ('again', 'hard'),
            'quick': question['quick_recall'] and question['scope'] != 'chapter',
            'data': question['format'] == 'fill_blank',
            'concepts': question['category'] in ('concept', 'reasoning', 'relationship') and question['scope'] != 'chapter',
            'institutions': question['institution'],
            'chapter': question['scope'] == 'chapter',
            'bookmarked': bool(state.get('bookmarked'))}[mode]


def search_text(question):
    return ' '.join([question['prompt'], question['chapter_title'], *question['tags'],
                     *question['expected_answer']['items'], question.get('source_note', '')]).casefold()
