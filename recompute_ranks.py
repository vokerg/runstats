import sqlite3, sys
db = sys.argv[1] if len(sys.argv)>1 else "db/runs.sqlite"
con = sqlite3.connect(db)
con.executescript(open("db/recompute_ranks.sql","r",encoding="utf-8").read())
con.close()
print("Ranks recomputed and stored.")