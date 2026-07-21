from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    'fifa_world_cup_pipeline',
    default_args=default_args,
    description='An end-to-end Medallion Architecture data pipeline for FIFA World Cup data',
    schedule_interval=None,  # Manual trigger for demonstration
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=['fifa', 'medallion', 'poc'],
) as dag:

    # Task 1: Ingestion
    ingest_task = BashOperator(
        task_id='ingest_to_bronze',
        bash_command='python /opt/airflow/scripts/ingest_to_bronze.py "{{ run_id }}"',
    )

    # Task 2: Validation
    validate_task = BashOperator(
        task_id='validate_bronze',
        bash_command='python /opt/airflow/scripts/validate_bronze.py "{{ run_id }}"',
    )

    # Task 3: Silver Transformations (SCD 1 & 2)
    silver_task = BashOperator(
        task_id='load_to_silver',
        bash_command='python /opt/airflow/scripts/load_to_silver.py "{{ run_id }}"',
    )

    # Task 4: Gold Analytics and Business Marts
    gold_task = BashOperator(
        task_id='load_to_gold',
        bash_command='python /opt/airflow/scripts/load_to_gold.py "{{ run_id }}"',
    )

    # Define execution order
    ingest_task >> validate_task >> silver_task >> gold_task
