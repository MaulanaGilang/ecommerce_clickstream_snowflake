from airflow.models import DagBag


def test_dag_loads():
    bag = DagBag(dag_folder="/opt/airflow/dags", include_examples=False)
    assert not bag.import_errors
    dag = bag.get_dag("clickstream_daily")
    assert [t.task_id for t in dag.topological_sort()] == ["upload_to_s3", "copy_into_raw", "dbt_build"]