"""SQLite progress with atomic rating/history writes and a small review schedule."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc)


@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def init_db(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS progress (
          question_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
          draft TEXT NOT NULL DEFAULT '""', bookmarked INTEGER NOT NULL DEFAULT 0,
          rating TEXT CHECK(rating IN ('again','hard','good')), good_streak INTEGER NOT NULL DEFAULT 0,
          last_attempt_at TEXT, due_at TEXT
        );
        CREATE TABLE IF NOT EXISTS attempts (
          id INTEGER PRIMARY KEY, question_id TEXT NOT NULL, revision INTEGER NOT NULL,
          attempted_at TEXT NOT NULL, rating TEXT NOT NULL CHECK(rating IN ('again','hard','good')),
          response TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS attempts_question ON attempts(question_id, attempted_at);
        ''')


def get_states(path, questions):
    with connect(path) as db:
        rows = {r['question_id']: dict(r) for r in db.execute('SELECT * FROM progress')}
    states = {}
    for q in questions:
        row = rows.get(q['id'])
        if not row:
            states[q['id']] = {'draft': '' if q['format'] == 'recall' else {}, 'bookmarked': False, 'rating': None, 'good_streak': 0, 'last_attempt_at': None, 'due_at': None}
        else:
            row['draft'] = json.loads(row['draft'])
            row['bookmarked'] = bool(row['bookmarked'])
            if row['revision'] != q['revision']:
                row.update(rating=None, good_streak=0, due_at=None, draft='' if q['format'] == 'recall' else {})
            states[q['id']] = row
    return states


def update(path, question, payload):
    """Mutation fields have already been checked by the route."""
    stamp = now()
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR IGNORE INTO progress(question_id,revision) VALUES(?,?)', (question['id'], question['revision']))
        row = dict(db.execute('SELECT * FROM progress WHERE question_id=?', (question['id'],)).fetchone())
        if row['revision'] != question['revision']:
            row.update(revision=question['revision'], rating=None, good_streak=0, due_at=None, draft=json.dumps('' if question['format']=='recall' else {}))
        if 'draft' in payload:
            row['draft'] = json.dumps(payload['draft'], ensure_ascii=False)
        if 'bookmarked' in payload:
            row['bookmarked'] = int(payload['bookmarked'])
        if 'rating' in payload:
            rating = payload['rating']
            streak = row['good_streak'] + 1 if rating == 'good' else 0
            delay = timedelta(minutes=10) if rating == 'again' else timedelta(days=1 if rating == 'hard' else [3, 7, 14, 30][min(streak-1, 3)])
            row.update(rating=rating, good_streak=streak, last_attempt_at=stamp.isoformat(), due_at=(stamp+delay).isoformat())
            db.execute('INSERT INTO attempts(question_id,revision,attempted_at,rating,response) VALUES(?,?,?,?,?)',
                       (question['id'], question['revision'], stamp.isoformat(), rating, row['draft']))
        db.execute('UPDATE progress SET revision=?,draft=?,bookmarked=?,rating=?,good_streak=?,last_attempt_at=?,due_at=? WHERE question_id=?',
                   (row['revision'], row['draft'], row['bookmarked'], row['rating'], row['good_streak'], row['last_attempt_at'], row['due_at'], question['id']))
    return get_states(path, [question])[question['id']]


def mastery(questions, states):
    counts = dict(strong=0, hard=0, weak=0, unseen=0, due=0)
    stamp = now().isoformat()
    for q in questions:
        state = states[q['id']]
        counts[{None: 'unseen', 'again': 'weak', 'hard': 'hard', 'good': 'strong'}[state['rating']]] += 1
        if state.get('due_at') and state['due_at'] <= stamp:
            counts['due'] += 1
    return counts
