import duckdb


def split_daily(src: str = "data/raw/*.csv", out: str = "data/landing") -> None:
    """Split the monthly CSVs into one Parquet folder per day (event_date=YYYY-MM-DD)."""
    duckdb.sql(f"""
        COPY (
            SELECT *, substr(event_time, 1, 10) AS event_date
            FROM read_csv('{src}', header = true, all_varchar = true)
        )
        TO '{out}'
        (FORMAT parquet, COMPRESSION zstd, PARTITION_BY (event_date), OVERWRITE_OR_IGNORE)
    """)

if __name__ == "__main__":
    split_daily()
