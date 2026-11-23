-- Step 3c + 3d: RAW table, first load, and the pipeline's service user.
-- Run as ACCOUNTADMIN; the pipeline itself never uses this role.
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE CLICKSTREAM_WH;
USE SCHEMA CLICKSTREAM.RAW;

-- Every column is text on purpose: a bad value can never fail the load.
CREATE TABLE IF NOT EXISTS EVENTS (
    event_time STRING,
    event_type STRING,
    product_id STRING,
    category_id STRING,
    category_code STRING,
    brand STRING,
    price STRING,
    user_id STRING,
    user_session STRING,
    event_date DATE,
    _source_file STRING,
    _loaded_at TIMESTAMP_NTZ
);

-- First load: one day by hand. Running it again loads 0 rows (Snowflake skips loaded files).
COPY INTO EVENTS
FROM (
    SELECT
        $1:event_time::STRING,
        $1:event_type::STRING,
        $1:product_id::STRING,
        $1:category_id::STRING,
        $1:category_code::STRING,
        $1:brand::STRING,
        $1:price::STRING,
        $1:user_id::STRING,
        $1:user_session::STRING,
        TO_DATE(REGEXP_SUBSTR(METADATA$FILENAME, 'event_date=([0-9-]+)', 1, 1, 'e', 1)),
        METADATA$FILENAME,
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM @LANDING/event_date=2019-10-01/
);

SELECT
    event_date,
    COUNT(*) AS n_rows
FROM EVENTS
GROUP BY event_date;

-- Least-privilege role for Airflow and dbt
CREATE ROLE IF NOT EXISTS TRANSFORMER;
GRANT USAGE ON WAREHOUSE CLICKSTREAM_WH TO ROLE TRANSFORMER;
GRANT USAGE, CREATE SCHEMA ON DATABASE CLICKSTREAM TO ROLE TRANSFORMER;
GRANT USAGE ON SCHEMA CLICKSTREAM.RAW TO ROLE TRANSFORMER;
GRANT SELECT, INSERT ON TABLE CLICKSTREAM.RAW.EVENTS TO ROLE TRANSFORMER;
GRANT USAGE ON STAGE CLICKSTREAM.RAW.LANDING TO ROLE TRANSFORMER;
GRANT USAGE ON FILE FORMAT CLICKSTREAM.RAW.PARQUET_FMT TO ROLE TRANSFORMER;
GRANT ROLE TRANSFORMER TO ROLE SYSADMIN;

-- Key-pair service user: paste the body of rsa_key.pub (without BEGIN/END lines).
CREATE USER IF NOT EXISTS PIPELINE_SVC
    TYPE = SERVICE
    DEFAULT_ROLE = TRANSFORMER
    DEFAULT_WAREHOUSE = CLICKSTREAM_WH
    RSA_PUBLIC_KEY = '<paste public key body here>';

GRANT ROLE TRANSFORMER TO USER PIPELINE_SVC;
