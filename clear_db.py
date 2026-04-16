import sqlite3
con = sqlite3.connect('runs.sqlite')
cur = con.cursor()
cur.execute('DELETE FROM runs')
con.commit()
con.close()
print('Database cleared')