"""Export the finished pipeline's results into dashboard/data/*.json for the website.

Run once after the 61-day backfill, and again after the Snowpipe demo, BEFORE the
Snowflake trial ends. The website only reads these files, so it keeps working
after Snowflake is gone.

    python dashboard/export.py --credits 3.7

Needs SNOWFLAKE_ACCOUNT and SNOWFLAKE_PRIVATE_KEY_PATH in the environment, and
the Airflow containers running (for run durations). --credits is the number
shown in Snowsight under Admin -> Cost management.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
from datetime import date, datetime

import snowflake.connector

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(__file__).resolve().parent / "data"
STG = "CLICKSTREAM.ANALYTICS_STAGING"
MARTS = "CLICKSTREAM.ANALYTICS_MARTS"

QUERIES = {
    # one row per day x top-level category
    "funnel_daily": f"""
        select event_date, category_l1, sessions_viewed, sessions_carted, sessions_purchased
        from {MARTS}.FCT_FUNNEL_DAILY order by event_date, category_l1""",
    "categories": f"""
        select category_l1,
               sum(sessions_viewed) as sessions_viewed, sum(sessions_carted) as sessions_carted,
               sum(sessions_purchased) as sessions_purchased, round(sum(revenue)) as revenue
        from {MARTS}.FCT_FUNNEL_DAILY group by 1 order by 1""",
    "price_bands": f"""
        with e as (
            select user_session, event_type,
                   case when price < 25 then '< $25' when price < 50 then '$25-50'
                        when price < 100 then '$50-100' when price < 250 then '$100-250'
                        when price < 500 then '$250-500' when price < 1000 then '$500-1k'
                        else '> $1k' end as price_band,
                   case when price < 25 then 1 when price < 50 then 2 when price < 100 then 3
                        when price < 250 then 4 when price < 500 then 5 when price < 1000 then 6
                        else 7 end as band_order
            from {STG}.STG_EVENTS where event_type in ('view', 'purchase'))
        select price_band,
               count(distinct iff(event_type = 'view', user_session, null)) as sessions_viewed,
               count(distinct iff(event_type = 'purchase', user_session, null)) as sessions_purchased
        from e group by price_band, band_order order by band_order""",
    "brands": f"""
        select brand,
               count(distinct iff(event_type = 'view', user_session, null)) as sessions_viewed,
               count(distinct iff(event_type = 'purchase', user_session, null)) as sessions_purchased
        from {STG}.STG_EVENTS where brand <> 'unknown'
        group by brand order by sessions_purchased desc limit 12""",
    # weekday: 0 = Sunday (matches the site's JS convention)
    "hourly_abandonment": f"""
        select mod(dayofweekiso(session_start), 7) as weekday, hour(session_start) as hour,
               count(*) as sessions_carted, count_if(purchases = 0) as sessions_abandoned
        from {MARTS}.FCT_SESSIONS where carts > 0 group by 1, 2 order by 1, 2""",
    "quality_daily": f"""
        select event_date, count(*) as raw_rows,
               count_if(reject_reason is not null) as quarantined,
               count_if(reject_reason is null and is_duplicate) as duplicates,
               count_if(reject_reason = 'bad_timestamp') as bad_timestamp,
               count_if(reject_reason = 'bad_event_type') as bad_event_type,
               count_if(reject_reason = 'bad_price') as bad_price,
               count_if(reject_reason = 'missing_user') as missing_user,
               count_if(reject_reason = 'missing_session') as missing_session
        from {STG}.STG_EVENTS_CHECKED group by 1 order by 1""",
    "session_totals": f"""
        select count_if(views > 0) as sessions_viewed, count_if(carts > 0) as sessions_carted,
               count_if(purchases > 0) as sessions_purchased, round(sum(revenue)) as revenue
        from {MARTS}.FCT_SESSIONS""",
    # needs 04_snowpipe.sql (grants) and the replay; returns nothing before that
    "snowpipe": """
        select file_name, row_count,
               datediff('second', min(pipe_received_time) over (), pipe_received_time) as sent_s,
               datediff('second', min(pipe_received_time) over (), last_load_time) as loaded_s,
               datediff('second', pipe_received_time, last_load_time) as latency_s
        from table(CLICKSTREAM.INFORMATION_SCHEMA.COPY_HISTORY(
            table_name => 'CLICKSTREAM.RAW.EVENTS_LIVE',
            start_time => dateadd('day', -14, current_timestamp())))
        where status = 'Loaded' order by pipe_received_time""",
}

AIRFLOW_SQL = """
    select to_char(dr.logical_date, 'YYYY-MM-DD'), ti.task_id,
           coalesce(extract(epoch from ti.end_date - ti.start_date), 0), ti.try_number, ti.state
    from task_instance ti join dag_run dr on dr.dag_id = ti.dag_id and dr.run_id = ti.run_id
    where ti.dag_id = 'clickstream_daily' order by 1"""


def jsonable(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    if hasattr(v, "is_integer"):  # Decimal / float
        return int(v) if float(v).is_integer() else float(v)
    return v


def run_snowflake() -> dict:
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user="PIPELINE_SVC",
        private_key_file=os.path.expanduser(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]),
        role="TRANSFORMER",
        warehouse="CLICKSTREAM_WH",
        database="CLICKSTREAM",
    )
    results = {}
    try:
        for name, sql in QUERIES.items():
            cur = conn.cursor()
            try:
                cur.execute(sql)
            except snowflake.connector.errors.ProgrammingError as e:
                if name == "snowpipe":
                    print("snowpipe: skipped (no EVENTS_LIVE yet)", e.msg)
                    results[name] = []
                    continue
                raise
            cols = [c[0].lower() for c in cur.description]
            results[name] = [{k: jsonable(v) for k, v in zip(cols, row)} for row in cur.fetchall()]
            print(f"{name}: {len(results[name])} rows")
    finally:
        conn.close()
    return results


def run_airflow() -> list[dict]:
    """Task durations from Airflow's metadata database (containers must be running)."""
    cmd = ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "airflow", "-d", "airflow",
           "-At", "-F", ",", "-c", AIRFLOW_SQL]
    try:
        out = subprocess.run(cmd, cwd=ROOT / "airflow", check=True, capture_output=True, text=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print("airflow_runs: skipped (start the Airflow containers first)", e)
        return []
    runs: dict[str, dict] = {}
    for line in out.strip().splitlines():
        ds, task_id, secs, tries, state = line.split(",")
        r = runs.setdefault(ds, {"ds": ds, "upload_s": 0, "copy_s": 0, "dbt_s": 0, "state": "success", "tries": 1})
        key = {"upload_to_s3": "upload_s", "copy_into_raw": "copy_s", "dbt_build": "dbt_s"}.get(task_id)
        if key:
            r[key] = round(float(secs))
        r["tries"] = max(r["tries"], int(tries or 1))
        if state != "success":
            r["state"] = state
    print(f"airflow_runs: {len(runs)} rows")
    return list(runs.values())


def dbt_counts() -> tuple[int, int]:
    manifest = ROOT / "dbt_project/clickstream/target/manifest.json"
    if not manifest.exists():
        return 0, 0
    nodes = json.loads(manifest.read_text())["nodes"].values()
    models = sum(1 for n in nodes if n["resource_type"] == "model" and n["package_name"] == "clickstream")
    tests = sum(1 for n in nodes if n["resource_type"] == "test" and n["package_name"] == "clickstream")
    return models, tests


def folder_gb(path: pathlib.Path, fallback: float) -> float:
    if not path.exists():
        return fallback
    return round(sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e9, 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--credits", type=float, required=True, help="Snowflake credits used (from Snowsight)")
    p.add_argument("--credit-cap", type=float, default=40)
    args = p.parse_args()

    sf = run_snowflake()
    runs = run_airflow()
    models, tests = dbt_counts()

    quality = [
        {
            "event_date": q["event_date"],
            "raw_rows": q["raw_rows"],
            "clean_rows": q["raw_rows"] - q["quarantined"] - q["duplicates"],
            "quarantined": q["quarantined"],
            "duplicates": q["duplicates"],
            "reasons": {k: q[k] for k in
                        ("bad_timestamp", "bad_event_type", "bad_price", "missing_user", "missing_session")},
        }
        for q in sf["quality_daily"]
    ]
    snowpipe = [
        {"file": f["file_name"], "rows": f["row_count"], "sent_s": f["sent_s"],
         "loaded_s": f["loaded_s"], "latency_s": f["latency_s"]}
        for f in sf["snowpipe"]
    ]
    latencies = sorted(f["latency_s"] for f in snowpipe)
    s = sf["session_totals"][0]
    raw_rows = sum(q["raw_rows"] for q in quality)
    day_match = re.search(r"\d{4}-\d{2}-\d{2}", snowpipe[0]["file"]) if snowpipe else None
    replay_day = day_match.group(0) if day_match else None

    totals = {
        "raw_events": raw_rows,
        "raw_csv_gb": folder_gb(ROOT / "data/raw", 14.7),
        "parquet_gb": folder_gb(ROOT / "data/landing", 2.1),
        "days": len(quality),
        "raw_rows": raw_rows,
        "clean_rows": sum(q["clean_rows"] for q in quality),
        "quarantined": sum(q["quarantined"] for q in quality),
        "duplicates": sum(q["duplicates"] for q in quality),
        "sessions_viewed": s["sessions_viewed"],
        "sessions_carted": s["sessions_carted"],
        "sessions_purchased": s["sessions_purchased"],
        "revenue": s["revenue"],
        "dbt_models": models,
        "dbt_tests": tests,
        "backfill_minutes": round(sum(r["upload_s"] + r["copy_s"] + r["dbt_s"] for r in runs) / 60),
        "credits_used": args.credits,
        "credit_cap": args.credit_cap,
        "snowpipe_files": len(snowpipe),
        "snowpipe_median_latency_s": latencies[len(latencies) // 2] if latencies else 0,
    }

    files = {
        "meta": {
            "preview": False,
            "note": "Exported from the Snowflake marts after the 61-day backfill.",
            "source": "REES46 eCommerce behavior data, multi-category store, Oct-Nov 2019",
            "replay_day": replay_day,
        },
        "totals": totals,
        "funnel_daily": sf["funnel_daily"],
        "categories": sf["categories"],
        "price_bands": sf["price_bands"],
        "brands": sf["brands"],
        "hourly_abandonment": sf["hourly_abandonment"],
        "quality_daily": quality,
        "airflow_runs": runs,
        "snowpipe_files": snowpipe,
    }
    OUT.mkdir(exist_ok=True)
    for name, data in files.items():
        (OUT / f"{name}.json").write_text(json.dumps(data))
    print("wrote", len(files), "files to", OUT)


if __name__ == "__main__":
    main()
