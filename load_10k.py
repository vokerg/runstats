import sqlite3

DB = "runs.sqlite"
TSV = "run_10k.tsv"


def hms_to_seconds(hms):
    h, m, s = map(int, hms.split("." if "." in hms else ":"))
    return h * 3600 + m * 60 + s


def dmy_to_iso(dmy_dot):
    d, m, y = map(int, dmy_dot.split("."))
    return f"{y:04d}-{m:02d}-{d:02d}"


def map_type(token):
    token = token.strip().lower()
    if token == "t":
        return "treadmill"
    elif token == "s":
        return "track"
    else:
        return "outdoor"


con = sqlite3.connect(DB)
cur = con.cursor()
rows = 0
with open(TSV, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        parts = line.strip().split("\t")
        if len(parts) != 4:
            print("Skipping:", line)
            continue
        time_hms, date_dot, type_token, run_no_str = parts
        cur.execute(
            """INSERT OR REPLACE INTO runs
               (run_no, date, distance_km, time_seconds, type)
               VALUES (?, ?, ?, ?, ?)""",
            (
                int(run_no_str),
                dmy_to_iso(date_dot),
                10.0,
                hms_to_seconds(time_hms),
                map_type(type_token),
            ),
        )
        rows += 1
con.commit()
con.close()
print(f"Upserted {rows} rows from {TSV} into {DB}")
