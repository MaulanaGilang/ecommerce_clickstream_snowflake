# Same version as the image tag in docker-compose.yaml
FROM apache/airflow:3.4.0

# AIRFLOW_VERSION is set inside the official image; pinning it stops pip upgrading Airflow
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" \
      apache-airflow-providers-amazon \
      apache-airflow-providers-snowflake

# dbt in its own venv so its dependencies can't clash with Airflow's
RUN python -m venv /home/airflow/dbt_venv && \
    /home/airflow/dbt_venv/bin/pip install --no-cache-dir "dbt-core>=1.10,<1.13" "dbt-snowflake>=1.10,<1.13"
