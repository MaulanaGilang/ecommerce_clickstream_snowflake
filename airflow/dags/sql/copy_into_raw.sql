-- Rendered by Airflow: {{ ds }} is the run's date, e.g. 2019-10-01.
-- Safe to retry: Snowflake skips files it has already loaded into this table.
COPY INTO CLICKSTREAM.RAW.EVENTS
FROM (
  SELECT $1:event_time::STRING,  $1:event_type::STRING,    $1:product_id::STRING,
         $1:category_id::STRING, $1:category_code::STRING, $1:brand::STRING,
         $1:price::STRING,       $1:user_id::STRING,       $1:user_session::STRING,
         TO_DATE(REGEXP_SUBSTR(METADATA$FILENAME, 'event_date=([0-9-]+)', 1, 1, 'e', 1)),
         METADATA$FILENAME, CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
  FROM @CLICKSTREAM.RAW.LANDING/event_date={{ ds }}/
);
