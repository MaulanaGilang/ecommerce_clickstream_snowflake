"""Step 8: replay one historical day into s3://<bucket>/live/ as one Parquet file per
minute of event time, so Snowpipe loads them as they arrive.

    python ingestion/replay_live.py 2019-11-30 10

Uses the uploader profile (AWS_PROFILE=uploader) and LANDING_BUCKET.
Stop it with Ctrl+C after 20-30 minutes; that's enough for the demo.
"""

import io
import os
import sys
import time

import boto3
import pandas as pd


def main(day: str, gap: float) -> None:
    df = pd.read_parquet(f"data/landing/event_date={day}")
    s3, bucket = boto3.client("s3"), os.environ["LANDING_BUCKET"]

    for minute, chunk in df.groupby(df.event_time.str[11:16]):  # "HH:MM"
        buf = io.BytesIO()
        chunk.to_parquet(buf, index=False)
        key = f"live/{day}/{minute.replace(':', '')}.parquet"
        s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
        print(minute, len(chunk), "events ->", key)
        time.sleep(gap)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 10)
