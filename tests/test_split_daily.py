import duckdb

from ingestion.split_daily import split_daily


def test_splits_into_one_folder_per_day(tmp_path):
    csv = tmp_path / "sample.csv"
    csv.write_text(
        "event_time,event_type,product_id\n"
        "2019-10-01 00:00:01 UTC,view,1\n"
        "2019-10-01 10:00:00 UTC,cart,1\n"
        "2019-10-01 23:59:59 UTC,purchase,1\n"
        "2019-10-02 00:00:00 UTC,view,2\n"
        "2019-10-02 12:00:00 UTC,view,3\n"
    )
    out = tmp_path / "landing"
    split_daily(str(csv), str(out))

    days = sorted(p.name for p in out.iterdir())
    assert days == ["event_date=2019-10-01", "event_date=2019-10-02"]
    count = lambda d: duckdb.sql(f"select count(*) from '{(out / d).as_posix()}/*.parquet'").fetchall()[0][0]
    assert count("event_date=2019-10-01") == 3
    assert count("event_date=2019-10-02") == 2
