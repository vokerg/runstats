import sqlite3, datetime

DB = "runs.sqlite"
TSV = "resources/runs.tsv"

def hms_to_seconds(hms):
    h, m, s = map(int, hms.split("." if "." in hms else ":"))
    return h * 3600 + m * 60 + s

def map_type(token):
    token = token.strip().lower()
    if token == "t":
        return "treadmill"
    elif token == "s":
        return "track"
    else:
        return "outdoor"

def dmy_to_iso(dmy_dot):
    d, m, y = map(int, dmy_dot.split("."))
    return f"{y:04d}-{m:02d}-{d:02d}"

try:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = 0
    with open(TSV, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) == 3:
                distance_str, time_hms, date_dot = parts
                type_token = ""
            elif len(parts) == 4:
                distance_str, time_hms, date_dot, type_token = parts
            else:
                print("Skipping:", line)
                continue
            cur.execute(
                """INSERT INTO runs
                   (date, distance_km, time_seconds, type)
                   VALUES (?, ?, ?, ?)""",
                (
                    dmy_to_iso(date_dot),
                    float(distance_str.replace(",", ".")),
                    hms_to_seconds(time_hms),
                    map_type(type_token),
                ),
            )
            rows += 1
    con.commit()
    con.close()
    print(f"Inserted {rows} rows from {TSV} into {DB}")
except Exception as e:
    print(f"Error: {e}")