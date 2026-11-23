-- Step 3b: let Snowflake read the S3 bucket. Run as ACCOUNTADMIN.
USE ROLE ACCOUNTADMIN;

CREATE STORAGE INTEGRATION IF NOT EXISTS S3_INT
TYPE = EXTERNAL_STAGE
STORAGE_PROVIDER = 'S3'
ENABLED = TRUE
STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::974913402595:role/snowflake-s3-read'
STORAGE_ALLOWED_LOCATIONS = (
    's3://gilang-clickstream-project2/landing/',
    's3://gilang-clickstream-project2/live/'
);

-- Copy STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID from this output
-- into the trust policy of the snowflake-s3-read role in AWS IAM.
DESC INTEGRATION S3_INT;

-- Run the rest AFTER the IAM trust policy is updated.
CREATE FILE FORMAT IF NOT EXISTS CLICKSTREAM.RAW.PARQUET_FMT TYPE = PARQUET;

CREATE STAGE IF NOT EXISTS CLICKSTREAM.RAW.LANDING
    URL = 's3://gilang-clickstream-project2/landing/'
    STORAGE_INTEGRATION = S3_INT
    FILE_FORMAT = CLICKSTREAM.RAW.PARQUET_FMT;

-- Should list the daily Parquet files. An access error here = trust policy or bucket name.
LIST @CLICKSTREAM.RAW.LANDING;
