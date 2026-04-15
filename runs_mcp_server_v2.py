# runs_mcp_server_v2.py
# LLM-friendly MCP server for runs database with support for natural language queries
from enum import Enum
import os, sqlite3, logging
from typing import Optional, List, Literal
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, conint, confloat, constr
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[MCP SERVER V2] %(asctime)s - %(levelname)s - %(message)s',
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
mcp = FastMCP("runs-service-v2")

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
    rank_all, rank_outdoor, rank_outdoor_track, rank_track, rank_treadmill, and is_record.
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
def query_runs(
    distance_km: Optional[confloat(ge=0)] = Field(None, description="Exact distance in km to filter on. Omit or use 0 to search all distances."),
    run_type: Optional[RunType] = Field(None, description="Limit to a run type (outdoor, track, treadmill)."),
    date_from: Optional[str] = Field(None, description="Inclusive start date YYYY-MM-DD."),
    date_to: Optional[str] = Field(None, description="Inclusive end date YYYY-MM-DD."),
    year: Optional[conint(ge=1900, le=2100)] = Field(None, description="Filter by specific year."),
    rank_all: Optional[conint(ge=0)] = Field(None, description="Filter to runs with this overall rank. Use 0 or omit to skip this filter."),
    rank_outdoor_track: Optional[conint(ge=0)] = Field(None, description="Filter to runs with this rank among outdoor+track runs only. Use 0 or omit to skip."),
    rank_track: Optional[conint(ge=0)] = Field(None, description="Filter to runs with this rank among track runs only. Use 0 or omit to skip."),
    rank_treadmill: Optional[conint(ge=0)] = Field(None, description="Filter to runs with this rank among treadmill runs only. Use 0 or omit to skip."),
    is_record: Optional[conint(ge=0, le=1)] = Field(None, description="1 for records only (fastest overall for that distance), 0 for non-records. Omit to get both."),
    limit: Optional[conint(ge=1, le=1000)] = Field(100, description="Maximum number of results to return.")
) -> dict:
    """
    Query runs with flexible filtering options. Returns data including all ranking columns.
    
    Examples:
      - Fastest 5k outdoor run in 2023: distance_km=5, run_type="outdoor", year=2023, limit=1
      - All 10k track runs: distance_km=10, run_type="track"
      - Top 5 runs overall: limit=5
      - All records: is_record=1
    """
    filters_log = []
    if distance_km is not None and distance_km > 0:
        filters_log.append(f"distance={distance_km}km")
    if run_type is not None:
        filters_log.append(f"type={run_type.value}")
    if year is not None:
        filters_log.append(f"year={year}")
    if date_from is not None:
        filters_log.append(f"date_from={date_from}")
    if date_to is not None:
        filters_log.append(f"date_to={date_to}")
    if rank_all is not None:
        filters_log.append(f"rank_all={rank_all}")
    if rank_outdoor_track is not None:
        filters_log.append(f"rank_outdoor_track={rank_outdoor_track}")
    if rank_track is not None:
        filters_log.append(f"rank_track={rank_track}")
    if rank_treadmill is not None:
        filters_log.append(f"rank_treadmill={rank_treadmill}")
    if is_record is not None:
        filters_log.append(f"is_record={is_record}")
    
    filter_str = ", ".join(filters_log) if filters_log else "no filters"
    logger.info(f"📝 TOOL CALL: query_runs({filter_str})")
    
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    filters, params = [], []
    
    if distance_km is not None and distance_km > 0:
        filters.append("distance_km = ?")
        params.append(float(distance_km))
    if run_type is not None:
        filters.append("type = ?")
        params.append(run_type.value)
    if year is not None:
        filters.append("year = ?")
        params.append(int(year))
    if date_from is not None and date_from.strip():
        filters.append("date >= ?")
        params.append(date_from.strip())
    if date_to is not None and date_to.strip():
        filters.append("date <= ?")
        params.append(date_to.strip())
    if rank_all is not None and rank_all > 0:
        filters.append("rank_all = ?")
        params.append(int(rank_all))
    if rank_outdoor_track is not None and rank_outdoor_track > 0:
        filters.append("rank_outdoor_track = ?")
        params.append(int(rank_outdoor_track))
    if rank_track is not None and rank_track > 0:
        filters.append("rank_track = ?")
        params.append(int(rank_track))
    if rank_treadmill is not None and rank_treadmill > 0:
        filters.append("rank_treadmill = ?")
        params.append(int(rank_treadmill))
    if is_record is not None:
        filters.append("is_record = ?")
        params.append(int(is_record))

    where_clause = " WHERE " + " AND ".join(filters) if filters else ""
    
    # Smart sorting: by speed for single distance, by distance then speed otherwise
    if distance_km is not None and distance_km > 0:
        order_clause = "ORDER BY time_seconds ASC, date DESC"
    else:
        order_clause = "ORDER BY distance_km ASC, time_seconds ASC, date DESC"
    
    query = f"""SELECT run_no, date, distance_km, time_seconds, type,
                       year, month,
                       rank_all, rank_outdoor, rank_outdoor_track, rank_track, rank_treadmill,
                       is_record, speed_kmh, pace_min_per_km
                FROM runs{where_clause}
                {order_clause}
                LIMIT ?"""
    
    params.append(int(limit))
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    
    logger.info(f"✅ query_runs() returned {len(rows)} run(s)")
    for row in rows[:3]:
        logger.info(f"   - #{row['run_no']}: {row['date']} {row['distance_km']}km {row['time_seconds']}s {row['type']} (rank_all={row['rank_all']})")
    if len(rows) > 3:
        logger.info(f"   ... and {len(rows)-3} more")
    
    return {
        "count": len(rows),
        "limit": limit,
        "rows": rows
    }

if __name__ == "__main__":
    mcp.run()
