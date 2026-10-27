import duckdb

sql = open("notebooks/explore.sql", encoding="utf-8").read()

for stmt in sql.split(";"):
    if stmt.strip():
        print(duckdb.sql(stmt))