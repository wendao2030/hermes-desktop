import sqlite3, datetime
db = sqlite3.connect(r'c:\Users\dtyao\AppData\Local\hermes\state.db')
rows = db.execute('SELECT id,title,started_at,message_count,source FROM sessions ORDER BY started_at DESC LIMIT 30').fetchall()
with open(r'c:\Users\dtyao\AppData\Local\hermes\_sessions.txt','w',encoding='utf-8') as f:
    for r in rows:
        ts = datetime.datetime.fromtimestamp(r[2])
        f.write(f'{ts} | {str(r[1])[:60] if r[1] else "-"} | {r[4]} | msgs={r[3]} | {r[0][:30]}\n')
db.close()
print('Done', len(rows))
