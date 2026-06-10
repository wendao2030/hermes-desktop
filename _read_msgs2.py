import sqlite3, datetime, sys
db = sqlite3.connect(r'c:\Users\dtyao\AppData\Local\hermes\state.db')

# Get all user messages from desktop source between Jun 5 and Jun 7
rows = db.execute('''
    SELECT m.session_id, m.role, m.content, m.timestamp
    FROM messages m
    JOIN sessions s ON m.session_id = s.id
    WHERE s.source = 'desktop'
      AND m.role = 'user'
      AND m.timestamp > 1749056000
    ORDER BY m.timestamp
''').fetchall()

with open(r'c:\Users\dtyao\AppData\Local\hermes\_user_msgs.txt', 'w', encoding='utf-8') as f:
    for r in rows:
        ts = datetime.datetime.fromtimestamp(r[3])
        content = str(r[2] or '')
        f.write(f'{ts} | {r[0][:25]} | {content[:500]}\n')
        f.write('---\n')

print(f'Done, {len(rows)} user messages')
db.close()
