import sqlite3, datetime
db = sqlite3.connect(r'c:\Users\dtyao\AppData\Local\hermes\state.db')

sessions = [
    ('20260605_094410_504f93', 'Jun 5 09:44'),
    ('default', 'Jun 5 11:22'),
    ('emp-3e664a0c', 'Jun 7 00:23 emp'),
]

for sid, desc in sessions:
    print(f'\n===== {desc} | {sid} =====')
    rows = db.execute(
        'SELECT role, content, timestamp FROM messages WHERE session_id=? ORDER BY id',
        (sid,)
    ).fetchall()
    print(f'Total: {len(rows)}')
    for i, r in enumerate(rows):
        role = r[0]
        content = str(r[1] or '')
        ts = datetime.datetime.fromtimestamp(r[2]) if r[2] else '?'
        print(f'  [{i}][{role}] {ts} | {content[:200]}')

db.close()
