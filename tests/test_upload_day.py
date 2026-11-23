from unittest.mock import MagicMock

import pytest

from ingestion.upload_day import upload_day


def test_uploads_each_file_with_partition_key(tmp_path):
    day_dir = tmp_path / "event_date=2019-10-01"
    day_dir.mkdir()
    (day_dir / "data_0.parquet").write_bytes(b"x")
    s3 = MagicMock()
    assert upload_day("2019-10-01", "bkt", root=str(tmp_path), s3=s3) == 1
    s3.upload_file.assert_called_once_with(
        str(day_dir / "data_0.parquet"), "bkt", "landing/event_date=2019-10-01/data_0.parquet")

def test_missing_day_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        upload_day("2019-10-02", "bkt", root=str(tmp_path), s3=MagicMock())