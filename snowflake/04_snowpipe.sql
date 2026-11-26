-- Step 8: near-real-time loading. Run as ACCOUNTADMIN only after Steps 1-7 work.
USE ROLE ACCOUNTADMIN;
USE SCHEMA CLICKSTREAM.RAW;

-- Same read-only IAM user key as the LANDING stage (the AWS free plan blocks the
-- storage-integration role; see 02_s3_integration.sql). Type the key in Snowsight
-- only. Never save it in this file or commit it.
CREATE STAGE IF NOT EXISTS LANDING_LIVE
    URL = 's3://gilang-clickstream-project2/live/'
    CREDENTIALS = (AWS_KEY_ID = '<reader key id>' AWS_SECRET_KEY = '<reader secret>')
    FILE_FORMAT = PARQUET_FMT;

-- Should return no error (and no files yet: live/ is empty until the replay starts)
LIST @LANDING_LIVE;

-- Separate table so the replay never mixes with the batch history
CREATE TABLE IF NOT EXISTS EVENTS_LIVE LIKE EVENTS;

CREATE PIPE IF NOT EXISTS EVENTS_PIPE AUTO_INGEST = TRUE AS
COPY INTO EVENTS_LIVE
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
        TO_DATE(LEFT($1:event_time::STRING, 10)),
        METADATA$FILENAME,
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM @LANDING_LIVE
);

-- Lets the live page and dashboard/export.py read the replay as PIPELINE_SVC
GRANT SELECT ON TABLE EVENTS_LIVE TO ROLE TRANSFORMER;
GRANT MONITOR ON PIPE EVENTS_PIPE TO ROLE TRANSFORMER;

-- Copy the notification_channel value (an SQS ARN) into the S3 event notification
SHOW PIPES;

-- After the demo:
-- ALTER PIPE CLICKSTREAM.RAW.EVENTS_PIPE SET PIPE_EXECUTION_PAUSED = TRUE;
