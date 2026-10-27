import os, sys, pathlib
import boto3

def upload_day(day: str, bucket: str, root: str = "data/landing") -> int:
    s3 = boto3.client("s3")
    files = sorted(pathlib.Path(root, f"event_date={day}").glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no files for {day}")
    for f in files:
        s3.upload_file(str(f), bucket, f"landing/event_date={day}/{f.name}")
    return len(files)

if __name__ == "__main__":
    print(upload_day(sys.argv[1], os.environ["LANDING_BUCKET"]), "file(s) uploaded")