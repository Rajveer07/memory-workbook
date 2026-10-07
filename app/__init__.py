import json
import secrets
from pathlib import Path
from flask import Flask, abort, jsonify, render_template, request, send_file, session
from .content import MODES, load_content, matches_mode, search_text
from .progress import connect, get_states, init_db, mastery, now, update

ROOT = Path(__file__).resolve().parents[1]


def create_app(test_config=None):
    app = Flask(__name__, template_folder=str(ROOT/'templates'), static_folder=str(ROOT/'static'), instance_path=str(ROOT/'instance'))
    app.config.update(DATABASE=str(ROOT/'instance'/'progress.sqlite3'), MAX_CONTENT_LENGTH=200_000,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict')
    if test_config:
        app.config.update(test_config)
    if not app.config.get('SECRET_KEY'):
        Path(app.instance_path).mkdir(exist_ok=True)
        key = Path(app.instance_path)/'session.key'
        if not key.exists():
            try:
                with key.open('x') as file: file.write(secrets.token_hex(32))
            except FileExistsError: pass
        app.config['SECRET_KEY'] = key.read_text()
    catalog, questions, units = load_content(ROOT/'questions')
    question_map = {q['id']: q for q in questions}
    chapter_map = {c['id']: c for c in catalog['chapters']}
    source_map = {s['id']: s for s in catalog['sources']}
    init_db(app.config['DATABASE'])
    app.extensions['workbook'] = dict(catalog=catalog, questions=questions)

    @app.before_request
    def protect_mutations():
        if request.method in ('POST', 'PUT', 'DELETE'):
            if not session.get('csrf') or not secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), session['csrf']):
                abort(403)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; object-src 'self'; base-uri 'self'; frame-ancestors 'self'"
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/')
    def index():
        session.setdefault('csrf', secrets.token_hex(24))
        return render_template('index.html', catalog=catalog, modes=MODES, csrf=session['csrf'])

    @app.get('/api/workbook')
    def workbook():
        states = get_states(app.config['DATABASE'], questions)
        mode = request.args.get('mode', 'learn')
        if mode not in MODES: abort(400)
        search = request.args.get('search', '').strip().casefold()
        chapter = request.args.get('chapter', '')
        subject = request.args.get('subject', '')
        page = request.args.get('page', type=int)
        if chapter and chapter not in chapter_map: abort(400)
        filtered = []
        for q in questions:
            if search:
                # Global search intentionally crosses current chapter/page/mode selections.
                if not all(word in search_text(q) for word in search.split()): continue
            else:
                if subject and q['subject_id'] != subject: continue
                if chapter and q['chapter_id'] != chapter: continue
                if page and page not in q['source_pages']: continue
                if not matches_mode(q, states[q['id']], mode): continue
            filtered.append(q)
        if mode == 'weak' and not search:
            stamp = now().isoformat()
            filtered.sort(key=lambda q: (states[q['id']].get('due_at', '') > stamp,
                                          states[q['id']]['rating'] != 'again', states[q['id']].get('due_at') or ''))
        counts = {c['id']: mastery([q for q in questions if q['chapter_id']==c['id']], states) for c in catalog['chapters']}
        return jsonify(questions=filtered, states={q['id']:states[q['id']] for q in filtered}, mastery=counts,
                       totals={c['id']:sum(q['chapter_id']==c['id'] for q in questions) for c in catalog['chapters']})

    @app.post('/api/progress/<qid>')
    def progress(qid):
        q = question_map.get(qid)
        if not q: abort(404)
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not payload or set(payload)-{'draft','rating','bookmarked'}: abort(400)
        if 'rating' in payload and payload['rating'] not in ('again','hard','good'): abort(400)
        if 'bookmarked' in payload and type(payload['bookmarked']) is not bool: abort(400)
        if 'draft' in payload:
            draft=payload['draft']
            if q['format']=='recall':
                if not isinstance(draft,str) or len(draft)>20_000: abort(400)
            elif not isinstance(draft,dict) or set(draft)-{b['id'] for b in q['blanks']} or any(not isinstance(v,str) or len(v)>500 for v in draft.values()):
                abort(400)
        state=update(app.config['DATABASE'],q,payload)
        states=get_states(app.config['DATABASE'],questions)
        return jsonify(state=state,mastery={c['id']:mastery([x for x in questions if x['chapter_id']==c['id']],states) for c in catalog['chapters']})

    @app.get('/api/history/<qid>')
    def history(qid):
        if qid not in question_map: abort(404)
        with connect(app.config['DATABASE']) as db:
            rows=[dict(r) for r in db.execute('SELECT attempted_at,rating,response,revision FROM attempts WHERE question_id=? ORDER BY id DESC',(qid,))]
        for row in rows: row['response']=json.loads(row['response'])
        return jsonify(attempts=rows)

    @app.get('/api/export')
    def export():
        with connect(app.config['DATABASE']) as db:
            obj=dict(schema_version=1,bank_version=catalog['bank_version'],exported_at=now().isoformat(),
                     progress=[dict(r) for r in db.execute('SELECT * FROM progress')],
                     attempts=[dict(r) for r in db.execute('SELECT * FROM attempts ORDER BY id')])
        response=jsonify(obj)
        response.headers['Content-Disposition']='attachment; filename="progress-backup.json"'
        return response

    @app.get('/source/<source_id>')
    def source(source_id):
        source=source_map.get(source_id)
        if not source: abort(404)
        path=ROOT/'sources'/source['private_filename']
        if not path.is_file():
            return render_template('missing-source.html',source=source),404
        return send_file(path,mimetype='application/pdf',conditional=True)

    return app
