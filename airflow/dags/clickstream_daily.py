"""One run = one day of 2019 data: upload to S3, COPY into Snowflake RAW, dbt build."""

import os
from datetime import timedelta

import pendulum
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task


@dag(
    dag_id="clickstream_daily",
    start_date=pendulum.datetime(2019, 10, 1, tz="UTC"),
    end_date=pendulum.datetime(2019, 11, 30, tz="UTC"),
    schedule="@daily",
    catchup=True,  # Airflow 3 defaults to False; we want the 61-day replay
    max_active_runs=1,  # days run in order; fct_sessions depends on earlier days
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["clickstream"],
)
def clickstream_daily():
    @task
    def upload_to_s3(**context) -> int:
        from ingestion.upload_day import upload_day

        s3 = S3Hook(aws_conn_id="aws_default").get_conn()
        return upload_day(
            context["ds"],
            os.environ["LANDING_BUCKET"],
            root="/opt/airflow/data/landing",
            s3=s3,
        )

    copy_into_raw = SQLExecuteQueryOperator(
        task_id="copy_into_raw",
        conn_id="snowflake_default",
        sql="sql/copy_into_raw.sql",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            "cd /opt/airflow/dbt_project/clickstream && "
            "/home/airflow/dbt_venv/bin/dbt build --profiles-dir . "
            "--target-path /tmp/dbt_target --log-path /tmp/dbt_logs "
            "--vars '{\"run_date\": \"{{ ds }}\"}'"
        ),
    )

    upload_to_s3() >> copy_into_raw >> dbt_build


clickstream_daily()
