# E-commerce Clickstream Pipeline

Idempotent daily ELT for 110M e-commerce events on **AWS S3, Snowflake, dbt and Airflow 3**.

[![ci](https://github.com/MaulanaGilang/ecommerce_clickstream_snowflake/actions/workflows/ci.yml/badge.svg)](https://github.com/MaulanaGilang/ecommerce_clickstream_snowflake/actions/workflows/ci.yml)
**Live dashboard:** _link coming after deploy_

**The question:** where do shoppers drop off between viewing, adding to cart and buying, and which categories, brands and price ranges convert best?

## Architecture

![architecture](docs/architecture.png)

```
CSV (14.7 GB) â”€splitâ”€â–¶ S3 landing/ (61 daily Parquet folders, ~2.5 GB)
                          â”‚  Airflow 3, one run per day:
                          â”œâ”€ upload_to_s3 â”€â–¶ copy_into_raw â”€â–¶ dbt_build
                          â–¼
              Snowflake RAW.EVENTS (all text) â”€â–¶ dbt staging â”€â–¶ dbt marts
                                                  (typed, flagged)   (sessions, funnel, products)
                                                                       â”‚
                                               dashboard/export.py â—€â”€â”€â”€â”˜ â”€â–¶ website (static)

Add-on: S3 live/ â”€(event notification)â”€â–¶ Snowpipe â”€â–¶ RAW.EVENTS_LIVE
```

## Results

> Replace the brackets with measured numbers before sharing.

| Metric | Value |
| --- | --- |
| Events loaded | 109,950,743 (42,448,764 Oct + 67,501,979 Nov) |
| Rows quarantined, by reason | [N] (`missing_session`: [N], `bad_price`: [N], ...) |
| Exact duplicates flagged | [N] ([X]%) |
| dbt models / tests | 8 models, 15 tests, all passing |
| 61-day backfill | [X] h [Y] min, [N] retries |
| Snowflake credits used | [X] of a 40-credit cap |
| Snowpipe median latency | [X] s |

Headline finding: _[one sentence with a number, from the dashboard]_

## How it works

**Daily partition contract.** The two monthly CSVs are split once into one Parquet folder per day (`landing/event_date=YYYY-MM-DD/`). Every Airflow run handles exactly one day, like a shop sending a new file each night. Airflow's catchup replays all 61 days in order (`max_active_runs=1`).

**Idempotency at every step.** Upload overwrites the same S3 keys. `COPY INTO` skips files Snowflake has already loaded (64-day load history). dbt models use `delete+insert` or `merge` keyed on the day or session. Any task can be retried, or a whole day cleared and rerun, without creating duplicates.

**Quarantine, not deletion.** RAW keeps every column as text, so a bad value can never fail the load. `stg_events_checked` types each row with `try_to_*`, then labels it with a `reject_reason` or `is_duplicate`. Clean rows flow on; the rest are counted in `quarantine_events`. A singular test (`assert_no_rows_lost`) fails the run if any RAW row is missing.

**Sessions that cross midnight.** `fct_sessions` finds sessions touched on the run date and rebuilds them from *all* their events before merging, so a session from 23:50 to 00:10 is updated, not split or half-counted.

## Data profile

| | Oct 2019 | Nov 2019 |
| --- | --- | --- |
| Rows | 42,448,764 | 67,501,979 |
| Views / carts / purchases (%) | 96.07 / 2.18 / 1.75 | 94.15 / 4.49 / 1.36 |
| Null `category_code` | 31.8% | 32.4% |
| Null `brand` | 14.4% | 13.7% |
| Exact duplicates | 30,220 | 100,530 |

Full profile: [docs/data_profile.md](docs/data_profile.md)

## Screenshots

- Airflow grid, 61 green runs: `docs/airflow_grid.png`
- dbt lineage: `docs/dbt_lineage.png`
- Quarantine counts by reason: `docs/quarantine.png`

## Run it yourself

Prerequisites: Python 3.12, Docker Desktop, AWS CLI, an AWS account and a Snowflake trial in the same region (here `ap-southeast-2`).

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# 1. data
kaggle datasets download -d mkechinov/ecommerce-behavior-data-from-multi-category-store -p data/raw --unzip
python ingestion/split_daily.py

# 2. Snowflake: run snowflake/01_setup.sql, 02_s3_integration.sql, 03_raw.sql in Snowsight

# 3. dbt
cd dbt_project/clickstream && dbt deps && dbt build --profiles-dir . --vars '{"run_date": "2019-10-01"}'

# 4. Airflow
cd airflow && copy .env.example .env   # then fill in the values
docker compose up airflow-init && docker compose up -d   # UI at http://localhost:8080
```

## Cost controls

| Item | Guardrail |
| --- | --- |
| Snowflake warehouse | XS, `AUTO_SUSPEND = 60`, resource monitor suspends at 40 credits |
| Snowpipe | Paused and S3 notification removed after the demo |
| S3 | Zero-spend budget alert; ~2.5 GB costs cents per month |
| Airflow | Local Docker, $0 (managed MWAA would be ~$358/month) |
| Dashboard | Static site reading exported JSON; never queries Snowflake |

## What I'd do next

- Terraform for the AWS and Snowflake setup
- A CI job that runs `dbt build` against a dev schema
- dbt snapshots for product price history
- Deploy the DAG to MWAA unchanged

## Data and licence

REES46 eCommerce behaviour data (multi-category store), via [Kaggle](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store). Used for education with attribution to the REES46 Marketing Platform.
