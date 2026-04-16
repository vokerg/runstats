import sqlite3

con = sqlite3.connect('runs.sqlite')
cur = con.cursor()

# Get total count
rows = cur.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
print(f'Total rows in database: {rows}\n')

if rows > 0:
    print('First 10 rows:')
    print('Date\t\tDistance\tTime(sec)\tType')
    print('-' * 60)
    for row in cur.execute('SELECT date, distance_km, time_seconds, type FROM runs LIMIT 10'):
        date, dist, time_sec, run_type = row
        print(f'{date}\t{dist}\t\t{time_sec}\t\t{run_type}')

con.close()