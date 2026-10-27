import duckdb

duckdb.sql("""
    COPY (
        SELECT *, substr(event_time, 1, 10) AS event_date
        FROM read_csv('data/raw/*.csv', header = true, all_varchar = true)
    )
    TO 'data/landing'
    (FORMAT parquet, COMPRESSION zstd, PARTITION_BY (event_date), OVERWRITE_OR_IGNORE)
""")