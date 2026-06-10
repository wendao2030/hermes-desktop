import sqlite3
db = sqlite3.connect(r'c:\Users\dtyao\AppData\Local\hermes\state.db')
cols = db.execute('PRAGMA table_info(messages)').fetchall()
for c in cols:
    print(c[1], c[2])
db.close()
