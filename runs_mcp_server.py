# runs_mcp_server.py
from enum import Enum
import os, sqlite3, logging
from typing import Optional, List, Literal
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, conint, confloat, constr
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[MCP SERVER] %(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('runstats.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class RunType(str, Enum):
    outdoor = "outdoor"
    track = "track"
    treadmill = "treadmill"


class Run(BaseModel):
    """Single workout entry."""
    run_no: conint(strict=True, ge=1) = Field(..., description="Unique run number (primary key).")
    date: constr(pattern=r"^\d{4}-\d{2}-\d{2}$") = Field(..., description="Date in YYYY-MM-DD.")
    distance_km: confloat(gt=0) = Field(...,
        description="Distance in kilometers. Allowed values: 5, 10, 21.1, 42.2."
    )
    time_seconds: conint(strict=True, gt=0) = Field(..., description="Elapsed time in seconds, > 0.")
    type: RunType = Field(..., description="Run surface/type. Allowed: outdoor, track, treadmill.")

DB = "runs.sqlite"
mcp = FastMCP("runs-service")

@mcp.tool()
def upsert_runs(runs: List[Run]) -> dict:
    """
    Insert or replace runs by run_no.
    - If a run_no already exists, it is replaced.
    - You must include all required fields for each run.
    """
    logger.info(f"📝 TOOL CALL: upsert_runs() with {len(runs)} run(s)")
    for run in runs:
        logger.info(f"   - Run #{run.run_no}: {run.date} {run.distance_km}km {run.type}")
    
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executemany(
        """INSERT OR REPLACE INTO runs
           (run_no, date, distance_km, time_seconds, type)
           VALUES (?,?,?,?,?)""",
        [(r.run_no, r.date, r.distance_km, r.time_seconds, r.type.value) for r in runs],
    )
    con.commit()
    con.close()
    result = {"ok": True, "count": len(runs)}
    logger.info(f"✅ upsert_runs() completed: {result}")
    return result

@mcp.tool()
def recompute_ranks() -> dict:
    """
    Run the SQL in ./recompute_ranks.sql to recompute ranking columns such as
    rank_all, rank_outdoor and is_record. The script must create/update those columns.
    """
    logger.info(f"📝 TOOL CALL: recompute_ranks()")
    path = "recompute_ranks.sql"
    if not os.path.exists(path):
        result = {"ok": False, "error": f"{path} not found"}
        logger.error(f"❌ recompute_ranks() failed: {result}")
        return result
    con = sqlite3.connect(DB)
    with open(path, "r", encoding="utf-8") as f:
        con.executescript(f.read())
    con.close()
    result = {"ok": True, "message": "Ranks recomputed"}
    logger.info(f"✅ recompute_ranks() completed: {result}")
    return result

@mcp.tool()
def get_runs(
    distance_km: Optional[confloat(ge=0)] = Field(None, description="Exact distance in km to filter on. Omit or use 0 to search all distances."),
    run_type: Optional[RunType] = Field(None, description="Limit to a run type."),
    date_from: Optional[constr(pattern=r"^\d{4}-\d{2}-\d{2}$")] = Field(None, description="Inclusive start date."),
    date_to: Optional[constr(pattern=r"^\d{4}-\d{2}-\d{2}$")] = Field(None, description="Inclusive end date."),
    rank_all: Optional[conint(ge=0)] = Field(None, description="Filter to runs with this overall rank (1=fastest overall). Use 0 or omit to get all results sorted by speed."),
    rank_outdoor: Optional[conint(ge=0)] = Field(None, description="Filter to runs with this outdoor rank (1=fastest outdoor). Use 0 or omit to get all results sorted by speed."),
    is_record: Optional[conint(ge=0, le=1)] = Field(None, description="1 for records only, 0 for non-records only. Omit to get both.")
) -> dict:
    """
    Returns runs filtered by any combination of available columns.

    Example:
      get_runs(distance_km=5, run_type="treadmill", date_from="2018-01-01", date_to="2018-12-31")
    """
    # Log input parameters
    filters_log = []
    if distance_km is not None and distance_km > 0:
        filters_log.append(f"distance={distance_km}km")
    if run_type is not None:
        filters_log.append(f"type={run_type.value}")
    if date_from is not None:
        filters_log.append(f"date_from={date_from}")
    if date_to is not None:
        filters_log.append(f"date_to={date_to}")
    if rank_all is not None and rank_all > 0:
        filters_log.append(f"rank_all={rank_all}")
    if rank_outdoor is not None and rank_outdoor > 0:
        filters_log.append(f"rank_outdoor={rank_outdoor}")
    if is_record is not None:
        filters_log.append(f"is_record={is_record}")
    
    filter_str = ", ".join(filters_log) if filters_log else "no filters"
    logger.info(f"📝 TOOL CALL: get_runs({filter_str})")
    
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    cur = con.cursor()

    filters, params = [], []
    if distance_km is not None and distance_km > 0:
        filters.append("distance_km = ?"); params.append(float(distance_km))
    if run_type is not None:
        filters.append("type = ?"); params.append(run_type.value)
    if date_from is not None:
        filters.append("date >= ?"); params.append(date_from)
    if date_to is not None:
        filters.append("date <= ?"); params.append(date_to)
    if rank_all is not None and rank_all > 0:
        filters.append("rank_all = ?"); params.append(int(rank_all))
    if rank_outdoor is not None and rank_outdoor > 0:
        filters.append("rank_outdoor = ?"); params.append(int(rank_outdoor))
    if is_record is not None and not (rank_all is not None and rank_all > 0) and not (rank_outdoor is not None and rank_outdoor > 0):
        filters.append("is_record = ?"); params.append(int(is_record))

    where_clause = " WHERE " + " AND ".join(filters) if filters else ""
    
    # Sort by speed (fastest first) when querying all distances, otherwise by distance/date
    if distance_km is None or distance_km == 0:
        order_clause = "ORDER BY time_seconds, distance_km, date"
    else:
        order_clause = "ORDER BY distance_km, date, time_seconds"
    
    query = f"""SELECT run_no, date, distance_km, time_seconds, type,
                       rank_all, rank_outdoor, is_record
                FROM runs{where_clause}
                {order_clause}"""
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    logger.info(f"✅ get_runs() returned {len(rows)} run(s)")
    for row in rows[:5]:  # Log first 5 results
        logger.info(f"   - #{row['run_no']}: {row['date']} {row['distance_km']}km {row['time_seconds']}s {row['type']}")
    if len(rows) > 5:
        logger.info(f"   ... and {len(rows)-5} more")
    return {"rows": rows}

if __name__ == "__main__":
    mcp.run()