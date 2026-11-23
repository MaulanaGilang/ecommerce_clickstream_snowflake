# Dashboard

The public website for the clickstream pipeline. It's a scroll-driven data story that opens with the S3 → Snowflake RAW → dbt staging → dbt marts pipeline, then walks through the funnel, timing, categories, data quality, Airflow runs and the Snowpipe demo.

Built with Next.js 16 (App Router, fully static), Tailwind v4, Motion, Motion Primitives and d3-scale/d3-shape for chart geometry. All aggregation happens at build time in `lib/data.ts`; client charts receive only the small arrays they draw. The site never queries Snowflake, so it keeps working after the trial ends.

## Run

```bash
npm install
npm run dev
```

## Data

The site reads the JSON files in `data/`:

| File | Shape (one row per) | Snowflake source |
| --- | --- | --- |
| `totals.json` | headline numbers | row counts, dbt metadata, resource monitor |
| `funnel_daily.json` | day x category_l1 | `ANALYTICS_MARTS.FCT_FUNNEL_DAILY` |
| `categories.json` | category_l1 | `FCT_FUNNEL_DAILY` rolled up |
| `price_bands.json` | price band | `FCT_SESSIONS` + `DIM_PRODUCT` |
| `brands.json` | brand | `FCT_PRODUCT_PERFORMANCE` |
| `hourly_abandonment.json` | weekday x hour | `FCT_SESSIONS` |
| `quality_daily.json` | day | `STG_EVENTS_CHECKED` (clean / quarantined by `reject_reason` / duplicates) |
| `airflow_runs.json` | day | Airflow task durations: `upload_to_s3`, `copy_into_raw`, `dbt_build` |
| `snowpipe_files.json` | file in `live/` | `INFORMATION_SCHEMA.COPY_HISTORY` for `RAW.EVENTS_LIVE` |
| `meta.json` | - | `preview` flag, Snowpipe replay day |

Right now these are **preview data** from `scripts/make-preview-data.mjs`: seeded and synthetic, except the raw event totals, which are the dataset's published counts. The page shows a "Preview data" badge while `meta.json` has `"preview": true`.

To switch to real numbers, extend `dashboard/export.py` (pipeline Step 7) to write these same files as JSON with `"preview": false`, then rebuild. Run it before the Snowflake trial ends.

## Settings

Edit `lib/site.ts` for the repo URL, LinkedIn link and author name.
